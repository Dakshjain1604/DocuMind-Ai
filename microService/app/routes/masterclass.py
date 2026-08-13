import json
import logging
import time
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.llm import get_llm
from app.core.sse import sse_event, sse_error
from app.indexing.store import load_artifacts, artifacts_exist
from app.core.observability import record_trace, new_request_id
from app.prompts.generation import (
    CHAPTER_EXTRACTOR_PROMPT,
    LEARNING_DRAFT_PROMPT,
    CHAPTER_QUIZ_PROMPT,
)
# Single source of truth for sampling and quiz-card shaping. This module used
# to carry its own near-identical copies of both, which drifted apart — the
# local quiz validator skipped the Pydantic check the other one performed.
from app.routes.generation import _get_document_sample, format_quiz_cards
from app.routes.schemas import (
    INVALID_LLM_OUTPUT,
    LLM_UNAVAILABLE,
    NOT_INDEXED,
    fail,
    ok,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class MasterclassRequest(BaseModel):
    doc_hash: str = Field(..., description="Indexed document hash")
    chapter_id: int | None = Field(default=1, description="Chapter ID to generate draft or quiz for")
    chapter_title: str | None = Field(default=None, description="Chapter title")


@router.post("/chapters")
async def extract_chapters(req: MasterclassRequest):
    request_id = new_request_id()
    start = time.perf_counter()
    if not artifacts_exist(req.doc_hash):
        return fail(NOT_INDEXED, "doc_hash not indexed", total_chapters=0, chapters=[])

    loaded = load_artifacts(req.doc_hash)
    sample = _get_document_sample(loaded, max_chunks=16)

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[{"role": "user", "content": CHAPTER_EXTRACTOR_PROMPT.format(content=sample.text)}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        # No stand-in chapter list. Inventing "Chapter 1: Core Principles"
        # for a document we failed to read is a fabricated table of contents.
        logger.error("chapter extraction failed: %s", e)
        record_trace(request_id, doc_hash=req.doc_hash, query="[masterclass_chapters]",
                     total_latency_ms=round((time.perf_counter() - start) * 1000, 1), error=str(e))
        return fail(LLM_UNAVAILABLE, str(e), total_chapters=0, chapters=[])

    try:
        data = json.loads(r.content)
    except json.JSONDecodeError as e:
        logger.error("chapter extraction returned non-JSON: %s", e)
        record_trace(request_id, doc_hash=req.doc_hash, query="[masterclass_chapters]",
                     total_latency_ms=round((time.perf_counter() - start) * 1000, 1), error=str(e))
        return fail(INVALID_LLM_OUTPUT, "model did not return valid JSON", total_chapters=0, chapters=[])

    chapters = data.get("chapters", [])
    record_trace(
        request_id,
        doc_hash=req.doc_hash,
        query="[masterclass_chapters]",
        total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
        total_tokens_in=r.tokens_in,
        total_tokens_out=r.tokens_out,
        total_cost_usd=r.cost_usd,
    )
    return ok(total_chapters=len(chapters), chapters=chapters, coverage=sample.coverage)


@router.post("/learning-draft")
async def generate_learning_draft(req: MasterclassRequest):
    if not artifacts_exist(req.doc_hash):
        raise HTTPException(status_code=404, detail="Document not found")

    loaded = load_artifacts(req.doc_hash)
    sample = _get_document_sample(loaded, max_chunks=12)
    title = req.chapter_title or f"Chapter {req.chapter_id or 1}"

    async def event_generator() -> AsyncGenerator[str, None]:
        request_id = new_request_id()
        start = time.perf_counter()
        acc = ""
        try:
            prompt = LEARNING_DRAFT_PROMPT.format(chapter_title=title, content=sample.text)
            stream = get_llm().stream(
                role="answer",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            async for delta, _model in stream:
                acc += delta
                yield sse_event("token", {"text": delta})
            yield sse_event("done", {"doc_hash": req.doc_hash, "coverage": sample.coverage})
            record_trace(
                request_id, doc_hash=req.doc_hash, query=f"[learning_draft_{req.chapter_id}]",
                total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
                answer_text=acc,
            )
        except Exception as e:
            logger.error("learning draft stream error: %s", e)
            record_trace(
                request_id, doc_hash=req.doc_hash, query=f"[learning_draft_{req.chapter_id}]",
                total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
                error=str(e),
            )
            yield sse_error(str(e))

    # Same headers as every other SSE route. Without no-transform /
    # X-Accel-Buffering, a proxy will buffer this stream and it appears frozen.
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chapter-quiz")
async def generate_chapter_quiz(req: MasterclassRequest):
    request_id = new_request_id()
    start = time.perf_counter()
    if not artifacts_exist(req.doc_hash):
        return fail(NOT_INDEXED, "doc_hash not indexed", total_questions=0, cards=[])

    loaded = load_artifacts(req.doc_hash)
    sample = _get_document_sample(loaded, max_chunks=10)
    title = req.chapter_title or f"Chapter {req.chapter_id or 1}"

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[{"role": "user", "content": CHAPTER_QUIZ_PROMPT.format(chapter_title=title, content=sample.text)}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(r.content)
        # Shared validator: the local copy this replaced skipped the Pydantic
        # check and then indexed q["question"] directly, raising KeyError on a
        # malformed item.
        valid_cards = format_quiz_cards(data.get("quiz", []))
        for card in valid_cards:
            card["metadata"] = {"difficulty": "medium", "category": title}

        record_trace(
            request_id,
            doc_hash=req.doc_hash,
            query=f"[chapter_quiz_{req.chapter_id}]",
            total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
            total_tokens_in=r.tokens_in,
            total_tokens_out=r.tokens_out,
            total_cost_usd=r.cost_usd,
        )
        return ok(total_questions=len(valid_cards), cards=valid_cards, coverage=sample.coverage)
    except json.JSONDecodeError as e:
        logger.error("chapter quiz returned non-JSON: %s", e)
        record_trace(
            request_id, doc_hash=req.doc_hash, query=f"[chapter_quiz_{req.chapter_id}]",
            total_latency_ms=round((time.perf_counter() - start) * 1000, 1), error=str(e)
        )
        return fail(INVALID_LLM_OUTPUT, "model did not return valid JSON", total_questions=0, cards=[])
    except Exception as e:
        logger.error("chapter quiz error: %s", e)
        record_trace(
            request_id, doc_hash=req.doc_hash, query=f"[chapter_quiz_{req.chapter_id}]",
            total_latency_ms=round((time.perf_counter() - start) * 1000, 1), error=str(e)
        )
        return fail(LLM_UNAVAILABLE, str(e), total_questions=0, cards=[])
