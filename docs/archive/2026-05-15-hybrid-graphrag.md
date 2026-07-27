# Hybrid GraphRAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-shot vector RAG in `microService/` with a hybrid GraphRAG pipeline (vector + BM25 + knowledge-graph traversal fused via Reciprocal Rank Fusion), backed by OpenRouter with a per-role model fallback chain, streamed end-to-end via SSE, with an interactive graph viz in the Next.js frontend.

**Architecture:** A new layered Python package — `core/` (LLM client, chunker, cache, streaming, logging), `indexing/` (pipeline + graph extraction + community summaries + persistence), `retrieval/` (rewriter + 3 retrievers + RRF fusion + optional rerank + orchestrator) — feeds three new FastAPI routes (`/index`, `/query`, `/graph/{doc_hash}`). Documents are content-hash-addressed; per-process LRU cache replaces the broken global clear. Frontend adds an SSE proxy route, streaming chat UI, citation chips, and `react-force-graph-2d`-based graph view.

**Tech Stack:** FastAPI, OpenRouter (via openai SDK, OpenAI-compatible mode), LangChain (only for embeddings + Chroma vector store), Chroma (existing), NetworkX, python-louvain, rank-bm25, tiktoken, pytest + respx + httpx, Next.js 15 App Router, react-force-graph-2d.

**Spec:** `docs/superpowers/specs/2026-05-15-hybrid-graphrag-design.md`

---

## Phase 0 — Setup

### Task 1: Create the new backend package skeleton

**Files:**
- Create: `microService/app/core/__init__.py`
- Create: `microService/app/indexing/__init__.py`
- Create: `microService/app/retrieval/__init__.py`
- Create: `microService/tests/__init__.py`
- Create: `microService/tests/unit/__init__.py`
- Create: `microService/tests/integration/__init__.py`
- Create: `microService/tests/api/__init__.py`
- Create: `microService/tests/e2e/__init__.py`
- Create: `microService/tests/fixtures/.gitkeep`
- Create: `microService/tests/fixtures/llm_responses/.gitkeep`

- [ ] **Step 1: Create the directories**

```bash
cd microService
mkdir -p app/core app/indexing app/retrieval \
         tests/unit tests/integration tests/api tests/e2e \
         tests/fixtures/llm_responses
```

- [ ] **Step 2: Create empty `__init__.py` files and placeholders**

```bash
touch app/core/__init__.py \
      app/indexing/__init__.py \
      app/retrieval/__init__.py \
      tests/__init__.py \
      tests/unit/__init__.py \
      tests/integration/__init__.py \
      tests/api/__init__.py \
      tests/e2e/__init__.py \
      tests/fixtures/.gitkeep \
      tests/fixtures/llm_responses/.gitkeep
```

- [ ] **Step 3: Verify**

Run: `find microService/app/core microService/app/indexing microService/app/retrieval microService/tests -type f | sort`
Expected: shows all `__init__.py` and `.gitkeep` files.

- [ ] **Step 4: Commit**

```bash
git add microService/app/core microService/app/indexing microService/app/retrieval microService/tests
git commit -m "feat(rag): scaffold core/indexing/retrieval packages and test layout"
```

---

### Task 2: Update Python dependencies

**Files:**
- Modify: `microService/requirements.txt`

- [ ] **Step 1: Replace requirements.txt**

Open `microService/requirements.txt` and replace its contents with:

```
fastapi
uvicorn
python-multipart
python-dotenv
aiofiles
httpx
openai>=1.0
tiktoken

# Document loading + chunking + vector store
langchain
langchain-core
langchain-community
langchain-openai
langchain-chroma
pypdf
unstructured

# Hybrid retrieval
rank-bm25
networkx
python-louvain

# Testing
pytest
pytest-asyncio
respx
```

Removed: `langchain-redis`, `redis` (unused). Kept `langchain-openai` for OpenAI embeddings + `langchain-chroma` for the existing vector store. Direct `openai>=1.0` is the OpenRouter client.

- [ ] **Step 2: Install**

```bash
cd microService
pip install -r requirements.txt
```

Expected: all packages install without conflicts.

- [ ] **Step 3: Commit**

```bash
git add microService/requirements.txt
git commit -m "build(rag): pin deps for hybrid retrieval + tests"
```

---

### Task 3: Add OpenRouter env vars and gitignore the artifact dir

**Files:**
- Modify: `microService/.env` (user does this manually — file is gitignored)
- Create: `microService/.env.example`
- Modify: `.gitignore`

- [ ] **Step 1: Create `.env.example` to document required vars**

Create `microService/.env.example`:

```
# OpenAI (embeddings only — text-embedding-3-large)
OPENAI_API_KEY=sk-...

# OpenRouter (all chat completions)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Per-role model fallback chains (comma-separated, free models first)
OPENROUTER_MODEL_EXTRACT=deepseek/deepseek-chat-v3-0324:free,meta-llama/llama-3.3-70b-instruct:free,openai/gpt-4o-mini
OPENROUTER_MODEL_ANSWER=meta-llama/llama-3.3-70b-instruct:free,deepseek/deepseek-chat-v3-0324:free,openai/gpt-4o-mini
OPENROUTER_MODEL_REWRITE=meta-llama/llama-3.1-8b-instruct:free
OPENROUTER_MODEL_RERANK=qwen/qwen-2.5-7b-instruct:free

# Feature flags
RAG_ENABLE_RERANK=false

# Cache / paths
RAG_PERSIST_DIR=./local_chroma
RAG_MAX_CACHE_DOCS=3
RAG_MAX_FILE_MB=25
```

- [ ] **Step 2: Add the same keys to `microService/.env`** (manually — keep the existing `OPENAI_API_KEY` value, add the rest with real values).

You must obtain an OpenRouter API key from https://openrouter.ai/keys.

- [ ] **Step 3: Ensure `microService/local_chroma/` is gitignored**

Open `.gitignore`. Confirm `microService/local_chroma/` is present (the existing gitignore has `microService/app/local_chroma/` — the new code persists under `microService/local_chroma/`, so add it).

Add a line:

```
microService/local_chroma/
```

if it isn't already there (the existing entry is `microService/app/local_chroma/`).

- [ ] **Step 4: Commit**

```bash
git add microService/.env.example .gitignore
git commit -m "build(rag): document required env vars and gitignore artifact dir"
```

---

### Task 4: Pytest configuration

**Files:**
- Create: `microService/pytest.ini`
- Create: `microService/tests/conftest.py`
- Create: `microService/run_tests.sh`

- [ ] **Step 1: Create `microService/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

- [ ] **Step 2: Create `microService/tests/conftest.py`**

```python
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


@pytest.fixture
def tmp_persist_dir(tmp_path, monkeypatch):
    """Isolated persist directory per test."""
    p = tmp_path / "local_chroma"
    p.mkdir()
    monkeypatch.setenv("RAG_PERSIST_DIR", str(p))
    return p
```

- [ ] **Step 3: Create `microService/run_tests.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
pytest "$@"
```

```bash
chmod +x microService/run_tests.sh
```

- [ ] **Step 4: Verify pytest collects cleanly**

Run: `cd microService && ./run_tests.sh --collect-only`
Expected: collects 0 tests, no errors.

- [ ] **Step 5: Commit**

```bash
git add microService/pytest.ini microService/tests/conftest.py microService/run_tests.sh
git commit -m "test(rag): pytest config and shared fixtures"
```

---

## Phase 1 — Core Primitives

### Task 5: `core/llm.py` — OpenRouter client with role-based fallback

**Files:**
- Create: `microService/app/core/llm.py`
- Create: `microService/tests/unit/test_llm.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/unit/test_llm.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd microService && ./run_tests.sh tests/unit/test_llm.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_models_for_role' from 'app.core.llm'`

- [ ] **Step 3: Implement `core/llm.py`**

Create `microService/app/core/llm.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd microService && ./run_tests.sh tests/unit/test_llm.py -v`
Expected: PASS — 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add microService/app/core/llm.py microService/tests/unit/test_llm.py
git commit -m "feat(rag): OpenRouter client with per-role fallback chains"
```

---

### Task 6: `core/embeddings.py` — single source for the embedding model

**Files:**
- Create: `microService/app/core/embeddings.py`

- [ ] **Step 1: Implement**

Create `microService/app/core/embeddings.py`:

```python
"""Embedding model — OpenAI text-embedding-3-large, used by Chroma."""
import os
from functools import lru_cache
from langchain_openai import OpenAIEmbeddings


@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="text-embedding-3-large",
        openai_api_key=os.environ["OPENAI_API_KEY"],
    )
```

- [ ] **Step 2: Smoke-import**

Run: `cd microService && python -c "from app.core.embeddings import get_embeddings; print(get_embeddings().model)"`
Expected: prints `text-embedding-3-large`.

- [ ] **Step 3: Commit**

```bash
git add microService/app/core/embeddings.py
git commit -m "feat(rag): single-source embedding model factory"
```

---

### Task 7: `core/chunker.py` — recursive chunking with metadata preservation

**Files:**
- Create: `microService/app/core/chunker.py`
- Create: `microService/tests/unit/test_chunker.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/unit/test_chunker.py`:

```python
from langchain_core.documents import Document
from app.core.chunker import chunk_documents


def test_chunks_preserve_source_metadata():
    docs = [Document(page_content="abc " * 1000, metadata={"source": "x.pdf", "page": 3})]
    chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1
    for c in chunks:
        assert c.metadata["source"] == "x.pdf"
        assert c.metadata["page"] == 3
        assert "chunk_id" in c.metadata


def test_chunks_have_sequential_ids():
    docs = [Document(page_content="x" * 5000, metadata={"source": "y.pdf"})]
    chunks = chunk_documents(docs, chunk_size=500, chunk_overlap=50)
    ids = [c.metadata["chunk_id"] for c in chunks]
    assert ids == list(range(len(chunks)))


def test_empty_input_returns_empty():
    assert chunk_documents([], chunk_size=500, chunk_overlap=50) == []
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/unit/test_chunker.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Create `microService/app/core/chunker.py`:

```python
"""Document chunking with metadata preservation."""
from __future__ import annotations
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


def chunk_documents(
    docs: list[Document],
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[Document]:
    if not docs:
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    out: list[Document] = []
    counter = 0
    for d in docs:
        for piece in splitter.split_text(d.page_content):
            meta = dict(d.metadata)
            meta["chunk_id"] = counter
            out.append(Document(page_content=piece, metadata=meta))
            counter += 1
    return out
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/unit/test_chunker.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add microService/app/core/chunker.py microService/tests/unit/test_chunker.py
git commit -m "feat(rag): recursive chunker with chunk_id metadata"
```

---

### Task 8: `core/cache.py` — per-doc LRU cache (fixes the global-clear bug)

**Files:**
- Create: `microService/app/core/cache.py`
- Create: `microService/tests/unit/test_cache.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/unit/test_cache.py`:

```python
import pytest
from app.core.cache import DocLRUCache


def test_cache_returns_stored_value():
    c = DocLRUCache(max_size=3)
    c.put("hash-a", {"v": 1})
    assert c.get("hash-a") == {"v": 1}


def test_cache_returns_none_on_miss():
    c = DocLRUCache(max_size=3)
    assert c.get("nope") is None


def test_cache_lru_eviction_when_full():
    c = DocLRUCache(max_size=2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert c.get("a") is None  # evicted
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_cache_lru_promotes_on_access():
    c = DocLRUCache(max_size=2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")          # promote a
    c.put("c", 3)       # should evict b, not a
    assert c.get("a") == 1
    assert c.get("b") is None
    assert c.get("c") == 3


def test_cache_uploading_doc_b_does_not_evict_doc_a_when_room_exists():
    """Regression test for the original clear_document_cache() bug.
    Uploading a second doc must NOT wipe the first when cache has room."""
    c = DocLRUCache(max_size=3)
    c.put("doc-a", "first")
    c.put("doc-b", "second")
    assert c.get("doc-a") == "first"
    assert c.get("doc-b") == "second"
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/unit/test_cache.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Create `microService/app/core/cache.py`:

```python
"""Per-doc LRU cache. Replaces the prior global clear-on-every-upload behavior."""
from __future__ import annotations
from collections import OrderedDict
from typing import Any


class DocLRUCache:
    def __init__(self, max_size: int = 3) -> None:
        self._data: OrderedDict[str, Any] = OrderedDict()
        self._max = max_size

    def get(self, key: str) -> Any | None:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: Any) -> None:
        if key in self._data:
            self._data.move_to_end(key)
            self._data[key] = value
            return
        self._data[key] = value
        if len(self._data) > self._max:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)


import os
_singleton: DocLRUCache | None = None


def get_cache() -> DocLRUCache:
    global _singleton
    if _singleton is None:
        _singleton = DocLRUCache(max_size=int(os.environ.get("RAG_MAX_CACHE_DOCS", "3")))
    return _singleton
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/unit/test_cache.py -v`
Expected: PASS — 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add microService/app/core/cache.py microService/tests/unit/test_cache.py
git commit -m "feat(rag): per-doc LRU cache (replaces broken global clear)"
```

---

### Task 9: `core/streaming.py` — SSE event helpers

**Files:**
- Create: `microService/app/core/streaming.py`
- Create: `microService/tests/unit/test_streaming.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/unit/test_streaming.py`:

```python
import json
from app.core.streaming import sse_event


def test_sse_event_formats_with_event_name_and_json_data():
    out = sse_event("progress", {"step": "chunking", "n": 12})
    assert out.startswith("event: progress\n")
    assert "data: " in out
    body = out.split("data: ", 1)[1].rstrip("\n\n")
    assert json.loads(body) == {"step": "chunking", "n": 12}
    assert out.endswith("\n\n")


def test_sse_event_handles_done_with_empty_data():
    out = sse_event("done", {})
    assert "event: done" in out
    assert "data: {}" in out
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/unit/test_streaming.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Create `microService/app/core/streaming.py`:

```python
"""SSE event-stream helpers."""
import json
from typing import Any


def sse_event(name: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {name}\ndata: {payload}\n\n"


def sse_error(message: str, *, partial: bool = False) -> str:
    return sse_event("error", {"message": message, "partial": partial})


def sse_token(text: str) -> str:
    return sse_event("token", {"text": text})
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/unit/test_streaming.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add microService/app/core/streaming.py microService/tests/unit/test_streaming.py
git commit -m "feat(rag): SSE event helpers"
```

---

### Task 10: `core/logging.py` — structured JSON request logs

**Files:**
- Create: `microService/app/core/logging.py`

- [ ] **Step 1: Implement**

Create `microService/app/core/logging.py`:

```python
"""Lightweight structured logging — stdout JSON per request stage."""
import json
import sys
import time
import uuid
from contextlib import contextmanager


def log_event(event: str, **fields) -> None:
    line = json.dumps({"ts": time.time(), "event": event, **fields}, default=str)
    print(line, file=sys.stdout, flush=True)


@contextmanager
def timed_stage(stage: str, request_id: str, **extra):
    start = time.perf_counter()
    try:
        yield
        duration_ms = (time.perf_counter() - start) * 1000
        log_event("stage_ok", stage=stage, request_id=request_id, duration_ms=round(duration_ms, 1), **extra)
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        log_event("stage_err", stage=stage, request_id=request_id, duration_ms=round(duration_ms, 1), error=str(e), **extra)
        raise


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]
```

- [ ] **Step 2: Smoke test**

Run: `cd microService && python -c "from app.core.logging import log_event, new_request_id; log_event('boot', request_id=new_request_id())"`
Expected: prints one JSON line to stdout.

- [ ] **Step 3: Commit**

```bash
git add microService/app/core/logging.py
git commit -m "feat(rag): structured stdout JSON logging"
```

---

## Phase 2 — Retrieval Primitives (pure functions first)

### Task 11: `retrieval/fusion.py` — Reciprocal Rank Fusion

**Files:**
- Create: `microService/app/retrieval/fusion.py`
- Create: `microService/tests/unit/test_fusion.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/unit/test_fusion.py`:

```python
from app.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_merges_two_overlapping_lists():
    a = ["x", "y", "z"]
    b = ["y", "x", "w"]
    result = reciprocal_rank_fusion([a, b], k=60)
    assert result[0] in {"x", "y"}
    assert "w" in result
    assert "z" in result


def test_rrf_handles_disjoint_results():
    a = ["a", "b"]
    b = ["c", "d"]
    result = reciprocal_rank_fusion([a, b], k=60)
    assert set(result) == {"a", "b", "c", "d"}
    assert len(result) == 4


def test_rrf_handles_empty_branches():
    assert reciprocal_rank_fusion([], k=60) == []
    assert reciprocal_rank_fusion([[], []], k=60) == []


def test_rrf_respects_top_k():
    a = ["a", "b", "c", "d", "e"]
    b = ["e", "d", "c", "b", "a"]
    result = reciprocal_rank_fusion([a, b], k=60, top_k=3)
    assert len(result) == 3


def test_rrf_higher_ranks_score_higher():
    a = ["winner", "loser"]
    b = ["winner", "loser"]
    result = reciprocal_rank_fusion([a, b], k=60)
    assert result[0] == "winner"
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/unit/test_fusion.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Create `microService/app/retrieval/fusion.py`:

```python
"""Reciprocal Rank Fusion — pure function, no I/O."""
from __future__ import annotations
from typing import Hashable, Sequence


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[Hashable]],
    *,
    k: int = 60,
    top_k: int | None = None,
) -> list:
    scores: dict[Hashable, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank + 1)
    sorted_items = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    items = [item for item, _ in sorted_items]
    return items[:top_k] if top_k is not None else items
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/unit/test_fusion.py -v`
Expected: PASS — 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add microService/app/retrieval/fusion.py microService/tests/unit/test_fusion.py
git commit -m "feat(rag): reciprocal rank fusion (pure function)"
```

---

### Task 12: `retrieval/bm25.py` — in-memory BM25 retriever

**Files:**
- Create: `microService/app/retrieval/bm25.py`
- Create: `microService/tests/unit/test_bm25.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/unit/test_bm25.py`:

```python
from app.retrieval.bm25 import BM25Index


def test_bm25_ranks_relevant_doc_higher():
    idx = BM25Index.build([
        "the mitochondria produces atp through cellular respiration",
        "the nucleus contains the dna",
        "ribosomes synthesize proteins",
    ])
    hits = idx.search("what produces atp", top_k=2)
    assert hits[0][0] == 0  # chunk index 0 should rank first


def test_bm25_empty_corpus_returns_empty():
    idx = BM25Index.build([])
    assert idx.search("anything", top_k=5) == []


def test_bm25_serialize_roundtrip(tmp_path):
    corpus = ["alpha beta gamma", "beta gamma delta"]
    idx = BM25Index.build(corpus)
    p = tmp_path / "bm25.pkl"
    idx.save(p)
    reloaded = BM25Index.load(p)
    a = idx.search("alpha", top_k=2)
    b = reloaded.search("alpha", top_k=2)
    assert a == b
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/unit/test_bm25.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Create `microService/app/retrieval/bm25.py`:

```python
"""In-memory BM25 over chunk text."""
from __future__ import annotations
import pickle
import re
from pathlib import Path
from rank_bm25 import BM25Okapi

_token_re = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _token_re.findall(text)]


class BM25Index:
    def __init__(self, tokenized_corpus: list[list[str]]) -> None:
        self._tokens = tokenized_corpus
        self._bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None

    @classmethod
    def build(cls, corpus: list[str]) -> "BM25Index":
        return cls([_tokenize(t) for t in corpus])

    def search(self, query: str, *, top_k: int = 10) -> list[tuple[int, float]]:
        if self._bm25 is None:
            return []
        q = _tokenize(query)
        scores = self._bm25.get_scores(q)
        ranked = sorted(enumerate(scores), key=lambda kv: kv[1], reverse=True)
        return ranked[:top_k]

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(pickle.dumps(self._tokens))

    @classmethod
    def load(cls, path: str | Path) -> "BM25Index":
        return cls(pickle.loads(Path(path).read_bytes()))
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/unit/test_bm25.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add microService/app/retrieval/bm25.py microService/tests/unit/test_bm25.py
git commit -m "feat(rag): BM25 index with pickle persistence"
```

---

### Task 13: `retrieval/vector.py` — Chroma similarity wrapper

**Files:**
- Create: `microService/app/retrieval/vector.py`

- [ ] **Step 1: Implement**

Create `microService/app/retrieval/vector.py`:

```python
"""Thin wrapper over Chroma — returns (chunk_id, score) tuples."""
from __future__ import annotations
from langchain_chroma import Chroma


def vector_search(
    chroma: Chroma,
    query: str,
    *,
    top_k: int = 10,
) -> list[tuple[int, float]]:
    """Returns list of (chunk_id, score). Lower distance == better, so we invert."""
    results = chroma.similarity_search_with_score(query, k=top_k)
    out: list[tuple[int, float]] = []
    for doc, distance in results:
        cid = doc.metadata.get("chunk_id")
        if cid is None:
            continue
        out.append((int(cid), -float(distance)))
    return out
```

No test in isolation — exercised in the API/e2e tests where a real Chroma is available.

- [ ] **Step 2: Smoke import**

Run: `cd microService && python -c "from app.retrieval.vector import vector_search; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add microService/app/retrieval/vector.py
git commit -m "feat(rag): Chroma vector-search wrapper returning chunk_ids"
```

---

## Phase 3 — Indexing Pipeline

### Task 14: `indexing/graph_extractor.py` — LLM entity/relation extraction

**Files:**
- Create: `microService/app/indexing/graph_extractor.py`
- Create: `microService/tests/integration/test_graph_extractor.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/integration/test_graph_extractor.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.documents import Document
from app.indexing.graph_extractor import extract_graph, ExtractionResult


@pytest.mark.asyncio
async def test_extract_graph_parses_valid_response():
    fake = ExtractionResult(
        entities=[{"id": "Mitochondria", "type": "Organelle", "description": "ATP producer"}],
        relationships=[{"src": "Mitochondria", "dst": "ATP", "type": "produces", "description": "via respiration"}],
    )
    mock_result = AsyncMock(return_value=fake)
    with patch("app.indexing.graph_extractor._extract_one", mock_result):
        chunks = [Document(page_content="mitochondria produce ATP", metadata={"chunk_id": 0})]
        merged = await extract_graph(chunks, concurrency=2)
    assert len(merged.entities) == 1
    assert merged.entities[0]["id"] == "Mitochondria"
    assert len(merged.relationships) == 1


@pytest.mark.asyncio
async def test_extract_graph_dedupes_entities_across_chunks():
    same = ExtractionResult(
        entities=[{"id": "X", "type": "T", "description": "d"}],
        relationships=[],
    )
    with patch("app.indexing.graph_extractor._extract_one", AsyncMock(return_value=same)):
        chunks = [
            Document(page_content="chunk a", metadata={"chunk_id": 0}),
            Document(page_content="chunk b", metadata={"chunk_id": 1}),
        ]
        merged = await extract_graph(chunks, concurrency=2)
    assert len(merged.entities) == 1


@pytest.mark.asyncio
async def test_extract_graph_skips_chunks_that_fail_twice():
    async def flaky(client, doc):
        raise ValueError("bad json")
    with patch("app.indexing.graph_extractor._extract_one", flaky):
        chunks = [Document(page_content="x", metadata={"chunk_id": 0})]
        merged = await extract_graph(chunks, concurrency=2)
    assert merged.entities == []
    assert merged.warnings  # records that chunk 0 failed
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/integration/test_graph_extractor.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Create `microService/app/indexing/graph_extractor.py`:

```python
"""LLM-based entity + relationship extraction per chunk."""
from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass, field
from typing import Any
from langchain_core.documents import Document

from app.core.llm import LLMClient, get_llm

EXTRACTION_PROMPT = """You extract a knowledge graph from a passage of text.

Return ONLY valid JSON matching this schema:
{
  "entities":      [{"id": "string", "type": "string", "description": "string"}],
  "relationships": [{"src": "string", "dst": "string", "type": "string", "description": "string"}]
}

Rules:
- entity id is the canonical name (e.g. "Mitochondria", not "the mitochondria")
- type is one of: Person, Organization, Concept, Process, Thing, Place, Event
- only include relationships where BOTH endpoints appear in entities
- be conservative — only include entities/relations actually stated in the passage

Passage:
"""


@dataclass
class ExtractionResult:
    entities: list[dict[str, str]]
    relationships: list[dict[str, str]]


@dataclass
class GraphBuild:
    entities: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


async def _extract_one(client: LLMClient, doc: Document) -> ExtractionResult:
    messages = [
        {"role": "system", "content": "You output strict JSON only."},
        {"role": "user", "content": EXTRACTION_PROMPT + doc.page_content},
    ]
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            result = await client.complete(
                role="extract",
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            data = json.loads(result.content)
            return ExtractionResult(
                entities=data.get("entities", []),
                relationships=data.get("relationships", []),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            last_err = e
            messages[0]["content"] = "You output ONLY valid JSON. No prose, no markdown fences."
    raise ValueError(f"Failed to parse extraction JSON after 2 attempts: {last_err}")


async def extract_graph(chunks: list[Document], *, concurrency: int = 8) -> GraphBuild:
    """Run extraction concurrently across chunks. Failed chunks are skipped, not fatal."""
    client = get_llm()
    sem = asyncio.Semaphore(concurrency)

    async def run(doc: Document) -> tuple[Document, ExtractionResult | Exception]:
        async with sem:
            try:
                r = await _extract_one(client, doc)
                return doc, r
            except Exception as e:
                return doc, e

    results = await asyncio.gather(*[run(c) for c in chunks])

    build = GraphBuild()
    seen_entities: set[str] = set()
    seen_rels: set[tuple[str, str, str]] = set()
    for doc, r in results:
        cid = doc.metadata.get("chunk_id")
        if isinstance(r, Exception):
            build.warnings.append(f"chunk {cid}: {r}")
            continue
        for e in r.entities:
            eid = e.get("id")
            if not eid or eid in seen_entities:
                continue
            seen_entities.add(eid)
            e["source_chunks"] = [cid]
            build.entities.append(e)
        for rel in r.relationships:
            key = (rel.get("src", ""), rel.get("dst", ""), rel.get("type", ""))
            if key in seen_rels:
                continue
            seen_rels.add(key)
            rel["source_chunks"] = [cid]
            build.relationships.append(rel)
    return build
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/integration/test_graph_extractor.py -v`
Expected: PASS — 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add microService/app/indexing/graph_extractor.py microService/tests/integration/test_graph_extractor.py
git commit -m "feat(rag): LLM-based concurrent entity/relation extraction"
```

---

### Task 15: `indexing/community.py` — Louvain communities + summaries

**Files:**
- Create: `microService/app/indexing/community.py`
- Create: `microService/tests/unit/test_community.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/unit/test_community.py`:

```python
import networkx as nx
import pytest
from unittest.mock import AsyncMock, patch
from app.indexing.community import detect_communities, build_networkx_graph


def test_build_networkx_creates_nodes_and_edges():
    entities = [
        {"id": "A", "type": "Concept", "description": "alpha", "source_chunks": [0]},
        {"id": "B", "type": "Concept", "description": "beta", "source_chunks": [1]},
    ]
    rels = [{"src": "A", "dst": "B", "type": "related_to", "description": "x", "source_chunks": [0]}]
    g = build_networkx_graph(entities, rels)
    assert set(g.nodes) == {"A", "B"}
    assert g.has_edge("A", "B")


def test_detect_communities_assigns_ids():
    g = nx.Graph()
    g.add_edges_from([("a", "b"), ("b", "c"), ("x", "y"), ("y", "z")])
    comms = detect_communities(g)
    # two groups: {a,b,c} and {x,y,z}
    assert comms["a"] == comms["b"] == comms["c"]
    assert comms["x"] == comms["y"] == comms["z"]
    assert comms["a"] != comms["x"]


def test_detect_communities_skips_when_graph_too_small():
    g = nx.Graph()
    g.add_node("only")
    comms = detect_communities(g)
    assert comms == {}
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/unit/test_community.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Create `microService/app/indexing/community.py`:

```python
"""Louvain community detection + LLM summarization."""
from __future__ import annotations
import asyncio
import networkx as nx
from community import community_louvain  # provided by python-louvain
from app.core.llm import get_llm


MIN_NODES_FOR_COMMUNITIES = 5


def build_networkx_graph(entities: list[dict], relationships: list[dict]) -> nx.Graph:
    g = nx.Graph()
    for e in entities:
        g.add_node(e["id"], **{k: v for k, v in e.items() if k != "id"})
    for r in relationships:
        if r["src"] in g and r["dst"] in g:
            g.add_edge(r["src"], r["dst"], type=r.get("type", ""), description=r.get("description", ""))
    return g


def detect_communities(g: nx.Graph) -> dict[str, int]:
    if g.number_of_nodes() < MIN_NODES_FOR_COMMUNITIES:
        return {}
    return community_louvain.best_partition(g)


SUMMARY_PROMPT = """Summarize the following group of related concepts in 2-3 sentences.
Concepts:
{members}

Relationships:
{edges}

Summary:"""


async def summarize_communities(
    g: nx.Graph,
    communities: dict[str, int],
    *,
    concurrency: int = 8,
) -> dict[int, str]:
    if not communities:
        return {}
    by_comm: dict[int, list[str]] = {}
    for node, cid in communities.items():
        by_comm.setdefault(cid, []).append(node)

    client = get_llm()
    sem = asyncio.Semaphore(concurrency)

    async def one(cid: int, members: list[str]) -> tuple[int, str]:
        async with sem:
            edges = [
                f"{u} -[{d.get('type','related')}]- {v}"
                for u, v, d in g.subgraph(members).edges(data=True)
            ]
            r = await client.complete(
                role="extract",
                messages=[{"role": "user", "content": SUMMARY_PROMPT.format(
                    members=", ".join(members),
                    edges="\n".join(edges) or "(no edges)",
                )}],
                temperature=0.2,
            )
            return cid, r.content.strip()

    pairs = await asyncio.gather(*[one(cid, m) for cid, m in by_comm.items()])
    return dict(pairs)
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/unit/test_community.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add microService/app/indexing/community.py microService/tests/unit/test_community.py
git commit -m "feat(rag): Louvain community detection + LLM summaries"
```

---

### Task 16: `indexing/store.py` — per-doc persistence

**Files:**
- Create: `microService/app/indexing/store.py`
- Create: `microService/tests/unit/test_store.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/unit/test_store.py`:

```python
import json
from pathlib import Path
from app.indexing.store import (
    doc_hash_from_bytes,
    persist_artifacts,
    load_artifacts,
    artifacts_exist,
)


def test_doc_hash_is_deterministic_and_content_based():
    h1 = doc_hash_from_bytes(b"hello world")
    h2 = doc_hash_from_bytes(b"hello world")
    h3 = doc_hash_from_bytes(b"different")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # sha256 hex


def test_persist_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    h = "abc" * 21 + "x"  # 64 chars
    graph = {"nodes": [{"id": "A"}], "edges": [], "communities": {}, "community_summaries": {}}
    stats = {"n_chunks": 10, "n_entities": 1, "n_edges": 0, "n_communities": 0}
    persist_artifacts(h, graph=graph, bm25_corpus=["hello world"], manifest=stats)

    assert artifacts_exist(h) is True

    loaded = load_artifacts(h)
    assert loaded["graph"] == graph
    assert loaded["manifest"] == stats
    assert Path(loaded["bm25_path"]).exists()


def test_artifacts_exist_returns_false_for_unknown_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    assert artifacts_exist("nonexistent") is False
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/unit/test_store.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Create `microService/app/indexing/store.py`:

```python
"""Per-doc artifact persistence under RAG_PERSIST_DIR/<doc_hash>/."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from app.retrieval.bm25 import BM25Index


def _root() -> Path:
    return Path(os.environ.get("RAG_PERSIST_DIR", "./local_chroma"))


def doc_dir(doc_hash: str) -> Path:
    return _root() / doc_hash


def doc_hash_from_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def artifacts_exist(doc_hash: str) -> bool:
    d = doc_dir(doc_hash)
    return (d / "manifest.json").exists() and (d / "graph.json").exists()


def persist_artifacts(
    doc_hash: str,
    *,
    graph: dict[str, Any],
    bm25_corpus: list[str],
    manifest: dict[str, Any],
) -> Path:
    d = doc_dir(doc_hash)
    d.mkdir(parents=True, exist_ok=True)
    (d / "graph.json").write_text(json.dumps(graph, ensure_ascii=False))
    (d / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False))
    BM25Index.build(bm25_corpus).save(d / "bm25_corpus.pkl")
    return d


def load_artifacts(doc_hash: str) -> dict[str, Any]:
    d = doc_dir(doc_hash)
    return {
        "graph": json.loads((d / "graph.json").read_text()),
        "manifest": json.loads((d / "manifest.json").read_text()),
        "bm25_path": str(d / "bm25_corpus.pkl"),
        "chroma_dir": str(d / "chroma"),
    }


def chroma_dir(doc_hash: str) -> Path:
    return doc_dir(doc_hash) / "chroma"
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/unit/test_store.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add microService/app/indexing/store.py microService/tests/unit/test_store.py
git commit -m "feat(rag): per-doc artifact persistence (hash-addressed)"
```

---

### Task 17: `indexing/pipeline.py` — end-to-end indexing orchestrator

**Files:**
- Create: `microService/app/indexing/pipeline.py`
- Create: `microService/tests/integration/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/integration/test_pipeline.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.documents import Document
from app.indexing.graph_extractor import GraphBuild, ExtractionResult
from app.indexing.pipeline import index_document


@pytest.mark.asyncio
async def test_pipeline_emits_progress_events(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))

    docs = [Document(page_content="alpha beta gamma " * 200, metadata={"source": "x.pdf", "page": 1})]

    async def fake_extract(chunks, concurrency=8):
        return GraphBuild(
            entities=[{"id": "Alpha", "type": "Concept", "description": "x", "source_chunks": [0]}],
            relationships=[],
        )

    async def fake_summarize(g, c, concurrency=8):
        return {}

    fake_chroma = type("C", (), {"persist": lambda self: None, "_collection": None})()

    with patch("app.indexing.pipeline.extract_graph", fake_extract), \
         patch("app.indexing.pipeline.summarize_communities", fake_summarize), \
         patch("app.indexing.pipeline._build_chroma", return_value=fake_chroma):
        events = []
        async for ev in index_document(file_bytes=b"hello", documents=docs):
            events.append(ev)

    names = [e["event"] for e in events]
    assert "chunking" in names
    assert "embedding" in names
    assert "extracting_graph" in names
    assert "done" in names

    done = next(e for e in events if e["event"] == "done")
    assert "doc_hash" in done["data"]
    assert done["data"]["stats"]["n_entities"] == 1


@pytest.mark.asyncio
async def test_pipeline_skips_when_artifacts_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    from app.indexing.store import doc_hash_from_bytes, doc_dir
    import json

    content = b"already-indexed"
    h = doc_hash_from_bytes(content)
    d = doc_dir(h)
    d.mkdir(parents=True)
    (d / "graph.json").write_text("{}")
    (d / "manifest.json").write_text(json.dumps({"n_chunks": 5}))

    events = []
    async for ev in index_document(file_bytes=content, documents=[]):
        events.append(ev)

    assert events[-1]["event"] == "done"
    assert events[-1]["data"]["cached"] is True
    assert events[-1]["data"]["doc_hash"] == h
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/integration/test_pipeline.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Create `microService/app/indexing/pipeline.py`:

```python
"""Indexing pipeline. Async generator yielding progress events.

Each event is {"event": name, "data": {...}}.
"""
from __future__ import annotations
import asyncio
from typing import AsyncIterator
from langchain_core.documents import Document
from langchain_chroma import Chroma

from app.core.chunker import chunk_documents
from app.core.embeddings import get_embeddings
from app.indexing.graph_extractor import extract_graph
from app.indexing.community import (
    build_networkx_graph,
    detect_communities,
    summarize_communities,
)
from app.indexing.store import (
    doc_hash_from_bytes,
    artifacts_exist,
    persist_artifacts,
    load_artifacts,
    chroma_dir,
)


def _build_chroma(chunks: list[Document], persist_dir: str) -> Chroma:
    return Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=persist_dir,
    )


def _serialize_graph(g, communities: dict[str, int], summaries: dict[int, str]) -> dict:
    return {
        "nodes": [{"id": n, **g.nodes[n]} for n in g.nodes],
        "edges": [
            {"src": u, "dst": v, **g.edges[u, v]}
            for u, v in g.edges
        ],
        "communities": communities,
        "community_summaries": {str(k): v for k, v in summaries.items()},
    }


async def index_document(
    *,
    file_bytes: bytes,
    documents: list[Document],
) -> AsyncIterator[dict]:
    h = doc_hash_from_bytes(file_bytes)

    if artifacts_exist(h):
        loaded = load_artifacts(h)
        yield {"event": "done", "data": {"doc_hash": h, "cached": True, "stats": loaded["manifest"]}}
        return

    yield {"event": "chunking", "data": {}}
    chunks = chunk_documents(documents)
    yield {"event": "chunking", "data": {"n_chunks": len(chunks)}}

    embed_task = asyncio.create_task(asyncio.to_thread(_build_chroma, chunks, str(chroma_dir(h))))
    yield {"event": "embedding", "data": {}}

    yield {"event": "extracting_graph", "data": {"total": len(chunks)}}
    build = await extract_graph(chunks)

    yield {"event": "embedding", "data": {"status": "waiting"}}
    await embed_task

    yield {"event": "detecting_communities", "data": {}}
    g = build_networkx_graph(build.entities, build.relationships)
    communities = detect_communities(g)

    yield {"event": "summarizing_communities", "data": {"n": len(set(communities.values())) if communities else 0}}
    summaries = await summarize_communities(g, communities)

    graph_payload = _serialize_graph(g, communities, summaries)
    stats = {
        "n_chunks": len(chunks),
        "n_entities": g.number_of_nodes(),
        "n_edges": g.number_of_edges(),
        "n_communities": len(set(communities.values())) if communities else 0,
        "warnings": build.warnings,
    }
    persist_artifacts(
        h,
        graph=graph_payload,
        bm25_corpus=[c.page_content for c in chunks],
        manifest=stats,
    )

    yield {"event": "done", "data": {"doc_hash": h, "cached": False, "stats": stats}}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/integration/test_pipeline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add microService/app/indexing/pipeline.py microService/tests/integration/test_pipeline.py
git commit -m "feat(rag): indexing pipeline with progress event stream"
```

---

## Phase 4 — Query Pipeline

### Task 18: `retrieval/rewriter.py` — query rewriting (HyDE + keywords + entities)

**Files:**
- Create: `microService/app/retrieval/rewriter.py`
- Create: `microService/tests/integration/test_rewriter.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/integration/test_rewriter.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock, patch
from app.retrieval.rewriter import rewrite_query, RewrittenQuery
from app.core.llm import LLMResult


@pytest.mark.asyncio
async def test_rewrite_returns_three_views():
    payload = {
        "hyde": "Mitochondria produce ATP via the electron transport chain.",
        "keywords": "mitochondria ATP electron transport",
        "entities_mentioned": ["Mitochondria", "ATP"],
    }
    with patch("app.retrieval.rewriter._call_llm",
               AsyncMock(return_value=LLMResult(content=json.dumps(payload), model_used="m", fallback_count=0))):
        rq = await rewrite_query("how do mitochondria work?")
    assert rq.hyde.startswith("Mitochondria produce")
    assert "ATP" in rq.entities_mentioned
    assert "atp" in rq.keywords.lower()


@pytest.mark.asyncio
async def test_rewrite_falls_back_to_raw_query_on_failure():
    with patch("app.retrieval.rewriter._call_llm", AsyncMock(side_effect=RuntimeError("boom"))):
        rq = await rewrite_query("plain query")
    assert rq.hyde == "plain query"
    assert rq.keywords == "plain query"
    assert rq.entities_mentioned == []
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/integration/test_rewriter.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

Create `microService/app/retrieval/rewriter.py`:

```python
"""Query rewriter — turns a raw query into HyDE + keywords + entity hints."""
from __future__ import annotations
import json
from dataclasses import dataclass
from app.core.llm import LLMResult, get_llm


REWRITE_PROMPT = """Given the user query, output JSON with three fields:
- "hyde": a 1-2 sentence hypothetical answer paragraph as if you knew the doc
- "keywords": 3-8 space-separated keywords for lexical search
- "entities_mentioned": list of named entities likely referenced (people, concepts, things)

Output JSON only.

Query: {query}
"""


@dataclass
class RewrittenQuery:
    hyde: str
    keywords: str
    entities_mentioned: list[str]


async def _call_llm(query: str) -> LLMResult:
    return await get_llm().complete(
        role="rewrite",
        messages=[
            {"role": "system", "content": "You output strict JSON only."},
            {"role": "user", "content": REWRITE_PROMPT.format(query=query)},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )


async def rewrite_query(query: str) -> RewrittenQuery:
    try:
        result = await _call_llm(query)
        data = json.loads(result.content)
        return RewrittenQuery(
            hyde=data.get("hyde") or query,
            keywords=data.get("keywords") or query,
            entities_mentioned=list(data.get("entities_mentioned") or []),
        )
    except Exception:
        return RewrittenQuery(hyde=query, keywords=query, entities_mentioned=[])
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/integration/test_rewriter.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add microService/app/retrieval/rewriter.py microService/tests/integration/test_rewriter.py
git commit -m "feat(rag): query rewriter with safe fallback to raw query"
```

---

### Task 19: `retrieval/graph.py` — graph traversal retriever

**Files:**
- Create: `microService/app/retrieval/graph.py`
- Create: `microService/tests/unit/test_graph_retriever.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/unit/test_graph_retriever.py`:

```python
from app.retrieval.graph import GraphIndex


SAMPLE_GRAPH = {
    "nodes": [
        {"id": "Mitochondria", "type": "Organelle", "description": "x", "source_chunks": [1, 4]},
        {"id": "ATP", "type": "Concept", "description": "y", "source_chunks": [4]},
        {"id": "Nucleus", "type": "Organelle", "description": "z", "source_chunks": [7]},
        {"id": "DNA", "type": "Concept", "description": "w", "source_chunks": [7, 8]},
    ],
    "edges": [
        {"src": "Mitochondria", "dst": "ATP", "type": "produces"},
        {"src": "Nucleus", "dst": "DNA", "type": "contains"},
    ],
    "communities": {"Mitochondria": 0, "ATP": 0, "Nucleus": 1, "DNA": 1},
    "community_summaries": {"0": "Energy production.", "1": "Genetic material storage."},
}


def test_fuzzy_match_finds_entity():
    idx = GraphIndex(SAMPLE_GRAPH)
    matches = idx.match_entities(["mitochondria"])
    assert matches == ["Mitochondria"]


def test_traverse_returns_neighbor_chunks():
    idx = GraphIndex(SAMPLE_GRAPH)
    chunks = idx.traverse_chunks(["Mitochondria"], hops=1)
    assert set(chunks) >= {1, 4}


def test_traverse_includes_community_chunks():
    idx = GraphIndex(SAMPLE_GRAPH)
    chunks = idx.traverse_chunks(["Mitochondria"], hops=2)
    assert set(chunks) >= {1, 4}


def test_community_summary_lookup():
    idx = GraphIndex(SAMPLE_GRAPH)
    assert idx.community_summary("Mitochondria") == "Energy production."
    assert idx.community_summary("Unknown") is None
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/unit/test_graph_retriever.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

Create `microService/app/retrieval/graph.py`:

```python
"""Graph-side retrieval — fuzzy entity match + k-hop chunk traversal."""
from __future__ import annotations
from collections import defaultdict


class GraphIndex:
    def __init__(self, graph: dict) -> None:
        self._nodes = {n["id"]: n for n in graph.get("nodes", [])}
        self._adj: dict[str, set[str]] = defaultdict(set)
        for e in graph.get("edges", []):
            self._adj[e["src"]].add(e["dst"])
            self._adj[e["dst"]].add(e["src"])
        self._comm = graph.get("communities", {})
        self._summaries = {int(k): v for k, v in graph.get("community_summaries", {}).items()}

    def match_entities(self, mentioned: list[str]) -> list[str]:
        out: list[str] = []
        lower_map = {nid.lower(): nid for nid in self._nodes}
        for m in mentioned:
            ml = m.lower().strip()
            if ml in lower_map:
                out.append(lower_map[ml])
                continue
            for k, nid in lower_map.items():
                if ml in k or k in ml:
                    out.append(nid)
                    break
        seen, deduped = set(), []
        for nid in out:
            if nid not in seen:
                seen.add(nid)
                deduped.append(nid)
        return deduped

    def traverse_chunks(self, entities: list[str], *, hops: int = 2) -> list[int]:
        frontier = set(entities)
        visited = set(entities)
        for _ in range(hops):
            nxt = set()
            for n in frontier:
                nxt |= self._adj.get(n, set())
            frontier = nxt - visited
            visited |= frontier
        chunks: list[int] = []
        for n in visited:
            for c in self._nodes.get(n, {}).get("source_chunks", []):
                chunks.append(c)
        seen, out = set(), []
        for c in chunks:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def community_summary(self, entity_id: str) -> str | None:
        cid = self._comm.get(entity_id)
        if cid is None:
            return None
        return self._summaries.get(int(cid))
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/unit/test_graph_retriever.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add microService/app/retrieval/graph.py microService/tests/unit/test_graph_retriever.py
git commit -m "feat(rag): graph retriever — fuzzy entity match + k-hop chunks"
```

---

### Task 20: `retrieval/reranker.py` — optional LLM-as-reranker

**Files:**
- Create: `microService/app/retrieval/reranker.py`

- [ ] **Step 1: Implement**

Create `microService/app/retrieval/reranker.py`:

```python
"""Optional rerank step. Env-flagged via RAG_ENABLE_RERANK."""
from __future__ import annotations
import json
import os
from app.core.llm import get_llm


RERANK_PROMPT = """Score each passage from 0 (irrelevant) to 10 (perfectly answers the query).
Return JSON array of scores in the same order. JSON only.

Query: {query}

Passages:
{passages}
"""


def is_enabled() -> bool:
    return os.environ.get("RAG_ENABLE_RERANK", "false").lower() == "true"


async def rerank(query: str, chunks: list[tuple[int, str]], *, top_k: int = 5) -> list[int]:
    """chunks: [(chunk_id, text)]. Returns chunk_ids in score order."""
    if not chunks:
        return []
    if not is_enabled():
        return [c[0] for c in chunks[:top_k]]

    passages = "\n".join(f"[{i}] {text}" for i, (_, text) in enumerate(chunks))
    try:
        r = await get_llm().complete(
            role="rerank",
            messages=[{"role": "user", "content": RERANK_PROMPT.format(query=query, passages=passages)}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        scores = json.loads(r.content)
        if isinstance(scores, dict) and "scores" in scores:
            scores = scores["scores"]
        if not isinstance(scores, list) or len(scores) != len(chunks):
            return [c[0] for c in chunks[:top_k]]
        ranked = sorted(zip(chunks, scores), key=lambda kv: kv[1], reverse=True)
        return [c[0][0] for c in ranked[:top_k]]
    except Exception:
        return [c[0] for c in chunks[:top_k]]
```

- [ ] **Step 2: Smoke import**

Run: `cd microService && python -c "from app.retrieval.reranker import rerank, is_enabled; print(is_enabled())"`
Expected: `False`.

- [ ] **Step 3: Commit**

```bash
git add microService/app/retrieval/reranker.py
git commit -m "feat(rag): optional LLM-as-reranker behind RAG_ENABLE_RERANK"
```

---

### Task 21: `retrieval/orchestrator.py` — query-time entry point

**Files:**
- Create: `microService/app/retrieval/orchestrator.py`
- Create: `microService/tests/integration/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

Create `microService/tests/integration/test_orchestrator.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock, patch
from app.retrieval.orchestrator import answer
from app.retrieval.rewriter import RewrittenQuery


@pytest.fixture
def fake_loaded(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    return {
        "graph": {"nodes": [], "edges": [], "communities": {}, "community_summaries": {}},
        "manifest": {"n_chunks": 2},
        "bm25_path": str(tmp_path / "bm25.pkl"),
        "chroma_dir": str(tmp_path / "chroma"),
    }


@pytest.mark.asyncio
async def test_answer_streams_tokens_with_one_retriever_dead(fake_loaded):
    async def fake_rewrite(q):
        return RewrittenQuery(hyde="h", keywords="k", entities_mentioned=[])

    def fake_vector(*a, **k):
        raise RuntimeError("vector down")

    def fake_bm25_load(path):
        class Idx:
            def search(self, q, top_k=10):
                return [(0, 1.0), (1, 0.5)]
        return Idx()

    async def fake_stream(*, role, messages, temperature):
        yield "Answer ", "m"
        yield "[1]", "m"

    chunks_by_id = {0: "Chunk zero text [c0]", 1: "Chunk one text [c1]"}

    with patch("app.retrieval.orchestrator._load_artifacts_cached", return_value=fake_loaded), \
         patch("app.retrieval.orchestrator.rewrite_query", fake_rewrite), \
         patch("app.retrieval.orchestrator._vector_search_chunks", fake_vector), \
         patch("app.retrieval.orchestrator.BM25Index.load", fake_bm25_load), \
         patch("app.retrieval.orchestrator._chunks_by_id", return_value=chunks_by_id), \
         patch("app.retrieval.orchestrator.get_llm") as gl:
        gl.return_value.stream = fake_stream

        events = []
        async for e in answer(doc_hash="abc", query="what?"):
            events.append(e)

    names = [e["event"] for e in events]
    assert names[0] == "context"
    assert "token" in names
    assert names[-1] == "done"
    text = "".join(e["data"]["text"] for e in events if e["event"] == "token")
    assert "Answer" in text and "[1]" in text


@pytest.mark.asyncio
async def test_answer_404s_on_unknown_doc(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        async for _ in answer(doc_hash="nope", query="x"):
            pass
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd microService && ./run_tests.sh tests/integration/test_orchestrator.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

Create `microService/app/retrieval/orchestrator.py`:

```python
"""Query orchestrator — public answer() entry point.

Fans out vector + BM25 + graph in parallel, fuses with RRF, optionally
reranks, streams answer with citation prompting.
"""
from __future__ import annotations
import asyncio
import os
import pickle
from functools import lru_cache
from typing import AsyncIterator

from langchain_chroma import Chroma
from app.core.cache import get_cache
from app.core.embeddings import get_embeddings
from app.core.llm import get_llm
from app.indexing.store import load_artifacts, artifacts_exist
from app.retrieval.bm25 import BM25Index
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.graph import GraphIndex
from app.retrieval.reranker import rerank, is_enabled as rerank_enabled
from app.retrieval.rewriter import rewrite_query
from app.retrieval.vector import vector_search


ANSWER_PROMPT = """Answer the question using the numbered passages below.

RULES:
- For every factual claim, cite the passage like [1], [2]. Multiple ok: [1,3].
- If the answer is not in the passages, say "I couldn't find that in the document."
- Be concise. Don't repeat the question.

Passages:
{context}

Question: {question}

Answer:"""


def _load_artifacts_cached(doc_hash: str) -> dict:
    cache = get_cache()
    cached = cache.get(doc_hash)
    if cached is not None:
        return cached
    if not artifacts_exist(doc_hash):
        raise FileNotFoundError(f"No indexed artifacts for doc_hash={doc_hash}")
    loaded = load_artifacts(doc_hash)
    chroma = Chroma(persist_directory=loaded["chroma_dir"], embedding_function=get_embeddings())
    bm25 = BM25Index.load(loaded["bm25_path"])
    graph = GraphIndex(loaded["graph"])
    chunks_by_id = _chunks_from_chroma(chroma)
    entry = {**loaded, "chroma": chroma, "bm25": bm25, "graph_idx": graph, "chunks_by_id": chunks_by_id}
    cache.put(doc_hash, entry)
    return entry


def _chunks_from_chroma(chroma: Chroma) -> dict[int, str]:
    res = chroma.get(include=["documents", "metadatas"])
    out: dict[int, str] = {}
    for text, meta in zip(res.get("documents", []), res.get("metadatas", [])):
        cid = meta.get("chunk_id") if meta else None
        if cid is None:
            continue
        out[int(cid)] = text
    return out


def _chunks_by_id(loaded: dict) -> dict[int, str]:
    return loaded["chunks_by_id"]


def _vector_search_chunks(chroma: Chroma, query: str, top_k: int) -> list[int]:
    return [cid for cid, _ in vector_search(chroma, query, top_k=top_k)]


def _bm25_search_chunks(bm25: BM25Index, keywords: str, top_k: int) -> list[int]:
    return [cid for cid, _ in bm25.search(keywords, top_k=top_k)]


def _graph_search_chunks(g: GraphIndex, entities: list[str]) -> list[int]:
    matched = g.match_entities(entities)
    return g.traverse_chunks(matched, hops=2) if matched else []


def _build_context(chunks_by_id: dict[int, str], chunk_ids: list[int]) -> tuple[str, list[dict]]:
    citations = []
    parts = []
    for i, cid in enumerate(chunk_ids, start=1):
        text = chunks_by_id.get(cid, "")
        if not text:
            continue
        parts.append(f"[{i}] {text}")
        citations.append({"n": i, "chunk_id": cid})
    return "\n\n".join(parts), citations


async def answer(
    *,
    doc_hash: str,
    query: str,
    history: list[dict[str, str]] | None = None,
) -> AsyncIterator[dict]:
    loaded = _load_artifacts_cached(doc_hash)
    chroma, bm25, graph_idx = loaded["chroma"], loaded["bm25"], loaded["graph_idx"]
    chunks_by_id = _chunks_by_id(loaded)

    rq = await rewrite_query(query)

    async def safe(fn):
        try:
            return await asyncio.to_thread(fn)
        except Exception:
            return []

    vec_ids, bm25_ids, graph_ids = await asyncio.gather(
        safe(lambda: _vector_search_chunks(chroma, rq.hyde, 10)),
        safe(lambda: _bm25_search_chunks(bm25, rq.keywords, 10)),
        safe(lambda: _graph_search_chunks(graph_idx, rq.entities_mentioned)),
    )

    fused = reciprocal_rank_fusion([vec_ids, bm25_ids, graph_ids], k=60, top_k=15)

    if rerank_enabled():
        pairs = [(cid, chunks_by_id.get(cid, "")) for cid in fused]
        fused = await rerank(query, pairs, top_k=5)
    else:
        fused = fused[:5]

    context, citations = _build_context(chunks_by_id, fused)
    yield {"event": "context", "data": {"citations": citations}}

    messages = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": ANSWER_PROMPT.format(context=context, question=query)})

    try:
        async for delta, _model in get_llm().stream(role="answer", messages=messages, temperature=0.2):
            yield {"event": "token", "data": {"text": delta}}
        yield {"event": "done", "data": {}}
    except Exception as e:
        yield {"event": "error", "data": {"message": str(e), "partial": True}}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd microService && ./run_tests.sh tests/integration/test_orchestrator.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add microService/app/retrieval/orchestrator.py microService/tests/integration/test_orchestrator.py
git commit -m "feat(rag): query orchestrator — parallel retrieval, RRF, streamed answer"
```

---

## Phase 5 — FastAPI Routes

### Task 22: New `/index` SSE endpoint

**Files:**
- Modify: `microService/app/main.py`

- [ ] **Step 1: Replace main.py with the new endpoint surface**

Replace `microService/app/main.py` with:

```python
"""FastAPI app — DocuMind AI hybrid GraphRAG."""
from __future__ import annotations
import json
import os
from pathlib import Path

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)

from app.core.streaming import sse_event, sse_error, sse_token
from app.indexing.pipeline import index_document
from app.indexing.store import load_artifacts, artifacts_exist, doc_hash_from_bytes
from app.retrieval.orchestrator import answer

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("./tmp/uploaded_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_MB = int(os.environ.get("RAG_MAX_FILE_MB", "25"))


@app.get("/")
def root():
    return {"message": "DocuMind AI — hybrid GraphRAG"}


def _load_documents(path: Path, file_type: str) -> list[Document]:
    if file_type == ".pdf":
        return PyPDFLoader(str(path)).load()
    if file_type == ".txt" or file_type == ".md":
        return TextLoader(str(path)).load()
    return UnstructuredWordDocumentLoader(str(path)).load()


@app.post("/index")
async def post_index(file: UploadFile = File(...)):
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_MB:
        raise HTTPException(status_code=413, detail=f"File too large ({size_mb:.1f}MB > {MAX_MB}MB)")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt", ".md", ".docx", ".doc"}:
        raise HTTPException(status_code=415, detail=f"Unsupported type: {suffix}")

    save_path = UPLOAD_DIR / (file.filename or "upload")
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(content)

    try:
        documents = _load_documents(save_path, suffix)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read document: {e}")

    if not documents or not any(d.page_content.strip() for d in documents):
        raise HTTPException(status_code=422, detail="No extractable text — is this a scanned PDF?")

    async def gen():
        try:
            async for ev in index_document(file_bytes=content, documents=documents):
                yield sse_event(ev["event"], ev["data"])
        except Exception as e:
            yield sse_error(str(e))

    return StreamingResponse(gen(), media_type="text/event-stream")
```

- [ ] **Step 2: Smoke-start the server**

Run: `cd microService && uvicorn app.main:app --port 8000 &  sleep 2 && curl -s http://localhost:8000/ && kill %1`
Expected: prints `{"message":"DocuMind AI — hybrid GraphRAG"}`.

- [ ] **Step 3: Commit**

```bash
git add microService/app/main.py
git commit -m "feat(rag): /index SSE endpoint with size/type guards"
```

---

### Task 23: `/query` SSE endpoint

**Files:**
- Modify: `microService/app/main.py`

- [ ] **Step 1: Add `/query` endpoint**

Append to `microService/app/main.py`:

```python


from pydantic import BaseModel


class QueryBody(BaseModel):
    doc_hash: str
    query: str
    history: list[dict] | None = None


@app.post("/query")
async def post_query(body: QueryBody):
    if not artifacts_exist(body.doc_hash):
        raise HTTPException(status_code=404, detail="doc_hash not indexed")

    async def gen():
        try:
            async for ev in answer(doc_hash=body.doc_hash, query=body.query, history=body.history):
                yield sse_event(ev["event"], ev["data"])
        except Exception as e:
            yield sse_error(str(e), partial=True)

    return StreamingResponse(gen(), media_type="text/event-stream")
```

- [ ] **Step 2: Smoke check the route exists**

Run: `cd microService && uvicorn app.main:app --port 8000 &  sleep 2 && curl -s -X POST http://localhost:8000/query -H 'content-type: application/json' -d '{"doc_hash":"nope","query":"x"}' ; kill %1`
Expected: returns `{"detail":"doc_hash not indexed"}`.

- [ ] **Step 3: Commit**

```bash
git add microService/app/main.py
git commit -m "feat(rag): /query SSE endpoint with 404 on unknown doc"
```

---

### Task 24: `/graph/{doc_hash}` JSON endpoint

**Files:**
- Modify: `microService/app/main.py`

- [ ] **Step 1: Add the graph endpoint**

Append to `microService/app/main.py`:

```python


@app.get("/graph/{doc_hash}")
def get_graph(doc_hash: str):
    if not artifacts_exist(doc_hash):
        raise HTTPException(status_code=404, detail="doc_hash not indexed")
    loaded = load_artifacts(doc_hash)
    return loaded["graph"]
```

- [ ] **Step 2: Smoke check**

Run: `cd microService && uvicorn app.main:app --port 8000 &  sleep 2 && curl -s http://localhost:8000/graph/nope ; kill %1`
Expected: `{"detail":"doc_hash not indexed"}`.

- [ ] **Step 3: Commit**

```bash
git add microService/app/main.py
git commit -m "feat(rag): /graph/{doc_hash} JSON endpoint"
```

---

### Task 25: Migrate `/getSummary` → `/summary` (doc_hash-based)

**Files:**
- Modify: `microService/app/routes/summary.py`
- Modify: `microService/app/main.py`

- [ ] **Step 1: Rewrite summary.py**

Replace `microService/app/routes/summary.py` with:

```python
"""Summary generation — reuses indexed artifacts."""
from app.core.llm import get_llm
from app.indexing.store import load_artifacts, artifacts_exist


SUMMARY_PROMPT = """Summarize the document. Output rules:

- Give a short title and a 1-sentence abstract.
- If the document has chapters, list each chapter with a 2-3 line summary (numbered).
- Otherwise give a 10-12 line summary with main points as a short list.
- No markdown fences. No leading prose.

Document content:
{content}
"""


async def summarize(doc_hash: str) -> str:
    if not artifacts_exist(doc_hash):
        raise FileNotFoundError(f"doc_hash {doc_hash} not indexed")
    loaded = load_artifacts(doc_hash)
    from langchain_chroma import Chroma
    from app.core.embeddings import get_embeddings

    chroma = Chroma(persist_directory=loaded["chroma_dir"], embedding_function=get_embeddings())
    res = chroma.get(include=["documents"])
    content = "\n\n".join(res.get("documents", [])[:8])  # cap to keep prompt size sane

    r = await get_llm().complete(
        role="answer",
        messages=[{"role": "user", "content": SUMMARY_PROMPT.format(content=content)}],
        temperature=0.2,
    )
    return r.content
```

- [ ] **Step 2: Replace the route in main.py**

Find the placeholder for old `/getSummary` (if present, remove). Add at the bottom of `main.py`:

```python


from app.routes.summary import summarize


class SummaryBody(BaseModel):
    doc_hash: str


@app.post("/summary")
async def post_summary(body: SummaryBody):
    try:
        text = await summarize(body.doc_hash)
        return {"summary": text}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="doc_hash not indexed")
```

- [ ] **Step 3: Smoke import**

Run: `cd microService && python -c "from app.main import app; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add microService/app/routes/summary.py microService/app/main.py
git commit -m "feat(rag): /summary endpoint takes doc_hash, reuses cached artifacts"
```

---

### Task 26: Migrate `/getQuiz` → `/quiz` (doc_hash-based)

**Files:**
- Modify: `microService/app/routes/quiz.py`
- Modify: `microService/app/main.py`

- [ ] **Step 1: Rewrite quiz.py**

Replace `microService/app/routes/quiz.py` with:

```python
"""Quiz generation — reuses indexed artifacts."""
import json
import logging
from typing import Any
from pydantic import BaseModel, Field

from app.core.llm import get_llm
from app.indexing.store import load_artifacts, artifacts_exist
from langchain_chroma import Chroma
from app.core.embeddings import get_embeddings

logger = logging.getLogger(__name__)


class QuizQuestion(BaseModel):
    id: int
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer: str
    explanation: str = ""


QUIZ_PROMPT = """Generate exactly 12 multiple-choice questions from the document content.

Rules:
- Each question has exactly 4 options.
- correct_answer must match one of the options character-for-character.
- Questions 1-3 easy; 4-9 medium; 10-12 hard.
- Cover different aspects of the content.

Return JSON of the form:
{{"quiz": [{{"id":1,"question":"...","options":["A","B","C","D"],"correct_answer":"B","explanation":"..."}}]}}

Document content:
{content}
"""


async def generate_quiz_cards(doc_hash: str) -> dict[str, Any]:
    if not artifacts_exist(doc_hash):
        return {"success": False, "error": "doc_hash not indexed", "data": {"total_questions": 0, "cards": []}}
    loaded = load_artifacts(doc_hash)
    chroma = Chroma(persist_directory=loaded["chroma_dir"], embedding_function=get_embeddings())
    res = chroma.get(include=["documents"])
    content = "\n\n".join(res.get("documents", [])[:8])

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[{"role": "user", "content": QUIZ_PROMPT.format(content=content)}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(r.content)
        cards = _format_for_frontend(data.get("quiz", []))
        if not cards:
            return {"success": False, "error": "No valid questions", "data": {"total_questions": 0, "cards": []}}
        return {"success": True, "data": {"total_questions": len(cards), "cards": cards}}
    except Exception as e:
        logger.error("quiz failed: %s", e)
        return {"success": False, "error": str(e), "data": {"total_questions": 0, "cards": []}}


def _format_for_frontend(items: list[dict]) -> list[dict]:
    cards = []
    for i, q in enumerate(items):
        try:
            QuizQuestion(**q)
        except Exception:
            continue
        if q["correct_answer"] not in q["options"]:
            continue
        cards.append({
            "id": q.get("id", i + 1),
            "type": "multiple-choice",
            "title": f"Question {q.get('id', i + 1)}",
            "question": q["question"],
            "options": [
                {"id": f"option_{j}", "text": opt, "correct": opt == q["correct_answer"]}
                for j, opt in enumerate(q["options"])
            ],
            "correctAnswer": q["correct_answer"],
            "explanation": q.get("explanation", ""),
            "metadata": {
                "difficulty": "easy" if i < 3 else "medium" if i < 9 else "hard",
                "category": "auto-generated",
            },
        })
    return cards
```

- [ ] **Step 2: Add route**

Append to `microService/app/main.py`:

```python


from app.routes.quiz import generate_quiz_cards


class QuizBody(BaseModel):
    doc_hash: str


@app.post("/quiz")
async def post_quiz(body: QuizBody):
    return await generate_quiz_cards(body.doc_hash)
```

- [ ] **Step 3: Smoke import**

Run: `cd microService && python -c "from app.main import app; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add microService/app/routes/quiz.py microService/app/main.py
git commit -m "feat(rag): /quiz endpoint takes doc_hash, reuses cached artifacts"
```

---

### Task 27: Delete deprecated `DocContent.py` and old `/RAG`, `/getSummary`, `/getQuiz`

**Files:**
- Delete: `microService/app/routes/DocContent.py`
- Delete: `microService/app/routes/RAG.py`
- Modify: `microService/app/main.py` (remove old route imports if any linger)

- [ ] **Step 1: Verify nothing imports DocContent or old RAG**

Run: `cd microService && grep -rn "from app.routes.DocContent\|from app.routes.RAG\|getSummary\|getQuiz" app/ tests/ --include='*.py' || echo "no references"`
Expected: `no references`.

- [ ] **Step 2: Delete the files**

```bash
git rm microService/app/routes/DocContent.py microService/app/routes/RAG.py
```

- [ ] **Step 3: Verify the app still imports**

Run: `cd microService && python -c "from app.main import app; print(sorted(r.path for r in app.routes))"`
Expected: includes `/index`, `/query`, `/graph/{doc_hash}`, `/summary`, `/quiz`, `/` — does NOT include `/RAG`, `/getSummary`, `/getQuiz`.

- [ ] **Step 4: Commit**

```bash
git add -u microService/
git commit -m "chore(rag): remove deprecated DocContent.py and old route handlers"
```

---

### Task 28: API tests — `/index` and `/query` SSE contracts

**Files:**
- Create: `microService/tests/api/test_index_endpoint.py`
- Create: `microService/tests/api/test_query_endpoint.py`

- [ ] **Step 1: Write the index endpoint test**

Create `microService/tests/api/test_index_endpoint.py`:

```python
import io
import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_index_rejects_oversized_file(monkeypatch):
    monkeypatch.setenv("RAG_MAX_FILE_MB", "1")
    big = b"x" * (2 * 1024 * 1024)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/index", files={"file": ("big.txt", big, "text/plain")})
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_index_rejects_unsupported_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/index", files={"file": ("a.exe", b"x", "application/octet-stream")})
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_index_returns_sse_done_event_when_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))

    async def fake_pipeline(*, file_bytes, documents):
        yield {"event": "done", "data": {"doc_hash": "x", "cached": False, "stats": {"n_chunks": 1}}}

    with patch("app.main.index_document", fake_pipeline):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/index", files={"file": ("a.txt", b"hello world", "text/plain")})

    assert r.status_code == 200
    body = r.text
    assert "event: done" in body
    assert "doc_hash" in body
```

- [ ] **Step 2: Write the query endpoint test**

Create `microService/tests/api/test_query_endpoint.py`:

```python
import pytest
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_query_404_on_unknown_doc():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/query", json={"doc_hash": "nope", "query": "x"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_query_streams_when_doc_exists(monkeypatch):
    async def fake_answer(*, doc_hash, query, history=None):
        yield {"event": "context", "data": {"citations": [{"n": 1, "chunk_id": 0}]}}
        yield {"event": "token", "data": {"text": "Hello"}}
        yield {"event": "done", "data": {}}

    with patch("app.main.artifacts_exist", return_value=True), \
         patch("app.main.answer", fake_answer):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/query", json={"doc_hash": "abc", "query": "what?"})
    assert r.status_code == 200
    body = r.text
    assert "event: context" in body
    assert "event: token" in body
    assert "event: done" in body
```

- [ ] **Step 3: Run**

Run: `cd microService && ./run_tests.sh tests/api -v`
Expected: 5 tests pass.

- [ ] **Step 4: Commit**

```bash
git add microService/tests/api
git commit -m "test(rag): SSE contract tests for /index and /query"
```

---

### Task 29: E2E test — full pipeline on a fixture document

**Files:**
- Create: `microService/tests/fixtures/short.md`
- Create: `microService/tests/e2e/test_full_pipeline.py`

- [ ] **Step 1: Write the fixture**

Create `microService/tests/fixtures/short.md`:

```markdown
# Cellular Energy

Mitochondria are organelles found in eukaryotic cells. They produce ATP through cellular respiration.

# DNA Storage

The nucleus contains the DNA of the cell. The nuclear envelope separates the nucleus from the cytoplasm.

# Protein Synthesis

Ribosomes synthesize proteins by reading messenger RNA. Some ribosomes are free in the cytoplasm; others are attached to the rough endoplasmic reticulum.
```

- [ ] **Step 2: Write the e2e test**

Create `microService/tests/e2e/test_full_pipeline.py`:

```python
"""End-to-end: index a small fixture, then query for a known fact.

Uses mock LLM responses so this runs offline. Validates that:
- indexing produces all artifacts
- chroma + bm25 retrieve the right chunk for a known query
- the answerer streams tokens that contain a citation
"""
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from langchain_core.documents import Document

from app.indexing.pipeline import index_document
from app.retrieval.orchestrator import answer
from app.indexing.graph_extractor import GraphBuild


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "short.md"


@pytest.fixture
def isolated_persist(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    return tmp_path


@pytest.mark.asyncio
async def test_index_then_query_for_known_fact(isolated_persist):
    text = FIXTURE.read_text()
    docs = [Document(page_content=text, metadata={"source": str(FIXTURE), "page": 1})]

    async def fake_extract(chunks, concurrency=8):
        return GraphBuild(
            entities=[
                {"id": "Mitochondria", "type": "Organelle", "description": "ATP producer", "source_chunks": [0]},
                {"id": "ATP", "type": "Concept", "description": "energy currency", "source_chunks": [0]},
            ],
            relationships=[{"src": "Mitochondria", "dst": "ATP", "type": "produces",
                            "description": "via cellular respiration", "source_chunks": [0]}],
        )

    async def fake_summaries(g, c, concurrency=8):
        return {}

    async def fake_rewrite(q):
        from app.retrieval.rewriter import RewrittenQuery
        return RewrittenQuery(hyde="mitochondria produce atp", keywords="mitochondria atp", entities_mentioned=["Mitochondria"])

    async def fake_stream(*, role, messages, temperature):
        yield "Mitochondria produce ATP ", "m"
        yield "[1]", "m"

    doc_hash = None
    with patch("app.indexing.pipeline.extract_graph", fake_extract), \
         patch("app.indexing.pipeline.summarize_communities", fake_summaries):
        async for ev in index_document(file_bytes=text.encode(), documents=docs):
            if ev["event"] == "done":
                doc_hash = ev["data"]["doc_hash"]
    assert doc_hash is not None

    # Files exist
    persist = isolated_persist / doc_hash
    assert (persist / "graph.json").exists()
    assert (persist / "manifest.json").exists()
    assert (persist / "bm25_corpus.pkl").exists()
    assert (persist / "chroma").exists()

    with patch("app.retrieval.orchestrator.rewrite_query", fake_rewrite), \
         patch("app.retrieval.orchestrator.get_llm") as gl:
        gl.return_value.stream = fake_stream
        events = []
        async for ev in answer(doc_hash=doc_hash, query="what produces ATP?"):
            events.append(ev)

    tokens = "".join(e["data"]["text"] for e in events if e["event"] == "token")
    assert "Mitochondria" in tokens
    assert "[1]" in tokens, "citation marker missing — answer prompt regression"
    assert events[-1]["event"] == "done"
```

- [ ] **Step 3: Run**

Run: `cd microService && ./run_tests.sh tests/e2e -v`
Expected: passes.

- [ ] **Step 4: Commit**

```bash
git add microService/tests/fixtures microService/tests/e2e
git commit -m "test(rag): e2e — index fixture then retrieve known entity"
```

---

## Phase 6 — Frontend

### Task 30: Frontend dependency: `react-force-graph-2d`

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install**

```bash
cd frontend
npm install react-force-graph-2d
```

- [ ] **Step 2: Verify**

Run: `cd frontend && grep react-force-graph-2d package.json`
Expected: dependency line present.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "build(frontend): add react-force-graph-2d for knowledge graph viz"
```

---

### Task 31: SSE proxy route in Next.js

**Files:**
- Create: `frontend/app/api/rag/index/route.ts`
- Create: `frontend/app/api/rag/query/route.ts`
- Create: `frontend/app/api/rag/graph/[doc_hash]/route.ts`

The backend lives at `process.env.RAG_BACKEND_URL` (default `http://localhost:8000`). The Next routes pass-through bytes to keep streaming intact.

- [ ] **Step 1: Create `/api/rag/index`**

Create `frontend/app/api/rag/index/route.ts`:

```typescript
export const runtime = 'nodejs';

const BACKEND = process.env.RAG_BACKEND_URL ?? 'http://localhost:8000';

export async function POST(req: Request) {
  const form = await req.formData();
  const upstream = await fetch(`${BACKEND}/index`, { method: 'POST', body: form });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      'Content-Type': upstream.headers.get('content-type') ?? 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
    },
  });
}
```

- [ ] **Step 2: Create `/api/rag/query`**

Create `frontend/app/api/rag/query/route.ts`:

```typescript
export const runtime = 'nodejs';

const BACKEND = process.env.RAG_BACKEND_URL ?? 'http://localhost:8000';

export async function POST(req: Request) {
  const body = await req.text();
  const upstream = await fetch(`${BACKEND}/query`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body,
  });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      'Content-Type': upstream.headers.get('content-type') ?? 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
    },
  });
}
```

- [ ] **Step 3: Create `/api/rag/graph/[doc_hash]`**

Create `frontend/app/api/rag/graph/[doc_hash]/route.ts`:

```typescript
export const runtime = 'nodejs';

const BACKEND = process.env.RAG_BACKEND_URL ?? 'http://localhost:8000';

export async function GET(_req: Request, { params }: { params: Promise<{ doc_hash: string }> }) {
  const { doc_hash } = await params;
  const r = await fetch(`${BACKEND}/graph/${encodeURIComponent(doc_hash)}`);
  return new Response(await r.text(), {
    status: r.status,
    headers: { 'Content-Type': r.headers.get('content-type') ?? 'application/json' },
  });
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/api/rag
git commit -m "feat(frontend): SSE proxy routes for /index, /query, /graph"
```

---

### Task 32: `ChatStream.tsx` — SSE consumer with citation chip rendering

**Files:**
- Create: `frontend/app/components/CitationChip.tsx`
- Create: `frontend/app/components/ChatStream.tsx`

- [ ] **Step 1: Create `CitationChip.tsx`**

Create `frontend/app/components/CitationChip.tsx`:

```tsx
"use client";

type Citation = { n: number; chunk_id: number };

export function CitationChip({
  n,
  citations,
  onClick,
}: {
  n: number;
  citations: Citation[];
  onClick?: (chunk_id: number) => void;
}) {
  const c = citations.find((x) => x.n === n);
  if (!c) return <span>[{n}]</span>;
  return (
    <button
      onClick={() => onClick?.(c.chunk_id)}
      className="inline-block mx-0.5 px-1.5 py-0.5 text-xs rounded bg-purple-700/30 text-purple-200 hover:bg-purple-700/60"
      title={`Source chunk ${c.chunk_id}`}
    >
      [{n}]
    </button>
  );
}
```

- [ ] **Step 2: Create `ChatStream.tsx`**

Create `frontend/app/components/ChatStream.tsx`:

```tsx
"use client";

import { useState, useCallback } from "react";
import { CitationChip } from "./CitationChip";

type Citation = { n: number; chunk_id: number };

function renderWithCitations(text: string, citations: Citation[], onCite: (id: number) => void) {
  const parts = text.split(/(\[\d+(?:,\d+)*\])/g);
  return parts.map((p, i) => {
    const m = p.match(/^\[(\d+(?:,\d+)*)\]$/);
    if (!m) return <span key={i}>{p}</span>;
    return (
      <span key={i}>
        {m[1].split(",").map((nStr) => (
          <CitationChip key={nStr} n={Number(nStr)} citations={citations} onClick={onCite} />
        ))}
      </span>
    );
  });
}

export function ChatStream({
  docHash,
  onCiteClick,
}: {
  docHash: string;
  onCiteClick?: (chunk_id: number) => void;
}) {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const ask = useCallback(async () => {
    setAnswer("");
    setCitations([]);
    setErr(null);
    setBusy(true);

    try {
      const r = await fetch("/api/rag/query", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ doc_hash: docHash, query }),
      });
      if (!r.ok || !r.body) {
        setErr(`Request failed: ${r.status}`);
        return;
      }
      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += dec.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const block of events) {
          const lines = block.split("\n");
          const eventLine = lines.find((l) => l.startsWith("event:"));
          const dataLine = lines.find((l) => l.startsWith("data:"));
          if (!eventLine || !dataLine) continue;
          const evt = eventLine.replace("event:", "").trim();
          const data = JSON.parse(dataLine.replace("data:", "").trim());
          if (evt === "context") setCitations(data.citations ?? []);
          else if (evt === "token") setAnswer((a) => a + data.text);
          else if (evt === "error") setErr(data.message ?? "stream error");
        }
      }
    } catch (e: unknown) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }, [docHash, query]);

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <input
          className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2"
          placeholder="Ask about this document…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !busy && ask()}
        />
        <button
          onClick={ask}
          disabled={busy || !query}
          className="px-4 py-2 rounded bg-purple-600 disabled:opacity-50"
        >
          {busy ? "…" : "Ask"}
        </button>
      </div>
      <div className="prose prose-invert max-w-none whitespace-pre-wrap">
        {renderWithCitations(answer, citations, (cid) => onCiteClick?.(cid))}
      </div>
      {err && <div className="text-red-400 text-sm">Error: {err}</div>}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/ChatStream.tsx frontend/app/components/CitationChip.tsx
git commit -m "feat(frontend): SSE chat stream with clickable citation chips"
```

---

### Task 33: `GraphView.tsx` — interactive knowledge graph

**Files:**
- Create: `frontend/app/components/GraphView.tsx`

- [ ] **Step 1: Create `GraphView.tsx`**

Create `frontend/app/components/GraphView.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

type Node = { id: string; type?: string; description?: string };
type Edge = { src: string; dst: string; type?: string };
type GraphData = {
  nodes: Node[];
  edges: Edge[];
  communities?: Record<string, number>;
};

export function GraphView({
  docHash,
  onNodeClick,
  highlightNode,
}: {
  docHash: string;
  onNodeClick?: (entityId: string) => void;
  highlightNode?: string | null;
}) {
  const [data, setData] = useState<GraphData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`/api/rag/graph/${encodeURIComponent(docHash)}`);
        if (!r.ok) {
          setErr(`Graph fetch failed: ${r.status}`);
          return;
        }
        const j = (await r.json()) as GraphData;
        if (!cancelled) setData(j);
      } catch (e: unknown) {
        if (!cancelled) setErr(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [docHash]);

  if (err) return <div className="text-red-400 text-sm">{err}</div>;
  if (!data) return <div className="text-zinc-400">Loading graph…</div>;
  if (data.nodes.length === 0) return <div className="text-zinc-500 text-sm">No graph extracted for this document.</div>;

  const fgData = {
    nodes: data.nodes.map((n) => ({
      id: n.id,
      group: data.communities?.[n.id] ?? 0,
      label: n.id,
    })),
    links: data.edges.map((e) => ({ source: e.src, target: e.dst })),
  };

  return (
    <div className="bg-zinc-900 rounded border border-zinc-800" style={{ height: 480 }}>
      <ForceGraph2D
        graphData={fgData}
        nodeLabel="label"
        nodeCanvasObject={(node, ctx, scale) => {
          const isHi = highlightNode === node.id;
          const r = isHi ? 7 : 4;
          ctx.beginPath();
          ctx.arc(node.x ?? 0, node.y ?? 0, r, 0, 2 * Math.PI);
          const hue = ((node.group as number) * 67) % 360;
          ctx.fillStyle = isHi ? "#fff" : `hsl(${hue},70%,60%)`;
          ctx.fill();
          if (scale > 1.5) {
            ctx.fillStyle = "#ddd";
            ctx.font = `${10 / scale}px sans-serif`;
            ctx.fillText(String(node.label ?? ""), (node.x ?? 0) + r + 2, (node.y ?? 0) + 3);
          }
        }}
        linkColor={() => "rgba(255,255,255,0.12)"}
        onNodeClick={(n) => onNodeClick?.(String(n.id))}
      />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/components/GraphView.tsx
git commit -m "feat(frontend): interactive knowledge graph view (react-force-graph-2d)"
```

---

### Task 34: Wire upload→doc_hash→Dashboard

**Files:**
- Read existing: `frontend/app/Dashboard/page.tsx` (or whatever the dashboard entry is — check `frontend/app/Dashboard/`)
- Modify: existing dashboard files to (a) upload to `/api/rag/index` and parse the SSE `done` event for `doc_hash`, (b) pass `docHash` to `ChatStream` and `GraphView`, (c) replace prior per-operation file uploads.

- [ ] **Step 1: Inspect the existing Dashboard**

Run: `ls frontend/app/Dashboard/ && cat frontend/app/Dashboard/page.tsx 2>/dev/null | head -80`

The current upload component will need an SSE-aware variant. Read it before editing — the file structure is project-specific so the changes below are illustrative.

- [ ] **Step 2: Replace the upload handler to use SSE and store `doc_hash`**

In the Dashboard root component, replace the current file upload logic with:

```tsx
"use client";

import { useState, useRef } from "react";
import { ChatStream } from "../components/ChatStream";
import { GraphView } from "../components/GraphView";

export default function Dashboard() {
  const [docHash, setDocHash] = useState<string | null>(null);
  const [progress, setProgress] = useState<string>("");
  const [highlight, setHighlight] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function upload(file: File) {
    setProgress("uploading…");
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch("/api/rag/index", { method: "POST", body: fd });
    if (!r.ok || !r.body) {
      setProgress(`error ${r.status}`);
      return;
    }
    const reader = r.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const evs = buf.split("\n\n");
      buf = evs.pop() ?? "";
      for (const block of evs) {
        const lines = block.split("\n");
        const evt = lines.find((l) => l.startsWith("event:"))?.slice(6).trim();
        const data = lines.find((l) => l.startsWith("data:"))?.slice(5).trim();
        if (!evt || !data) continue;
        const j = JSON.parse(data);
        if (evt === "done") {
          setDocHash(j.doc_hash);
          setProgress(j.cached ? "cached" : "indexed");
        } else {
          setProgress(evt + (j.n_chunks ? ` (${j.n_chunks} chunks)` : ""));
        }
      }
    }
  }

  return (
    <div className="min-h-screen bg-black text-white p-6 space-y-6">
      <div className="flex items-center gap-4">
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.txt,.md,.docx,.doc"
          onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
        />
        <span className="text-sm text-zinc-400">{progress}</span>
      </div>

      {docHash && (
        <div className="grid lg:grid-cols-2 gap-6">
          <ChatStream docHash={docHash} onCiteClick={(cid) => setHighlight(String(cid))} />
          <GraphView docHash={docHash} highlightNode={highlight} onNodeClick={(id) => setHighlight(id)} />
        </div>
      )}
    </div>
  );
}
```

Replace the existing `Dashboard/page.tsx` with the above (preserve any auth-guarded layout wrappers the project uses — wrap this content in them).

- [ ] **Step 3: Build to catch type errors**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/Dashboard
git commit -m "feat(frontend): dashboard wires SSE upload → doc_hash → chat + graph"
```

---

### Task 35: Manual frontend smoke test

**Files:**
- Modify: `frontend/README.md` (append checklist)

- [ ] **Step 1: Append the checklist**

Append to `frontend/README.md`:

```markdown

## Manual smoke test (hybrid GraphRAG)

Start backend (`cd microService && uvicorn app.main:app --port 8000`) and frontend (`npm run dev`). Then:

- [ ] Upload a PDF → progress events stream → graph view populates
- [ ] Ask a question → answer streams token-by-token
- [ ] Click citation chip → relevant chunk highlights, graph node highlights
- [ ] Click graph node → answer pane filters to that entity
- [ ] Re-upload same file → instant (cached); answer still works
- [ ] Network drop mid-stream → reconnect once, partial answer preserved
```

- [ ] **Step 2: Run the test manually**

Bring up backend + frontend, walk the list, fix any visible issues.

- [ ] **Step 3: Commit**

```bash
git add frontend/README.md
git commit -m "docs(frontend): manual smoke-test checklist for hybrid GraphRAG"
```

---

## Phase 7 — Acceptance Gate

### Task 36: Run the full backend test suite

- [ ] **Step 1: Run all tests**

Run: `cd microService && ./run_tests.sh`
Expected: all unit + integration + api + e2e tests pass.

- [ ] **Step 2: Fix any failures inline** (re-open the failing task, no need to recommit infrastructure)

- [ ] **Step 3: Commit fixes if any**

```bash
git add -u && git commit -m "fix(rag): address acceptance-gate test failures"
```

---

### Task 37: Latency and indexing-throughput checks

- [ ] **Step 1: Time a 20-page-equivalent fixture index**

Pick or create a ~20-page PDF (or use a long markdown file at least 30KB):

```bash
cd microService
time curl -N -X POST -F "file=@tests/fixtures/short.md" http://localhost:8000/index
```

Record the wall-clock time.

- [ ] **Step 2: Verify the indexing-time target**

Acceptance: < 30s for ~20 pages with the free OpenRouter chain.

If over budget: check `OPENROUTER_MODEL_EXTRACT` — extraction is the bottleneck. Reduce concurrency or pick a faster free model.

- [ ] **Step 3: Time a cold-cache query**

```bash
time curl -N -X POST http://localhost:8000/query \
  -H 'content-type: application/json' \
  -d "{\"doc_hash\":\"<paste-from-step-1>\",\"query\":\"what produces ATP?\"}"
```

Record TTFB (time-to-first-token) and total.

- [ ] **Step 4: Verify query target**

Acceptance: TTFB p50 < 1.5s, p95 < 3s on the fixture.

- [ ] **Step 5: Record the numbers in the spec**

Append a "Measured baseline" line in `docs/superpowers/specs/2026-05-15-hybrid-graphrag-design.md` under section 7:

```markdown
## Measured Baseline (sub-project 1 acceptance run, YYYY-MM-DD)
- Indexing (20-page fixture): X.Xs
- Query TTFB: X.Xs / total: X.Xs
- Citation rate (sampled 10 answers): X/10 contain [n] markers
```

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-05-15-hybrid-graphrag-design.md
git commit -m "docs(rag): record measured baseline for acceptance run"
```

---

### Task 38: Final acceptance review

- [ ] **Step 1: Walk the spec's section 7 acceptance criteria**

For each:
- (1) Query latency p50/p95 — verified in Task 37
- (2) Indexing throughput — verified in Task 37
- (3) Citation rate ≥ 90% — sample 10 answers, count `[n]` markers
- (4) All tests pass — verified in Task 36
- (5) Manual frontend checklist — Task 35
- (6) `/summary` and `/quiz` regression — manual check with the fixture

- [ ] **Step 2: If any criterion fails, fix inline before declaring sub-project 1 done**

- [ ] **Step 3: Tag the milestone**

```bash
git tag -a v0.2-hybrid-graphrag -m "Sub-project 1 complete: hybrid GraphRAG retrieval"
```

(Do not push the tag without the user's request.)

---

## Notes for the engineer

- **API key rotation:** The repo's `microService/.env` currently contains a real-looking OpenAI key. Before going further, **rotate that key on the OpenAI dashboard** — assume it has been exposed.
- **OpenRouter free-tier rate limits** are tight. If indexing chains hit 429 repeatedly, switch a paid model into position 1 of `OPENROUTER_MODEL_EXTRACT`.
- **No multi-turn memory** in this sub-project — the `history` field is passed verbatim into prompts but not persisted. Sub-project 2 introduces persistence.
- **Chroma collisions:** Chroma persists per-directory; `chroma_dir` lives under `local_chroma/<doc_hash>/chroma/`. If you change embedding models later, delete the artifact dir before re-indexing — Chroma does not detect embedding-dimension drift.
- **Graph extraction quality** is the single biggest lever for answer accuracy. If answers feel shallow, the first thing to inspect is `graph.json` — are the right entities present?
