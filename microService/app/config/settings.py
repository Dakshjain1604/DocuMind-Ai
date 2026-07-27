"""Centralized, typed settings — single source of truth for env-driven config.

get_settings() re-reads os.environ on every call (deliberately not memoized,
so tests using monkeypatch.setenv see the new value on the very next call —
there's no perf reason to cache ~25 environ lookups).

Retrieval knobs fall back through: env var > app/config/retrieval.json
(written by tuning/report.py after a sweep) > hardcoded default. This is
what makes the sweep -> report -> production loop actually close.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_RETRIEVAL_JSON_PATH = Path(__file__).resolve().parent / "retrieval.json"


def _load_retrieval_json() -> dict[str, Any]:
    if not _RETRIEVAL_JSON_PATH.exists():
        return {}
    try:
        return json.loads(_RETRIEVAL_JSON_PATH.read_text())
    except Exception:
        return {}


def _str(env_key: str, json_key: str | None, json_data: dict, default: str) -> str:
    v = os.environ.get(env_key)
    if v is not None:
        return v
    if json_key is not None and json_data.get(json_key) is not None:
        return str(json_data[json_key])
    return default


def _int(env_key: str, json_key: str | None, json_data: dict, default: int) -> int:
    v = os.environ.get(env_key)
    if v is not None:
        return int(v)
    if json_key is not None and json_data.get(json_key) is not None:
        return int(json_data[json_key])
    return default


def _float(env_key: str, json_key: str | None, json_data: dict, default: float) -> float:
    v = os.environ.get(env_key)
    if v is not None:
        return float(v)
    if json_key is not None and json_data.get(json_key) is not None:
        return float(json_data[json_key])
    return default


def _bool(env_key: str, default: bool) -> bool:
    v = os.environ.get(env_key)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _opt_str(env_key: str) -> str | None:
    return os.environ.get(env_key) or None


def _resolve_rerank_mode(json_data: dict) -> str:
    explicit = os.environ.get("RAG_RERANK_MODE")
    if explicit:
        return explicit
    # Legacy flag: RAG_ENABLE_RERANK=true/false maps to llm/off, honored only
    # when the new var is unset — preserves any existing deployment's behavior.
    legacy = os.environ.get("RAG_ENABLE_RERANK")
    if legacy is not None:
        return "llm" if legacy.strip().lower() == "true" else "off"
    if json_data.get("rerank_mode"):
        return str(json_data["rerank_mode"])
    return "cross_encoder"


@dataclass(frozen=True)
class Settings:
    # LLM Provider
    llm_provider: str  # openrouter | groq | nvidia
    openrouter_api_key: str | None
    openrouter_base_url: str
    groq_api_key: str | None
    groq_base_url: str
    nvidia_api_key: str | None
    nvidia_base_url: str

    # Chunking. RAG_CHUNK_SIZE/OVERLAP are the "parent" size for hierarchical
    # (small-to-big) chunking; RAG_CHILD_CHUNK_* is the small retrieval unit.
    chunk_size: int
    chunk_overlap: int
    child_chunk_size: int
    child_chunk_overlap: int
    max_graph_chunks: int
    graph_concurrency: int
    max_community_summaries: int
    min_nodes_for_communities: int

    # Retrieval / fusion
    per_retriever_top_k: int
    fused_top_k: int
    rerank_top_k: int
    multi_query_n: int
    rrf_k: int
    rrf_weight_vector: float
    rrf_weight_bm25: float
    rrf_weight_graph: float
    graph_hops: int
    max_community_context: int

    # Rerank
    rerank_mode: str  # cross_encoder | llm | off
    rerank_model: str

    # Cache
    cache_dir: str
    max_cache_docs: int
    llm_cache_enabled: bool
    llm_cache_ttl_s: int
    answer_cache_enabled: bool
    answer_cache_ttl_s: int

    # Embeddings
    embed_model: str
    embed_batch_size: int
    embed_device: str | None

    # Persistence / uploads
    persist_dir: str
    max_file_mb: int

    # Observability
    trace_db_path: str


def get_settings() -> Settings:
    rj = _load_retrieval_json()
    persist_dir = _str("RAG_PERSIST_DIR", None, rj, "./local_chroma")
    return Settings(
        llm_provider=_str("LLM_PROVIDER", None, rj, "openrouter").lower().strip(),
        openrouter_api_key=_opt_str("OPENROUTER_API_KEY"),
        openrouter_base_url=_str("OPENROUTER_BASE_URL", None, rj, "https://openrouter.ai/api/v1"),
        groq_api_key=_opt_str("GROQ_API_KEY"),
        groq_base_url=_str("GROQ_BASE_URL", None, rj, "https://api.groq.com/openai/v1"),
        nvidia_api_key=_opt_str("NVIDIA_API_KEY"),
        nvidia_base_url=_str("NVIDIA_BASE_URL", None, rj, "https://integrate.api.nvidia.com/v1"),
        chunk_size=_int("RAG_CHUNK_SIZE", "chunk_size", rj, 1500),
        chunk_overlap=_int("RAG_CHUNK_OVERLAP", "chunk_overlap", rj, 200),
        child_chunk_size=_int("RAG_CHILD_CHUNK_SIZE", "child_chunk_size", rj, 400),
        child_chunk_overlap=_int("RAG_CHILD_CHUNK_OVERLAP", "child_chunk_overlap", rj, 50),
        max_graph_chunks=_int("RAG_MAX_GRAPH_CHUNKS", "max_graph_chunks", rj, 25),
        graph_concurrency=_int("RAG_GRAPH_CONCURRENCY", None, rj, 5),
        max_community_summaries=_int("RAG_MAX_COMMUNITY_SUMMARIES", "max_community_summaries", rj, 30),
        min_nodes_for_communities=_int("RAG_MIN_NODES_FOR_COMMUNITIES", None, rj, 5),
        per_retriever_top_k=_int("RAG_PER_RETRIEVER_TOP_K", "per_retriever_top_k", rj, 10),
        fused_top_k=_int("RAG_FUSED_TOP_K", "fused_top_k", rj, 15),
        rerank_top_k=_int("RAG_RERANK_TOP_K", "rerank_top_k", rj, 5),
        multi_query_n=_int("RAG_MULTI_QUERY_N", "multi_query_n", rj, 3),
        rrf_k=_int("RAG_RRF_K", "rrf_k", rj, 60),
        rrf_weight_vector=_float("RAG_RRF_WEIGHT_VECTOR", "vector_weight", rj, 1.0),
        rrf_weight_bm25=_float("RAG_RRF_WEIGHT_BM25", "bm25_weight", rj, 1.0),
        rrf_weight_graph=_float("RAG_RRF_WEIGHT_GRAPH", "graph_weight", rj, 0.5),
        graph_hops=_int("RAG_GRAPH_HOPS", None, rj, 2),
        max_community_context=_int("RAG_MAX_COMMUNITY_CONTEXT", None, rj, 2),
        rerank_mode=_resolve_rerank_mode(rj),
        rerank_model=_str("RAG_RERANK_MODEL", None, rj, "cross-encoder/ms-marco-MiniLM-L-6-v2"),
        cache_dir=_str("RAG_CACHE_DIR", None, rj, "./.rag_cache"),
        max_cache_docs=_int("RAG_MAX_CACHE_DOCS", None, rj, 3),
        llm_cache_enabled=_bool("RAG_LLM_CACHE_ENABLED", True),
        llm_cache_ttl_s=_int("RAG_LLM_CACHE_TTL_S", None, rj, 7 * 24 * 3600),
        answer_cache_enabled=_bool("RAG_ANSWER_CACHE_ENABLED", True),
        answer_cache_ttl_s=_int("RAG_ANSWER_CACHE_TTL_S", None, rj, 24 * 3600),
        embed_model=_str("RAG_EMBED_MODEL", None, rj, "BAAI/bge-small-en-v1.5"),
        embed_batch_size=_int("RAG_EMBED_BATCH_SIZE", None, rj, 32),
        embed_device=_opt_str("RAG_EMBED_DEVICE"),
        persist_dir=persist_dir,
        max_file_mb=_int("RAG_MAX_FILE_MB", None, rj, 100),
        trace_db_path=_str("RAG_TRACE_DB_PATH", None, rj, f"{persist_dir}/traces.db"),
    )
