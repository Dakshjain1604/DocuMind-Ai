"""Per-user document ownership (app/routes/deps.py::require_owned).

Documents tagged with an "owners" list are only visible/mutable by an owner;
documents with no "owners" key at all (indexed before ownership existed) stay
shared, matching the app's pre-existing single-tenant behavior. Auth itself is
bypassed by the autouse tests/conftest.py::bypass_auth fixture, which returns
{"user_id": "test"} — app.core.auth.get_owner_id() falls through id/email/sub,
none of which "user_id" matches, so the bypassed identity resolves to None
unless a test overrides it.
"""
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_current_user
from app.main import app

DOC_HASH = "ef" * 32


def _as_user(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    return user_id


@pytest.fixture(autouse=True)
def _reset_override():
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_documents_filters_to_owner_and_legacy_shared():
    _as_user("alice")
    docs = [
        {"doc_hash": "a" * 64, "owners": ["alice"]},
        {"doc_hash": "b" * 64, "owners": ["bob"]},
        {"doc_hash": "c" * 64, "owners": []},  # legacy/shared
    ]
    with patch("app.routes.documents.list_all_documents", return_value=docs):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/documents")
    assert r.status_code == 200
    hashes = {d["doc_hash"] for d in r.json()["data"]["documents"]}
    assert hashes == {"a" * 64, "c" * 64}
    # "owners" is internal bookkeeping, not part of the public response shape.
    assert all("owners" not in d for d in r.json()["data"]["documents"])


@pytest.mark.asyncio
async def test_delete_403_for_non_owner():
    _as_user("bob")
    with patch("app.routes.deps.artifacts_exist", return_value=True), \
         patch("app.routes.deps.load_artifacts", return_value={"manifest": {"owners": ["alice"]}}):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete(f"/documents/{DOC_HASH}")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_200_for_owner():
    _as_user("alice")
    with patch("app.routes.deps.artifacts_exist", return_value=True), \
         patch("app.routes.deps.load_artifacts", return_value={"manifest": {"owners": ["alice"]}}), \
         patch("app.routes.documents.delete_document_artifacts", return_value=True):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete(f"/documents/{DOC_HASH}")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_delete_200_for_legacy_shared_document():
    """No "owners" key at all -> visible/mutable by anyone, matching pre-ownership behavior."""
    _as_user("anyone")
    with patch("app.routes.deps.artifacts_exist", return_value=True), \
         patch("app.routes.deps.load_artifacts", return_value={"manifest": {}}), \
         patch("app.routes.documents.delete_document_artifacts", return_value=True):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete(f"/documents/{DOC_HASH}")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_graph_403_for_non_owner():
    _as_user("bob")
    with patch("app.routes.documents.artifacts_exist", return_value=True), \
         patch("app.routes.deps.artifacts_exist", return_value=True), \
         patch("app.routes.deps.load_artifacts", return_value={"manifest": {"owners": ["alice"]}}):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/graph/{DOC_HASH}")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_query_403_for_non_owner():
    _as_user("bob")
    with patch("app.routes.deps.artifacts_exist", return_value=True), \
         patch("app.routes.deps.load_artifacts", return_value={"manifest": {"owners": ["alice"]}}):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/query", json={"doc_hash": DOC_HASH, "query": "what?"})
    assert r.status_code == 403
