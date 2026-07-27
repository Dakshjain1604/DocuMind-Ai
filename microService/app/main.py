"""FastAPI app — DocuMind AI hybrid GraphRAG."""
from __future__ import annotations
import asyncio
import json
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)
from pydantic import BaseModel

from app.config.settings import get_settings
from app.core.observability import get_trace, get_telemetry_stats, new_request_id
from app.core.streaming import sse_event, sse_error, sse_token
from app.indexing.pipeline import index_document
from app.indexing.store import (
    InvalidDocHash,
    load_artifacts,
    artifacts_exist,
    doc_hash_from_bytes,
    list_all_documents,
    delete_document_artifacts,
)
from app.retrieval.orchestrator import answer
from app.routes.generation import (
    generate_quiz_cards,
    summarize,
    summarize_stream,
    run_compliance_audit,
    generate_audio_briefing,
    generate_slide_deck,
)
from app.routes import masterclass

app = FastAPI()
app.include_router(masterclass.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(InvalidDocHash)
async def _invalid_doc_hash_handler(_request: Request, exc: InvalidDocHash) -> JSONResponse:
    """A malformed doc_hash is a client error, not a server fault."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})

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
            from pdf2image import convert_from_path
            import pytesseract
            import shutil

            if not shutil.which("tesseract") and Path("/opt/homebrew/bin/tesseract").exists():
                pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

            try:
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
                raise RuntimeError(f"OCR extraction failed for scanned PDF: {e}")
        return docs
    if file_type == ".txt" or file_type == ".md":
        return TextLoader(str(path)).load()
    return UnstructuredWordDocumentLoader(str(path)).load()


def _is_disconnect_error(e: Exception) -> bool:
    if isinstance(e, (BrokenPipeError, ConnectionResetError, asyncio.CancelledError)):
        return True
    msg = str(e).lower()
    return "broken pipe" in msg or "connection reset" in msg or "errno 32" in msg


async def with_heartbeat(generator, interval_s: float = 2.0):
    queue: asyncio.Queue = asyncio.Queue()

    async def producer():
        try:
            async for item in generator:
                await queue.put(item)
            await queue.put(None)
        except Exception as e:
            await queue.put(e)

    asyncio.create_task(producer())
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=interval_s)
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item
        except asyncio.TimeoutError:
            yield sse_event("ping", {"timestamp": time.time()})


@app.get("/documents")
def get_documents():
    """Retrieve all previously indexed documents from persistent storage library."""
    docs = list_all_documents()
    return {"success": True, "data": {"total": len(docs), "documents": docs}}


@app.delete("/documents/{doc_hash}")
def delete_document(doc_hash: str):
    """Delete an indexed document library entry."""
    success = delete_document_artifacts(doc_hash)
    if not success:
        raise HTTPException(status_code=404, detail="Document hash not found")
    return {"success": True, "message": f"Document {doc_hash} deleted successfully"}


@app.get("/telemetry/stats")
def get_telemetry():
    """Retrieve system observability and telemetry statistics."""
    stats = get_telemetry_stats()
    return {"success": True, "data": stats}


@app.post("/index")
async def post_index(
    files: list[UploadFile] = File(default=[]),
    file: UploadFile | None = File(default=None),
):
    upload_list: list[UploadFile] = []
    if files:
        upload_list.extend([f for f in files if f.filename])
    if file and file.filename and file not in upload_list:
        upload_list.append(file)
    if not upload_list:
        raise HTTPException(status_code=422, detail="No files uploaded")
    if len(upload_list) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files allowed per intake batch")

    combined_bytes = bytearray()
    all_documents = []

    for f_item in upload_list:
        content = await f_item.read()
        combined_bytes.extend(content)
        size_mb = len(content) / (1024 * 1024)
        max_mb = _max_mb()
        if size_mb > max_mb:
            raise HTTPException(status_code=413, detail=f"File {f_item.filename} too large ({size_mb:.1f}MB > {max_mb}MB)")

        suffix = Path(f_item.filename or "").suffix.lower()
        if suffix not in {".pdf", ".txt", ".md", ".docx", ".doc"}:
            raise HTTPException(status_code=415, detail=f"Unsupported type: {suffix} for file {f_item.filename}")

        # UploadFile.filename is attacker-controlled (Content-Disposition) and
        # Starlette does not sanitize it, so strip any directory component
        # before it reaches the filesystem. Keep the original for display.
        display_name = f_item.filename or "upload"
        safe_name = Path(display_name).name
        if not safe_name or safe_name in {".", ".."}:
            safe_name = "upload"
        save_path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_name}"
        if UPLOAD_DIR.resolve() not in save_path.resolve().parents:
            raise HTTPException(status_code=400, detail=f"Unsafe filename: {display_name}")
        async with aiofiles.open(save_path, "wb") as f_out:
            await f_out.write(content)

        try:
            docs = _load_documents(save_path, suffix)
            for d in docs:
                d.metadata["source_file"] = display_name
            all_documents.extend(docs)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not read document {f_item.filename}: {e}")

    if not all_documents or not any(d.page_content.strip() for d in all_documents):
        raise HTTPException(status_code=422, detail="No extractable text — check uploaded documents.")

    request_id = new_request_id()

    async def gen():
        try:
            async for ev in index_document(file_bytes=bytes(combined_bytes), documents=all_documents, request_id=request_id):
                yield sse_event(ev["event"], ev["data"])
        except Exception as e:
            if _is_disconnect_error(e):
                return
            yield sse_error(str(e))

    headers = {
        "X-Request-Id": request_id,
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(with_heartbeat(gen()), media_type="text/event-stream", headers=headers)


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
            if _is_disconnect_error(e):
                return
            yield sse_error(str(e), partial=True)

    headers = {
        "X-Request-Id": request_id,
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(with_heartbeat(gen()), media_type="text/event-stream", headers=headers)


@app.get("/trace/{request_id}")
def get_trace_endpoint(request_id: str):
    trace = get_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="trace not found")
    return trace


class StandardDocBody(BaseModel):
    doc_hash: str


@app.post("/summary")
async def post_summary(body: StandardDocBody):
    if not artifacts_exist(body.doc_hash):
        raise HTTPException(status_code=404, detail="doc_hash not indexed")
    request_id = new_request_id()

    async def gen():
        try:
            async for ev in summarize_stream(body.doc_hash, request_id=request_id):
                yield sse_event(ev["event"], ev["data"])
        except Exception as e:
            if _is_disconnect_error(e):
                return
            yield sse_error(str(e))

    headers = {
        "X-Request-Id": request_id,
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(with_heartbeat(gen()), media_type="text/event-stream", headers=headers)


@app.post("/quiz")
async def post_quiz(body: StandardDocBody, response: Response):
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await generate_quiz_cards(body.doc_hash, request_id=request_id)


@app.post("/compliance-audit")
async def post_compliance_audit(body: StandardDocBody, response: Response):
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await run_compliance_audit(body.doc_hash, request_id=request_id)


@app.post("/audio-briefing")
async def post_audio_briefing(body: StandardDocBody):
    if not artifacts_exist(body.doc_hash):
        raise HTTPException(status_code=404, detail="doc_hash not indexed")
    script = await generate_audio_briefing(body.doc_hash)
    return {"success": True, "data": {"script": script}}


@app.post("/slide-deck")
async def post_slide_deck(body: StandardDocBody, response: Response):
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await generate_slide_deck(body.doc_hash, request_id=request_id)
