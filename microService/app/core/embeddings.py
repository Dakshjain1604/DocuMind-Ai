"""Embedding model — local BAAI/bge-small-en-v1.5 via sentence-transformers.

384-dim English embeddings, ~134MB on disk, runs on CPU / MPS / CUDA.
Zero per-query cost, no API key required. Model is downloaded from
HuggingFace on first use.
"""
from __future__ import annotations
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from app.config.settings import get_settings


def detect_device(override: str | None = None) -> str:
    if override:
        return override
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    settings = get_settings()
    return HuggingFaceEmbeddings(
        model_name=settings.embed_model,
        model_kwargs={"device": detect_device(settings.embed_device)},
        encode_kwargs={"normalize_embeddings": True, "batch_size": settings.embed_batch_size},
    )
