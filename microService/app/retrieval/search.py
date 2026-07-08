"""The three retrieval legs (vector, BM25, graph) plus the Reciprocal Rank
Fusion combiner that merges their rankings — grouped together since none of
these are ever used independently of the others in orchestrator.py's fan-out.
"""
from __future__ import annotations
import pickle
import re
from collections import defaultdict
from pathlib import Path
from typing import Hashable, Sequence

from langchain_chroma import Chroma
from rank_bm25 import BM25Okapi


def vector_search(
    chroma: Chroma,
    query: str,
    *,
    top_k: int = 10,
) -> list[tuple[int, float]]:
    """Thin wrapper over Chroma. Returns (chunk_id, score); lower distance
    == better, so we invert."""
    results = chroma.similarity_search_with_score(query, k=top_k)
    out: list[tuple[int, float]] = []
    for doc, distance in results:
        cid = doc.metadata.get("chunk_id")
        if cid is None:
            continue
        out.append((int(cid), -float(distance)))
    return out


_token_re = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _token_re.findall(text)]


class BM25Index:
    """In-memory BM25 over chunk text."""

    def __init__(self, tokenized_corpus: list[list[str]]) -> None:
        self._tokens = tokenized_corpus
        self._bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None

    @classmethod
    def build(cls, corpus: list[str]) -> "BM25Index":
        return cls([_tokenize(t) for t in corpus])

    def search(self, query: str, *, top_k: int = 10) -> list[tuple[int, float]]:
        if self._bm25 is None:
            return []
        q = _tokenize(query)
        scores = self._bm25.get_scores(q)
        ranked = sorted(enumerate(scores), key=lambda kv: kv[1], reverse=True)
        return ranked[:top_k]

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(pickle.dumps(self._tokens))

    @classmethod
    def load(cls, path: str | Path) -> "BM25Index":
        return cls(pickle.loads(Path(path).read_bytes()))


class GraphIndex:
    """Graph-side retrieval — fuzzy entity match + k-hop chunk traversal +
    community-level summaries, all read from the graph JSON persisted by
    app/indexing/pipeline.py."""

    def __init__(self, graph: dict) -> None:
        self._nodes = {n["id"]: n for n in graph.get("nodes", [])}
        self._adj: dict[str, set[str]] = defaultdict(set)
        for e in graph.get("edges", []):
            self._adj[e["src"]].add(e["dst"])
            self._adj[e["dst"]].add(e["src"])
        self._comm = graph.get("communities", {})
        self._summaries = {int(k): v for k, v in graph.get("community_summaries", {}).items()}

    def match_entities(self, mentioned: list[str]) -> list[str]:
        out: list[str] = []
        lower_map = {nid.lower(): nid for nid in self._nodes}
        for m in mentioned:
            ml = m.lower().strip()
            if not ml:
                continue
            if ml in lower_map:
                out.append(lower_map[ml])
                continue
            if len(ml) >= 3:
                for k, nid in lower_map.items():
                    if ml in k or k in ml:
                        out.append(nid)
                        break
        seen, deduped = set(), []
        for nid in out:
            if nid not in seen:
                seen.add(nid)
                deduped.append(nid)
        return deduped

    def traverse_chunks(self, entities: list[str], *, hops: int = 2) -> list[int]:
        frontier = set(entities)
        visited = set(entities)
        for _ in range(hops):
            nxt = set()
            for n in frontier:
                nxt |= self._adj.get(n, set())
            frontier = nxt - visited
            visited |= frontier
        chunks: list[int] = []
        for n in visited:
            for c in self._nodes.get(n, {}).get("source_chunks", []):
                chunks.append(c)
        seen, out = set(), []
        for c in chunks:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def community_summary(self, entity_id: str) -> str | None:
        cid = self._comm.get(entity_id)
        if cid is None:
            return None
        return self._summaries.get(int(cid))

    def distinct_community_summaries(self, entities: list[str]) -> list[tuple[int, str]]:
        """Unique (community_id, summary) pairs across the given matched
        entities — used to inject community-level context alongside
        per-chunk retrieval, deduped so entities sharing a community don't
        repeat the same summary."""
        seen: set[int] = set()
        out: list[tuple[int, str]] = []
        for e in entities:
            cid = self._comm.get(e)
            if cid is None:
                continue
            cid = int(cid)
            if cid in seen:
                continue
            seen.add(cid)
            summary = self._summaries.get(cid)
            if summary:
                out.append((cid, summary))
        return out


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[Hashable]],
    *,
    k: int = 60,
    top_k: int | None = None,
    weights: Sequence[float] | None = None,
) -> list:
    """Pure function, no I/O. Combines multiple rankings by
    score[item] += weight / (k + rank + 1), summed across every ranking the
    item appears in — items ranked highly across more legs float to the top."""
    if weights is not None and len(weights) != len(rankings):
        raise ValueError(
            f"Number of rankings ({len(rankings)}) must match number of weights ({len(weights)})"
        )
    scores: dict[Hashable, float] = {}
    for i, ranking in enumerate(rankings):
        weight = weights[i] if weights is not None else 1.0
        for rank, item in enumerate(ranking):
            scores[item] = scores.get(item, 0.0) + weight / (k + rank + 1)
    sorted_items = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    items = [item for item, _ in sorted_items]
    return items[:top_k] if top_k is not None else items
