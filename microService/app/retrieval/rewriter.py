"""Query rewriter — turns a raw query into HyDE + keywords + entity hints
+ N alternate phrasings (multi-query retrieval), all from a single LLM call."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from app.config.settings import get_settings
from app.core.llm import LLMResult, get_llm
from app.core.observability import log_event
from app.prompts import REWRITE_PROMPT


@dataclass
class RewrittenQuery:
    hyde: str
    keywords: str
    entities_mentioned: list[str]
    query_variants: list[str] = field(default_factory=list)
    # Standalone, reference-resolved form of the query. Equal to the raw
    # query whenever there's no history (or nothing to resolve) — always
    # safe to use as "the query" for retrieval instead of the raw text.
    resolved_query: str = ""


def _format_history_block(history: list[dict] | None, *, max_turns: int = 6, max_chars: int = 500) -> str:
    if not history:
        return ""
    lines = []
    for turn in history[-max_turns:]:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        if role not in ("user", "assistant"):
            continue
        content = str(turn.get("content", "")).strip()[:max_chars]
        if content:
            lines.append(f"{role}: {content}")
    if not lines:
        return ""
    return (
        "\nRecent conversation (most recent last), for resolving references like "
        "\"it\"/\"that\"/\"those\" in the query below:\n" + "\n".join(lines) + "\n"
    )


async def _call_llm(query: str, *, n_variants: int, history_block: str) -> LLMResult:
    return await get_llm().complete(
        role="rewrite",
        messages=[
            {"role": "system", "content": "You output strict JSON only."},
            {
                "role": "user",
                "content": REWRITE_PROMPT.format(query=query, n_variants=n_variants, history_block=history_block),
            },
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )


async def rewrite_query(
    query: str,
    *,
    n_variants: int | None = None,
    history: list[dict] | None = None,
    request_id: str | None = None,
    degraded_out: dict | None = None,
) -> RewrittenQuery:
    """degraded_out, if given, gets {"degraded": True} set when rewrite fell
    back to the raw query — without this, a broken rewrite call looks
    identical to a successful one in the trace.

    history, when given, is expected already-sanitized (role/content only,
    capped) — this function only formats it into the prompt, it does not
    itself trust or validate caller-supplied content."""
    if n_variants is None:
        n_variants = get_settings().multi_query_n
    history_block = _format_history_block(history)
    try:
        result = await _call_llm(query, n_variants=n_variants, history_block=history_block)
        data = json.loads(result.content)
        variants = data.get("query_variants")
        if not isinstance(variants, list):
            variants = []
        return RewrittenQuery(
            hyde=data.get("hyde") or query,
            keywords=data.get("keywords") or query,
            entities_mentioned=list(data.get("entities_mentioned") or []),
            query_variants=[v for v in variants if isinstance(v, str) and v.strip()][:n_variants],
            resolved_query=data.get("resolved_query") or query,
        )
    except Exception as e:
        log_event("stage_err", stage="rewrite", request_id=request_id, error_type=type(e).__name__, error=str(e))
        if degraded_out is not None:
            degraded_out["degraded"] = True
        return RewrittenQuery(hyde=query, keywords=query, entities_mentioned=[], query_variants=[], resolved_query=query)
