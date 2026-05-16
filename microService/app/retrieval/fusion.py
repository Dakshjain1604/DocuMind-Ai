"""Reciprocal Rank Fusion — pure function, no I/O."""
from __future__ import annotations
from typing import Hashable, Sequence


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[Hashable]],
    *,
    k: int = 60,
    top_k: int | None = None,
) -> list:
    scores: dict[Hashable, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank + 1)
    sorted_items = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    items = [item for item, _ in sorted_items]
    return items[:top_k] if top_k is not None else items
