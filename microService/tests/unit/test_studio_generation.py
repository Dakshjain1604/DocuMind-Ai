"""The studio generators must never invent content.

These endpoints previously returned success with hardcoded stand-in results
when the model was unreachable — a compliance "finding", a slide, a podcast
script, a chapter list. To a caller, that was indistinguishable from a real
analysis of their document. The contract now has three distinct states:

    success + non-empty  -> real results
    success + empty      -> we looked and found nothing
    failure + error code -> we could not produce an answer

The point of these tests is that the third state can never masquerade as the
first, so each one asserts on the *absence* of fabricated content.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request

from app.routes.generation import (
    generate_audio_briefing,
    generate_quiz_cards,
    generate_slide_deck,
    run_compliance_audit,
)
from app.routes.masterclass import MasterclassRequest, extract_chapters
from app.routes.schemas import INVALID_LLM_OUTPUT, LLM_UNAVAILABLE, NOT_INDEXED

DOC_HASH = "ab" * 32
FAKE_LOADED = {"chroma_dir": "/nonexistent", "parents_path": None}


def _fake_request() -> Request:
    """A minimal real Request — slowapi's @limiter.limit() rejects anything
    that isn't an actual starlette.requests.Request instance, which callers
    invoking a route function directly (bypassing the ASGI app) must supply."""
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/chapters",
        "headers": [],
        "query_string": b"",
        "client": ("test", 0),
        "server": ("test", 80),
        "scheme": "http",
    })


class _FakeCompletion:
    def __init__(self, content: str):
        self.content = content
        self.tokens_in = 10
        self.tokens_out = 20
        self.cost_usd = None


def _patch_llm(*, raises: Exception | None = None, content: str = "{}"):
    client = AsyncMock()
    if raises is not None:
        client.complete.side_effect = raises
    else:
        client.complete.return_value = _FakeCompletion(content)
    return client


# ── LLM outage must not produce plausible content ────────────────────────────

@pytest.mark.parametrize(
    "func, empty_key",
    [
        (run_compliance_audit, "audit"),
        (generate_slide_deck, "slides"),
        (generate_quiz_cards, "cards"),
    ],
)
async def test_llm_outage_reports_failure_with_no_content(func, empty_key):
    outage = RuntimeError("connection refused")
    with patch("app.routes.generation.artifacts_exist", return_value=True), \
         patch("app.routes.generation.load_artifacts", return_value=FAKE_LOADED), \
         patch("app.routes.generation.record_trace"), \
         patch("app.routes.generation.get_llm", return_value=_patch_llm(raises=outage)):
        res = await func(DOC_HASH)

    assert res["success"] is False
    assert res["error"]["code"] == LLM_UNAVAILABLE
    assert res["data"][empty_key] == [], "an outage must not yield stand-in content"


async def test_audio_briefing_outage_returns_no_script():
    with patch("app.routes.generation.artifacts_exist", return_value=True), \
         patch("app.routes.generation.load_artifacts", return_value=FAKE_LOADED), \
         patch("app.routes.generation.get_llm", return_value=_patch_llm(raises=RuntimeError("down"))):
        res = await generate_audio_briefing(DOC_HASH)

    assert res["success"] is False
    assert res["data"]["script"] == ""
    # The old fallback shipped a canned two-host script.
    assert "Alex" not in json.dumps(res)
    assert "Morgan" not in json.dumps(res)


async def test_chapter_extraction_outage_returns_no_chapters():
    with patch("app.routes.masterclass.artifacts_exist", return_value=True), \
         patch("app.routes.masterclass.load_artifacts", return_value=FAKE_LOADED), \
         patch("app.routes.generation._get_document_sample") as sample, \
         patch("app.routes.masterclass.get_llm", return_value=_patch_llm(raises=RuntimeError("down"))):
        sample.return_value.text = "doc text"
        sample.return_value.coverage = {}
        res = await extract_chapters(_fake_request(), MasterclassRequest(doc_hash=DOC_HASH))

    assert res["success"] is False
    assert res["data"]["chapters"] == []
    assert "Core Principles" not in json.dumps(res), "must not invent a table of contents"


# ── "Nothing found" is a success, and distinct from an outage ────────────────

async def test_empty_audit_is_success_not_failure():
    with patch("app.routes.generation.artifacts_exist", return_value=True), \
         patch("app.routes.generation.load_artifacts", return_value=FAKE_LOADED), \
         patch("app.routes.generation.get_llm", return_value=_patch_llm(content='{"audit": []}')):
        res = await run_compliance_audit(DOC_HASH)

    assert res["success"] is True
    assert res["data"]["audit"] == []
    assert res["data"]["total_findings"] == 0


async def test_audit_passes_through_real_findings_with_coverage():
    finding = {"id": 1, "severity": "high", "category": "Access", "finding": "x", "mitigation": "y"}
    with patch("app.routes.generation.artifacts_exist", return_value=True), \
         patch("app.routes.generation.load_artifacts", return_value=FAKE_LOADED), \
         patch("app.routes.generation.get_llm",
               return_value=_patch_llm(content=json.dumps({"audit": [finding]}))):
        res = await run_compliance_audit(DOC_HASH)

    assert res["success"] is True
    assert res["data"]["audit"] == [finding]
    # Sampling is disclosed rather than left implicit.
    assert "coverage" in res["data"]
    assert "sampled_chunks" in res["data"]["coverage"]


# ── Malformed model output is its own error code ─────────────────────────────

async def test_non_json_response_is_invalid_llm_output():
    with patch("app.routes.generation.artifacts_exist", return_value=True), \
         patch("app.routes.generation.load_artifacts", return_value=FAKE_LOADED), \
         patch("app.routes.generation.get_llm", return_value=_patch_llm(content="I'm sorry, I can't.")):
        res = await run_compliance_audit(DOC_HASH)

    assert res["success"] is False
    assert res["error"]["code"] == INVALID_LLM_OUTPUT
    assert res["data"]["audit"] == []


# ── Un-indexed document ──────────────────────────────────────────────────────

async def test_not_indexed_is_reported_as_such():
    with patch("app.routes.generation.artifacts_exist", return_value=False):
        res = await run_compliance_audit(DOC_HASH)
    assert res["success"] is False
    assert res["error"]["code"] == NOT_INDEXED
    assert res["data"]["audit"] == []
