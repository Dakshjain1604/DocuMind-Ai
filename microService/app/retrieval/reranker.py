"""Optional rerank step. Env-flagged via RAG_ENABLE_RERANK."""
from __future__ import annotations
import json
import os
from app.core.llm import get_llm


RERANK_PROMPT = """Score each passage from 0 (irrelevant) to 10 (perfectly answers the query).
Return JSON array of scores in the same order. JSON only.

Query: {query}

Passages:
{passages}
"""


def is_enabled() -> bool:
    return os.environ.get("RAG_ENABLE_RERANK", "false").lower() == "true"


async def rerank(query: str, chunks: list[tuple[int, str]], *, top_k: int = 5) -> list[int]:
    """chunks: [(chunk_id, text)]. Returns chunk_ids in score order."""
    if not chunks:
        return []
    if not is_enabled():
        return [c[0] for c in chunks[:top_k]]

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
            return [c[0] for c in chunks[:top_k]]
        ranked = sorted(zip(chunks, scores), key=lambda kv: kv[1], reverse=True)
        return [c[0][0] for c in ranked[:top_k]]
    except Exception:
        return [c[0] for c in chunks[:top_k]]
