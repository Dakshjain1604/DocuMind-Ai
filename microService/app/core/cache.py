"""Per-doc LRU cache. Replaces the prior global clear-on-every-upload behavior."""
from __future__ import annotations
from collections import OrderedDict
from typing import Any


class DocLRUCache:
    def __init__(self, max_size: int = 3) -> None:
        self._data: OrderedDict[str, Any] = OrderedDict()
        self._max = max_size

    def get(self, key: str) -> Any | None:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: Any) -> None:
        if key in self._data:
            self._data.move_to_end(key)
            self._data[key] = value
            return
        self._data[key] = value
        if len(self._data) > self._max:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)


import os
_singleton: DocLRUCache | None = None


def get_cache() -> DocLRUCache:
    global _singleton
    if _singleton is None:
        _singleton = DocLRUCache(max_size=int(os.environ.get("RAG_MAX_CACHE_DOCS", "3")))
    return _singleton
