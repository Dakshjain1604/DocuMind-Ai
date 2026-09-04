"""Health, telemetry and trace lookup."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.config.settings import get_settings
from app.core.auth import get_current_user
from app.core.observability import get_telemetry_stats, get_trace
from app.routes.deps import require_owned

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


_PROVIDER_KEY_ATTR = {
    "openrouter": "openrouter_api_key",
    "groq": "groq_api_key",
    "nvidia": "nvidia_api_key",
}


@router.get("/health")
def health():
    """Liveness probe. Deliberately cheap — no model or network calls, just a
    filesystem check and reading already-loaded config, so misconfiguration
    (e.g. no API key for the selected provider) surfaces without adding
    latency or spending a request against the LLM provider."""
    from pathlib import Path

    s = get_settings()
    persist = Path(s.persist_dir)
    key_attr = _PROVIDER_KEY_ATTR.get(s.llm_provider)
    provider_key_configured = bool(key_attr and getattr(s, key_attr, None))
    return {
        "status": "ok" if provider_key_configured else "degraded",
        "persist_dir_writable": persist.exists() and persist.is_dir(),
        "llm_provider": s.llm_provider,
        "llm_provider_key_configured": provider_key_configured,
    }


@router.get("/telemetry/stats")
def get_telemetry():
    """Aggregate request statistics from the trace store."""
    return {"success": True, "data": get_telemetry_stats()}


@router.get("/trace/{request_id}")
async def get_trace_endpoint(request_id: str, user: dict = Depends(get_current_user)):
    """Full trace for one request. Auth-gated (like every /query trace it can
    expose an owned document's answer text) and additionally scoped to
    documents this user owns — a shared-feature flag must not leak another
    user's indexed content.

    /telemetry/stats stays public on purpose (the landing page renders it);
    it only exposes aggregates, never per-request text.
    """
    trace = get_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="trace not found")
    require_owned(trace["doc_hash"], user)
    return trace
