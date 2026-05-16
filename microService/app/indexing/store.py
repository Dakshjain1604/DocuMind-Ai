"""Per-doc artifact persistence under RAG_PERSIST_DIR/<doc_hash>/."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from app.retrieval.bm25 import BM25Index


def _root() -> Path:
    return Path(os.environ.get("RAG_PERSIST_DIR", "./local_chroma"))


def doc_dir(doc_hash: str) -> Path:
    return _root() / doc_hash


def doc_hash_from_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def artifacts_exist(doc_hash: str) -> bool:
    d = doc_dir(doc_hash)
    return (d / "manifest.json").exists() and (d / "graph.json").exists()


def persist_artifacts(
    doc_hash: str,
    *,
    graph: dict[str, Any],
    bm25_corpus: list[str],
    manifest: dict[str, Any],
) -> Path:
    d = doc_dir(doc_hash)
    d.mkdir(parents=True, exist_ok=True)
    (d / "graph.json").write_text(json.dumps(graph, ensure_ascii=False))
    (d / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False))
    BM25Index.build(bm25_corpus).save(d / "bm25_corpus.pkl")
    return d


def load_artifacts(doc_hash: str) -> dict[str, Any]:
    d = doc_dir(doc_hash)
    return {
        "graph": json.loads((d / "graph.json").read_text()),
        "manifest": json.loads((d / "manifest.json").read_text()),
        "bm25_path": str(d / "bm25_corpus.pkl"),
        "chroma_dir": str(d / "chroma"),
    }


def chroma_dir(doc_hash: str) -> Path:
    return doc_dir(doc_hash) / "chroma"
