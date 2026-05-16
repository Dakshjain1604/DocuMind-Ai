import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.llm import get_models_for_role, LLMClient, LLMRoleNotConfigured


def test_get_models_for_role_parses_comma_list(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL_EXTRACT", "a/b:free,c/d,e/f")
    assert get_models_for_role("extract") == ["a/b:free", "c/d", "e/f"]


def test_get_models_for_role_strips_whitespace(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL_ANSWER", " a/b , c/d ")
    assert get_models_for_role("answer") == ["a/b", "c/d"]


def test_get_models_for_role_unknown_role_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_MODEL_BOGUS", raising=False)
    with pytest.raises(LLMRoleNotConfigured):
        get_models_for_role("bogus")


@pytest.mark.asyncio
async def test_llm_client_falls_back_on_rate_limit(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL_ANSWER", "model-a,model-b")

    async def fake_chat(*, model, **kwargs):
        if model == "model-a":
            raise RuntimeError("429 too many requests")
        return MagicMock(choices=[MagicMock(message=MagicMock(content=f"ok-{model}"))])

    client = LLMClient()
    with patch.object(client, "_raw_chat", side_effect=fake_chat):
        result = await client.complete(role="answer", messages=[{"role": "user", "content": "hi"}])
    assert result.content == "ok-model-b"
    assert result.model_used == "model-b"
    assert result.fallback_count == 1


@pytest.mark.asyncio
async def test_llm_client_raises_when_all_models_fail(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL_ANSWER", "model-a,model-b")

    async def always_fail(*, model, **kwargs):
        raise RuntimeError("500")

    client = LLMClient()
    with patch.object(client, "_raw_chat", side_effect=always_fail):
        with pytest.raises(RuntimeError, match="All models in fallback chain failed"):
            await client.complete(role="answer", messages=[{"role": "user", "content": "hi"}])
