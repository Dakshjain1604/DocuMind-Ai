"""FastAPI app — DocuMind AI hybrid GraphRAG."""
from __future__ import annotations
import json
from pathlib import Path

from dotenv import load_dotenv

# Load microService/.env BEFORE any module that reads os.environ at import time
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)
from pydantic import BaseModel

from app.config.settings import get_settings
from app.core.observability import get_trace, new_request_id
from app.core.streaming import sse_event, sse_error, sse_token
from app.indexing.pipeline import index_document
from app.indexing.store import load_artifacts, artifacts_exist, doc_hash_from_bytes
from app.retrieval.orchestrator import answer
from app.routes.generation import generate_quiz_cards, summarize

app = FastAPI()
# All calls to this service come from the Next.js server (server-to-server
# proxy in frontend/app/api/rag/*/route.ts), never directly from the browser —
# no cookies/auth headers cross this boundary, so allow_credentials isn't
# needed. ["*"] + allow_credentials=True is also an invalid combination per
# the CORS spec, which is why it's dropped here rather than kept "for safety".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("./tmp/uploaded_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _max_mb() -> int:
    return get_settings().max_file_mb


@app.get("/")
def root():
    return {"message": "DocuMind AI — hybrid GraphRAG"}


def _load_documents(path: Path, file_type: str) -> list[Document]:
    if file_type == ".pdf":
        docs = PyPDFLoader(str(path)).load()
        if not docs or not any(d.page_content.strip() for d in docs):
            # Scanned PDF detected: convert PDF pages to images and run Tesseract OCR
            from pdf2image import convert_from_path
            import pytesseract
            import shutil

            # Direct fallback for macOS M1/M2/M3 Homebrew path
            if not shutil.which("tesseract") and Path("/opt/homebrew/bin/tesseract").exists():
                pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

            try:
                # Dynamically query available tesseract languages to see if Hindi (hin) is installed
                langs = "eng"
                try:
                    available = pytesseract.get_languages(config="")
                    if "hin" in available:
                        langs = "eng+hin"
                except Exception:
                    pass

                images = convert_from_path(str(path))
                ocr_docs = []
                for i, img in enumerate(images):
                    text = pytesseract.image_to_string(img, lang=langs)
                    if text.strip():
                        ocr_docs.append(
                            Document(
                                page_content=text,
                                metadata={"source": str(path), "page": i + 1}
                            )
                        )
                return ocr_docs
            except Exception as e:
                # Log or propagate OCR failures
                raise RuntimeError(f"OCR extraction failed for scanned PDF: {e}")
        return docs
    if file_type == ".txt" or file_type == ".md":
        return TextLoader(str(path)).load()
    return UnstructuredWordDocumentLoader(str(path)).load()


@app.post("/index")
async def post_index(file: UploadFile = File(...)):
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    max_mb = _max_mb()
    if size_mb > max_mb:
        raise HTTPException(status_code=413, detail=f"File too large ({size_mb:.1f}MB > {max_mb}MB)")

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

    request_id = new_request_id()

    async def gen():
        try:
            async for ev in index_document(file_bytes=content, documents=documents, request_id=request_id):
                yield sse_event(ev["event"], ev["data"])
        except Exception as e:
            yield sse_error(str(e))

    return StreamingResponse(
        gen(), media_type="text/event-stream", headers={"X-Request-Id": request_id}
    )


@app.get("/graph/{doc_hash}")
def get_graph(doc_hash: str):
    if not artifacts_exist(doc_hash):
        raise HTTPException(status_code=404, detail="doc_hash not indexed")
    loaded = load_artifacts(doc_hash)
    return loaded["graph"]


class QueryBody(BaseModel):
    doc_hash: str
    query: str
    history: list[dict] | None = None


@app.post("/query")
async def post_query(body: QueryBody):
    if not artifacts_exist(body.doc_hash):
        raise HTTPException(status_code=404, detail="doc_hash not indexed")

    request_id = new_request_id()

    async def gen():
        try:
            async for ev in answer(
                doc_hash=body.doc_hash, query=body.query, history=body.history, request_id=request_id
            ):
                yield sse_event(ev["event"], ev["data"])
        except Exception as e:
            yield sse_error(str(e), partial=True)

    return StreamingResponse(
        gen(), media_type="text/event-stream", headers={"X-Request-Id": request_id}
    )


@app.get("/trace/{request_id}")
def get_trace_endpoint(request_id: str):
    trace = get_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="trace not found")
    return trace


class SummaryBody(BaseModel):
    doc_hash: str


@app.post("/summary")
async def post_summary(body: SummaryBody, response: Response):
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    try:
        text = await summarize(body.doc_hash, request_id=request_id)
        return {"summary": text}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="doc_hash not indexed")


class QuizBody(BaseModel):
    doc_hash: str


@app.post("/quiz")
async def post_quiz(body: QuizBody, response: Response):
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await generate_quiz_cards(body.doc_hash, request_id=request_id)
