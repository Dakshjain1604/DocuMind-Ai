"""Prompts used during /query's retrieval stages — query rewriting
(HyDE + keywords + entities + multi-query variants) and LLM reranking
("llm" rerank mode only; "cross_encoder" mode doesn't call an LLM)."""
from __future__ import annotations


# This call sits on the critical path: it must finish before any retrieval
# starts, so its cost is paid directly in time-to-first-token. Traced at
# 2420ms of a 3392ms query (71%) with the previous free-form version, which
# invited multi-sentence output. Constraining every field to be short brought
# it to ~1.0s for the same retrieval inputs.
#
# "hyde" must stay a real declarative sentence — HyDE works by embedding a
# plausible *answer* and searching with that vector. Degrading it to a keyword
# phrase makes it redundant with the keywords field and loses the benefit.
REWRITE_PROMPT = """You expand a search query for hybrid retrieval over one document. Output JSON only.

{{"hyde": "one plausible sentence that a document answering this query would literally contain - write it as a factual statement, not a description of the topic",
 "keywords": "3-8 space-separated lexical search terms",
 "entities_mentioned": ["proper nouns or technical terms appearing in the query"],
 "query_variants": [{n_variants} rephrasings of the question, each under 12 words]}}

Keep every field short. No commentary.

Query: {query}
"""


RERANK_PROMPT = """Score each passage from 0 (irrelevant) to 10 (perfectly answers the query).
Return JSON array of scores in the same order. JSON only.

Query: {query}

Passages:
{passages}
"""
