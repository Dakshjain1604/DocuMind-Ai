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


async def _call_llm(query: str, *, n_variants: int) -> LLMResult:
    return await get_llm().complete(
        role="rewrite",
        messages=[
            {"role": "system", "content": "You output strict JSON only."},
            {"role": "user", "content": REWRITE_PROMPT.format(query=query, n_variants=n_variants)},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )


async def rewrite_query(
    query: str,
    *,
    n_variants: int | None = None,
    request_id: str | None = None,
    degraded_out: dict | None = None,
) -> RewrittenQuery:
    """degraded_out, if given, gets {"degraded": True} set when rewrite fell
    back to the raw query — without this, a broken rewrite call looks
    identical to a successful one in the trace."""
    if n_variants is None:
        n_variants = get_settings().multi_query_n
    try:
        result = await _call_llm(query, n_variants=n_variants)
        data = json.loads(result.content)
        variants = data.get("query_variants")
        if not isinstance(variants, list):
            variants = []
        return RewrittenQuery(
            hyde=data.get("hyde") or query,
            keywords=data.get("keywords") or query,
            entities_mentioned=list(data.get("entities_mentioned") or []),
            query_variants=[v for v in variants if isinstance(v, str) and v.strip()][:n_variants],
        )
    except Exception as e:
        log_event("stage_err", stage="rewrite", request_id=request_id, error_type=type(e).__name__, error=str(e))
        if degraded_out is not None:
            degraded_out["degraded"] = True
        return RewrittenQuery(hyde=query, keywords=query, entities_mentioned=[], query_variants=[])
