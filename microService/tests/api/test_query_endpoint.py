import pytest
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_query_404_on_unknown_doc():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/query", json={"doc_hash": "nope", "query": "x"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_query_streams_when_doc_exists(monkeypatch):
    async def fake_answer(*, doc_hash, query, history=None, request_id=None):
        yield {"event": "context", "data": {"citations": [{"n": 1, "chunk_id": 0}]}}
        yield {"event": "token", "data": {"text": "Hello"}}
        yield {"event": "done", "data": {}}

    with patch("app.routes.deps.artifacts_exist", return_value=True), \
         patch("app.routes.query.answer", fake_answer):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/query", json={"doc_hash": "abc", "query": "what?"})
    assert r.status_code == 200
    assert "X-Request-Id" in r.headers
    body = r.text
    assert "event: context" in body
    assert "event: token" in body
    assert "event: done" in body
