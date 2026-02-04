from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .config import DOC_STORE, SESSION_DB


def load_docs() -> List[Dict[str, Any]]:
    if not DOC_STORE.exists():
        return []
    with DOC_STORE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_docs(docs: List[Dict[str, Any]]) -> None:
    with DOC_STORE.open("w", encoding="utf-8") as handle:
        json.dump(docs, handle, indent=2)


def add_doc(doc: Dict[str, Any]) -> None:
    docs = load_docs()
    docs.append(doc)
    save_docs(docs)


def update_doc(doc_id: str, updates: Dict[str, Any]) -> None:
    docs = load_docs()
    for doc in docs:
        if doc.get("id") == doc_id:
            doc.update(updates)
            break
    save_docs(docs)


def get_doc(doc_id: str) -> Dict[str, Any] | None:
    for doc in load_docs():
        if doc.get("id") == doc_id:
            return doc
    return None


def delete_doc(doc_id: str) -> Dict[str, Any] | None:
    docs = load_docs()
    remaining = []
    removed = None
    for doc in docs:
        if doc.get("id") == doc_id:
            removed = doc
        else:
            remaining.append(doc)
    save_docs(remaining)
    return removed


def clear_docs() -> int:
    docs = load_docs()
    save_docs([])
    return len(docs)


def ensure_session_db() -> None:
    conn = sqlite3.connect(SESSION_DB)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def create_session_id() -> str:
    return uuid.uuid4().hex


def add_message(session_id: str, role: str, content: str) -> None:
    ensure_session_db()
    conn = sqlite3.connect(SESSION_DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_history VALUES (?, ?, ?, ?, ?)",
        (uuid.uuid4().hex, session_id, role, content, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_history(session_id: str, limit: int) -> List[Dict[str, str]]:
    ensure_session_db()
    conn = sqlite3.connect(SESSION_DB)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT role, content FROM chat_history
        WHERE session_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (session_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    rows.reverse()
    return [{"role": role, "content": content} for role, content in rows]


def clear_history(session_id: str | None = None) -> int:
    ensure_session_db()
    conn = sqlite3.connect(SESSION_DB)
    cur = conn.cursor()
    if session_id:
        cur.execute("SELECT COUNT(*) FROM chat_history WHERE session_id = ?", (session_id,))
        count = cur.fetchone()[0]
        cur.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
    else:
        cur.execute("SELECT COUNT(*) FROM chat_history")
        count = cur.fetchone()[0]
        cur.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()
    return count
