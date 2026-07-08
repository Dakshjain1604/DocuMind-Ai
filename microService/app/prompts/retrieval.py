"""Prompts used during /query's retrieval stages — query rewriting
(HyDE + keywords + entities + multi-query variants) and LLM reranking
("llm" rerank mode only; "cross_encoder" mode doesn't call an LLM)."""
from __future__ import annotations


REWRITE_PROMPT = """Given the user query, output JSON with four fields:
- "hyde": a 1-2 sentence hypothetical answer paragraph as if you knew the doc
- "keywords": 3-8 space-separated keywords for lexical search
- "entities_mentioned": list of named entities likely referenced (people, concepts, things)
- "query_variants": a list of {n_variants} alternate phrasings of the user's question —
  same meaning, different wording/angle, to broaden retrieval recall (multi-query retrieval)

Output JSON only.

Query: {query}
"""


RERANK_PROMPT = """Score each passage from 0 (irrelevant) to 10 (perfectly answers the query).
Return JSON array of scores in the same order. JSON only.

Query: {query}

Passages:
{passages}
"""
