# Medical Document Assistant

A simple end-to-end system that ingests medical documents, answers questions with citations, and generates PDF reports.

## Architecture (high level)
Diagram file: `diagrams/architecture.svg`

## Setup
**Python version:** Use Python 3.11 (required for dependency compatibility). Download: https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe

1. **Backend**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r backend/requirements.txt
   copy .env.example .env
   ```
   Fill in `OPENAI_API_KEY` in `.env` for full functionality.
   For a free-tier option, set `LLM_PROVIDER=groq` and add `GROQ_API_KEY`.
   Suggested model: `llama-3.1-8b-instant`.
   Key link: https://console.groq.com/keys

2. **Run**
   ```bash
   uvicorn backend.app.main:app --reload
   ```
   Open http://localhost:8000

## Docker (Bonus)
```bash
docker compose up --build
```
Then open http://localhost:8000

## Agentic Workflow (Bonus)
See `docs/workflows/agentic-report-workflow.md` for the report generation workflow.

## Notes
- Without an OpenAI key, the system falls back to extractive answers from top chunks.
- Groq free tier: create a key at https://console.groq.com/keys and set `LLM_PROVIDER=groq`.
- Google Drive file-level links require a service account (see `.env.example`).

## Tech Stack
- **Backend**: Python, FastAPI, Uvicorn
- **Vector search**: ChromaDB
- **Embeddings**: OpenAI `text-embedding-3-small` (fallback: `sentence-transformers`)
- **LLM**: OpenAI `gpt-3.5-turbo` with function calling for report sections
- **Parsing**: pdfplumber, python-docx, pandas/openpyxl, pytesseract (OCR)
- **Storage**: local file system + SQLite
- **Reports**: ReportLab PDF generation
- **Frontend**: Vanilla HTML/CSS/JS served from FastAPI

## OCR Dependency (Images)
Image OCR uses **Tesseract**. If you want image ingestion, install it and ensure `tesseract` is on PATH.
