"""Summary + quiz + compliance audit + audio briefing + slide deck generation.

Every generator here works from a *sample* of the document, not the whole of
it. That sampling is reported back to the caller as a `coverage` object rather
than left implicit, so the UI can say what the output was actually derived
from.

None of these functions invent content. If the model is unreachable or returns
something unusable, they return a `fail(...)` envelope — an empty result and an
error are different answers, and both are honest ones.
"""
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from langchain_chroma import Chroma

from app.core.embeddings import get_embeddings
from app.core.llm import get_llm
from app.core.observability import new_request_id, record_trace
from app.prompts.generation import (
    DOCUMENT_SUMMARY_PROMPT,
    QUIZ_PROMPT,
    COMPLIANCE_AUDIT_PROMPT,
    AUDIO_BRIEFING_PROMPT,
    SLIDE_DECK_PROMPT,
    SUGGESTED_QUESTIONS_PROMPT,
)
from app.indexing.store import load_artifacts, artifacts_exist
from app.routes.schemas import (
    INVALID_LLM_OUTPUT,
    LLM_UNAVAILABLE,
    NOT_INDEXED,
    fail,
    ok,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentSample:
    """Text handed to a generator, plus what it was drawn from."""

    text: str
    sampled_chunks: int
    total_chunks: int
    unit: str  # "parent_chunks" | "child_chunks"

    @property
    def coverage(self) -> dict[str, Any]:
        return {
            "sampled_chunks": self.sampled_chunks,
            "total_chunks": self.total_chunks,
            "unit": self.unit,
            "strategy": "even-stride",
            "is_partial": self.sampled_chunks < self.total_chunks,
        }


def _even_stride(items: list[tuple[int, str]], max_chunks: int) -> list[tuple[int, str]]:
    """Pick max_chunks items spread evenly across the document, preserving order."""
    total = len(items)
    if total <= max_chunks:
        return items
    step = total / max_chunks
    return [items[min(int(i * step), total - 1)] for i in range(max_chunks)]


def _get_document_sample(loaded: dict, max_chunks: int = 8) -> DocumentSample:
    """Evenly-sampled slice of the document, preferring parent chunks."""
    parents_path = loaded.get("parents_path")
    if parents_path and Path(parents_path).exists():
        try:
            parents_data = json.loads(Path(parents_path).read_text())
            sorted_parents = sorted(((int(k), v) for k, v in parents_data.items()), key=lambda x: x[0])
            sampled = _even_stride(sorted_parents, max_chunks)
            return DocumentSample(
                text="\n\n".join(text for _, text in sampled),
                sampled_chunks=len(sampled),
                total_chunks=len(sorted_parents),
                unit="parent_chunks",
            )
        except Exception as e:
            logger.warning("parents.json unusable, falling back to Chroma: %s", e)

    # Fallback to child chunks from Chroma, ordered by chunk_id.
    try:
        chroma = Chroma(persist_directory=loaded["chroma_dir"], embedding_function=get_embeddings())
        res = chroma.get(include=["documents", "metadatas"])
        docs_with_meta: list[tuple[int, str]] = []
        for text, meta in zip(res.get("documents", []), res.get("metadatas", [])):
            cid = meta.get("chunk_id") if meta else None
            if cid is not None:
                docs_with_meta.append((int(cid), text))
        docs_with_meta.sort(key=lambda x: x[0])
        sampled = _even_stride(docs_with_meta, max_chunks)
        return DocumentSample(
            text="\n\n".join(text for _, text in sampled),
            sampled_chunks=len(sampled),
            total_chunks=len(docs_with_meta),
            unit="child_chunks",
        )
    except Exception as e:
        logger.error("Failed to load chunks for sampling: %s", e)
        return DocumentSample(text="", sampled_chunks=0, total_chunks=0, unit="child_chunks")


async def summarize_stream(doc_hash: str, *, request_id: str | None = None):
    if not artifacts_exist(doc_hash):
        raise FileNotFoundError(f"doc_hash {doc_hash} not indexed")
    request_id = request_id or new_request_id()
    start = time.perf_counter()
    loaded = load_artifacts(doc_hash)

    sample = _get_document_sample(loaded, max_chunks=8)
    messages = [{"role": "user", "content": DOCUMENT_SUMMARY_PROMPT.format(content=sample.text)}]

    acc = ""
    model_used = ""
    try:
        async for delta, model in get_llm().stream(role="answer", messages=messages, temperature=0.2):
            acc += delta
            model_used = model
            yield {"event": "token", "data": {"text": delta}}

        record_trace(
            request_id,
            doc_hash=doc_hash,
            query="[summary]",
            total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
            answer_text=acc,
        )
        yield {"event": "done", "data": {"text": acc, "model": model_used, "coverage": sample.coverage}}
    except Exception as e:
        record_trace(
            request_id,
            doc_hash=doc_hash,
            query="[summary]",
            total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
            error=str(e),
        )
        yield {"event": "error", "data": {"message": str(e)}}


class QuizQuestion(BaseModel):
    id: int
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer: str
    explanation: str = ""


# Quiz depth scales with how much derived text there is to test against: a
# 2-page memo and a booklength manual warrant different quiz sizes. Tuning
# knobs are named here rather than inlined so the tiers read as policy.
_QUIZ_SMALL_TEXT_LIMIT = 3000
_QUIZ_MEDIUM_TEXT_LIMIT = 15000
# (n_questions, max_chunks sampled from the document) per text-length tier.
_QUIZ_SMALL = (5, 5)
_QUIZ_MEDIUM = (10, 10)
_QUIZ_LARGE = (18, 16)


async def generate_quiz_cards(doc_hash: str, *, request_id: str | None = None) -> dict[str, Any]:
    if not artifacts_exist(doc_hash):
        return fail(NOT_INDEXED, "doc_hash not indexed", total_questions=0, cards=[])
    request_id = request_id or new_request_id()
    start = time.perf_counter()
    loaded = load_artifacts(doc_hash)

    probe = _get_document_sample(loaded, max_chunks=8)
    content_len = len(probe.text)

    if content_len < _QUIZ_SMALL_TEXT_LIMIT:
        n_questions, max_chunks = _QUIZ_SMALL
    elif content_len < _QUIZ_MEDIUM_TEXT_LIMIT:
        n_questions, max_chunks = _QUIZ_MEDIUM
    else:
        n_questions, max_chunks = _QUIZ_LARGE

    sample = _get_document_sample(loaded, max_chunks=max_chunks)

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[
                {"role": "user", "content": QUIZ_PROMPT.format(n_questions=n_questions, content=sample.text)}
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.error("quiz generation failed: %s", e)
        record_trace(
            request_id, doc_hash=doc_hash, query="[quiz]",
            total_latency_ms=round((time.perf_counter() - start) * 1000, 1), error=str(e),
        )
        return fail(LLM_UNAVAILABLE, str(e), total_questions=0, cards=[])

    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    try:
        data = json.loads(r.content)
    except json.JSONDecodeError as e:
        logger.error("quiz returned non-JSON: %s", e)
        record_trace(request_id, doc_hash=doc_hash, query="[quiz]",
                     total_latency_ms=latency_ms, error=str(e))
        return fail(INVALID_LLM_OUTPUT, "model did not return valid JSON", total_questions=0, cards=[])

    cards = format_quiz_cards(data.get("quiz", []))
    record_trace(
        request_id,
        doc_hash=doc_hash,
        query="[quiz]",
        total_latency_ms=latency_ms,
        total_tokens_in=r.tokens_in,
        total_tokens_out=r.tokens_out,
        total_cost_usd=r.cost_usd,
    )
    # An empty list is a real answer ("nothing usable came back"), reported as
    # success with zero cards rather than as invented questions.
    return ok(total_questions=len(cards), cards=cards, coverage=sample.coverage)


def format_quiz_cards(items: list[dict]) -> list[dict]:
    """Validate and reshape raw LLM quiz items for the frontend.

    Items that fail validation are dropped, not repaired — a malformed question
    is worse than a missing one.
    """
    cards: list[dict] = []
    total_items = len(items)
    for i, q in enumerate(items):
        try:
            QuizQuestion(**q)
        except Exception:
            continue
        if q["correct_answer"] not in q["options"]:
            continue
        if any(len(str(opt).strip()) <= 2 for opt in q.get("options", [])):
            continue
        cards.append({
            "id": len(cards) + 1,
            "type": "multiple-choice",
            "title": f"Question {len(cards) + 1}",
            "question": q["question"],
            "options": [
                {"id": f"option_{j}", "text": opt, "correct": opt == q["correct_answer"]}
                for j, opt in enumerate(q["options"])
            ],
            "correctAnswer": q["correct_answer"],
            "explanation": q.get("explanation", ""),
            "metadata": {
                "difficulty": (
                    "easy" if i < max(1, total_items // 4)
                    else "medium" if i < max(2, (total_items * 3) // 4)
                    else "hard"
                ),
                "category": "auto-generated",
            },
        })
    return cards


async def generate_suggested_questions(doc_hash: str, *, request_id: str | None = None) -> dict[str, Any]:
    """3 example questions grounded in this specific document, for the Query
    Console's empty state — replaces a static, generic set of prompts that
    was the same for every document regardless of what it actually covered."""
    if not artifacts_exist(doc_hash):
        return fail(NOT_INDEXED, "doc_hash not indexed", questions=[])
    request_id = request_id or new_request_id()
    start = time.perf_counter()
    loaded = load_artifacts(doc_hash)

    # A handful of chunks is plenty to write plausible example questions from
    # - this is a UI nicety, not an artifact that needs full-document coverage.
    sample = _get_document_sample(loaded, max_chunks=6)

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[{"role": "user", "content": SUGGESTED_QUESTIONS_PROMPT.format(content=sample.text)}],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.error("suggested-questions generation failed: %s", e)
        record_trace(
            request_id, doc_hash=doc_hash, query="[suggested-questions]",
            total_latency_ms=round((time.perf_counter() - start) * 1000, 1), error=str(e),
        )
        return fail(LLM_UNAVAILABLE, str(e), questions=[])

    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    try:
        data = json.loads(r.content)
    except json.JSONDecodeError as e:
        logger.error("suggested-questions returned non-JSON: %s", e)
        record_trace(request_id, doc_hash=doc_hash, query="[suggested-questions]",
                     total_latency_ms=latency_ms, error=str(e))
        return fail(INVALID_LLM_OUTPUT, "model did not return valid JSON", questions=[])

    questions = [str(q).strip() for q in data.get("questions", []) if str(q).strip()][:3]
    record_trace(
        request_id,
        doc_hash=doc_hash,
        query="[suggested-questions]",
        total_latency_ms=latency_ms,
        total_tokens_in=r.tokens_in,
        total_tokens_out=r.tokens_out,
        total_cost_usd=r.cost_usd,
    )
    return ok(questions=questions, coverage=sample.coverage)


async def run_compliance_audit(doc_hash: str, *, request_id: str | None = None) -> dict[str, Any]:
    if not artifacts_exist(doc_hash):
        return fail(NOT_INDEXED, "doc_hash not indexed", total_findings=0, audit=[])
    request_id = request_id or new_request_id()
    start = time.perf_counter()
    loaded = load_artifacts(doc_hash)
    sample = _get_document_sample(loaded, max_chunks=10)

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[{"role": "user", "content": COMPLIANCE_AUDIT_PROMPT.format(content=sample.text)}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        # Emphatically NOT a place for a default finding. Returning invented
        # audit results on an LLM outage is indistinguishable, to the caller,
        # from a real audit of the document.
        logger.error("compliance audit failed: %s", e)
        record_trace(request_id, doc_hash=doc_hash, query="[compliance_audit]",
                     total_latency_ms=round((time.perf_counter() - start) * 1000, 1), error=str(e))
        return fail(LLM_UNAVAILABLE, str(e), total_findings=0, audit=[])

    try:
        data = json.loads(r.content)
    except json.JSONDecodeError as e:
        logger.error("compliance audit returned non-JSON: %s", e)
        record_trace(request_id, doc_hash=doc_hash, query="[compliance_audit]",
                     total_latency_ms=round((time.perf_counter() - start) * 1000, 1), error=str(e))
        return fail(INVALID_LLM_OUTPUT, "model did not return valid JSON", total_findings=0, audit=[])

    audit_items = data.get("audit", [])
    record_trace(
        request_id, doc_hash=doc_hash, query="[compliance_audit]",
        total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
        total_tokens_in=r.tokens_in, total_tokens_out=r.tokens_out, total_cost_usd=r.cost_usd
    )
    return ok(total_findings=len(audit_items), audit=audit_items, coverage=sample.coverage)


async def generate_audio_briefing(doc_hash: str, *, request_id: str | None = None) -> dict[str, Any]:
    if not artifacts_exist(doc_hash):
        return fail(NOT_INDEXED, "doc_hash not indexed", script="")
    request_id = request_id or new_request_id()
    start = time.perf_counter()
    loaded = load_artifacts(doc_hash)
    sample = _get_document_sample(loaded, max_chunks=8)

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[
                {
                    "role": "user",
                    "content": AUDIO_BRIEFING_PROMPT.format(
                        title="Document Intelligence Briefing", content=sample.text
                    ),
                }
            ],
            temperature=0.3,
        )
    except Exception as e:
        logger.error("audio briefing failed: %s", e)
        record_trace(request_id, doc_hash=doc_hash, query="[audio_briefing]",
                     total_latency_ms=round((time.perf_counter() - start) * 1000, 1), error=str(e))
        return fail(LLM_UNAVAILABLE, str(e), script="")

    record_trace(
        request_id, doc_hash=doc_hash, query="[audio_briefing]",
        total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
        total_tokens_in=r.tokens_in, total_tokens_out=r.tokens_out, total_cost_usd=r.cost_usd
    )
    return ok(script=r.content, coverage=sample.coverage)


async def generate_slide_deck(doc_hash: str, *, request_id: str | None = None) -> dict[str, Any]:
    if not artifacts_exist(doc_hash):
        return fail(NOT_INDEXED, "doc_hash not indexed", total_slides=0, slides=[])
    request_id = request_id or new_request_id()
    start = time.perf_counter()
    loaded = load_artifacts(doc_hash)
    sample = _get_document_sample(loaded, max_chunks=10)

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[{"role": "user", "content": SLIDE_DECK_PROMPT.format(content=sample.text)}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.error("slide deck failed: %s", e)
        record_trace(request_id, doc_hash=doc_hash, query="[slide_deck]",
                     total_latency_ms=round((time.perf_counter() - start) * 1000, 1), error=str(e))
        return fail(LLM_UNAVAILABLE, str(e), total_slides=0, slides=[])

    try:
        data = json.loads(r.content)
    except json.JSONDecodeError as e:
        logger.error("slide deck returned non-JSON: %s", e)
        record_trace(request_id, doc_hash=doc_hash, query="[slide_deck]",
                     total_latency_ms=round((time.perf_counter() - start) * 1000, 1), error=str(e))
        return fail(INVALID_LLM_OUTPUT, "model did not return valid JSON", total_slides=0, slides=[])

    slides = data.get("slides", [])
    record_trace(
        request_id, doc_hash=doc_hash, query="[slide_deck]",
        total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
        total_tokens_in=r.tokens_in, total_tokens_out=r.tokens_out, total_cost_usd=r.cost_usd
    )
    return ok(total_slides=len(slides), slides=slides, coverage=sample.coverage)
