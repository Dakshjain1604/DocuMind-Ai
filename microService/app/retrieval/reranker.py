"""Rerank step. Mode-driven via RAG_RERANK_MODE (app.config.settings.rerank_mode):
- "cross_encoder" (default): local sentence-transformers CrossEncoder — fast,
  free, no extra LLM round trip.
- "llm": legacy listwise LLM scorer (kept for back-compat / A-B comparison).
- "off": passthrough truncation.
"""
from __future__ import annotations
import asyncio
import json
from functools import lru_cache

from app.config.settings import get_settings
from app.core.embeddings import detect_device
from app.core.llm import get_llm
from app.core.observability import log_event
from app.prompts import RERANK_PROMPT


def is_enabled() -> bool:
    """True whenever rerank is doing anything (mode != off)."""
    return get_settings().rerank_mode != "off"


@lru_cache(maxsize=1)
def _get_cross_encoder(model_name: str, device: str):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device=device)


async def rerank(
    query: str,
    chunks: list[tuple[int, str]],
    *,
    top_k: int = 5,
    with_scores: bool = False,
    request_id: str | None = None,
    degraded_out: dict | None = None,
) -> list[int] | list[tuple[int, float]]:
    """chunks: [(chunk_id, text)]. Returns chunk_ids in score order, or
    (chunk_id, score) tuples when with_scores=True (used for tracing).
    degraded_out, if given, gets {"degraded": True} set when the rerank
    model/LLM call failed and fell back to passthrough truncation — without
    this, a broken rerank looks identical to a working one in the trace."""
    if not chunks:
        return []

    mode = get_settings().rerank_mode
    if mode == "cross_encoder":
        ranked, degraded = await _rerank_cross_encoder(query, chunks, top_k=top_k, request_id=request_id)
    elif mode == "llm":
        ranked, degraded = await _rerank_llm(query, chunks, top_k=top_k, request_id=request_id)
    else:
        ranked, degraded = [(cid, 0.0) for cid, _ in chunks[:top_k]], False

    if degraded_out is not None:
        degraded_out["degraded"] = degraded

    return ranked if with_scores else [cid for cid, _ in ranked]


async def _rerank_cross_encoder(
    query: str, chunks: list[tuple[int, str]], *, top_k: int, request_id: str | None = None
) -> tuple[list[tuple[int, float]], bool]:
    try:
        settings = get_settings()
        model = _get_cross_encoder(settings.rerank_model, detect_device(settings.embed_device))
        pairs = [[query, text] for _, text in chunks]
        scores = await asyncio.to_thread(model.predict, pairs)
        ranked = sorted(zip(chunks, scores), key=lambda kv: kv[1], reverse=True)
        return [(cid, float(score)) for (cid, _), score in ranked[:top_k]], False
    except Exception as e:
        log_event(
            "stage_err", stage="rerank", request_id=request_id, mode="cross_encoder",
            error_type=type(e).__name__, error=str(e),
        )
        return [(cid, 0.0) for cid, _ in chunks[:top_k]], True


async def _rerank_llm(
    query: str, chunks: list[tuple[int, str]], *, top_k: int, request_id: str | None = None
) -> tuple[list[tuple[int, float]], bool]:
    passages = "\n".join(f"[{i}] {text}" for i, (_, text) in enumerate(chunks))
    try:
        r = await get_llm().complete(
            role="rerank",
            messages=[{"role": "user", "content": RERANK_PROMPT.format(query=query, passages=passages)}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        scores = json.loads(r.content)
        if isinstance(scores, dict) and "scores" in scores:
            scores = scores["scores"]
        if not isinstance(scores, list) or len(scores) != len(chunks):
            log_event(
                "stage_err", stage="rerank", request_id=request_id, mode="llm",
                error_type="MalformedScores", error="scores missing or length mismatch",
            )
            return [(cid, 0.0) for cid, _ in chunks[:top_k]], True
        ranked = sorted(zip(chunks, scores), key=lambda kv: kv[1], reverse=True)
        return [(cid, float(score)) for (cid, _), score in ranked[:top_k]], False
    except Exception as e:
        log_event(
            "stage_err", stage="rerank", request_id=request_id, mode="llm",
            error_type=type(e).__name__, error=str(e),
        )
        return [(cid, 0.0) for cid, _ in chunks[:top_k]], True
