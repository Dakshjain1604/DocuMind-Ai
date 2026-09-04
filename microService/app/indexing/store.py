"""Per-doc artifact persistence under RAG_PERSIST_DIR/<doc_hash>/."""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any
from app.config.settings import get_settings
from app.indexing.bm25 import BM25Index

# A doc_hash is always sha256 hex. Anything else is rejected before it can
# reach the filesystem: doc_hash arrives from user-controlled path params and
# request bodies, and Starlette's default path converter matches "..", so an
# unvalidated value would let doc_dir() escape the persist root.
_DOC_HASH_RE = re.compile(r"\A[0-9a-f]{64}\Z")


class InvalidDocHash(ValueError):
    """Raised when a doc_hash is not a sha256 hex digest."""


def validate_doc_hash(doc_hash: str) -> str:
    if not isinstance(doc_hash, str) or not _DOC_HASH_RE.match(doc_hash):
        raise InvalidDocHash(f"invalid doc_hash: {doc_hash!r}")
    return doc_hash


def _root() -> Path:
    return Path(get_settings().persist_dir)


def doc_dir(doc_hash: str) -> Path:
    """Resolve a document's artifact directory.

    Validation lives here rather than at each call site so every path that
    reaches the filesystem — reads, writes and deletes alike — is covered.
    """
    return _root() / validate_doc_hash(doc_hash)


def doc_hash_from_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def artifacts_exist(doc_hash: str) -> bool:
    try:
        d = doc_dir(doc_hash)
    except InvalidDocHash:
        return False
    # bm25_corpus.pkl is required: it is written last, so treating a doc as
    # complete without it would let a crash mid-write leave a "valid" document
    # that raises FileNotFoundError on its first query.
    return all(
        (d / name).exists()
        for name in ("manifest.json", "graph.json", "bm25_corpus.pkl")
    )


def _write_atomic(path: Path, payload: str) -> None:
    """Write via a temp file + os.replace so readers never see a partial file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


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
    # Order matters: everything artifacts_exist() checks for is written last,
    # so an interrupted run leaves the document looking un-indexed (and thus
    # re-indexable) rather than half-present.
    if parent_chunks is not None:
        _write_atomic(
            d / "parents.json",
            json.dumps({str(k): v for k, v in parent_chunks.items()}, ensure_ascii=False),
        )
    _write_atomic(d / "graph.json", json.dumps(graph, ensure_ascii=False))
    BM25Index.build(bm25_corpus).save(d / "bm25_corpus.pkl")
    _write_atomic(d / "manifest.json", json.dumps(manifest, ensure_ascii=False))
    return d


def update_manifest(doc_hash: str, manifest: dict[str, Any]) -> None:
    """Rewrite manifest.json in place (e.g. to append a new document owner)."""
    _write_atomic(doc_dir(doc_hash) / "manifest.json", json.dumps(manifest, ensure_ascii=False))


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


def list_all_documents() -> list[dict[str, Any]]:
    root = _root()
    if not root.exists():
        return []
    docs = []
    for d in root.iterdir():
        if d.is_dir() and (d / "manifest.json").exists():
            try:
                manifest = json.loads((d / "manifest.json").read_text())
                docs.append({
                    "doc_hash": d.name,
                    "filename": manifest.get("filename", manifest.get("sources", [d.name])[0] if manifest.get("sources") else d.name),
                    "sources": manifest.get("sources", []),
                    "n_chunks": manifest.get("n_chunks", 0),
                    "created_at": manifest.get("created_at", d.stat().st_mtime),
                    "owners": manifest.get("owners", []),
                })
            except Exception:
                pass
    docs.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return docs


def delete_document_artifacts(doc_hash: str) -> bool:
    d = doc_dir(doc_hash)  # raises InvalidDocHash on anything but a sha256 hex
    root = _root().resolve()
    resolved = d.resolve()
    # Belt and braces alongside the hash regex: never rmtree outside the root,
    # and never the root itself.
    if resolved == root or root not in resolved.parents:
        raise InvalidDocHash(f"refusing to delete outside persist root: {doc_hash!r}")
    if resolved.is_dir():
        shutil.rmtree(resolved)
        return True
    return False
