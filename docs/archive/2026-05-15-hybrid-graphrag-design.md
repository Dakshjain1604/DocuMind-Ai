# DocuMind AI — Hybrid GraphRAG Retrieval Foundation

**Status:** Approved
**Date:** 2026-05-15
**Scope:** Sub-project 1 of 3 (foundation). Sub-project 2 = persistent multi-doc. Sub-project 3 = agentic loop.

## 1. Problem & Goals

The current RAG pipeline (`microService/app/routes/RAG.py`) is a single-shot vector retrieval that:

- Uses deprecated LangChain APIs (`LLMChain`, `get_relevant_documents`)
- Chunks with a naive `CharacterTextSplitter` (1500/250)
- Retrieves with MMR k=5 only — no lexical fallback, no reranking, no query rewriting
- Hard-codes `gpt-3.5-turbo` for answers
- Clobbers the in-memory cache on every upload (`main.py:25` — `clear_document_cache()` before every operation)
- Returns a blocking response (no streaming, no citations, no progress feedback)
- Re-uploads the file for every operation (`/getSummary`, `/getQuiz`, `/RAG` each take a fresh `UploadFile`)

**Goals for this sub-project:**

1. Replace single-shot vector retrieval with **hybrid GraphRAG**: vector + BM25 + knowledge-graph traversal fused via Reciprocal Rank Fusion.
2. Add **knowledge-graph extraction per document** (entities + relationships + community summaries) with an interactive frontend visualization.
3. Move all LLM calls to **OpenRouter** with an env-driven model fallback chain (free models first, paid as safety net).
4. **Stream** all long-running operations (indexing progress, answer tokens) via SSE.
5. Add **citations** to every answer with frontend chip UI that ties citations to chunks and graph nodes.
6. Fix the cache eviction bug; switch to per-doc content-hash addressing so re-uploading the same file is a no-op.
7. Decouple upload from query: upload once → `doc_hash` → all subsequent operations reuse it.

**Non-goals (deferred):**

- Multi-tenant, per-user persistent stores (sub-project 2)
- Agentic loop, tool use, multi-step retrieval (sub-project 3)
- OCR for scanned PDFs
- Real-time graph editing in the UI
- Auth / MongoDB schema changes

## 2. Architecture Overview

```
┌─────────────┐      ┌─────────────────────────────────────────────────┐
│   Next.js   │ ───► │  FastAPI / microService                         │
│  frontend   │      │                                                 │
│             │      │  ┌──────────────┐    ┌──────────────────────┐  │
│  - upload   │ ───► │  │ Indexer      │    │ Query Orchestrator   │  │
│  - chat     │      │  │ - chunk      │    │  ┌────────────────┐  │  │
│  - graph    │ ◄─── │  │ - embed      │    │  │ Query Rewriter │  │  │
│  - cite UI  │ SSE  │  │ - extract    │    │  └────┬───────────┘  │  │
└─────────────┘      │  │   graph      │    │       ▼              │  │
                     │  │ - community  │    │  ┌─────────────────┐ │  │
                     │  │   summarize  │    │  │  Vector  BM25   │ │  │
                     │  └──────────────┘    │  │  Graph traversal│ │  │
                     │         │            │  └────────┬────────┘ │  │
                     │         ▼            │           ▼          │  │
                     │  ┌──────────────┐    │     ┌────────────┐   │  │
                     │  │ Chroma (vec) │ ◄──┤     │   RRF      │   │  │
                     │  │ Graph (JSON) │    │     │   fusion   │   │  │
                     │  │ BM25 (mem)   │    │     │   + rerank │   │  │
                     │  └──────────────┘    │     └─────┬──────┘   │  │
                     │                      │           ▼          │  │
                     │                      │     ┌────────────┐   │  │
                     │  OpenRouter ◄────────┼─────│  Answerer  │   │  │
                     │  (LLMs, free→paid)   │     │  (stream)  │   │  │
                     │                      │     └────────────┘   │  │
                     │                      └──────────────────────┘  │
                     └─────────────────────────────────────────────────┘
```

**Key shifts vs. current code:**

- LLM provider: OpenRouter, role-based model routing with ordered fallback list per role.
- Chunking: `RecursiveCharacterTextSplitter` (1000/150) with `{chapter, section, page}` metadata.
- Retrieval: triple-source — Chroma vector + in-memory BM25 + NetworkX graph traversal — fused via Reciprocal Rank Fusion.
- New artifacts per doc: `chroma/`, `graph.json`, `bm25_corpus.pkl` all under `./local_chroma/<doc_hash>/`.
- Transport: SSE for both indexing progress and answer streaming.
- Bugfix: per-doc LRU cache replaces global clear-on-every-upload.

## 3. Components

### 3.1 Backend module layout (`microService/app/`)

```
microService/app/
├── main.py                    # FastAPI routes (modified)
├── routes/
│   ├── DocContent.py          # refactored — delegates to core + indexing
│   ├── summary.py             # uses new retrieval (modified)
│   ├── quiz.py                # uses new retrieval (modified)
│   ├── RAG.py                 # thin wrapper over retrieval.orchestrator
│   └── utils.py
├── core/                      # NEW — provider-agnostic primitives
│   ├── llm.py                 # OpenRouter client + role-based fallback
│   ├── chunker.py             # RecursiveCharacterTextSplitter wrapper
│   ├── embeddings.py          # embedding model (OpenAI text-embedding-3-large)
│   ├── cache.py               # per-doc LRU cache (max 3 docs)
│   ├── streaming.py           # SSE helpers (event format, error events)
│   └── logging.py             # structured JSON request logs
├── indexing/                  # NEW — build-time pipeline
│   ├── pipeline.py            # load → chunk → embed → graph → community → persist
│   ├── graph_extractor.py     # LLM-based entity/relation extraction (async, batched)
│   ├── community.py           # Louvain + community summarization
│   └── store.py               # persist Chroma + graph.json + bm25_corpus.pkl
└── retrieval/                 # NEW — query-time pipeline
    ├── orchestrator.py        # public answer() entry point
    ├── rewriter.py            # query → {hyde, keywords, entities_mentioned}
    ├── vector.py              # Chroma search wrapper
    ├── bm25.py                # in-memory BM25 over chunks
    ├── graph.py               # NetworkX traversal (entity match → k-hop)
    ├── fusion.py              # pure Reciprocal Rank Fusion
    └── reranker.py            # optional cross-encoder rerank (env-flagged)
```

### 3.2 Module responsibilities

- **`core/llm.py`** — single `get_llm(role)` factory. Uses the `openai` SDK pointed at `https://openrouter.ai/api/v1` (OpenAI-compatible mode) for chat completions. Roles: `extract`, `answer`, `rewrite`, `rerank`. Each role maps to an ordered fallback list of OpenRouter model IDs via env. On 429/5xx/timeout the client walks the list. Embeddings stay on OpenAI direct (`text-embedding-3-large`) via `langchain_openai.OpenAIEmbeddings`.
- **`core/chunker.py`** — chunks with chapter/section regex metadata preserved on each chunk for graph anchoring.
- **`core/cache.py`** — per-process LRU `{doc_hash → (Chroma, NetworkX graph, BM25)}`, max 3 entries, true LRU eviction (not global clear).
- **`indexing/graph_extractor.py`** — for each chunk, calls LLM with structured-output schema `{entities: [{id, type, description}], relationships: [{src, dst, type, description}]}`. Runs concurrent batches of 8 chunks via `asyncio.gather`.
- **`indexing/community.py`** — Louvain on merged graph, then LLM-summarizes each community in 2-3 sentences.
- **`indexing/store.py`** — writes `./local_chroma/<doc_hash>/{chroma/, graph.json, bm25_corpus.pkl}`. `doc_hash` is SHA-256 of file content.
- **`retrieval/orchestrator.py`** — public `async def answer(query, doc_hash, stream=True)`. Fans out vector/bm25/graph in parallel, fuses, optionally reranks, builds context with citation anchors, streams answer.
- **`retrieval/fusion.py`** — pure function, no I/O. Easy to unit-test.

### 3.3 Frontend (`frontend/app/`)

```
frontend/app/
├── components/
│   ├── ChatStream.tsx         # NEW — SSE consumer, token-by-token rendering
│   ├── CitationChip.tsx       # NEW — clickable [1], [2] markers
│   └── GraphView.tsx          # NEW — react-force-graph-2d, lazy-loaded
├── Dashboard/                 # modified — adds GraphView panel + ChatStream
├── api/
│   └── rag/route.ts           # NEW — proxies SSE from FastAPI to browser
```

### 3.4 Dependency changes

**Backend** (`microService/requirements.txt`) — add:
- `rank_bm25`
- `networkx`
- `python-louvain`
- `httpx` (OpenRouter client)
- `openai>=1.0` (used as OpenRouter SDK in OpenAI-compatible mode)
- `tiktoken` (token counting for context budgeting)

**Frontend** (`frontend/package.json`) — add:
- `react-force-graph-2d`

### 3.5 What gets deleted

- `langchain.chains.LLMChain` usage in `RAG.py` (deprecated, replaced by direct chain composition)
- The global `clear_document_cache()` call at `main.py:25`
- `CharacterTextSplitter` usage in `DocContent.py`

## 4. Data Flow

### 4.1 Indexing pipeline (on file upload)

```
POST /index  (multipart: file)
       │
       ▼
1. Save file → tmp/uploaded_files/<name>
2. Compute SHA-256 of file content → doc_hash
3. If ./local_chroma/<doc_hash>/ exists → SKIP indexing.
   SSE stream emits a single `done` event:
     { doc_hash, cached: true, stats: <loaded from saved manifest.json> }
   and closes.
       │
       ▼
4. Load (PyPDFLoader / TextLoader / Unstructured)
       │
       ▼
5. Chunk (RecursiveCharacterTextSplitter, 1000/150, metadata: {chapter, section, page})
       │
       ▼
6. PARALLEL ────────────────────────────────────────────┐
   │ branch A: embed chunks → Chroma (persist on disk) │
   │ branch B: graph extraction                        │
   │   for batch of 8 chunks (asyncio.gather):         │
   │     LLM(extract) → {entities, relationships}      │
   │   merge into NetworkX MultiDiGraph                │
   │     - same entity_id across chunks = same node    │
   │     - dedupe relationships by (src, dst, type)    │
   └───────────────────────────────────────────────────┘
       │
       ▼
7. Community detection (Louvain) → community_id per entity
       │
       ▼
8. Community summarisation (one LLM call per community, parallel, max 8)
       │
       ▼
9. Persist:
   - ./local_chroma/<doc_hash>/chroma/          (Chroma vectors)
   - ./local_chroma/<doc_hash>/graph.json       (nodes, edges, communities, summaries)
   - ./local_chroma/<doc_hash>/bm25_corpus.pkl  (tokenised chunks for BM25 reload)
   - ./local_chroma/<doc_hash>/manifest.json    (stats + indexing version for cache-hit return)
       │
       ▼
10. Return { doc_hash, stats: { n_chunks, n_entities, n_edges, n_communities } }
```

The `/index` endpoint is itself SSE — the frontend renders `chunking → embedding → extracting graph (12/47) → detecting communities → done` so the 10-30s indexing doesn't feel like a hang.

### 4.2 Query pipeline (on chat message)

```
POST /query  (json: { doc_hash, query, history? })   → text/event-stream
  history (optional): array of { role: "user"|"assistant", content: string }
                      passed verbatim into the answer prompt.
                      No server-side memory store this round.
       │
       ▼
1. Load doc artifacts (Chroma, graph.json, bm25_corpus) — cached in-process per doc_hash
       │
       ▼
2. Query rewriter (single LLM call, fast model)
   → { hyde: "<hypothetical answer paragraph>",
       keywords: "term1 term2 term3",
       entities_mentioned: ["X", "Y"] }
       │
       ▼
3. PARALLEL retrieval ──────────────────────────────────┐
   │ vector:   Chroma.similarity_search(hyde, k=10)     │
   │ bm25:     BM25.get_top(keywords, k=10)             │
   │ graph:    for each entity in entities_mentioned:   │
   │             match node (fuzzy) → 1-hop + 2-hop neighbours │
   │             pull source chunks → top 10            │
   │             also pull community summaries that contain it │
   └────────────────────────────────────────────────────┘
       │
       ▼
4. Reciprocal Rank Fusion (k=60 default)
   score(chunk) = Σ 1 / (k + rank_in_source_i)
   → top 15
       │
       ▼
5. Cross-encoder rerank (optional, env-flagged) → top 5
       │
       ▼
6. Build context:
   [chunk_1] (page 4, entity: Mitochondria) <text>
   [chunk_2] (community: "Cellular respiration") <community summary>
   ...
       │
       ▼
7. Answer LLM (stream) with citation-required prompt:
   "Answer the question. For every claim, cite the chunk: [1], [2]..."
       │
       ▼
8. Stream tokens via SSE to frontend
   - frontend renders `[1]` → <CitationChip chunkId={...} />
   - clicking chip → highlights chunk text + entity in GraphView
```

Branches in step 3 run concurrently via `asyncio.gather`. Target: retrieval under 200ms total, first token ~800-1200ms.

### 4.3 Persistence model

- **Per-doc store on disk:** `./local_chroma/<doc_hash>/{chroma,graph.json,bm25_corpus.pkl}`
- **Per-process LRU in memory:** `{doc_hash → (Chroma, NetworkX graph, BM25)}`, max 3 docs, true LRU eviction
- **MongoDB:** no schema changes. Doc-to-user mapping is sub-project 2.

### 4.4 Endpoint changes

| Current                         | New                                                   |
|---------------------------------|-------------------------------------------------------|
| `POST /RAG` (file + input)      | `POST /index` (file) → SSE progress, returns `doc_hash` |
|                                 | `POST /query` (doc_hash + query) → SSE token stream  |
|                                 | `GET /graph/{doc_hash}` → returns nodes+edges JSON   |
| `POST /getSummary` (file)       | `POST /summary` (doc_hash) — reuses cached store     |
| `POST /getQuiz` (file)          | `POST /quiz` (doc_hash) — reuses cached store        |

Frontend uploads once → gets `doc_hash` → all subsequent calls reuse it. **Eliminates the current re-upload-per-operation pattern.**

## 5. Error Handling & Fallbacks

### 5.1 Failure modes

| Stage | Failure | Response |
|---|---|---|
| Upload | File > 25MB | 413 + actionable message |
| Upload | Unsupported file type | 415 + supported list (`.pdf .txt .docx .md`) |
| Upload | Corrupt PDF / empty content | 422 + `"No extractable text — is this a scanned PDF?"` |
| Indexing | OpenRouter free model rate-limit / 429 | Fall back to next model in role chain. If all exhausted, surface SSE `error` event with which role failed; partial artifacts kept so user can retry without re-uploading |
| Indexing | Graph extraction returns malformed JSON | Retry once with stricter prompt + JSON-mode. On second failure, skip that chunk (log + warning event); indexing continues. Doc still queryable via vector + BM25 |
| Indexing | Community detection on graph with <5 nodes | Skip community step; graph traversal still works at entity level |
| Query | `doc_hash` not found on disk | 404 — frontend triggers re-upload |
| Query | Query rewriter fails | Fall back to raw query for all three retrievers. Log + continue |
| Query | One retrieval branch raises | Other two still fuse. Branch errors logged. All-three-fail bubbles up |
| Query | Rerank model unavailable | Skip rerank, use RRF top-5 directly |
| Query | Answer LLM stream interrupted mid-stream | SSE `error` event with `partial: true` + tokens received so far. Frontend keeps partial + shows retry |
| Frontend | SSE connection drop | Auto-reconnect once with same query; second failure surfaces as toast |

### 5.2 Fallback chain

Every LLM role reads an ordered list from env:

```
OPENROUTER_MODEL_EXTRACT="deepseek/deepseek-chat-v3:free,meta-llama/llama-3.3-70b-instruct:free,anthropic/claude-sonnet-4.5"
OPENROUTER_MODEL_ANSWER="meta-llama/llama-3.3-70b-instruct:free,deepseek/deepseek-chat-v3:free,openai/gpt-4o-mini"
OPENROUTER_MODEL_REWRITE="meta-llama/llama-3.1-8b-instruct:free"
OPENROUTER_MODEL_RERANK="qwen/qwen-2.5-7b-instruct:free"
```

`core/llm.py` walks the list on 429/5xx/timeout. Final fallback failure bubbles up as a structured route-level error.

### 5.3 Idempotency & safety

- **Re-upload of same content is a no-op:** SHA-256 of file bytes is the `doc_hash`. Existing `./local_chroma/<doc_hash>/` returns immediately.
- **Partial-index recovery:** on crash mid-flight, next attempt checks which artifacts exist (`chroma/`, `graph.json`, `bm25_corpus.pkl`) and resumes from the missing one.
- **No silent quality degradation:** if graph extraction's success rate drops below 50% of chunks, surface a warning in the indexing response. Don't pretend everything is fine.

### 5.4 Observability

- Structured JSON logs per request: `{ request_id, stage, duration_ms, model_used, fallback_count }`.
- One file: `microService/app/core/logging.py`.
- Stdout only this round; sub-project 2 wires to a real backend.

## 6. Testing Strategy

### 6.1 Test layers

| Layer | Type | Tool | Notes |
|---|---|---|---|
| Pure functions (fusion, chunker, BM25, graph traversal, cache) | Unit | `pytest` | Deterministic, no LLM/network. Fast (<1s total). |
| LLM-using stages | Integration with recorded responses | `pytest` + `respx` | Capture fixtures once against real OpenRouter; replay offline thereafter. |
| Full pipeline | E2E | `pytest` + tiny corpus | One short PDF + one MD doc in `microService/tests/fixtures/`. |
| API contracts (SSE) | API | `pytest` + `httpx.AsyncClient` | Verify event stream format, error events, headers. |
| Frontend graph + streaming UI | Manual | Browser | Checklist in `frontend/README.md`. |

### 6.2 Test layout

```
microService/tests/
├── conftest.py                       # fixtures: tiny corpus, mock OpenRouter
├── fixtures/
│   ├── short.pdf
│   ├── short.md
│   └── llm_responses/                # recorded OpenRouter responses
├── unit/
│   ├── test_fusion.py
│   ├── test_chunker.py
│   ├── test_bm25.py
│   ├── test_graph_traversal.py
│   └── test_cache.py
├── integration/
│   ├── test_graph_extractor.py
│   ├── test_query_rewriter.py
│   └── test_answerer.py
├── api/
│   ├── test_index_endpoint.py
│   └── test_query_endpoint.py
└── e2e/
    └── test_full_pipeline.py
```

### 6.3 Critical assertions

1. **`test_cache::test_lru_eviction_not_global_clear`** — uploading doc B does NOT evict doc A unless cache is full. Regression test for the `clear_document_cache()` bug.
2. **`test_fusion::test_rrf_handles_disjoint_results`** — when vector and BM25 return zero overlap, fusion still produces a ranked list.
3. **`test_index_endpoint::test_reupload_same_file_is_noop`** — SHA-256 cache hit returns existing `doc_hash` without re-indexing.
4. **`test_answerer::test_response_contains_citations`** — sampled output regex-matches `\[\d+\]`.
5. **`test_query_endpoint::test_one_retriever_failure_still_answers`** — kill the graph retriever mid-request; vector+BM25 still answer.
6. **`test_full_pipeline::test_known_entity_retrievable`** — fixture mentions "mitochondria"; query "what produces ATP?" returns a chunk containing that word.

### 6.4 CI

- `microService/run_tests.sh` → `pytest -v --tb=short`
- Pre-commit runs unit tests only.
- Integration + e2e run on-demand.
- Recorded LLM fixtures → CI never hits OpenRouter (no flakiness, no cost).

### 6.5 Manual frontend checklist (in `frontend/README.md`)

- [ ] Upload PDF → progress events stream → graph view populates
- [ ] Ask a question → answer streams token-by-token
- [ ] Click citation chip → relevant chunk highlights, graph node highlights
- [ ] Click graph node → answer pane filters to that entity
- [ ] Re-upload same file → instant (cached); answer still works
- [ ] Network drop mid-stream → reconnect once, partial answer preserved

## 7. Acceptance Criteria

1. End-to-end query latency (TTFB after upload cached): **p50 < 1.5s, p95 < 3s** on fixture corpus.
2. Indexing throughput: **20-page PDF in < 30s** with free OpenRouter models.
3. Citation rate: **≥90%** of factual claims in answers carry a `[n]` citation.
4. All unit + integration + e2e tests pass.
5. Manual frontend checklist all green.
6. Zero regressions on `/getSummary` and `/getQuiz` — they migrate to the `doc_hash` flow and produce equivalent or better output on fixture docs.

## 8. Open Questions Resolved During Brainstorming

- **LLM provider:** OpenRouter, free models first, paid fallback per role.
- **Graph role:** Hybrid (graph + vector + BM25 fused with RRF), not graph-primary.
- **Graph viz:** Interactive in frontend (`react-force-graph-2d`).
- **Persistence scope this round:** Per-document (multi-doc is sub-project 2).
- **Approach selected:** A — Polished hybrid GraphRAG.

## Acceptance Status (sub-project 1)

Implementation completed 2026-05-16 on branch `feature/hybrid-graphrag`.

| Criterion | Status |
|---|---|
| Backend test suite | ✅ 47 passed, 1 skipped (e2e — requires real OPENAI_API_KEY) |
| All planned routes wired | ✅ `/`, `/index`, `/query`, `/graph/{doc_hash}`, `/summary`, `/quiz` (verified via `python -c "from app.main import app"`) |
| Server boots + guard endpoints respond | ✅ verified — 200/404/415 paths return expected JSON |
| Frontend builds | ✅ `npm run build` clean, 15/15 pages compiled |
| Indexing throughput (p20-page < 30s) | ⏳ pending — requires real `OPENROUTER_API_KEY` in `microService/.env` to measure |
| Query TTFB (p50 < 1.5s, p95 < 3s) | ⏳ pending — same |
| Citation rate ≥ 90% | ⏳ pending — same (sample 10 answers post-config) |
| Manual frontend checklist (`frontend/README.md`) | ⏳ pending — same |

### To complete acceptance

1. Add `OPENROUTER_API_KEY` and the four `OPENROUTER_MODEL_*` env vars to `microService/.env` (see `.env.example`).
2. Start backend (`cd microService && uvicorn app.main:app --port 8000`) and frontend (`cd frontend && npm run dev`).
3. Walk the manual checklist in `frontend/README.md`.
4. Record measured numbers below.

### Measured Baseline (fill in when you run the acceptance)

- Indexing (20-page fixture): TBD
- Query TTFB: TBD / total: TBD
- Citation rate (sampled 10 answers): TBD/10

## 9. Follow-on Work (sub-projects 2 and 3)

- **Sub-project 2** — Persistent multi-doc per-user knowledge base. Adds doc-to-user mapping in MongoDB, cross-document graph merging, per-user query scope, real metrics backend.
- **Sub-project 3** — Agentic loop. Adds query decomposition, multi-step retrieval, tool use (e.g. summarize-section, compare-chapters, calc), self-correction. Builds on the hybrid retrieval primitives this spec delivers.
