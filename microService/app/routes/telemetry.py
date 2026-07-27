"""Health, telemetry and trace lookup."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config.settings import get_settings
from app.core.observability import get_telemetry_stats, get_trace

router = APIRouter(tags=["telemetry"])


@router.get("/")
def root():
    """Service identity and the configuration that shapes its answers."""
    s = get_settings()
    return {
        "message": "DocuMind AI — hybrid GraphRAG",
        "provider": s.llm_provider,
        "embed_model": s.embed_model,
        "rerank_mode": s.rerank_mode,
    }


@router.get("/health")
def health():
    """Liveness probe. Deliberately cheap — no model or network calls."""
    from pathlib import Path

    persist = Path(get_settings().persist_dir)
    return {
        "status": "ok",
        "persist_dir_writable": persist.exists() and persist.is_dir(),
    }


@router.get("/telemetry/stats")
def get_telemetry():
    """Aggregate request statistics from the trace store."""
    return {"success": True, "data": get_telemetry_stats()}


@router.get("/trace/{request_id}")
def get_trace_endpoint(request_id: str):
    trace = get_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="trace not found")
    return trace
