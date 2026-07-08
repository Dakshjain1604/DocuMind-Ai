import pytest
from app.retrieval import reranker
from app.retrieval.reranker import rerank, is_enabled


@pytest.mark.asyncio
async def test_off_mode_passes_through_truncated(monkeypatch):
    monkeypatch.setenv("RAG_RERANK_MODE", "off")
    chunks = [(0, "a"), (1, "b"), (2, "c")]
    result = await rerank("q", chunks, top_k=2)
    assert result == [0, 1]


@pytest.mark.asyncio
async def test_empty_chunks_returns_empty_regardless_of_mode(monkeypatch):
    monkeypatch.setenv("RAG_RERANK_MODE", "cross_encoder")
    assert await rerank("q", [], top_k=5) == []


def test_is_enabled_false_when_off(monkeypatch):
    monkeypatch.setenv("RAG_RERANK_MODE", "off")
    assert is_enabled() is False


def test_is_enabled_true_for_cross_encoder_and_llm(monkeypatch):
    monkeypatch.setenv("RAG_RERANK_MODE", "cross_encoder")
    assert is_enabled() is True
    monkeypatch.setenv("RAG_RERANK_MODE", "llm")
    assert is_enabled() is True


@pytest.mark.asyncio
async def test_with_scores_returns_tuples(monkeypatch):
    monkeypatch.setenv("RAG_RERANK_MODE", "off")
    chunks = [(0, "a"), (1, "b")]
    result = await rerank("q", chunks, top_k=2, with_scores=True)
    assert result == [(0, 0.0), (1, 0.0)]


@pytest.mark.asyncio
async def test_cross_encoder_mode_uses_predicted_scores(monkeypatch):
    monkeypatch.setenv("RAG_RERANK_MODE", "cross_encoder")
    reranker._get_cross_encoder.cache_clear()

    class _FakeModel:
        def predict(self, pairs):
            # score higher for the passage containing "match"
            return [1.0 if "match" in text else 0.0 for _, text in pairs]

    monkeypatch.setattr(reranker, "_get_cross_encoder", lambda model_name, device: _FakeModel())

    chunks = [(0, "irrelevant text"), (1, "this is a match"), (2, "also irrelevant")]
    result = await rerank("q", chunks, top_k=3)
    assert result[0] == 1


@pytest.mark.asyncio
async def test_cross_encoder_falls_back_to_passthrough_on_model_error(monkeypatch):
    monkeypatch.setenv("RAG_RERANK_MODE", "cross_encoder")

    def _raise(*a, **k):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(reranker, "_get_cross_encoder", _raise)

    chunks = [(0, "a"), (1, "b")]
    result = await rerank("q", chunks, top_k=2)
    assert result == [0, 1]
