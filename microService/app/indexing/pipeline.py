"""Indexing pipeline. Async generator yielding progress events.

Each event is {"event": name, "data": {...}}.
"""
from __future__ import annotations
import asyncio
from typing import AsyncIterator
from langchain_core.documents import Document
from langchain_chroma import Chroma

from app.core.chunker import chunk_documents
from app.core.embeddings import get_embeddings
from app.indexing.graph_extractor import extract_graph
from app.indexing.community import (
    build_networkx_graph,
    detect_communities,
    summarize_communities,
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


async def index_document(
    *,
    file_bytes: bytes,
    documents: list[Document],
) -> AsyncIterator[dict]:
    h = doc_hash_from_bytes(file_bytes)

    if artifacts_exist(h):
        loaded = load_artifacts(h)
        yield {"event": "done", "data": {"doc_hash": h, "cached": True, "stats": loaded["manifest"]}}
        return

    yield {"event": "chunking", "data": {}}
    chunks = chunk_documents(documents)
    yield {"event": "chunking", "data": {"n_chunks": len(chunks)}}

    embed_task = asyncio.create_task(asyncio.to_thread(_build_chroma, chunks, str(chroma_dir(h))))
    yield {"event": "embedding", "data": {}}

    yield {"event": "extracting_graph", "data": {"total": len(chunks)}}
    build = await extract_graph(chunks)

    yield {"event": "embedding", "data": {"status": "waiting"}}
    await embed_task

    yield {"event": "detecting_communities", "data": {}}
    g = build_networkx_graph(build.entities, build.relationships)
    communities = detect_communities(g)

    yield {"event": "summarizing_communities", "data": {"n": len(set(communities.values())) if communities else 0}}
    summaries = await summarize_communities(g, communities)

    graph_payload = _serialize_graph(g, communities, summaries)
    stats = {
        "n_chunks": len(chunks),
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
    )

    yield {"event": "done", "data": {"doc_hash": h, "cached": False, "stats": stats}}
