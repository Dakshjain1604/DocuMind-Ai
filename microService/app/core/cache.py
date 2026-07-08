"""Per-doc LRU cache (heavy artifact handles) + a TTL disk cache (LLM
responses / query answers). Replaces the prior global clear-on-every-upload
behavior for the former; the latter survives process restarts, which
in-memory caching can't — the actual pain point given repeated identical
LLM calls across dev iterations and tuning/sweep.py re-invocations."""
from __future__ import annotations
import hashlib
import json
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


class TTLDiskCache:
    """Thin wrapper over diskcache.Cache with a canonical-JSON key helper.
    One physical directory serves both LLM-response and answer caches — they
    share key prefixes ("llm:...", "answer:...") rather than needing two
    separate cache instances/directories for what is the same underlying tool.
    """

    def __init__(self, directory: str) -> None:
        import diskcache

        self._cache = diskcache.Cache(directory)

    @staticmethod
    def make_key(*parts: Any) -> str:
        canonical = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        return self._cache.get(key)

    def put(self, key: str, value: Any, *, ttl: int) -> None:
        self._cache.set(key, value, expire=ttl)


from app.config.settings import get_settings

_singleton: DocLRUCache | None = None
_disk_singleton: "TTLDiskCache | _NullDiskCache | None" = None


class _NullDiskCache:
    """No-op fallback used only if the real diskcache.Cache fails to
    construct (disk full, permission denied, corrupted cache db) — keeps
    /query, /summary, /quiz serving instead of hard-crashing on every request."""

    def get(self, key: str) -> Any | None:
        return None

    def put(self, key: str, value: Any, *, ttl: int) -> None:
        pass

    @staticmethod
    def make_key(*parts: Any) -> str:
        return TTLDiskCache.make_key(*parts)


def get_cache() -> DocLRUCache:
    global _singleton
    if _singleton is None:
        _singleton = DocLRUCache(max_size=get_settings().max_cache_docs)
    return _singleton


def get_disk_cache() -> "TTLDiskCache | _NullDiskCache":
    global _disk_singleton
    if _disk_singleton is None:
        try:
            _disk_singleton = TTLDiskCache(get_settings().cache_dir)
        except Exception as e:
            from app.core.observability import log_event

            log_event("disk_cache_init_failed", error_type=type(e).__name__, error=str(e))
            _disk_singleton = _NullDiskCache()
    return _disk_singleton
