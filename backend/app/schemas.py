from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatCitation(BaseModel):
    doc_name: str
    chunk_id: str
    source_link: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: List[ChatCitation]


class ReportRequest(BaseModel):
    session_id: Optional[str] = None
    sections: List[str]
    include_summary: bool = False


class ReportResponse(BaseModel):
    report_id: str
    download_url: str
