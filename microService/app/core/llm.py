"""OpenRouter LLM client with role-based fallback chains.

Roles read an ordered list of model IDs from env (comma-separated).
On 429/5xx/timeout the client walks the list. Embeddings live elsewhere
(see core/embeddings.py).
"""
from __future__ import annotations

import asyncio
import json
import os
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
    env_key = f"OPENROUTER_MODEL_{role.upper()}"
    raw = os.environ.get(env_key)
    if not raw:
        raise LLMRoleNotConfigured(f"env var {env_key} is unset")
    return [m.strip() for m in raw.split(",") if m.strip()]


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
    Includes 404 (model deprecated / unavailable on OpenRouter) and 5xx
    in addition to rate-limits / timeouts."""
    msg = str(err).lower()
    return any(
        s in msg
        for s in (
            "404", "not found", "no endpoints",
            "429", "rate", "timeout",
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
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set or empty — set it in microService/.env "
                "before starting the service."
            )
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
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
    ) -> LLMResult:
        settings = get_settings()
        models = get_models_for_role(role)

        cache = get_disk_cache() if settings.llm_cache_enabled else None
        cache_key = None
        if cache is not None:
            # Keyed on the formatted content itself (not a prompt-version
            # constant) plus the resolved model list — either the messages
            # or the role's configured models changing busts the cache
            # automatically (self-invalidating), so a stale completion from
            # a since-replaced model is never served.
            cache_key = cache.make_key("llm", role, models, messages, temperature, response_format)
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        last_err: Exception | None = None
        for idx, model in enumerate(models):
            try:
                kwargs: dict[str, Any] = {"messages": messages, "temperature": temperature}
                if response_format is not None:
                    kwargs["response_format"] = response_format
                resp = await self._raw_chat(model=model, **kwargs)
                content = resp.choices[0].message.content

                # Prefer provider-reported usage (OpenRouter proxies OpenAI-
                # style `usage`); fall back to a local tiktoken estimate when
                # absent or malformed (also handles test mocks gracefully —
                # a MagicMock attribute is not an int, so it's ignored).
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
                        f"OpenRouter authentication failed for model={model} — check OPENROUTER_API_KEY. "
                        f"Original error: {e}"
                    ) from e
                if not _is_retriable(e) and idx == 0:
                    raise
        raise RuntimeError(f"All models in fallback chain failed for role={role}: {last_err}")

    async def stream(
        self,
        *,
        role: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> AsyncIterator[tuple[str, str]]:
        """Yields (delta_text, model_used) tuples. Falls back across the role chain
        only if the FIRST chunk fails — once streaming has started, partial output is preserved."""
        models = get_models_for_role(role)
        last_err: Exception | None = None
        for idx, model in enumerate(models):
            try:
                stream = await self._client.chat.completions.create(
                    model=model, messages=messages, temperature=temperature, stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield delta, model
                return
            except Exception as e:
                last_err = e
                if _is_auth_error(e):
                    raise RuntimeError(
                        f"OpenRouter authentication failed for model={model} — check OPENROUTER_API_KEY. "
                        f"Original error: {e}"
                    ) from e
                if not _is_retriable(e) and idx == 0:
                    raise
        raise RuntimeError(f"All models failed during streaming for role={role}: {last_err}")


_singleton: LLMClient | None = None


def get_llm() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton
