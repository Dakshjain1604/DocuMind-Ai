"""Graph-side retrieval — fuzzy entity match + k-hop chunk traversal."""
from __future__ import annotations
from collections import defaultdict


class GraphIndex:
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
            if ml in lower_map:
                out.append(lower_map[ml])
                continue
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
