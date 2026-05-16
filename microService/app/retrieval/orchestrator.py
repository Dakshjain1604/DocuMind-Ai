"""Query orchestrator — public answer() entry point.

Fans out vector + BM25 + graph in parallel, fuses with RRF, optionally
reranks, streams answer with citation prompting.
"""
from __future__ import annotations
import asyncio
import os
import pickle
from functools import lru_cache
from typing import AsyncIterator

from langchain_chroma import Chroma
from app.core.cache import get_cache
from app.core.embeddings import get_embeddings
from app.core.llm import get_llm
from app.indexing.store import load_artifacts, artifacts_exist
from app.retrieval.bm25 import BM25Index
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.graph import GraphIndex
from app.retrieval.reranker import rerank, is_enabled as rerank_enabled
from app.retrieval.rewriter import rewrite_query
from app.retrieval.vector import vector_search


ANSWER_PROMPT = """Answer the question using the numbered passages below.

RULES:
- For every factual claim, cite the passage like [1], [2]. Multiple ok: [1,3].
- If the answer is not in the passages, say "I couldn't find that in the document."
- Be concise. Don't repeat the question.

Passages:
{context}

Question: {question}

Answer:"""


def _load_artifacts_cached(doc_hash: str) -> dict:
    cache = get_cache()
    cached = cache.get(doc_hash)
    if cached is not None:
        return cached
    if not artifacts_exist(doc_hash):
        raise FileNotFoundError(f"No indexed artifacts for doc_hash={doc_hash}")
    loaded = load_artifacts(doc_hash)
    chroma = Chroma(persist_directory=loaded["chroma_dir"], embedding_function=get_embeddings())
    bm25 = BM25Index.load(loaded["bm25_path"])
    graph = GraphIndex(loaded["graph"])
    chunks_by_id = _chunks_from_chroma(chroma)
    entry = {**loaded, "chroma": chroma, "bm25": bm25, "graph_idx": graph, "chunks_by_id": chunks_by_id}
    cache.put(doc_hash, entry)
    return entry


def _chunks_from_chroma(chroma: Chroma) -> dict[int, str]:
    res = chroma.get(include=["documents", "metadatas"])
    out: dict[int, str] = {}
    for text, meta in zip(res.get("documents", []), res.get("metadatas", [])):
        cid = meta.get("chunk_id") if meta else None
        if cid is None:
            continue
        out[int(cid)] = text
    return out


def _chunks_by_id(loaded: dict) -> dict[int, str]:
    return loaded["chunks_by_id"]


def _vector_search_chunks(chroma: Chroma, query: str, top_k: int) -> list[int]:
    return [cid for cid, _ in vector_search(chroma, query, top_k=top_k)]


def _bm25_search_chunks(bm25: BM25Index, keywords: str, top_k: int) -> list[int]:
    return [cid for cid, _ in bm25.search(keywords, top_k=top_k)]


def _graph_search_chunks(g: GraphIndex, entities: list[str]) -> list[int]:
    matched = g.match_entities(entities)
    return g.traverse_chunks(matched, hops=2) if matched else []


def _build_context(chunks_by_id: dict[int, str], chunk_ids: list[int]) -> tuple[str, list[dict]]:
    citations = []
    parts = []
    for i, cid in enumerate(chunk_ids, start=1):
        text = chunks_by_id.get(cid, "")
        if not text:
            continue
        parts.append(f"[{i}] {text}")
        citations.append({"n": i, "chunk_id": cid})
    return "\n\n".join(parts), citations


async def answer(
    *,
    doc_hash: str,
    query: str,
    history: list[dict[str, str]] | None = None,
) -> AsyncIterator[dict]:
    loaded = _load_artifacts_cached(doc_hash)
    chroma, bm25, graph_idx = loaded["chroma"], loaded["bm25"], loaded["graph_idx"]
    chunks_by_id = _chunks_by_id(loaded)

    rq = await rewrite_query(query)

    async def safe(fn):
        try:
            return await asyncio.to_thread(fn)
        except Exception:
            return []

    vec_ids, bm25_ids, graph_ids = await asyncio.gather(
        safe(lambda: _vector_search_chunks(chroma, rq.hyde, 10)),
        safe(lambda: _bm25_search_chunks(bm25, rq.keywords, 10)),
        safe(lambda: _graph_search_chunks(graph_idx, rq.entities_mentioned)),
    )

    fused = reciprocal_rank_fusion([vec_ids, bm25_ids, graph_ids], k=60, top_k=15)

    if rerank_enabled():
        pairs = [(cid, chunks_by_id.get(cid, "")) for cid in fused]
        fused = await rerank(query, pairs, top_k=5)
    else:
        fused = fused[:5]

    context, citations = _build_context(chunks_by_id, fused)
    yield {"event": "context", "data": {"citations": citations}}

    messages = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": ANSWER_PROMPT.format(context=context, question=query)})

    try:
        async for delta, _model in get_llm().stream(role="answer", messages=messages, temperature=0.2):
            yield {"event": "token", "data": {"text": delta}}
        yield {"event": "done", "data": {}}
    except Exception as e:
        yield {"event": "error", "data": {"message": str(e), "partial": True}}
