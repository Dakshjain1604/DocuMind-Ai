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
