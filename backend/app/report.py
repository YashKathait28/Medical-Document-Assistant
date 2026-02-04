from __future__ import annotations

import uuid
from pathlib import Path
from typing import Dict, List

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .config import REPORT_DIR, TOP_K
from .llm import LLMClient
from .storage import get_doc
from .vectorstore import VectorStore


def collect_section_data(section: str, vectorstore: VectorStore, top_k: int) -> Dict[str, List[str]]:
    result = vectorstore.query(section, top_k)
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]

    filtered_docs: List[str] = []
    filtered_metas: List[Dict[str, str]] = []
    for text, meta in zip(documents, metadatas):
        doc_id = meta.get("doc_id")
        doc = get_doc(doc_id) if doc_id else None
        if doc and doc.get("source") == "upload":
            filtered_docs.append(text)
            filtered_metas.append(meta)

    return {"documents": filtered_docs, "metadatas": filtered_metas}


def build_report(sections: List[str], include_summary: bool) -> Dict[str, str]:
    report_id = uuid.uuid4().hex
    report_path = REPORT_DIR / f"report_{report_id}.pdf"

    vectorstore = VectorStore()
    llm = LLMClient()
    styles = getSampleStyleSheet()
    story = []
    collected_text: List[str] = []

    for section in sections:
        requested = llm.request_section_tool(section) if llm.available() else None
        section_title = (requested or {}).get("section") or section
        story.append(Paragraph(section_title, styles["Heading2"]))
        payload = collect_section_data(section_title, vectorstore, TOP_K)
        documents = payload["documents"]
        metadatas = payload["metadatas"]
        table_added = set()

        for text, meta in zip(documents, metadatas):
            doc_id = meta.get("doc_id")
            doc = get_doc(doc_id) if doc_id else None
            story.append(Paragraph(text, styles["BodyText"]))
            collected_text.append(text)
            if doc and doc.get("tables") and doc_id not in table_added:
                for table in doc["tables"]:
                    story.append(Paragraph("<pre>%s</pre>" % table, styles["Code"]))
                    collected_text.append(table)
                table_added.add(doc_id)
            story.append(Spacer(1, 12))

    if include_summary and llm.available():
        summary = llm.summarize("\n".join(collected_text))
        if summary:
            story.append(Paragraph("Summary", styles["Heading2"]))
            story.append(Paragraph(summary, styles["BodyText"]))

    SimpleDocTemplate(str(report_path), pagesize=letter).build(story)
    return {"report_id": report_id, "path": str(report_path)}
