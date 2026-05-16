import pytest
from app.core.cache import DocLRUCache


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
