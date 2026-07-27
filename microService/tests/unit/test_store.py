import json
from pathlib import Path

import pytest

from app.indexing.store import (
    InvalidDocHash,
    delete_document_artifacts,
    doc_dir,
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
    h = "ab" * 32  # 64 hex chars, sha256-shaped
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
    h = "cd" * 32
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
    h = "ef" * 32
    graph = {"nodes": [], "edges": [], "communities": {}, "community_summaries": {}}
    persist_artifacts(h, graph=graph, bm25_corpus=["a"], manifest={"n_chunks": 1})

    loaded = load_artifacts(h)
    assert "parents_path" not in loaded


# ── Regression: path traversal via doc_hash ───────────────────────────────────
# Starlette's default path converter matches "..", so before doc_dir()
# validated its input, DELETE /documents/.. resolved to <persist_dir>/.. and
# shutil.rmtree'd the service's working directory.
@pytest.mark.parametrize(
    "bad",
    [
        "..",
        ".",
        "../..",
        "../../etc",
        "not-a-hash",
        "ab" * 31,          # 62 chars, too short
        "ab" * 33,          # 66 chars, too long
        "zz" * 32,          # right length, not hex
        "AB" * 32,          # uppercase hex is not what we emit
        "",
    ],
)
def test_doc_dir_rejects_non_sha256_hashes(bad, tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    with pytest.raises(InvalidDocHash):
        doc_dir(bad)


def test_delete_refuses_traversal_and_leaves_tree_intact(tmp_path, monkeypatch):
    persist = tmp_path / "local_chroma"
    persist.mkdir()
    monkeypatch.setenv("RAG_PERSIST_DIR", str(persist))
    sibling = tmp_path / "source_code_do_not_delete.py"
    sibling.write_text("print('important')")

    with pytest.raises(InvalidDocHash):
        delete_document_artifacts("..")

    assert sibling.exists(), "traversal delete must not touch anything above the persist root"
    assert persist.exists()


def test_artifacts_exist_is_false_without_bm25_corpus(tmp_path, monkeypatch):
    """A crash between graph.json and bm25_corpus.pkl must not look indexed.

    artifacts_exist() previously checked only graph.json + manifest.json, so a
    half-written document was reported as ready and then raised
    FileNotFoundError on its first query.
    """
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    h = "ab" * 32
    d = tmp_path / h
    d.mkdir()
    (d / "graph.json").write_text("{}")
    (d / "manifest.json").write_text(json.dumps({"n_chunks": 1}))

    assert artifacts_exist(h) is False

    from app.retrieval.search import BM25Index

    BM25Index.build(["now complete"]).save(d / "bm25_corpus.pkl")
    assert artifacts_exist(h) is True


def test_artifacts_exist_is_false_for_invalid_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    assert artifacts_exist("..") is False
    assert artifacts_exist("garbage") is False
