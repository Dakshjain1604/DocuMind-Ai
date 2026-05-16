"""OpenRouter LLM client with role-based fallback chains.

Roles read an ordered list of model IDs from env (comma-separated).
On 429/5xx/timeout the client walks the list. Embeddings live elsewhere
(see core/embeddings.py).
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator

from openai import AsyncOpenAI


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


def _is_retriable(err: Exception) -> bool:
    msg = str(err).lower()
    return any(s in msg for s in ("429", "rate", "timeout", "500", "502", "503", "504"))


class LLMClient:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            timeout=60.0,
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
        models = get_models_for_role(role)
        last_err: Exception | None = None
        for idx, model in enumerate(models):
            try:
                kwargs: dict[str, Any] = {"messages": messages, "temperature": temperature}
                if response_format is not None:
                    kwargs["response_format"] = response_format
                resp = await self._raw_chat(model=model, **kwargs)
                return LLMResult(
                    content=resp.choices[0].message.content,
                    model_used=model,
                    fallback_count=idx,
                )
            except Exception as e:
                last_err = e
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
                if not _is_retriable(e) and idx == 0:
                    raise
        raise RuntimeError(f"All models failed during streaming for role={role}: {last_err}")


_singleton: LLMClient | None = None


def get_llm() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton
