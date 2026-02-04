from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional

from openai import OpenAI
from sentence_transformers import SentenceTransformer

from .config import (
    EMBEDDING_MODEL,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)


@dataclass
class LLMResult:
    answer: str


class EmbeddingClient:
    def __init__(self) -> None:
        self._openai = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self._local_model = None

    def embed(self, texts: List[str]) -> List[List[float]]:
        if self._openai:
            response = self._openai.embeddings.create(model=EMBEDDING_MODEL, input=texts)
            return [item.embedding for item in response.data]
        if self._local_model is None:
            self._local_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._local_model.encode(texts, convert_to_numpy=True).tolist()


class LLMClient:
    def __init__(self) -> None:
        self._client = None
        self._model = None

        try:
            if LLM_PROVIDER == "groq" and GROQ_API_KEY:
                self._client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
                self._model = GROQ_MODEL
            elif OPENAI_API_KEY:
                self._client = OpenAI(api_key=OPENAI_API_KEY)
                self._model = OPENAI_MODEL
        except Exception:
            self._client = None
            self._model = None

    def available(self) -> bool:
        return self._client is not None

    def model_name(self) -> str:
        return self._model or ""

    def answer_with_context(self, question: str, context: str, history: str = "") -> LLMResult:
        if not self._client:
            return LLMResult(answer="")
        history_block = f"Conversation so far:\n{history}\n\n" if history else ""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Answer only using the provided context. If the answer is not in the context, "
                            "say the information is not available. Use the conversation to understand the question, "
                            "but do not add facts not in the context."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"{history_block}Context:\n{context}\n\nQuestion: {question}",
                    },
                ],
                temperature=0.1,
            )
            return LLMResult(answer=response.choices[0].message.content.strip())
        except Exception:
            return LLMResult(answer="")

    def summarize(self, text: str) -> str:
        if not self._client:
            return ""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Summarize the following medical content briefly."},
                    {"role": "user", "content": text},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return ""

    def request_section_tool(self, section: str) -> Optional[Dict[str, Any]]:
        if not self._client:
            return None
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "collect_section_data",
                    "description": "Collect raw chunks and tables for a report section.",
                    "parameters": {
                        "type": "object",
                        "properties": {"section": {"type": "string"}},
                        "required": ["section"],
                    },
                },
            }
        ]
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": f"Prepare data for this report section and call the tool: {section}",
                    }
                ],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "collect_section_data"}},
                temperature=0,
            )
            message = response.choices[0].message
            if not message.tool_calls:
                return None
            args = json.loads(message.tool_calls[0].function.arguments)
            return args
        except Exception:
            return None
