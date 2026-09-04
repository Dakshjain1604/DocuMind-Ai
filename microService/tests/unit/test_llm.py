import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import app.core.cache as cache_module
from app.core.llm import get_models_for_role, LLMClient, LLMRoleNotConfigured


@pytest.fixture
def isolated_llm_cache(tmp_path, monkeypatch):
    """Fresh disk-cache singleton pointed at a tmp dir, cache enabled."""
    monkeypatch.setattr(cache_module, "_disk_singleton", None)
    monkeypatch.setenv("RAG_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("RAG_LLM_CACHE_ENABLED", "true")
    yield
    monkeypatch.setattr(cache_module, "_disk_singleton", None)


def test_get_models_for_role_parses_comma_list(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL_EXTRACT", "a/b:free,c/d,e/f")
    assert get_models_for_role("extract") == ["a/b:free", "c/d", "e/f"]


def test_get_models_for_role_strips_whitespace(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL_ANSWER", " a/b , c/d ")
    assert get_models_for_role("answer") == ["a/b", "c/d"]


def test_get_models_for_role_unknown_role_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.delenv("OPENROUTER_MODEL_BOGUS", raising=False)
    with pytest.raises(LLMRoleNotConfigured):
        get_models_for_role("bogus")


@pytest.mark.asyncio
async def test_llm_client_falls_back_on_rate_limit(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
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
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL_ANSWER", "model-a,model-b")

    async def always_fail(*, model, **kwargs):
        raise RuntimeError("500")

    client = LLMClient()
    with patch.object(client, "_raw_chat", side_effect=always_fail):
        with pytest.raises(RuntimeError, match="All models in fallback chain failed"):
            await client.complete(role="answer", messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_complete_returns_cached_result_without_calling_api(monkeypatch, isolated_llm_cache):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL_ANSWER", "model-a")
    call_count = 0

    async def fake_chat(*, model, **kwargs):
        nonlocal call_count
        call_count += 1
        return MagicMock(choices=[MagicMock(message=MagicMock(content="first response"))])

    client = LLMClient()
    with patch.object(client, "_raw_chat", side_effect=fake_chat):
        first = await client.complete(role="answer", messages=[{"role": "user", "content": "hi"}])
        second = await client.complete(role="answer", messages=[{"role": "user", "content": "hi"}])

    assert call_count == 1  # second call served from cache
    assert first.content == second.content == "first response"


@pytest.mark.asyncio
async def test_complete_bypasses_cache_when_disabled(monkeypatch, isolated_llm_cache):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("RAG_LLM_CACHE_ENABLED", "false")
    monkeypatch.setenv("OPENROUTER_MODEL_ANSWER", "model-a")
    call_count = 0

    async def fake_chat(*, model, **kwargs):
        nonlocal call_count
        call_count += 1
        return MagicMock(choices=[MagicMock(message=MagicMock(content=f"response-{call_count}"))])

    client = LLMClient()
    with patch.object(client, "_raw_chat", side_effect=fake_chat):
        first = await client.complete(role="answer", messages=[{"role": "user", "content": "hi"}])
        second = await client.complete(role="answer", messages=[{"role": "user", "content": "hi"}])

    assert call_count == 2
    assert first.content == "response-1"
    assert second.content == "response-2"


@pytest.mark.asyncio
async def test_complete_cache_key_distinguishes_different_messages(monkeypatch, isolated_llm_cache):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL_ANSWER", "model-a")

    async def fake_chat(*, model, messages, **kwargs):
        return MagicMock(choices=[MagicMock(message=MagicMock(content=messages[0]["content"]))])

    client = LLMClient()
    with patch.object(client, "_raw_chat", side_effect=fake_chat):
        a = await client.complete(role="answer", messages=[{"role": "user", "content": "question A"}])
        b = await client.complete(role="answer", messages=[{"role": "user", "content": "question B"}])

    assert a.content == "question A"
    assert b.content == "question B"


@pytest.mark.asyncio
async def test_complete_uses_provider_reported_usage_when_present(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL_ANSWER", "model-a")
    monkeypatch.setenv("RAG_LLM_CACHE_ENABLED", "false")

    async def fake_chat(*, model, **kwargs):
        usage = MagicMock(prompt_tokens=123, completion_tokens=45)
        return MagicMock(choices=[MagicMock(message=MagicMock(content="hi"))], usage=usage)

    client = LLMClient()
    with patch.object(client, "_raw_chat", side_effect=fake_chat):
        result = await client.complete(role="answer", messages=[{"role": "user", "content": "hi"}])

    assert result.tokens_in == 123
    assert result.tokens_out == 45


@pytest.mark.asyncio
async def test_complete_estimates_tokens_when_usage_absent(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL_ANSWER", "model-a")
    monkeypatch.setenv("RAG_LLM_CACHE_ENABLED", "false")

    async def fake_chat(*, model, **kwargs):
        return MagicMock(choices=[MagicMock(message=MagicMock(content="a longer reply here"))], usage=None)

    client = LLMClient()
    with patch.object(client, "_raw_chat", side_effect=fake_chat):
        result = await client.complete(role="answer", messages=[{"role": "user", "content": "hi"}])

    assert isinstance(result.tokens_in, int) and result.tokens_in > 0
    assert isinstance(result.tokens_out, int) and result.tokens_out > 0
    assert result.cost_usd is None  # unpriced, non-":free" model — unknown, not zero


def test_groq_provider_models_default_and_override(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    # Defaults
    assert get_models_for_role("answer") == ["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b"]

    # Explicit override
    monkeypatch.setenv("GROQ_MODEL_ANSWER", "llama-3.1-8b-instant, mixtral-8x7b-32768")
    assert get_models_for_role("answer") == ["llama-3.1-8b-instant", "mixtral-8x7b-32768"]


def test_groq_client_init_requires_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY is not set or empty"):
        LLMClient()


@pytest.mark.asyncio
async def test_groq_client_completion(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-testkey")
    monkeypatch.setenv("GROQ_MODEL_ANSWER", "groq-llama-3.3")

    async def fake_chat(*, model, **kwargs):
        return MagicMock(choices=[MagicMock(message=MagicMock(content="groq response"))])

    client = LLMClient()
    assert client.provider == "groq"
    with patch.object(client, "_raw_chat", side_effect=fake_chat):
        result = await client.complete(role="answer", messages=[{"role": "user", "content": "hello"}])
    assert result.content == "groq response"
    assert result.model_used == "groq-llama-3.3"


def test_nvidia_provider_models_default_and_override(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    # Pin the env explicitly so the "default" assertion is hermetic — it must
    # not depend on whether the local/CI shell happens to export NVIDIA_MODEL_ANSWER
    # (the autouse bypass_auth fixture imports app.main, which loads microService/.env).
    monkeypatch.setenv("NVIDIA_MODEL_ANSWER", "meta/llama-3.1-8b-instruct")
    assert get_models_for_role("answer") == ["meta/llama-3.1-8b-instruct"]

    # Explicit override
    monkeypatch.setenv("NVIDIA_MODEL_ANSWER", "meta/llama-3.3-70b-instruct, z-ai/glm-5.2")
    assert get_models_for_role("answer") == ["meta/llama-3.3-70b-instruct", "z-ai/glm-5.2"]


def test_nvidia_client_init_requires_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="NVIDIA_API_KEY is not set or empty"):
        LLMClient()


@pytest.mark.asyncio
async def test_nvidia_client_completion(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-testkey")
    monkeypatch.setenv("NVIDIA_MODEL_ANSWER", "z-ai/glm-5.2")

    async def fake_chat(*, model, **kwargs):
        return MagicMock(choices=[MagicMock(message=MagicMock(content="nvidia response"))])

    client = LLMClient()
    assert client.provider == "nvidia"
    with patch.object(client, "_raw_chat", side_effect=fake_chat):
        result = await client.complete(role="answer", messages=[{"role": "user", "content": "hello"}])
    assert result.content == "nvidia response"
    assert result.model_used == "z-ai/glm-5.2"



