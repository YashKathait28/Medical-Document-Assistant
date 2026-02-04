from __future__ import annotations

import uuid
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import LLM_PROVIDER, MAX_HISTORY, REPORT_DIR, TOP_K, UPLOAD_DIR, ensure_dirs
from .drive import download_public_folder, download_with_service_account
from .ingest import build_chunk_payload, ingest_file
from .llm import LLMClient
from .schemas import ChatRequest, ChatResponse, ReportRequest, ReportResponse
from .storage import (
    add_message,
    clear_docs,
    clear_history,
    create_session_id,
    delete_doc,
    get_doc,
    get_history,
    load_docs,
)
from .vectorstore import VectorStore


app = FastAPI(title="Medical Document Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    ensure_dirs()


app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/")
async def root() -> HTMLResponse:
    index_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/health")
async def health() -> dict:
    llm = LLMClient()
    return {
        "status": "ok",
        "llm_enabled": llm.available(),
        "llm_provider": LLM_PROVIDER,
        "llm_model": llm.model_name(),
    }


@app.get("/documents")
async def list_docs() -> dict:
    return {"documents": load_docs()}


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str) -> dict:
    vectorstore = VectorStore()
    removed = delete_doc(doc_id)
    if not removed:
        return {"error": "Document not found"}
    path = removed.get("path")
    if path:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass
    vectorstore.delete_doc(doc_id)
    return {"deleted": removed}


@app.post("/documents/clear")
async def clear_documents() -> dict:
    vectorstore = VectorStore()
    docs = load_docs()
    for doc in docs:
        path = doc.get("path")
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
    removed = clear_docs()
    vectorstore.reset()
    return {"cleared": removed}


@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)) -> dict:
    vectorstore = VectorStore()
    responses = []
    for file in files:
        content = await file.read()
        meta = ingest_file(content, file.filename, source="upload")
        doc = get_doc(meta["id"])
        if doc:
            chunks = meta.get("chunk_text", [])
            chunk_docs, metadatas, ids = build_chunk_payload(
                doc_id=doc["id"],
                doc_name=doc["name"],
                source_link=doc.get("source_link"),
                chunks=chunks,
            )
            vectorstore.add_chunks(chunk_docs, metadatas, ids)
        responses.append(meta)
    return {"uploaded": responses}


@app.post("/ingest/drive")
async def ingest_drive() -> dict:
    vectorstore = VectorStore()
    downloaded = download_with_service_account(UPLOAD_DIR) or download_public_folder(UPLOAD_DIR)
    ingested = []
    for item in downloaded:
        path = Path(item["path"])
        if path.is_dir():
            continue
        content = path.read_bytes()
        meta = ingest_file(content, path.name, source="drive", source_link=item.get("source_link"))
        doc = get_doc(meta["id"])
        if doc:
            chunks = meta.get("chunk_text", [])
            chunk_docs, metadatas, ids = build_chunk_payload(doc["id"], doc["name"], doc.get("source_link"), chunks)
            vectorstore.add_chunks(chunk_docs, metadatas, ids)
        ingested.append(meta)
    return {"ingested": ingested}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or create_session_id()
    vectorstore = VectorStore()
    llm = LLMClient()

    add_message(session_id, "user", request.message)

    results = vectorstore.query(request.message, TOP_K)
    docs = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    history = get_history(session_id, MAX_HISTORY)
    history_text = "\n".join([f"{item['role']}: {item['content']}" for item in history])

    citations = []
    context = "\n\n".join(docs)

    if not docs:
        answer = "The information is not available in the provided documents."
    else:
        if llm.available():
            answer = llm.answer_with_context(request.message, context, history_text).answer
            if not answer:
                answer = "The information is not available in the provided documents."
        else:
            answer = docs[0]

    for meta in metadatas:
        citations.append(
            {
                "doc_name": meta.get("doc_name", ""),
                "chunk_id": meta.get("chunk_id", ""),
                "source_link": meta.get("source_link") or None,
            }
        )

    add_message(session_id, "assistant", answer)
    return ChatResponse(session_id=session_id, answer=answer, citations=citations)


@app.post("/chat/clear")
async def clear_chat(session_id: str | None = None) -> dict:
    cleared = clear_history(session_id)
    return {"cleared": cleared, "session_id": session_id}


@app.post("/report", response_model=ReportResponse)
async def report(request: ReportRequest) -> ReportResponse:
    from .report import build_report

    result = build_report(request.sections, request.include_summary)
    download_url = f"/reports/{result['report_id']}"
    return ReportResponse(report_id=result["report_id"], download_url=download_url)


@app.get("/reports/{report_id}")
async def download_report(report_id: str):
    report_path = REPORT_DIR / f"report_{report_id}.pdf"
    if not report_path.exists():
        return {"error": "Report not found"}
    return FileResponse(report_path, media_type="application/pdf", filename=report_path.name)
