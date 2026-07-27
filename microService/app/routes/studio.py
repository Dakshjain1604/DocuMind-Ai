"""Generated artifacts: summary, quiz, compliance audit, audio briefing, slides.

Thin handlers — the generation logic lives in routes/generation.py. Every JSON
endpoint returns the envelope from routes/schemas.py, and none of them
substitute invented content when the model is unavailable.
"""
from __future__ import annotations

from fastapi import APIRouter, Response

from app.core.observability import new_request_id
from app.core.sse import sse_stream_response
from app.routes.deps import DocHashBody, require_indexed
from app.routes.generation import (
    generate_audio_briefing,
    generate_quiz_cards,
    generate_slide_deck,
    run_compliance_audit,
    summarize_stream,
)

router = APIRouter(tags=["studio"])


@router.post("/summary")
async def post_summary(body: DocHashBody):
    """Stream an executive summary of the document."""
    require_indexed(body.doc_hash)
    request_id = new_request_id()

    def events():
        return summarize_stream(body.doc_hash, request_id=request_id)

    return sse_stream_response(events, request_id=request_id)


@router.post("/quiz")
async def post_quiz(body: DocHashBody, response: Response):
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await generate_quiz_cards(body.doc_hash, request_id=request_id)


@router.post("/compliance-audit")
async def post_compliance_audit(body: DocHashBody, response: Response):
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await run_compliance_audit(body.doc_hash, request_id=request_id)


@router.post("/audio-briefing")
async def post_audio_briefing(body: DocHashBody, response: Response):
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await generate_audio_briefing(body.doc_hash, request_id=request_id)


@router.post("/slide-deck")
async def post_slide_deck(body: DocHashBody, response: Response):
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await generate_slide_deck(body.doc_hash, request_id=request_id)
