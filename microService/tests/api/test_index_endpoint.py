import io
import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_index_rejects_oversized_file(monkeypatch):
    monkeypatch.setenv("RAG_MAX_FILE_MB", "1")
    big = b"x" * (2 * 1024 * 1024)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/index", files={"file": ("big.txt", big, "text/plain")})
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_index_rejects_unsupported_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/index", files={"file": ("a.exe", b"x", "application/octet-stream")})
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_index_returns_sse_done_event_when_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_PERSIST_DIR", str(tmp_path))

    async def fake_pipeline(*, file_bytes, documents, request_id=None):
        yield {"event": "done", "data": {"doc_hash": "x", "cached": False, "stats": {"n_chunks": 1}}}

    with patch("app.routes.documents.index_document", fake_pipeline):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/index", files={"file": ("a.txt", b"hello world", "text/plain")})

    assert r.status_code == 200
    body = r.text
    assert "event: done" in body
    assert "doc_hash" in body
