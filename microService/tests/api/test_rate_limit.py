"""Rate limiting (app/core/rate_limit.py). conftest.py sets a very high default
limit for every other test, so this file overrides it down to something small
enough to trip within a handful of requests, then restores state after."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_query_429_once_limit_exceeded(monkeypatch):
    monkeypatch.setenv("RAG_RATE_LIMIT_QUERY_PER_MIN", "2")
    # slowapi's in-memory storage is keyed by client address; ASGITransport
    # requests all share the same synthetic client, so consecutive calls in
    # this test hit the same bucket.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        statuses = []
        for _ in range(4):
            r = await client.post("/query", json={"doc_hash": "0" * 64, "query": "x"})
            statuses.append(r.status_code)

    # First two: normal 404 (doc_hash not indexed) — the limiter doesn't block
    # them, it's the *third* request that should be rejected before reaching
    # the route body.
    assert statuses[:2] == [404, 404]
    assert 429 in statuses[2:]
