"""Shared pytest fixtures."""
import os
import sys
from pathlib import Path
import pytest

# Make `app` importable when pytest runs from microService/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Test env defaults — avoid hitting real OpenRouter in unit tests
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("OPENROUTER_MODEL_EXTRACT", "test-model-extract")
os.environ.setdefault("OPENROUTER_MODEL_ANSWER", "test-model-answer")
os.environ.setdefault("OPENROUTER_MODEL_REWRITE", "test-model-rewrite")
os.environ.setdefault("OPENROUTER_MODEL_RERANK", "test-model-rerank")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("RAG_PERSIST_DIR", "./test_local_chroma")
os.environ.setdefault("RAG_MAX_CACHE_DOCS", "3")
# Default rerank off so fast unit/integration tests never trigger a real
# cross-encoder model load/download; tests that exercise rerank modes
# explicitly override this via monkeypatch.
os.environ.setdefault("RAG_RERANK_MODE", "off")
# Default caching off — tests that reuse identical (role, messages) across
# different mocked behaviors would otherwise leak a cached result from one
# test into another. Cache tests explicitly opt in with an isolated tmp dir.
os.environ.setdefault("RAG_LLM_CACHE_ENABLED", "false")
os.environ.setdefault("RAG_ANSWER_CACHE_ENABLED", "false")


@pytest.fixture
def tmp_persist_dir(tmp_path, monkeypatch):
    """Isolated persist directory per test."""
    p = tmp_path / "local_chroma"
    p.mkdir()
    monkeypatch.setenv("RAG_PERSIST_DIR", str(p))
    return p
