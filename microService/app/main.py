"""FastAPI app — DocuMind AI hybrid GraphRAG."""
from __future__ import annotations
import json
import os
from pathlib import Path

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)

from app.core.streaming import sse_event, sse_error, sse_token
from app.indexing.pipeline import index_document
from app.indexing.store import load_artifacts, artifacts_exist, doc_hash_from_bytes
from app.retrieval.orchestrator import answer

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("./tmp/uploaded_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_MB = int(os.environ.get("RAG_MAX_FILE_MB", "25"))


@app.get("/")
def root():
    return {"message": "DocuMind AI — hybrid GraphRAG"}


def _load_documents(path: Path, file_type: str) -> list[Document]:
    if file_type == ".pdf":
        return PyPDFLoader(str(path)).load()
    if file_type == ".txt" or file_type == ".md":
        return TextLoader(str(path)).load()
    return UnstructuredWordDocumentLoader(str(path)).load()


@app.post("/index")
async def post_index(file: UploadFile = File(...)):
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_MB:
        raise HTTPException(status_code=413, detail=f"File too large ({size_mb:.1f}MB > {MAX_MB}MB)")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt", ".md", ".docx", ".doc"}:
        raise HTTPException(status_code=415, detail=f"Unsupported type: {suffix}")

    save_path = UPLOAD_DIR / (file.filename or "upload")
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(content)

    try:
        documents = _load_documents(save_path, suffix)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read document: {e}")

    if not documents or not any(d.page_content.strip() for d in documents):
        raise HTTPException(status_code=422, detail="No extractable text — is this a scanned PDF?")

    async def gen():
        try:
            async for ev in index_document(file_bytes=content, documents=documents):
                yield sse_event(ev["event"], ev["data"])
        except Exception as e:
            yield sse_error(str(e))

    return StreamingResponse(gen(), media_type="text/event-stream")
