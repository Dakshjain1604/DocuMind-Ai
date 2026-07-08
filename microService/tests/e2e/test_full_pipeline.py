"""End-to-end: index a small fixture, then query for a known fact.

LLM calls (graph extraction, summaries, query rewrite, answer streaming) are
mocked. Embeddings via Chroma are NOT mocked — this test requires a real
OPENAI_API_KEY to validate the full real-Chroma + real-BM25 retrieval path.
The test skips when only the placeholder test key is present.
"""
import json
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from langchain_core.documents import Document

from app.indexing.pipeline import index_document
from app.retrieval.orchestrator import answer
from app.indexing.graph_extractor import GraphBuild


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "short.md"


pytestmark = pytest.mark.skipif(
    os.environ.get("OPENAI_API_KEY", "sk-test").startswith("sk-test"),
    reason="e2e requires a real OPENAI_API_KEY for Chroma embeddings",
)


@pytest.fixture
def isolated_persist(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))
    return tmp_path


@pytest.mark.asyncio
async def test_index_then_query_for_known_fact(isolated_persist):
    text = FIXTURE.read_text()
    docs = [Document(page_content=text, metadata={"source": str(FIXTURE), "page": 1})]

    async def fake_extract(chunks, *, concurrency=16):
        yield "result", GraphBuild(
            entities=[
                {"id": "Mitochondria", "type": "Organelle", "description": "ATP producer", "source_chunks": [0]},
                {"id": "ATP", "type": "Concept", "description": "energy currency", "source_chunks": [0]},
            ],
            relationships=[{"src": "Mitochondria", "dst": "ATP", "type": "produces",
                            "description": "via cellular respiration", "source_chunks": [0]}],
        )

    async def fake_summaries(g, c, *, concurrency=8, max_communities=None):
        yield "result", {}

    async def fake_rewrite(q, *, n_variants=0):
        from app.retrieval.rewriter import RewrittenQuery
        return RewrittenQuery(hyde="mitochondria produce atp", keywords="mitochondria atp", entities_mentioned=["Mitochondria"])

    async def fake_stream(*, role, messages, temperature):
        yield "Mitochondria produce ATP ", "m"
        yield "[1]", "m"

    doc_hash = None
    with patch("app.indexing.pipeline.extract_graph_streaming", fake_extract), \
         patch("app.indexing.pipeline.summarize_communities_streaming", fake_summaries):
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
