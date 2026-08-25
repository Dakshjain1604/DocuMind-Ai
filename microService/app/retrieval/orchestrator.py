"""Query orchestrator — public answer() entry point.

Fans out vector + BM25 + graph in parallel, fuses with RRF, optionally
reranks, streams answer with citation prompting.
"""
from __future__ import annotations
import asyncio
import json
import os
import pickle
import time
from functools import lru_cache
from pathlib import Path
from typing import AsyncIterator

from langchain_chroma import Chroma
from app.config.settings import get_settings
from app.core.cache import get_cache, get_disk_cache
from app.core.embeddings import get_embeddings
from app.core.llm import get_llm
from app.core.observability import (
    count_tokens,
    estimate_cost_usd,
    log_event,
    new_request_id,
    record_trace,
    timed_stage,
)
from app.indexing.store import load_artifacts, artifacts_exist
from app.retrieval.search import BM25Index, GraphIndex, reciprocal_rank_fusion, vector_search
from app.retrieval.reranker import rerank
from app.retrieval.rewriter import rewrite_query
from app.prompts import ANSWER_SYSTEM_PROMPT, ANSWER_USER_PROMPT


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
    chunks_by_id, parent_id_by_chunk = _chunks_from_chroma(chroma)
    parents_by_id = _load_parents(loaded.get("parents_path"))
    entry = {
        **loaded,
        "chroma": chroma,
        "bm25": bm25,
        "graph_idx": graph,
        "chunks_by_id": chunks_by_id,
        "parent_id_by_chunk": parent_id_by_chunk,
        "parents_by_id": parents_by_id,
    }
    cache.put(doc_hash, entry)
    return entry


def _chunks_from_chroma(chroma: Chroma) -> tuple[dict[int, str], dict[int, int]]:
    """One chroma.get() call yields both the chunk text-by-id map AND the
    child->parent back-reference — no extra I/O for the small-to-big lookup."""
    res = chroma.get(include=["documents", "metadatas"])
    chunks_by_id: dict[int, str] = {}
    parent_id_by_chunk: dict[int, int] = {}
    for text, meta in zip(res.get("documents", []), res.get("metadatas", [])):
        cid = meta.get("chunk_id") if meta else None
        if cid is None:
            continue
        cid = int(cid)
        chunks_by_id[cid] = text
        pid = meta.get("parent_id") if meta else None
        if pid is not None:
            parent_id_by_chunk[cid] = int(pid)
    return chunks_by_id, parent_id_by_chunk


def _load_parents(parents_path: str | None) -> dict[int, str]:
    if not parents_path:
        return {}
    p = Path(parents_path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {int(k): v for k, v in data.items()}


def _chunks_by_id(loaded: dict) -> dict[int, str]:
    return loaded["chunks_by_id"]


def _vector_search_chunks(chroma: Chroma, query: str, top_k: int) -> list[int]:
    return [cid for cid, _ in vector_search(chroma, query, top_k=top_k)]


def _bm25_search_chunks(bm25: BM25Index, keywords: str, top_k: int) -> list[int]:
    return [cid for cid, _ in bm25.search(keywords, top_k=top_k)]


def _graph_search_chunks(g: GraphIndex, entities: list[str], *, hops: int) -> list[int]:
    matched = g.match_entities(entities)
    return g.traverse_chunks(matched, hops=hops) if matched else []


def _graph_community_context(
    g: GraphIndex, entities: list[str], *, max_summaries: int
) -> list[tuple[int, str]]:
    """Community-level context: not chunk-ranked, so it isn't fused via RRF
    with the other legs — fetched alongside them, appended after
    fusion/rerank/expansion as supplementary numbered passages instead."""
    matched = g.match_entities(entities)
    if not matched:
        return []
    return g.distinct_community_summaries(matched)[:max_summaries]


def _expand_to_parents(
    ranked_child_ids: list[int],
    parent_id_by_chunk: dict[int, int],
    parents_by_id: dict[int, str],
    chunks_by_id: dict[int, str],
) -> list[tuple[int, str]]:
    """Small-to-big expansion: prefer each ranked child's parent (bigger,
    more coherent) text; falls back to the child's own text when no parent
    data exists (e.g. docs indexed before this feature shipped). Dedupes by
    parent so multiple matched children under the same parent collapse into
    one passage — keeps the prompt from repeating near-identical context."""
    seen_parents: set[int] = set()
    seen_bare: set[int] = set()
    out: list[tuple[int, str]] = []
    for cid in ranked_child_ids:
        pid = parent_id_by_chunk.get(cid)
        if pid is not None and pid in parents_by_id:
            if pid in seen_parents:
                continue
            seen_parents.add(pid)
            out.append((cid, parents_by_id[pid]))
        else:
            if cid in seen_bare:
                continue
            seen_bare.add(cid)
            text = chunks_by_id.get(cid, "")
            if text:
                out.append((cid, text))
    return out


def _build_context(
    expanded: list[tuple[int, str]], community_ctx: list[tuple[int, str]] | None = None
) -> tuple[str, list[dict]]:
    citations = []
    parts = []
    i = 0
    for cid, text in expanded:
        if not text:
            continue
        i += 1
        parts.append(f"[{i}] {text}")
        citations.append({"n": i, "chunk_id": cid})
    for comm_id, summary in community_ctx or []:
        i += 1
        parts.append(f"[{i}] (Community-level summary) {summary}")
        citations.append({"n": i, "chunk_id": None, "community_id": comm_id, "source": "community_summary"})
    return "\n\n".join(parts), citations


_MAX_HISTORY_TURNS = 20
_MAX_HISTORY_CHARS = 8000


def _sanitize_history(history: list[dict] | None) -> list[dict[str, str]]:
    """Client-supplied turns are untrusted: only user/assistant roles are
    accepted, content is coerced to str and capped, and the list is
    truncated. Splicing it verbatim let a caller inject a system turn
    (overriding the answer prompt) or blow up cost with a huge array.

    Sanitized once here and reused for both the retrieval-rewrite stage and
    the final answer messages, rather than re-validating (and re-trusting)
    the same raw input twice."""
    if not history:
        return []
    safe: list[dict[str, str]] = []
    for turn in history[-_MAX_HISTORY_TURNS:]:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        if role not in ("user", "assistant"):
            continue
        content = str(turn.get("content", ""))[:_MAX_HISTORY_CHARS]
        if content:
            safe.append({"role": role, "content": content})
    return safe


async def answer(
    *,
    doc_hash: str,
    query: str,
    history: list[dict[str, str]] | None = None,
    request_id: str | None = None,
) -> AsyncIterator[dict]:
    request_id = request_id or new_request_id()
    start_time = time.perf_counter()
    stage_records: list[dict] = []
    safe_history = _sanitize_history(history)

    settings = get_settings()
    loaded = _load_artifacts_cached(doc_hash)
    chroma, bm25, graph_idx = loaded["chroma"], loaded["bm25"], loaded["graph_idx"]
    chunks_by_id = _chunks_by_id(loaded)

    # Answer cache: only for fresh (no-history) questions, keyed on the
    # content itself (doc_hash + normalized query) — correctness never
    # depends on TTL since doc_hash is already content-addressed.
    disk_cache = get_disk_cache() if settings.answer_cache_enabled else None
    answer_cache_key = None
    if disk_cache is not None and not safe_history:
        answer_cache_key = disk_cache.make_key("answer", doc_hash, query.strip().lower())
        cached = disk_cache.get(answer_cache_key)
        if cached is not None:
            yield {"event": "context", "data": {"citations": cached["citations"], "request_id": request_id}}
            yield {"event": "token", "data": {"text": cached["answer"]}}
            yield {"event": "done", "data": {}}
            record_trace(
                request_id,
                doc_hash=doc_hash,
                query=query,
                total_latency_ms=round((time.perf_counter() - start_time) * 1000, 1),
                cache_hit=True,
                context=cached["citations"],
                answer_text=cached["answer"],
            )
            return

    answer_parts: list[str] = []
    citations: list[dict] = []
    error_text: str | None = None
    try:
        rewrite_diag: dict = {}
        with timed_stage("rewrite", request_id, sink=stage_records):
            rq = await rewrite_query(
                query, n_variants=settings.multi_query_n, history=safe_history,
                request_id=request_id, degraded_out=rewrite_diag,
            )
        if rewrite_diag.get("degraded"):
            stage_records[-1]["degraded"] = True

        async def safe(fn, *, leg: str):
            try:
                return await asyncio.to_thread(fn)
            except Exception as e:
                log_event(
                    "stage_err", stage="retrieval", request_id=request_id, leg=leg,
                    error_type=type(e).__name__, error=str(e),
                )
                return []

        # Seed with the history-resolved standalone query, not the raw text —
        # on a follow-up like "what are its limitations?" the raw text alone
        # retrieves whatever passage happens to match "limitations" best,
        # which is rarely the thing "its" actually referred to.
        variant_queries = [rq.resolved_query or query]
        if rq.hyde and rq.hyde not in variant_queries:
            variant_queries.append(rq.hyde)
        for v in rq.query_variants[: settings.multi_query_n]:
            if v and v not in variant_queries:
                variant_queries.append(v)

        async def vector_fanout() -> list[int]:
            per_variant = await asyncio.gather(
                *(
                    safe(
                        lambda vq=vq: _vector_search_chunks(chroma, vq, settings.per_retriever_top_k),
                        leg="vector",
                    )
                    for vq in variant_queries
                )
            )
            if len(per_variant) == 1:
                return per_variant[0]
            return reciprocal_rank_fusion(per_variant, k=settings.rrf_k, top_k=settings.per_retriever_top_k)

        with timed_stage("retrieval", request_id, sink=stage_records, n_variants=len(variant_queries)):
            vec_ids, bm25_ids, graph_ids, community_ctx = await asyncio.gather(
                vector_fanout(),
                safe(lambda: _bm25_search_chunks(bm25, rq.keywords, settings.per_retriever_top_k), leg="bm25"),
                safe(
                    lambda: _graph_search_chunks(graph_idx, rq.entities_mentioned, hops=settings.graph_hops),
                    leg="graph",
                ),
                safe(
                    lambda: _graph_community_context(
                        graph_idx, rq.entities_mentioned, max_summaries=settings.max_community_context
                    ),
                    leg="graph_community",
                ),
            )

        with timed_stage("fusion", request_id, sink=stage_records):
            fused = reciprocal_rank_fusion(
                [vec_ids, bm25_ids, graph_ids],
                k=settings.rrf_k,
                top_k=settings.fused_top_k,
                weights=[settings.rrf_weight_vector, settings.rrf_weight_bm25, settings.rrf_weight_graph],
            )

        pairs = [(cid, chunks_by_id.get(cid, "")) for cid in fused]
        rerank_diag: dict = {}
        with timed_stage("rerank", request_id, sink=stage_records, mode=settings.rerank_mode):
            reranked = await rerank(
                query, pairs, top_k=settings.rerank_top_k, with_scores=True,
                request_id=request_id, degraded_out=rerank_diag,
            )
        if rerank_diag.get("degraded"):
            stage_records[-1]["degraded"] = True
        rerank_scores = {cid: score for cid, score in reranked}
        fused = [cid for cid, _ in reranked]

        # Retrieval provenance: which leg(s) contributed each surfaced chunk —
        # cheap set-membership checks, no extra I/O.
        vec_set, bm25_set, graph_set = set(vec_ids), set(bm25_ids), set(graph_ids)

        expanded = _expand_to_parents(
            fused,
            loaded.get("parent_id_by_chunk", {}),
            loaded.get("parents_by_id", {}),
            chunks_by_id,
        )
        context, citations = _build_context(expanded, community_ctx)
        for c in citations:
            if c.get("source") == "community_summary":
                c["sources"] = ["graph_community"]
                continue
            cid = c["chunk_id"]
            c["rerank_score"] = rerank_scores.get(cid)
            c["sources"] = [
                name for name, s in (("vector", vec_set), ("bm25", bm25_set), ("graph", graph_set)) if cid in s
            ]

        yield {"event": "context", "data": {"citations": citations, "request_id": request_id}}

        # System turn carries the grounding/citation contract; see
        # ANSWER_SYSTEM_PROMPT for why it is not folded into the user turn.
        # safe_history is already sanitized (see _sanitize_history) - reused
        # here rather than re-validated a second time.
        messages = [{"role": "system", "content": ANSWER_SYSTEM_PROMPT}, *safe_history]
        messages.append(
            {"role": "user", "content": ANSWER_USER_PROMPT.format(context=context, question=query)}
        )

        gen_start = time.perf_counter()
        model_used: str | None = None
        async for delta, model_used in get_llm().stream(
            role="answer", messages=messages, temperature=0.2, max_tokens=settings.answer_max_tokens
        ):
            answer_parts.append(delta)
            yield {"event": "token", "data": {"text": delta}}
        answer_text = "".join(answer_parts)
        gen_latency_ms = round((time.perf_counter() - gen_start) * 1000, 1)
        # Streamed-answer token/cost are ESTIMATED (tiktoken over the prompt +
        # accumulated text), not provider-exact — stream()'s (delta, model)
        # generator contract intentionally isn't changed to request usage.
        tokens_in_est = count_tokens(json.dumps(messages))
        tokens_out_est = count_tokens(answer_text)
        stage_records.append({
            "stage": "generation",
            "latency_ms": gen_latency_ms,
            "model_used": model_used,
            "tokens_in": tokens_in_est,
            "tokens_out": tokens_out_est,
            "cost_usd": estimate_cost_usd(model_used or "", tokens_in_est, tokens_out_est),
            "tokens_estimated": True,
        })

        yield {"event": "done", "data": {}}
        if answer_cache_key is not None:
            disk_cache.put(
                answer_cache_key,
                {"citations": citations, "answer": answer_text},
                ttl=settings.answer_cache_ttl_s,
            )
    except Exception as e:
        error_text = str(e)
        # Emit a frame the client can render, then re-raise. Swallowing it here
        # meant the stream ended on `error` with no `done`, and the transport's
        # disconnect handling never ran.
        yield {"event": "error", "data": {"message": str(e), "partial": True}}
        raise
    finally:
        answer_text = "".join(answer_parts)
        # A stage's cost_usd is None when its model is unpriced (see
        # estimate_cost_usd) — propagate that as "unknown" for the whole
        # request rather than treating an unpriced stage as free.
        _stage_costs = [s.get("cost_usd") for s in stage_records if "cost_usd" in s]
        total_cost_usd = None if any(c is None for c in _stage_costs) else sum(c or 0.0 for c in _stage_costs)
        record_trace(
            request_id,
            doc_hash=doc_hash,
            query=query,
            total_latency_ms=round((time.perf_counter() - start_time) * 1000, 1),
            total_tokens_in=sum(s.get("tokens_in") or 0 for s in stage_records) or None,
            total_tokens_out=sum(s.get("tokens_out") or 0 for s in stage_records) or None,
            total_cost_usd=total_cost_usd,
            cache_hit=False,
            stages=stage_records,
            context=citations,
            answer_text=answer_text or None,
            error=error_text,
        )
