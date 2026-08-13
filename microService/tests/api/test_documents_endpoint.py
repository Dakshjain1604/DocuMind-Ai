import pytest
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_get_documents():
    with patch("app.routes.documents.list_all_documents", return_value=[{"doc_hash": "abc"}]):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/documents")
    assert r.status_code == 200
    assert r.json() == {"success": True, "data": {"total": 1, "documents": [{"doc_hash": "abc"}]}}


@pytest.mark.asyncio
async def test_delete_document_success():
    with patch("app.routes.documents.delete_document_artifacts", return_value=True):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete("/documents/abc")
    assert r.status_code == 200
    assert r.json() == {"success": True, "message": "Document abc deleted successfully"}


@pytest.mark.asyncio
async def test_delete_document_not_found():
    with patch("app.routes.documents.delete_document_artifacts", return_value=False):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete("/documents/abc")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_graph_success():
    fake_graph = {"nodes": [], "edges": []}
    with patch("app.routes.documents.artifacts_exist", return_value=True), \
         patch("app.routes.documents.load_artifacts", return_value={"graph": fake_graph}):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/graph/abc")
    assert r.status_code == 200
    assert r.json() == fake_graph


@pytest.mark.asyncio
async def test_get_graph_not_found():
    with patch("app.routes.documents.artifacts_exist", return_value=False):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/graph/abc")
    assert r.status_code == 404
