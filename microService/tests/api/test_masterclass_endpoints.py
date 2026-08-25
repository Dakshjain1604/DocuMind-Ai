"""HTTP-level coverage for /chapters, /learning-draft, /chapter-quiz — none of
this had route-level tests before (only unit-level via test_studio_generation.py,
and only for /chapters' outage path). Auth is bypassed by the autouse
tests/conftest.py::bypass_auth fixture, like every other route test in this
package.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

DOC_HASH = "cd" * 32
FAKE_LOADED = {"chroma_dir": "/nonexistent", "parents_path": None}


class _FakeCompletion:
    def __init__(self, content: str):
        self.content = content
        self.tokens_in = 10
        self.tokens_out = 20
        self.cost_usd = None


def _llm_returning(content: str):
    client = AsyncMock()
    client.complete.return_value = _FakeCompletion(content)
    return client


@pytest.mark.asyncio
async def test_chapters_not_indexed_returns_fail_envelope_not_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/chapters", json={"doc_hash": "0" * 64})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "not_indexed"


@pytest.mark.asyncio
async def test_chapters_success():
    chapters_json = json.dumps({"chapters": [{"id": 1, "title": "Intro"}]})
    with patch("app.routes.masterclass.artifacts_exist", return_value=True), \
         patch("app.routes.masterclass.load_artifacts", return_value=FAKE_LOADED), \
         patch("app.routes.generation._get_document_sample") as sample, \
         patch("app.routes.masterclass.get_llm", return_value=_llm_returning(chapters_json)):
        sample.return_value.text = "doc text"
        sample.return_value.coverage = {}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/chapters", json={"doc_hash": DOC_HASH})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["total_chapters"] == 1


@pytest.mark.asyncio
async def test_learning_draft_404_when_not_indexed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/learning-draft", json={"doc_hash": "0" * 64})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_learning_draft_streams_tokens():
    async def fake_stream(*, role, messages, temperature):
        for tok in ["Hello", " world"]:
            yield tok, "test-model"

    llm = AsyncMock()
    llm.stream = fake_stream
    with patch("app.routes.masterclass.artifacts_exist", return_value=True), \
         patch("app.routes.masterclass.load_artifacts", return_value=FAKE_LOADED), \
         patch("app.routes.generation._get_document_sample") as sample, \
         patch("app.routes.masterclass.get_llm", return_value=llm):
        sample.return_value.text = "doc text"
        sample.return_value.coverage = {}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/learning-draft", json={"doc_hash": DOC_HASH, "chapter_id": 1, "chapter_title": "Intro"}
            )
    assert r.status_code == 200
    body = r.text
    assert "event: token" in body
    assert "event: done" in body


@pytest.mark.asyncio
async def test_chapter_quiz_not_indexed_returns_fail_envelope():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/chapter-quiz", json={"doc_hash": "0" * 64})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "not_indexed"


@pytest.mark.asyncio
async def test_chapter_quiz_success():
    quiz_json = json.dumps({
        "quiz": [{
            "id": 1,
            "question": "What is X?",
            "options": ["A option", "B option", "C option", "D option"],
            "correct_answer": "A option",
            "explanation": "because",
        }]
    })
    with patch("app.routes.masterclass.artifacts_exist", return_value=True), \
         patch("app.routes.masterclass.load_artifacts", return_value=FAKE_LOADED), \
         patch("app.routes.generation._get_document_sample") as sample, \
         patch("app.routes.masterclass.get_llm", return_value=_llm_returning(quiz_json)):
        sample.return_value.text = "doc text"
        sample.return_value.coverage = {}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/chapter-quiz", json={"doc_hash": DOC_HASH})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["total_questions"] == 1
