"""The telemetry router's non-trace routes: /, /health, /telemetry/stats.

/trace/{id} already has dedicated coverage in test_trace_endpoint.py.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.observability import record_trace
from app.main import app


@pytest.mark.asyncio
async def test_root_reports_service_identity():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"]
    assert "embed_model" in body
    assert "rerank_mode" in body


@pytest.mark.asyncio
async def test_health_reports_ok_when_provider_key_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm_provider"] == "openrouter"
    assert body["llm_provider_key_configured"] is True


@pytest.mark.asyncio
async def test_health_reports_degraded_when_provider_key_missing(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert body["llm_provider_key_configured"] is False


@pytest.mark.asyncio
async def test_telemetry_stats_empty_db(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_TRACE_DB_PATH", str(tmp_path / "empty_traces.db"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/telemetry/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["total_requests"] == 0
    assert body["data"]["recent_traces"] == []


@pytest.mark.asyncio
async def test_telemetry_stats_aggregates_recorded_traces(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_TRACE_DB_PATH", str(tmp_path / "traces.db"))
    record_trace(
        "req-a", doc_hash="abc", query="q1", total_latency_ms=10.0,
        total_tokens_in=5, total_tokens_out=5, total_cost_usd=0.0,
    )
    record_trace(
        "req-b", doc_hash="abc", query="q2", total_latency_ms=30.0, error="boom",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/telemetry/stats")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total_requests"] == 2
    assert data["error_count"] == 1
    assert len(data["recent_traces"]) == 2
