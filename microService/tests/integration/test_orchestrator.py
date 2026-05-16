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
