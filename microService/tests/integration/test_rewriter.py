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
