# DocuMind service

FastAPI backend: indexing, hybrid retrieval, and the generated artifacts.
See the [root README](../README.md) for the architecture and setup.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
./run_tests.sh                # 134 tests; add -q for a quiet run
```

Interactive API docs at `http://localhost:8000/docs`.

## Endpoints

`doc_hash` is always a sha256 hex digest and is validated as such — anything
else is a 400, since these values reach the filesystem.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/` | — | service identity, active provider, embed model, rerank mode |
| GET | `/health` | — | liveness; no model or network calls |
| GET | `/documents` | — | every indexed document |
| DELETE | `/documents/{doc_hash}` | — | deletes that document's artifacts |
| GET | `/graph/{doc_hash}` | — | entity graph, communities, community summaries |
| POST | `/index` | multipart (`files`) | **SSE** — indexing progress |
| POST | `/query` | `{doc_hash, query, history?}` | **SSE** — `context`, `token`…, `done` |
| POST | `/summary` | `{doc_hash}` | **SSE** — `token`…, `done` |
| POST | `/quiz` | `{doc_hash}` | envelope: `cards`, `coverage` |
| POST | `/compliance-audit` | `{doc_hash}` | envelope: `audit`, `coverage` |
| POST | `/audio-briefing` | `{doc_hash}` | envelope: `script`, `coverage` |
| POST | `/slide-deck` | `{doc_hash}` | envelope: `slides`, `coverage` |
| POST | `/chapters` | `{doc_hash}` | envelope: `chapters`, `coverage` |
| POST | `/learning-draft` | `{doc_hash, chapter_id, chapter_title}` | **SSE** |
| POST | `/chapter-quiz` | `{doc_hash, chapter_id, chapter_title}` | envelope: `cards` |
| GET | `/telemetry/stats` | — | aggregate request statistics |
| GET | `/trace/{request_id}` | — | one request's stages, context and answer |

### Response envelope

JSON endpoints return the shape defined in `app/routes/schemas.py`. Three
states, deliberately distinct — an empty result and a failure are different
answers, and no endpoint substitutes invented content for either:

```jsonc
{"success": true,  "data": {"audit": [...], "coverage": {...}}}   // results
{"success": true,  "data": {"audit": [],    "coverage": {...}}}   // nothing found
{"success": false, "error": {"code": "llm_unavailable", "message": "..."},
                   "data": {"audit": []}}                          // could not answer
```

Error codes: `not_indexed`, `llm_unavailable`, `invalid_llm_output`.

`coverage` reports what a generated artifact was actually derived from —
`{sampled_chunks, total_chunks, unit, strategy, is_partial}` — because these
endpoints work from a sample of the document rather than all of it.

### SSE events

`/index` emits `chunking`, `embedding`, `extracting_graph`, `graph_progress`,
`warning`, `detecting_communities`, `summarizing_communities`,
`community_progress`, `done`, `error`.
`/query` and `/summary` emit `context`, `token`, `done`, `error`.
All streams also emit `ping` while idle to keep the connection open.

## Layout

```
app/
  main.py            composition root: lifespan, CORS, error handler, routers
  routes/
    deps.py          request models + require_indexed (one 404 policy)
    schemas.py       ok() / fail() envelope
    documents.py     list, delete, index, graph
    query.py         hybrid retrieval
    studio.py        summary, quiz, audit, briefing, slides
    masterclass.py   chapters, learning draft, chapter quiz
    telemetry.py     root, health, stats, trace
    generation.py    generation logic behind studio.py
  services/
    ingest.py        document loading (incl. OCR), upload save/cleanup
  indexing/          pipeline, graph_extractor, community, store
  retrieval/         orchestrator, search, rewriter, reranker
  core/              llm, embeddings, cache, sse, observability, logging_config
  config/settings.py typed settings; env > retrieval.json > default
```

## Artifacts

Each document lives in `<RAG_PERSIST_DIR>/<doc_hash>/`:

| File | |
|---|---|
| `chroma/` | vector index |
| `bm25_corpus.pkl` | tokenised corpus for BM25 |
| `graph.json` | entities, relations, communities, community summaries |
| `parents.json` | parent-section text, for small-to-big expansion |
| `manifest.json` | filename, sources, created_at, embed_model, counts, warnings |

Writes are atomic (temp file + `os.replace`) and `manifest.json` lands last, so
an interrupted index reads as un-indexed rather than as a document that fails
on its first query.

## Tuning

`tuning/` holds a manual grid search over chunking and fusion parameters
(`sweep.py` → `report.py`), which writes `app/config/retrieval.json`. Settings
resolve as **env var > retrieval.json > default**, so a completed sweep feeds
back into the service. It is run by hand and needs its own source PDF; nothing
in the app depends on it.
