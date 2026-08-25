"""Generated artifacts: summary, quiz, compliance audit, audio briefing, slides.

Thin handlers — the generation logic lives in routes/generation.py. Every JSON
endpoint returns the envelope from routes/schemas.py, and none of them
substitute invented content when the model is unavailable.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.core.auth import get_current_user
from app.core.observability import new_request_id
from app.core.rate_limit import limiter, studio_limit
from app.core.sse import sse_stream_response
from app.routes.deps import DocHashBody, require_indexed, require_owned
from app.routes.generation import (
    generate_audio_briefing,
    generate_quiz_cards,
    generate_slide_deck,
    generate_suggested_questions,
    run_compliance_audit,
    summarize_stream,
)

router = APIRouter(tags=["studio"])


@router.post("/summary")
@limiter.limit(studio_limit)
async def post_summary(request: Request, body: DocHashBody, user: dict = Depends(get_current_user)):
    """Stream an executive summary of the document."""
    require_indexed(body.doc_hash)
    require_owned(body.doc_hash, user)
    request_id = new_request_id()

    def events():
        return summarize_stream(body.doc_hash, request_id=request_id)

    return sse_stream_response(events, request_id=request_id)


@router.post("/quiz")
@limiter.limit(studio_limit)
async def post_quiz(
    request: Request, body: DocHashBody, response: Response, user: dict = Depends(get_current_user)
):
    require_owned(body.doc_hash, user)
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await generate_quiz_cards(body.doc_hash, request_id=request_id)


@router.post("/suggested-questions")
@limiter.limit(studio_limit)
async def post_suggested_questions(
    request: Request, body: DocHashBody, response: Response, user: dict = Depends(get_current_user)
):
    """3 example questions grounded in this document, for the Query Console's empty state."""
    require_owned(body.doc_hash, user)
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await generate_suggested_questions(body.doc_hash, request_id=request_id)


@router.post("/compliance-audit")
@limiter.limit(studio_limit)
async def post_compliance_audit(
    request: Request, body: DocHashBody, response: Response, user: dict = Depends(get_current_user)
):
    require_owned(body.doc_hash, user)
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await run_compliance_audit(body.doc_hash, request_id=request_id)


@router.post("/audio-briefing")
@limiter.limit(studio_limit)
async def post_audio_briefing(
    request: Request, body: DocHashBody, response: Response, user: dict = Depends(get_current_user)
):
    require_owned(body.doc_hash, user)
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await generate_audio_briefing(body.doc_hash, request_id=request_id)


@router.post("/slide-deck")
@limiter.limit(studio_limit)
async def post_slide_deck(
    request: Request, body: DocHashBody, response: Response, user: dict = Depends(get_current_user)
):
    require_owned(body.doc_hash, user)
    request_id = new_request_id()
    response.headers["X-Request-Id"] = request_id
    return await generate_slide_deck(body.doc_hash, request_id=request_id)
