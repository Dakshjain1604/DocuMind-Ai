import json
import pytest
from unittest.mock import AsyncMock, patch
import app.core.cache as cache_module
from app.core.observability import get_trace
from app.retrieval.orchestrator import answer
from app.retrieval.rewriter import RewrittenQuery


class _FakeBM25:
    def search(self, q, top_k=10):
        return [(0, 1.0), (1, 0.5)]


class _FakeGraphIdx:
    def match_entities(self, mentioned):
        return []

    def traverse_chunks(self, entities, hops=2):
        return []

    def distinct_community_summaries(self, entities):
        return []


@pytest.fixture
def fake_loaded(tmp_path, monkeypatch):
    """Mirrors what _load_artifacts_cached returns: raw paths PLUS pre-built heavy objects."""
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    return {
        "graph": {"nodes": [], "edges": [], "communities": {}, "community_summaries": {}},
        "manifest": {"n_chunks": 2},
        "bm25_path": str(tmp_path / "bm25.pkl"),
        "chroma_dir": str(tmp_path / "chroma"),
        "chroma": object(),  # opaque — _vector_search_chunks is patched
        "bm25": _FakeBM25(),
        "graph_idx": _FakeGraphIdx(),
        "chunks_by_id": {0: "Chunk zero text [c0]", 1: "Chunk one text [c1]"},
    }


@pytest.mark.asyncio
async def test_answer_streams_tokens_with_one_retriever_dead(fake_loaded):
    async def fake_rewrite(q, *, n_variants=0, **_kwargs):
        return RewrittenQuery(hyde="h", keywords="k", entities_mentioned=[])

    def fake_vector(*a, **k):
        raise RuntimeError("vector down")

    async def fake_stream(*, role, messages, temperature, max_tokens=None):
        yield "Answer ", "m"
        yield "[1]", "m"

    with patch("app.retrieval.orchestrator._load_artifacts_cached", return_value=fake_loaded), \
         patch("app.retrieval.orchestrator.rewrite_query", fake_rewrite), \
         patch("app.retrieval.orchestrator._vector_search_chunks", fake_vector), \
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


@pytest.mark.asyncio
async def test_answer_fans_out_vector_search_across_query_variants(fake_loaded):
    """Multi-query retrieval: one vector_search call per (hyde + variants),
    fused together before the outer vector/BM25/graph RRF."""
    async def fake_rewrite(q, *, n_variants=0, **_kwargs):
        return RewrittenQuery(
            hyde="hyde text", keywords="k", entities_mentioned=[],
            query_variants=["variant one", "variant two"],
        )

    calls = []

    def fake_vector_search_chunks(chroma, query, top_k):
        calls.append(query)
        return [0] if query == "hyde text" else [1]

    async def fake_stream(*, role, messages, temperature, max_tokens=None):
        yield "ok", "m"

    with patch("app.retrieval.orchestrator._load_artifacts_cached", return_value=fake_loaded), \
         patch("app.retrieval.orchestrator.rewrite_query", fake_rewrite), \
         patch("app.retrieval.orchestrator._vector_search_chunks", fake_vector_search_chunks), \
         patch("app.retrieval.orchestrator.get_llm") as gl:
        gl.return_value.stream = fake_stream
        events = []
        async for e in answer(doc_hash="abc", query="what?"):
            events.append(e)

    # query + hyde + 2 variants = 4 calls to the vector leg
    assert sorted(calls) == ["hyde text", "variant one", "variant two", "what?"]
    assert events[0]["event"] == "context"


@pytest.fixture
def fake_loaded_with_parents(fake_loaded):
    """Two child chunks (0, 1) both belong to parent 0; chunk 2 has no parent data."""
    fake_loaded["parent_id_by_chunk"] = {0: 0, 1: 0}
    fake_loaded["parents_by_id"] = {0: "Big coherent parent passage covering chunks zero and one."}
    fake_loaded["chunks_by_id"] = {
        0: "Chunk zero text [c0]",
        1: "Chunk one text [c1]",
        2: "Chunk two text, no parent [c2]",
    }
    return fake_loaded


@pytest.mark.asyncio
async def test_answer_dedupes_children_sharing_a_parent_into_one_passage(fake_loaded_with_parents):
    """Two ranked children (0 and 1) share parent 0 — should collapse into a
    single context passage using the parent's text, not two near-duplicates."""
    async def fake_rewrite(q, *, n_variants=0, **_kwargs):
        return RewrittenQuery(hyde="h", keywords="k", entities_mentioned=[])

    def fake_vector_search_chunks(chroma, query, top_k):
        return [0, 1]  # both children of parent 0

    async def fake_stream(*, role, messages, temperature, max_tokens=None):
        yield "ok", "m"

    with patch("app.retrieval.orchestrator._load_artifacts_cached", return_value=fake_loaded_with_parents), \
         patch("app.retrieval.orchestrator.rewrite_query", fake_rewrite), \
         patch("app.retrieval.orchestrator._vector_search_chunks", fake_vector_search_chunks), \
         patch("app.retrieval.orchestrator._bm25_search_chunks", return_value=[]), \
         patch("app.retrieval.orchestrator.get_llm") as gl:
        gl.return_value.stream = fake_stream
        events = []
        async for e in answer(doc_hash="abc", query="what?"):
            events.append(e)

    context_event = next(e for e in events if e["event"] == "context")
    citations = context_event["data"]["citations"]
    # one passage, not two, even though both chunk 0 and chunk 1 were ranked
    assert len(citations) == 1


@pytest.mark.asyncio
async def test_answer_falls_back_to_child_text_when_no_parent_data(fake_loaded):
    """Docs indexed before parent-child chunking shipped have no parents_path —
    context expansion must gracefully fall back to child text, not crash."""
    async def fake_rewrite(q, *, n_variants=0, **_kwargs):
        return RewrittenQuery(hyde="h", keywords="k", entities_mentioned=[])

    def fake_vector_search_chunks(chroma, query, top_k):
        return [0, 1]

    async def fake_stream(*, role, messages, temperature, max_tokens=None):
        yield "ok", "m"

    with patch("app.retrieval.orchestrator._load_artifacts_cached", return_value=fake_loaded), \
         patch("app.retrieval.orchestrator.rewrite_query", fake_rewrite), \
         patch("app.retrieval.orchestrator._vector_search_chunks", fake_vector_search_chunks), \
         patch("app.retrieval.orchestrator._bm25_search_chunks", return_value=[]), \
         patch("app.retrieval.orchestrator.get_llm") as gl:
        gl.return_value.stream = fake_stream
        events = []
        async for e in answer(doc_hash="abc", query="what?"):
            events.append(e)

    context_event = next(e for e in events if e["event"] == "context")
    assert len(context_event["data"]["citations"]) == 2


@pytest.mark.asyncio
async def test_answer_returns_cached_response_on_repeat_query(fake_loaded, monkeypatch, tmp_path):
    monkeypatch.setattr(cache_module, "_disk_singleton", None)
    monkeypatch.setenv("RAG_CACHE_DIR", str(tmp_path / "disk_cache"))
    monkeypatch.setenv("RAG_ANSWER_CACHE_ENABLED", "true")

    async def fake_rewrite(q, *, n_variants=0, **_kwargs):
        return RewrittenQuery(hyde="h", keywords="k", entities_mentioned=[])

    def fake_vector_search_chunks(chroma, query, top_k):
        return [0]

    stream_call_count = 0

    async def fake_stream(*, role, messages, temperature, max_tokens=None):
        nonlocal stream_call_count
        stream_call_count += 1
        yield "Answer one", "m"

    with patch("app.retrieval.orchestrator._load_artifacts_cached", return_value=fake_loaded), \
         patch("app.retrieval.orchestrator.rewrite_query", fake_rewrite), \
         patch("app.retrieval.orchestrator._vector_search_chunks", fake_vector_search_chunks), \
         patch("app.retrieval.orchestrator._bm25_search_chunks", return_value=[]), \
         patch("app.retrieval.orchestrator.get_llm") as gl:
        gl.return_value.stream = fake_stream

        first_events = [e async for e in answer(doc_hash="abc", query="what is it?")]
        second_events = [e async for e in answer(doc_hash="abc", query="what is it?")]

    monkeypatch.setattr(cache_module, "_disk_singleton", None)

    assert stream_call_count == 1  # second call served from the answer cache, no LLM stream
    first_text = "".join(e["data"]["text"] for e in first_events if e["event"] == "token")
    second_text = "".join(e["data"]["text"] for e in second_events if e["event"] == "token")
    assert first_text == second_text == "Answer one"
    assert [e["event"] for e in second_events] == ["context", "token", "done"]


@pytest.mark.asyncio
async def test_answer_does_not_use_cache_when_history_present(fake_loaded, monkeypatch, tmp_path):
    monkeypatch.setattr(cache_module, "_disk_singleton", None)
    monkeypatch.setenv("RAG_CACHE_DIR", str(tmp_path / "disk_cache"))
    monkeypatch.setenv("RAG_ANSWER_CACHE_ENABLED", "true")

    async def fake_rewrite(q, *, n_variants=0, **_kwargs):
        return RewrittenQuery(hyde="h", keywords="k", entities_mentioned=[])

    def fake_vector_search_chunks(chroma, query, top_k):
        return [0]

    stream_call_count = 0

    async def fake_stream(*, role, messages, temperature, max_tokens=None):
        nonlocal stream_call_count
        stream_call_count += 1
        yield f"Answer {stream_call_count}", "m"

    with patch("app.retrieval.orchestrator._load_artifacts_cached", return_value=fake_loaded), \
         patch("app.retrieval.orchestrator.rewrite_query", fake_rewrite), \
         patch("app.retrieval.orchestrator._vector_search_chunks", fake_vector_search_chunks), \
         patch("app.retrieval.orchestrator._bm25_search_chunks", return_value=[]), \
         patch("app.retrieval.orchestrator.get_llm") as gl:
        gl.return_value.stream = fake_stream

        history = [{"role": "user", "content": "earlier turn"}]
        _ = [e async for e in answer(doc_hash="abc", query="what is it?", history=history)]
        _ = [e async for e in answer(doc_hash="abc", query="what is it?", history=history)]

    monkeypatch.setattr(cache_module, "_disk_singleton", None)
    assert stream_call_count == 2  # history present -> cache bypassed both times


@pytest.mark.asyncio
async def test_answer_persists_trace_with_stages_and_context(fake_loaded, tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_TRACE_DB_PATH", str(tmp_path / "traces.db"))

    async def fake_rewrite(q, *, n_variants=0, **_kwargs):
        return RewrittenQuery(hyde="h", keywords="k", entities_mentioned=[])

    def fake_vector_search_chunks(chroma, query, top_k):
        return [0]

    async def fake_stream(*, role, messages, temperature, max_tokens=None):
        yield "The answer", "test-model"

    with patch("app.retrieval.orchestrator._load_artifacts_cached", return_value=fake_loaded), \
         patch("app.retrieval.orchestrator.rewrite_query", fake_rewrite), \
         patch("app.retrieval.orchestrator._vector_search_chunks", fake_vector_search_chunks), \
         patch("app.retrieval.orchestrator._bm25_search_chunks", return_value=[]), \
         patch("app.retrieval.orchestrator.get_llm") as gl:
        gl.return_value.stream = fake_stream
        events = [e async for e in answer(doc_hash="abc", query="what is it?", request_id="trace-test-1")]

    trace = get_trace("trace-test-1")
    assert trace is not None
    assert trace["doc_hash"] == "abc"
    assert trace["query"] == "what is it?"
    assert trace["cache_hit"] is False
    assert trace["answer_text"] == "The answer"
    assert trace["total_latency_ms"] > 0
    stage_names = [s["stage"] for s in trace["stages"]]
    assert stage_names == ["rewrite", "retrieval", "fusion", "rerank", "generation"]
    assert len(trace["context"]) >= 1


@pytest.mark.asyncio
async def test_answer_persists_partial_trace_on_error(fake_loaded, tmp_path, monkeypatch):
    """If generation raises mid-stream, a trace record should still be
    written (partial answer, error message) rather than silently lost, and the
    stream should end on a single `error` frame — not re-raise, which used to
    produce a duplicate error frame via the sse transporter's wrapper."""
    monkeypatch.setenv("RAG_TRACE_DB_PATH", str(tmp_path / "traces.db"))

    async def fake_rewrite(q, *, n_variants=0, **_kwargs):
        return RewrittenQuery(hyde="h", keywords="k", entities_mentioned=[])

    def fake_vector_search_chunks(chroma, query, top_k):
        return [0]

    async def fake_stream(*, role, messages, temperature, max_tokens=None):
        yield "partial ", "test-model"
        raise RuntimeError("connection dropped")

    with patch("app.retrieval.orchestrator._load_artifacts_cached", return_value=fake_loaded), \
         patch("app.retrieval.orchestrator.rewrite_query", fake_rewrite), \
         patch("app.retrieval.orchestrator._vector_search_chunks", fake_vector_search_chunks), \
         patch("app.retrieval.orchestrator._bm25_search_chunks", return_value=[]), \
         patch("app.retrieval.orchestrator.get_llm") as gl:
        gl.return_value.stream = fake_stream
        events = []
        # answer() emits an `error` frame and stops the generator cleanly.
        async for e in answer(doc_hash="abc", query="what is it?", request_id="trace-test-error"):
            events.append(e)

    assert [e["event"] for e in events][-1] == "error"
    trace = get_trace("trace-test-error")
    assert trace is not None
    assert trace["error"] is not None
    assert trace["answer_text"] == "partial "
