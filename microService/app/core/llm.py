"""Unified LLM client supporting OpenRouter and Groq with role-based fallback chains.

Roles read an ordered list of model IDs from Settings (env + defaults, see
app/config/settings.py). On 429/5xx/timeout the client walks the list.
Embeddings live elsewhere (see core/embeddings.py).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from app.config.settings import get_settings
from app.core.cache import get_disk_cache
from app.core.observability import count_tokens, estimate_cost_usd


class LLMRoleNotConfigured(Exception):
    pass


VALID_ROLES = {"extract", "answer", "rewrite", "rerank"}


def get_models_for_role(role: str) -> list[str]:
    settings = get_settings()
    provider = settings.llm_provider
    chains_by_provider = {
        "groq": settings.groq_models,
        "nvidia": settings.nvidia_models,
        "openrouter": settings.openrouter_models,
    }
    env_key = f"{provider.upper()}_MODEL_{role.upper()}"
    models = chains_by_provider.get(provider, {}).get(role)
    if not models:
        raise LLMRoleNotConfigured(
            f"Role '{role}' is not configured for provider '{provider}' (set {env_key})"
        )
    return models


@dataclass
class LLMResult:
    content: str
    model_used: str
    fallback_count: int
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None


def _is_retriable(err: Exception) -> bool:
    """Errors that warrant walking to the next model in the fallback chain.
    Includes 404 (model deprecated / unavailable on provider) and 5xx
    in addition to rate-limits / timeouts."""
    msg = str(err).lower()
    return any(
        s in msg
        for s in (
            "404", "not found", "no endpoints",
            "429", "rate", "timeout", "timed out",
            "500", "502", "503", "504",
            "model_not_found", "model not available",
        )
    )


def _is_auth_error(err: Exception) -> bool:
    """401/403 fail identically for every model in the fallback chain, so
    they're worth detecting explicitly rather than exhausting retries."""
    msg = str(err).lower()
    return any(s in msg for s in ("401", "403", "unauthorized", "invalid api key", "authentication"))


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.provider = settings.llm_provider

        if self.provider == "groq":
            api_key = (settings.groq_api_key or "").strip()
            if not api_key:
                raise RuntimeError(
                    "GROQ_API_KEY is not set or empty — set it in microService/.env "
                    "before starting the service."
                )
            base_url = settings.groq_base_url
        elif self.provider == "nvidia":
            api_key = (settings.nvidia_api_key or "").strip()
            if not api_key:
                raise RuntimeError(
                    "NVIDIA_API_KEY is not set or empty — set it in microService/.env "
                    "before starting the service."
                )
            base_url = settings.nvidia_base_url
        else:
            api_key = (settings.openrouter_api_key or "").strip()
            if not api_key:
                raise RuntimeError(
                    "OPENROUTER_API_KEY is not set or empty — set it in microService/.env "
                    "before starting the service."
                )
            base_url = settings.openrouter_base_url

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=120.0,
        )

    async def _raw_chat(self, *, model: str, **kwargs: Any) -> Any:
        return await self._client.chat.completions.create(model=model, **kwargs)

    async def complete(
        self,
        *,
        role: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        response_format: dict | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        settings = get_settings()
        models = get_models_for_role(role)

        cache = get_disk_cache() if settings.llm_cache_enabled else None
        cache_key = None
        if cache is not None:
            # Keyed on provider + content + role model list
            cache_key = cache.make_key("llm", self.provider, role, models, messages, temperature, response_format)
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        last_err: Exception | None = None
        for idx, model in enumerate(models):
            try:
                kwargs: dict[str, Any] = {"messages": messages, "temperature": temperature}
                if response_format is not None:
                    kwargs["response_format"] = response_format
                if max_tokens is not None:
                    kwargs["max_tokens"] = max_tokens
                resp = await self._raw_chat(model=model, **kwargs)
                if not resp.choices:
                    raise ValueError(f"Model {model} returned empty choices list")
                content = resp.choices[0].message.content

                # Prefer provider-reported usage; fall back to tiktoken estimate
                usage = getattr(resp, "usage", None)
                tokens_in = getattr(usage, "prompt_tokens", None) if usage is not None else None
                tokens_out = getattr(usage, "completion_tokens", None) if usage is not None else None
                if not isinstance(tokens_in, int):
                    tokens_in = count_tokens(json.dumps(messages))
                if not isinstance(tokens_out, int):
                    tokens_out = count_tokens(content or "")

                result = LLMResult(
                    content=content,
                    model_used=model,
                    fallback_count=idx,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=estimate_cost_usd(model, tokens_in, tokens_out),
                )
                if cache is not None:
                    cache.put(cache_key, result, ttl=settings.llm_cache_ttl_s)
                return result
            except Exception as e:
                last_err = e
                if _is_auth_error(e):
                    raise RuntimeError(
                        f"{self.provider.capitalize()} authentication failed for model={model} — check API key. "
                        f"Original error: {e}"
                    ) from e
                if not _is_retriable(e) and idx == 0:
                    raise
        raise RuntimeError(f"All models in fallback chain failed for role={role} on provider={self.provider}: {last_err}")

    async def stream(
        self,
        *,
        role: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> AsyncIterator[tuple[str, str]]:
        """Yields (delta_text, model_used) tuples. Falls back across the role chain
        only if the FIRST chunk fails — once streaming has started, partial output is preserved."""
        models = get_models_for_role(role)
        last_err: Exception | None = None
        for idx, model in enumerate(models):
            try:
                kwargs: dict[str, Any] = {
                    "model": model, "messages": messages, "temperature": temperature, "stream": True,
                }
                if max_tokens is not None:
                    kwargs["max_tokens"] = max_tokens
                stream = await self._client.chat.completions.create(**kwargs)
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield delta, model
                return
            except Exception as e:
                last_err = e
                if _is_auth_error(e):
                    raise RuntimeError(
                        f"{self.provider.capitalize()} authentication failed for model={model} — check API key. "
                        f"Original error: {e}"
                    ) from e
                if not _is_retriable(e) and idx == 0:
                    raise
        raise RuntimeError(f"All models failed during streaming for role={role} on provider={self.provider}: {last_err}")


_singleton: LLMClient | None = None


def get_llm() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton

