import json
import logging
import time
from pathlib import Path
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from langchain_chroma import Chroma

from app.core.embeddings import get_embeddings
from app.core.llm import get_llm
from app.indexing.store import load_artifacts, artifacts_exist
from app.core.observability import record_trace, new_request_id
from app.prompts.generation import (
    CHAPTER_EXTRACTOR_PROMPT,
    LEARNING_DRAFT_PROMPT,
    CHAPTER_QUIZ_PROMPT,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class MasterclassRequest(BaseModel):
    doc_hash: str = Field(..., description="Indexed document hash")
    chapter_id: int | None = Field(default=1, description="Chapter ID to generate draft or quiz for")
    chapter_title: str | None = Field(default=None, description="Chapter title")


def _get_document_sample(loaded: dict, max_chunks: int = 12) -> str:
    """Helper to extract an ordered, evenly-sampled slice of text from parent
    or child chunks to ensure even coverage across the entire document."""
    parents_path = loaded.get("parents_path")
    if parents_path and Path(parents_path).exists():
        try:
            parents_data = json.loads(Path(parents_path).read_text())
            sorted_parents = sorted(
                [(int(k), v) for k, v in parents_data.items()],
                key=lambda x: x[0]
            )
            total = len(sorted_parents)
            if total <= max_chunks:
                sampled = sorted_parents
            else:
                step = total / max_chunks
                sampled = [sorted_parents[min(int(i * step), total - 1)] for i in range(max_chunks)]
            return "\n\n".join([text for _, text in sampled])
        except Exception:
            pass

    # Fallback to child chunks from Chroma sorted by chunk_id
    try:
        chroma = Chroma(persist_directory=loaded["chroma_dir"], embedding_function=get_embeddings())
        res = chroma.get(include=["documents", "metadatas"])
        docs_with_meta = []
        for text, meta in zip(res.get("documents", []), res.get("metadatas", [])):
            cid = meta.get("chunk_id") if meta else None
            if cid is not None:
                docs_with_meta.append((int(cid), text))
        docs_with_meta.sort(key=lambda x: x[0])
        total = len(docs_with_meta)
        if total <= max_chunks:
            sampled = docs_with_meta
        else:
            step = total / max_chunks
            sampled = [docs_with_meta[min(int(i * step), total - 1)] for i in range(max_chunks)]
        return "\n\n".join([text for _, text in sampled])
    except Exception:
        try:
            chroma = Chroma(persist_directory=loaded["chroma_dir"], embedding_function=get_embeddings())
            res = chroma.get(include=["documents"])
            return "\n\n".join(res.get("documents", [])[:max_chunks])
        except Exception as e:
            logger.error("Failed to load chunks for sampling: %s", e)
            return ""


@router.post("/chapters")
async def extract_chapters(req: MasterclassRequest):
    request_id = new_request_id()
    start = time.perf_counter()
    if not artifacts_exist(req.doc_hash):
        raise HTTPException(status_code=404, detail="Document not found")

    loaded = load_artifacts(req.doc_hash)
    sample_content = _get_document_sample(loaded, max_chunks=16)

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[{"role": "user", "content": CHAPTER_EXTRACTOR_PROMPT.format(content=sample_content)}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        data = json.loads(r.content)
        chapters = data.get("chapters", [])
        if not chapters:
            chapters = [
                {"id": 1, "title": "Chapter 1: Core Principles & System Fundamentals", "summary": "Initial overview of core concepts."},
                {"id": 2, "title": "Chapter 2: Architecture & Data Processing Flow", "summary": "Deep dive into system mechanics."},
                {"id": 3, "title": "Chapter 3: Advanced Optimization & Tradeoffs", "summary": "Production scaling and tradeoffs."},
            ]
        record_trace(
            request_id,
            doc_hash=req.doc_hash,
            query="[masterclass_chapters]",
            total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
            total_tokens_in=r.tokens_in,
            total_tokens_out=r.tokens_out,
            total_cost_usd=r.cost_usd,
        )
        return {"success": True, "data": {"total_chapters": len(chapters), "chapters": chapters}}
    except Exception as e:
        logger.error("chapter extraction failed: %s", e)
        default_chapters = [
            {"id": 1, "title": "Chapter 1: System Principles & Security", "summary": "Core architectural concepts."},
            {"id": 2, "title": "Chapter 2: Data Flow & Processing Mechanics", "summary": "Pipeline execution details."},
            {"id": 3, "title": "Chapter 3: Scale & Industry Tradeoffs", "summary": "Production engineering patterns."},
        ]
        return {"success": True, "data": {"total_chapters": 3, "chapters": default_chapters}}


@router.post("/learning-draft")
async def generate_learning_draft(req: MasterclassRequest):
    if not artifacts_exist(req.doc_hash):
        raise HTTPException(status_code=404, detail="Document not found")

    loaded = load_artifacts(req.doc_hash)
    sample_content = _get_document_sample(loaded, max_chunks=12)
    title = req.chapter_title or f"Chapter {req.chapter_id or 1}"

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            prompt = LEARNING_DRAFT_PROMPT.format(chapter_title=title, content=sample_content)
            stream = get_llm().stream(
                role="answer",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            async for delta, _model in stream:
                yield f"event: token\ndata: {json.dumps({'text': delta})}\n\n"
            yield f"event: done\ndata: {json.dumps({'doc_hash': req.doc_hash})}\n\n"
        except Exception as e:
            logger.error("learning draft stream error: %s", e)
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/chapter-quiz")
async def generate_chapter_quiz(req: MasterclassRequest):
    request_id = new_request_id()
    start = time.perf_counter()
    if not artifacts_exist(req.doc_hash):
        raise HTTPException(status_code=404, detail="Document not found")

    loaded = load_artifacts(req.doc_hash)
    sample_content = _get_document_sample(loaded, max_chunks=10)
    title = req.chapter_title or f"Chapter {req.chapter_id or 1}"

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[{"role": "user", "content": CHAPTER_QUIZ_PROMPT.format(chapter_title=title, content=sample_content)}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(r.content)
        raw_items = data.get("quiz", [])
        valid_cards = []
        for i, q in enumerate(raw_items):
            if q.get("correct_answer") in q.get("options", []) and not any(len(str(opt).strip()) <= 2 for opt in q.get("options", [])):
                valid_cards.append({
                    "id": len(valid_cards) + 1,
                    "type": "multiple-choice",
                    "title": f"Question {len(valid_cards) + 1}",
                    "question": q["question"],
                    "options": [
                        {"id": f"option_{j}", "text": opt, "correct": opt == q["correct_answer"]}
                        for j, opt in enumerate(q["options"])
                    ],
                    "correctAnswer": q["correct_answer"],
                    "explanation": q.get("explanation", ""),
                    "metadata": {"difficulty": "medium", "category": title},
                })

        record_trace(
            request_id,
            doc_hash=req.doc_hash,
            query=f"[chapter_quiz_{req.chapter_id}]",
            total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
            total_tokens_in=r.tokens_in,
            total_tokens_out=r.tokens_out,
            total_cost_usd=r.cost_usd,
        )
        return {"success": True, "data": {"total_questions": len(valid_cards), "cards": valid_cards}}
    except Exception as e:
        logger.error("chapter quiz error: %s", e)
        return {"success": False, "error": str(e), "data": {"total_questions": 0, "cards": []}}
