"""Embedding model — NVIDIA NIM GPU-accelerated embeddings with local HuggingFace fallback.

NVIDIA NIM model: nvidia/nv-embedqa-e5-v5 (1024-dim, sub-second execution).
Local fallback: BAAI/bge-small-en-v1.5 (384-dim).
"""
from __future__ import annotations
import os
from functools import lru_cache
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from openai import OpenAI

from app.config.settings import get_settings


class NVIDIAEmbeddings(Embeddings):
    def __init__(self, model: str = "nvidia/nv-embedqa-e5-v5", api_key: str | None = None, base_url: str | None = None):
        self.model = model
        self.client = OpenAI(
            api_key=api_key or os.environ.get("NVIDIA_API_KEY", ""),
            base_url=base_url or os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        batch_size = 32
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            res = self.client.embeddings.create(
                model=self.model,
                input=batch,
                extra_body={"input_type": "passage"},
            )
            for item in res.data:
                embeddings.append(item.embedding)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        res = self.client.embeddings.create(
            model=self.model,
            input=[text],
            extra_body={"input_type": "query"},
        )
        if not res.data:
            return []
        return res.data[0].embedding


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
def get_embeddings() -> Embeddings:
    settings = get_settings()

    if settings.nvidia_api_key and (
        settings.embed_model.startswith("nvidia/") or settings.llm_provider == "nvidia"
    ):
        model_name = (
            settings.embed_model
            if settings.embed_model.startswith("nvidia/")
            else "nvidia/nv-embedqa-e5-v5"
        )
        try:
            return NVIDIAEmbeddings(
                model=model_name, api_key=settings.nvidia_api_key, base_url=settings.nvidia_base_url
            )
        except Exception as e:
            # Deliberately fatal. Falling through to the HuggingFace model here
            # silently swaps a 1024-dim provider for a 384-dim local one, which
            # does not fail until query time — as a dimension mismatch against
            # every document already indexed.
            raise RuntimeError(
                f"NVIDIA embeddings ({model_name}) are configured but failed to initialize: {e}. "
                f"Fix the credentials or set RAG_EMBED_MODEL to a local model explicitly."
            ) from e

    return HuggingFaceEmbeddings(
        model_name=settings.embed_model,
        model_kwargs={"device": detect_device(settings.embed_device)},
        encode_kwargs={"normalize_embeddings": True, "batch_size": settings.embed_batch_size},
    )
