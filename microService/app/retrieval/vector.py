"""Thin wrapper over Chroma — returns (chunk_id, score) tuples."""
from __future__ import annotations
from langchain_chroma import Chroma


def vector_search(
    chroma: Chroma,
    query: str,
    *,
    top_k: int = 10,
) -> list[tuple[int, float]]:
    """Returns list of (chunk_id, score). Lower distance == better, so we invert."""
    results = chroma.similarity_search_with_score(query, k=top_k)
    out: list[tuple[int, float]] = []
    for doc, distance in results:
        cid = doc.metadata.get("chunk_id")
        if cid is None:
            continue
        out.append((int(cid), -float(distance)))
    return out
