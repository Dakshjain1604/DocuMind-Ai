"""Indexing pipeline. Async generator yielding progress events.

Each event is {"event": name, "data": {...}}.
"""
from __future__ import annotations
import asyncio
import time
from typing import AsyncIterator
from langchain_core.documents import Document
from langchain_chroma import Chroma

from app.config.settings import get_settings
from app.core.chunker import chunk_documents_hierarchical
from app.core.embeddings import get_embeddings
from app.core.observability import log_event, new_request_id, record_trace, timed_stage
from app.indexing.graph_extractor import extract_graph_streaming
from app.indexing.community import (
    build_networkx_graph,
    detect_communities,
    summarize_communities_streaming,
)
from app.indexing.store import (
    doc_hash_from_bytes,
    artifacts_exist,
    persist_artifacts,
    load_artifacts,
    chroma_dir,
)


def _build_chroma(chunks: list[Document], persist_dir: str) -> Chroma:
    return Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=persist_dir,
    )


def _serialize_graph(g, communities: dict[str, int], summaries: dict[int, str]) -> dict:
    return {
        "nodes": [{"id": n, **g.nodes[n]} for n in g.nodes],
        "edges": [
            {"src": u, "dst": v, **g.edges[u, v]}
            for u, v in g.edges
        ],
        "communities": communities,
        "community_summaries": {str(k): v for k, v in summaries.items()},
    }


def _translate_parent_source_chunks(
    items: list[dict], parent_to_children: dict[int, list[int]]
) -> None:
    """Entity/relationship extraction ran over PARENT chunks (fewer, richer
    LLM calls). graph_extractor.py stamps whatever it's given under
    "source_chunks" — here that's parent_ids. Translate each parent_id into
    that parent's child chunk_ids in place, so GraphIndex.traverse_chunks()
    returns ids fusable with vector/BM25 rankings (all keyed on chunk_id).
    """
    for item in items:
        parent_ids = item.get("source_chunks", [])
        child_ids: list[int] = []
        seen = set()
        for pid in parent_ids:
            for cid in parent_to_children.get(pid, []):
                if cid not in seen:
                    seen.add(cid)
                    child_ids.append(cid)
        item["source_chunks"] = child_ids


async def index_document(
    *,
    file_bytes: bytes,
    documents: list[Document],
    request_id: str | None = None,
) -> AsyncIterator[dict]:
    request_id = request_id or new_request_id()
    start_time = time.perf_counter()
    stage_records: list[dict] = []
    h = doc_hash_from_bytes(file_bytes)

    if artifacts_exist(h):
        loaded = load_artifacts(h)
        record_trace(
            request_id,
            doc_hash=h,
            query=f"[index] {h}",
            total_latency_ms=round((time.perf_counter() - start_time) * 1000, 1),
            cache_hit=True,
        )
        yield {
            "event": "done",
            "data": {"doc_hash": h, "cached": True, "stats": loaded["manifest"], "request_id": request_id},
        }
        return

    settings = get_settings()
    max_graph_chunks = settings.max_graph_chunks
    graph_concurrency = settings.graph_concurrency

    error_text: str | None = None
    try:
        yield {"event": "chunking", "data": {}}
        with timed_stage("chunking", request_id, sink=stage_records):
            parents, chunks = chunk_documents_hierarchical(
                documents,
                parent_chunk_size=settings.chunk_size,
                parent_chunk_overlap=settings.chunk_overlap,
                child_chunk_size=settings.child_chunk_size,
                child_chunk_overlap=settings.child_chunk_overlap,
            )
        yield {"event": "chunking", "data": {"n_chunks": len(chunks), "n_parents": len(parents)}}

        parent_to_children: dict[int, list[int]] = {}
        for c in chunks:
            parent_to_children.setdefault(c.metadata["parent_id"], []).append(c.metadata["chunk_id"])

        embed_start = time.perf_counter()
        embed_task = asyncio.create_task(asyncio.to_thread(_build_chroma, chunks, str(chroma_dir(h))))
        yield {"event": "embedding", "data": {}}

        # Graph extraction runs on PARENT chunks — fewer, richer LLM calls at the
        # same call-volume as the old flat chunker (parent size == old default
        # chunk size). Vector + BM25 already cover the full doc at child
        # granularity; graph traversal works fine off a representative sample.
        if len(parents) > max_graph_chunks:
            step = len(parents) / max_graph_chunks
            sampled_parents = [parents[int(i * step)] for i in range(max_graph_chunks)]
            skipped = len(parents) - max_graph_chunks
            log_event(
                "graph_sampling_partial",
                request_id=request_id,
                total_parents=len(parents),
                sampled=max_graph_chunks,
                skipped=skipped,
            )
            yield {
                "event": "warning",
                "data": {
                    "stage": "extracting_graph",
                    "message": (
                        f"Graph coverage is partial: sampled {max_graph_chunks} of {len(parents)} "
                        f"parent chunks ({skipped} skipped, max_graph_chunks={max_graph_chunks})."
                    ),
                },
            }
            yield {
                "event": "extracting_graph",
                "data": {"total": len(sampled_parents), "sampled_from": len(parents)},
            }
        else:
            sampled_parents = parents
            yield {"event": "extracting_graph", "data": {"total": len(sampled_parents)}}

        # graph_extractor keys extraction results off metadata["chunk_id"]; feed
        # it parent_id under that key so extraction is unaffected, and translate
        # back to child chunk_ids afterwards (see _translate_parent_source_chunks).
        graph_source_docs = [
            Document(page_content=p.page_content, metadata={**p.metadata, "chunk_id": p.metadata["parent_id"]})
            for p in sampled_parents
        ]

        build = None
        with timed_stage("extract_graph", request_id, sink=stage_records, n_chunks=len(sampled_parents)):
            async for kind, payload in extract_graph_streaming(graph_source_docs, concurrency=graph_concurrency):
                if kind == "progress":
                    yield {"event": "graph_progress", "data": payload}
                elif kind == "warning":
                    yield {"event": "warning", "data": {"stage": "extracting_graph", **payload}}
                elif kind == "result":
                    build = payload

        yield {"event": "embedding", "data": {"status": "waiting"}}
        await embed_task
        stage_records.append({
            "stage": "embedding",
            "latency_ms": round((time.perf_counter() - embed_start) * 1000, 1),
        })

        _translate_parent_source_chunks(build.entities, parent_to_children)
        _translate_parent_source_chunks(build.relationships, parent_to_children)

        yield {"event": "detecting_communities", "data": {}}
        with timed_stage("detect_communities", request_id, sink=stage_records):
            g = build_networkx_graph(build.entities, build.relationships)
            communities = detect_communities(g)

        n_communities_total = len(set(communities.values())) if communities else 0
        max_summaries = settings.max_community_summaries
        n_to_summarize = min(n_communities_total, max_summaries)
        yield {
            "event": "summarizing_communities",
            "data": {"total": n_to_summarize, "skipped": max(0, n_communities_total - n_to_summarize)},
        }
        summaries: dict[int, str] = {}
        with timed_stage(
            "summarize_communities", request_id, sink=stage_records, n_communities=n_to_summarize
        ):
            async for kind, payload in summarize_communities_streaming(
                g, communities, concurrency=graph_concurrency, max_communities=max_summaries
            ):
                if kind == "progress":
                    yield {"event": "community_progress", "data": payload}
                else:
                    summaries = payload

        graph_payload = _serialize_graph(g, communities, summaries)
        stats = {
            "n_chunks": len(chunks),
            "n_parents": len(parents),
            "n_entities": g.number_of_nodes(),
            "n_edges": g.number_of_edges(),
            "n_communities": len(set(communities.values())) if communities else 0,
            "warnings": build.warnings,
        }
        persist_artifacts(
            h,
            graph=graph_payload,
            bm25_corpus=[c.page_content for c in chunks],
            manifest=stats,
            parent_chunks={p.metadata["parent_id"]: p.page_content for p in parents},
        )

        yield {
            "event": "done",
            "data": {"doc_hash": h, "cached": False, "stats": stats, "request_id": request_id},
        }
    except Exception as e:
        error_text = str(e)
        raise
    finally:
        record_trace(
            request_id,
            doc_hash=h,
            query=f"[index] {h}",
            total_latency_ms=round((time.perf_counter() - start_time) * 1000, 1),
            stages=stage_records,
            error=error_text,
        )
