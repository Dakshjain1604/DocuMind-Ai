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
