import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.observability import record_trace


@pytest.mark.asyncio
async def test_trace_404_on_unknown_request_id(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_TRACE_DB_PATH", str(tmp_path / "traces.db"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/trace/does-not-exist")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_trace_returns_recorded_fields(tmp_path, monkeypatch):
    db_path = str(tmp_path / "traces.db")
    monkeypatch.setenv("RAG_TRACE_DB_PATH", db_path)

    record_trace(
        "req-123",
        doc_hash="abc",
        query="what is it?",
        total_latency_ms=42.0,
        total_tokens_in=10,
        total_tokens_out=20,
        total_cost_usd=0.0,
        cache_hit=False,
        stages=[{"stage": "rewrite", "latency_ms": 5.0}],
        context=[{"n": 1, "chunk_id": 0}],
        answer_text="the answer",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/trace/req-123")

    assert r.status_code == 200
    body = r.json()
    assert body["doc_hash"] == "abc"
    assert body["query"] == "what is it?"
    assert body["total_latency_ms"] == 42.0
    assert body["cache_hit"] is False
    assert body["stages"] == [{"stage": "rewrite", "latency_ms": 5.0}]
    assert body["context"] == [{"n": 1, "chunk_id": 0}]
    assert body["answer_text"] == "the answer"
