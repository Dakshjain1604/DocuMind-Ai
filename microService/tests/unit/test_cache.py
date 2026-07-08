import time
import pytest
from app.core.cache import DocLRUCache, TTLDiskCache


def test_cache_returns_stored_value():
    c = DocLRUCache(max_size=3)
    c.put("hash-a", {"v": 1})
    assert c.get("hash-a") == {"v": 1}


def test_cache_returns_none_on_miss():
    c = DocLRUCache(max_size=3)
    assert c.get("nope") is None


def test_cache_lru_eviction_when_full():
    c = DocLRUCache(max_size=2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert c.get("a") is None  # evicted
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_cache_lru_promotes_on_access():
    c = DocLRUCache(max_size=2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")          # promote a
    c.put("c", 3)       # should evict b, not a
    assert c.get("a") == 1
    assert c.get("b") is None
    assert c.get("c") == 3


def test_cache_uploading_doc_b_does_not_evict_doc_a_when_room_exists():
    """Regression test for the original clear_document_cache() bug.
    Uploading a second doc must NOT wipe the first when cache has room."""
    c = DocLRUCache(max_size=3)
    c.put("doc-a", "first")
    c.put("doc-b", "second")
    assert c.get("doc-a") == "first"
    assert c.get("doc-b") == "second"


def test_ttl_disk_cache_put_get_roundtrip(tmp_path):
    c = TTLDiskCache(str(tmp_path))
    key = c.make_key("role", "hello")
    c.put(key, {"content": "cached answer"}, ttl=60)
    assert c.get(key) == {"content": "cached answer"}


def test_ttl_disk_cache_miss_returns_none(tmp_path):
    c = TTLDiskCache(str(tmp_path))
    assert c.get(c.make_key("nope")) is None


def test_ttl_disk_cache_expires_after_ttl(tmp_path):
    c = TTLDiskCache(str(tmp_path))
    key = c.make_key("expiring")
    c.put(key, "value", ttl=0.05)
    assert c.get(key) == "value"
    time.sleep(0.15)
    assert c.get(key) is None


def test_ttl_disk_cache_make_key_is_deterministic_and_order_sensitive():
    k1 = TTLDiskCache.make_key("llm", "answer", "same content")
    k2 = TTLDiskCache.make_key("llm", "answer", "same content")
    k3 = TTLDiskCache.make_key("llm", "different", "same content")
    assert k1 == k2
    assert k1 != k3


def test_ttl_disk_cache_persists_across_instances(tmp_path):
    """The whole point of diskcache over in-memory LRU: survives process
    restarts (modeled here as a second TTLDiskCache instance over the same dir)."""
    key = TTLDiskCache.make_key("persist-me")
    TTLDiskCache(str(tmp_path)).put(key, "still here", ttl=60)
    reopened = TTLDiskCache(str(tmp_path))
    assert reopened.get(key) == "still here"
