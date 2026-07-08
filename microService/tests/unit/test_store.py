import json
from pathlib import Path
from app.indexing.store import (
    doc_hash_from_bytes,
    persist_artifacts,
    load_artifacts,
    artifacts_exist,
)


def test_doc_hash_is_deterministic_and_content_based():
    h1 = doc_hash_from_bytes(b"hello world")
    h2 = doc_hash_from_bytes(b"hello world")
    h3 = doc_hash_from_bytes(b"different")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # sha256 hex


def test_persist_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    h = "abc" * 21 + "x"  # 64 chars
    graph = {"nodes": [{"id": "A"}], "edges": [], "communities": {}, "community_summaries": {}}
    stats = {"n_chunks": 10, "n_entities": 1, "n_edges": 0, "n_communities": 0}
    persist_artifacts(h, graph=graph, bm25_corpus=["hello world"], manifest=stats)

    assert artifacts_exist(h) is True

    loaded = load_artifacts(h)
    assert loaded["graph"] == graph
    assert loaded["manifest"] == stats
    assert Path(loaded["bm25_path"]).exists()


def test_artifacts_exist_returns_false_for_unknown_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    assert artifacts_exist("nonexistent") is False


def test_persist_and_load_roundtrip_with_parents(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    h = "def" * 21 + "x"
    graph = {"nodes": [], "edges": [], "communities": {}, "community_summaries": {}}
    stats = {"n_chunks": 4, "n_parents": 2}
    persist_artifacts(
        h, graph=graph, bm25_corpus=["a", "b", "c", "d"], manifest=stats,
        parent_chunks={0: "parent zero text", 1: "parent one text"},
    )

    loaded = load_artifacts(h)
    assert "parents_path" in loaded
    parents = json.loads(Path(loaded["parents_path"]).read_text())
    assert parents == {"0": "parent zero text", "1": "parent one text"}


def test_load_artifacts_omits_parents_path_when_not_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    h = "ghi" * 21 + "x"
    graph = {"nodes": [], "edges": [], "communities": {}, "community_summaries": {}}
    persist_artifacts(h, graph=graph, bm25_corpus=["a"], manifest={"n_chunks": 1})

    loaded = load_artifacts(h)
    assert "parents_path" not in loaded
