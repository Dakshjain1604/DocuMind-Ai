"""Document library: list, delete, index, and graph retrieval."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.config.settings import get_settings
from app.core.auth import get_current_user, get_owner_id
from app.core.observability import new_request_id
from app.core.rate_limit import index_limit, limiter
from app.core.sse import sse_stream_response
from app.indexing.pipeline import index_document
from app.indexing.store import (
    artifacts_exist,
    delete_document_artifacts,
    list_all_documents,
    load_artifacts,
)
from app.routes.deps import require_owned
from app.services.ingest import UnsafeFilename, cleanup_upload, load_documents, save_upload

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])


@router.get("/documents")
def get_documents(user: dict = Depends(get_current_user)):
    """List documents visible to the caller: their own uploads plus any
    legacy/shared document that predates per-user ownership (no owners
    recorded at all)."""
    user_id = get_owner_id(user)
    docs = [
        {k: v for k, v in d.items() if k != "owners"}
        for d in list_all_documents()
        if not d.get("owners") or user_id in d["owners"]
    ]
    return {"success": True, "data": {"total": len(docs), "documents": docs}}


@router.delete("/documents/{doc_hash}")
def delete_document(doc_hash: str, user: dict = Depends(get_current_user)):
    """Delete one document's artifacts. Invalid hashes are rejected in store.doc_dir."""
    require_owned(doc_hash, user)
    if not delete_document_artifacts(doc_hash):
        raise HTTPException(status_code=404, detail="Document hash not found")
    return {"success": True, "message": f"Document {doc_hash} deleted successfully"}


@router.get("/graph/{doc_hash}")
def get_graph(doc_hash: str, user: dict = Depends(get_current_user)):
    if not artifacts_exist(doc_hash):
        raise HTTPException(status_code=404, detail="doc_hash not indexed")
    require_owned(doc_hash, user)
    return load_artifacts(doc_hash)["graph"]


@router.post("/index")
@limiter.limit(index_limit)
async def post_index(
    request: Request,
    files: list[UploadFile] = File(default=[]),
    file: UploadFile | None = File(default=None),
    user: dict = Depends(get_current_user),
):
    """Accept a batch of documents and stream the indexing pipeline's progress."""
    settings = get_settings()

    upload_list: list[UploadFile] = [f for f in files if f.filename] if files else []
    if file and file.filename and file not in upload_list:
        upload_list.append(file)
    if not upload_list:
        raise HTTPException(status_code=422, detail="No files uploaded")
    if len(upload_list) > settings.max_files_per_batch:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_files_per_batch} files allowed per intake batch",
        )

    combined_bytes = bytearray()
    all_documents = []
    max_mb = settings.max_file_mb

    for f_item in upload_list:
        content = await f_item.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > max_mb:
            raise HTTPException(
                status_code=413,
                detail=f"File {f_item.filename} too large ({size_mb:.1f}MB > {max_mb}MB)",
            )

        suffix = (f_item.filename or "").lower()
        suffix = suffix[suffix.rfind("."):] if "." in suffix else ""
        if suffix not in settings.allowed_extensions:
            raise HTTPException(
                status_code=415, detail=f"Unsupported type: {suffix} for file {f_item.filename}"
            )

        combined_bytes.extend(content)
        try:
            saved = save_upload(content, f_item.filename)
        except UnsafeFilename as e:
            raise HTTPException(status_code=400, detail=str(e))

        try:
            # Parsing (and OCR in particular) is CPU-bound and synchronous;
            # awaiting it inline would stall the event loop for every other
            # in-flight request.
            docs = await run_in_threadpool(load_documents, saved.path, suffix)
            for d in docs:
                d.metadata["source_file"] = saved.display_name
            all_documents.extend(docs)
        except Exception as e:
            raise HTTPException(
                status_code=422, detail=f"Could not read document {f_item.filename}: {e}"
            )
        finally:
            cleanup_upload(saved.path)

    if not all_documents or not any(d.page_content.strip() for d in all_documents):
        raise HTTPException(status_code=422, detail="No extractable text — check uploaded documents.")

    request_id = new_request_id()
    payload = bytes(combined_bytes)
    owner = get_owner_id(user)

    def events():
        return index_document(
            file_bytes=payload, documents=all_documents, request_id=request_id, owner=owner
        )

    return sse_stream_response(events, request_id=request_id)
