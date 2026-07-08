"""Per-doc artifact persistence under RAG_PERSIST_DIR/<doc_hash>/."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from app.config.settings import get_settings
from app.retrieval.search import BM25Index


def _root() -> Path:
    return Path(get_settings().persist_dir)


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
    parent_chunks: dict[int, str] | None = None,
) -> Path:
    d = doc_dir(doc_hash)
    d.mkdir(parents=True, exist_ok=True)
    (d / "graph.json").write_text(json.dumps(graph, ensure_ascii=False))
    (d / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False))
    BM25Index.build(bm25_corpus).save(d / "bm25_corpus.pkl")
    if parent_chunks is not None:
        (d / "parents.json").write_text(
            json.dumps({str(k): v for k, v in parent_chunks.items()}, ensure_ascii=False)
        )
    return d


def load_artifacts(doc_hash: str) -> dict[str, Any]:
    d = doc_dir(doc_hash)
    out: dict[str, Any] = {
        "graph": json.loads((d / "graph.json").read_text()),
        "manifest": json.loads((d / "manifest.json").read_text()),
        "bm25_path": str(d / "bm25_corpus.pkl"),
        "chroma_dir": str(d / "chroma"),
    }
    parents_path = d / "parents.json"
    if parents_path.exists():
        out["parents_path"] = str(parents_path)
    return out


def chroma_dir(doc_hash: str) -> Path:
    return doc_dir(doc_hash) / "chroma"
