"""JWT auth on protected routes.

The autouse `bypass_auth` fixture (tests/conftest.py) overrides
get_current_user for every other test in the suite so they don't need a real
token. These tests remove that override to exercise the real dependency:
missing/invalid/expired tokens must be rejected, a valid one must pass, and
the telemetry routes must stay open regardless.
"""
import time

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_current_user
from app.main import app

# Matches the JWT_SECRET conftest.py sets via os.environ.setdefault.
SECRET = "test-jwt-secret-do-not-use-in-prod-0123456789"


def _token(*, exp_delta: int = 3600, secret: str = SECRET, **extra_claims) -> str:
    payload = {"id": "user-1", "email": "user@example.com", "name": "Test User",
               "exp": int(time.time()) + exp_delta, **extra_claims}
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def real_auth():
    """Exercise the real get_current_user dependency instead of the autouse bypass."""
    app.dependency_overrides.pop(get_current_user, None)
    yield


PROTECTED_ROUTES = [
    ("GET", "/documents", None),
    ("GET", "/graph/" + "0" * 64, None),
    ("DELETE", "/documents/" + "0" * 64, None),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,json_body", PROTECTED_ROUTES)
async def test_protected_route_401_without_token(real_auth, method, path, json_body):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.request(method, path, json=json_body)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_401_on_malformed_header(real_auth):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/documents", headers={"Authorization": "NotBearer abc"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_401_on_invalid_token(real_auth):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/documents", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_401_on_wrong_secret(real_auth):
    token = _token(secret="a-completely-different-secret-value")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/documents", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_401_on_expired_token(real_auth):
    token = _token(exp_delta=-3600)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/documents", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_200_with_valid_token(real_auth, monkeypatch):
    monkeypatch.setattr("app.routes.documents.list_all_documents", lambda: [])
    token = _token()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/documents", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/", "/health", "/telemetry/stats"])
async def test_telemetry_routes_stay_open_without_token(real_auth, path):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(path)
    assert r.status_code == 200
