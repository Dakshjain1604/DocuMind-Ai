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
    assert rq.query_variants == []


@pytest.mark.asyncio
async def test_rewrite_returns_query_variants():
    payload = {
        "hyde": "Mitochondria produce ATP.",
        "keywords": "mitochondria ATP",
        "entities_mentioned": ["Mitochondria"],
        "query_variants": [
            "How does the mitochondria generate energy?",
            "What is the process by which mitochondria create ATP?",
            "Explain ATP production in mitochondria.",
        ],
    }
    with patch("app.retrieval.rewriter._call_llm",
               AsyncMock(return_value=LLMResult(content=json.dumps(payload), model_used="m", fallback_count=0))):
        rq = await rewrite_query("how do mitochondria work?", n_variants=3)
    assert len(rq.query_variants) == 3
    assert "energy" in rq.query_variants[0].lower()


@pytest.mark.asyncio
async def test_rewrite_truncates_variants_to_n_variants():
    payload = {
        "hyde": "h", "keywords": "k", "entities_mentioned": [],
        "query_variants": ["a", "b", "c", "d", "e"],
    }
    with patch("app.retrieval.rewriter._call_llm",
               AsyncMock(return_value=LLMResult(content=json.dumps(payload), model_used="m", fallback_count=0))):
        rq = await rewrite_query("q", n_variants=2)
    assert rq.query_variants == ["a", "b"]


@pytest.mark.asyncio
async def test_rewrite_falls_back_to_raw_query_on_failure():
    with patch("app.retrieval.rewriter._call_llm", AsyncMock(side_effect=RuntimeError("boom"))):
        rq = await rewrite_query("plain query")
    assert rq.hyde == "plain query"
    assert rq.keywords == "plain query"
    assert rq.entities_mentioned == []
    assert rq.query_variants == []


@pytest.mark.asyncio
async def test_rewrite_falls_back_with_empty_variants_on_malformed_field():
    payload = {"hyde": "h", "keywords": "k", "entities_mentioned": [], "query_variants": "not-a-list"}
    with patch("app.retrieval.rewriter._call_llm",
               AsyncMock(return_value=LLMResult(content=json.dumps(payload), model_used="m", fallback_count=0))):
        rq = await rewrite_query("q")
    assert rq.query_variants == []
