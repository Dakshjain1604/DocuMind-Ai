"""Query rewriter — turns a raw query into HyDE + keywords + entity hints."""
from __future__ import annotations
import json
from dataclasses import dataclass
from app.core.llm import LLMResult, get_llm


REWRITE_PROMPT = """Given the user query, output JSON with three fields:
- "hyde": a 1-2 sentence hypothetical answer paragraph as if you knew the doc
- "keywords": 3-8 space-separated keywords for lexical search
- "entities_mentioned": list of named entities likely referenced (people, concepts, things)

Output JSON only.

Query: {query}
"""


@dataclass
class RewrittenQuery:
    hyde: str
    keywords: str
    entities_mentioned: list[str]


async def _call_llm(query: str) -> LLMResult:
    return await get_llm().complete(
        role="rewrite",
        messages=[
            {"role": "system", "content": "You output strict JSON only."},
            {"role": "user", "content": REWRITE_PROMPT.format(query=query)},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )


async def rewrite_query(query: str) -> RewrittenQuery:
    try:
        result = await _call_llm(query)
        data = json.loads(result.content)
        return RewrittenQuery(
            hyde=data.get("hyde") or query,
            keywords=data.get("keywords") or query,
            entities_mentioned=list(data.get("entities_mentioned") or []),
        )
    except Exception:
        return RewrittenQuery(hyde=query, keywords=query, entities_mentioned=[])
