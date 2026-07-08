"""Integration test against the REAL cross-encoder model (small, ~80MB).
Skips gracefully if the model can't be downloaded (no network / no HF cache) —
the pure-logic mode-selection and fallback behavior is already covered by
tests/unit/test_reranker.py with a mocked model.
"""
import pytest
from app.retrieval.reranker import rerank, _get_cross_encoder

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _model_available() -> bool:
    try:
        _get_cross_encoder.cache_clear()
        _get_cross_encoder(MODEL_NAME, "cpu")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _model_available(), reason="cross-encoder model unavailable (no network / no HF cache)"
)


@pytest.mark.asyncio
async def test_real_cross_encoder_ranks_relevant_passage_first(monkeypatch):
    monkeypatch.setenv("RAG_RERANK_MODE", "cross_encoder")
    monkeypatch.setenv("RAG_RERANK_MODEL", MODEL_NAME)

    chunks = [
        (0, "The Eiffel Tower is located in Paris, France."),
        (1, "Bananas are a good source of potassium."),
        (2, "Paris is the capital city of France."),
    ]
    result = await rerank("What is the capital of France?", chunks, top_k=3)
    assert result[0] in (0, 2)  # one of the France-relevant passages ranks first
    assert result[-1] == 1  # the banana passage ranks last
