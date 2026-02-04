from __future__ import annotations

from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings

from .config import CHROMA_DIR
from .llm import EmbeddingClient


class VectorStore:
    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection("medical_docs")
        self._embedder = EmbeddingClient()

    def add_chunks(self, chunks: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        if not chunks:
            return
        embeddings = self._embedder.embed(chunks)
        self._collection.add(documents=chunks, metadatas=metadatas, ids=ids, embeddings=embeddings)

    def delete_doc(self, doc_id: str) -> None:
        if self._collection.count() == 0:
            return
        self._collection.delete(where={"doc_id": doc_id})

    def reset(self) -> None:
        try:
            self._client.delete_collection("medical_docs")
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection("medical_docs")

    def query(self, text: str, top_k: int) -> Dict[str, Any]:
        if self._collection.count() == 0:
            return {"documents": [[]], "metadatas": [[]], "ids": [[]]}
        embedding = self._embedder.embed([text])[0]
        return self._collection.query(query_embeddings=[embedding], n_results=top_k)
