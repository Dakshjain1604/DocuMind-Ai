"""Summary + quiz generation — both reuse indexed artifacts for a single
LLM call over the doc's content, grouped together since they're the same
shape (load artifacts -> one LLM call -> return)."""
import json
import logging
import time
from typing import Any
from pydantic import BaseModel, Field

from langchain_chroma import Chroma

from app.core.embeddings import get_embeddings
from app.core.llm import get_llm
from app.core.observability import new_request_id, record_trace
from app.prompts import DOCUMENT_SUMMARY_PROMPT, QUIZ_PROMPT
from app.indexing.store import load_artifacts, artifacts_exist

logger = logging.getLogger(__name__)


from pathlib import Path

def _get_document_sample(loaded: dict, max_chunks: int = 8) -> str:
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
                sampled = [sorted_parents[int(i * step)] for i in range(max_chunks)]
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
            sampled = [docs_with_meta[int(i * step)] for i in range(max_chunks)]
        return "\n\n".join([text for _, text in sampled])
    except Exception:
        # Final fallback to raw document chunks from chroma get
        try:
            chroma = Chroma(persist_directory=loaded["chroma_dir"], embedding_function=get_embeddings())
            res = chroma.get(include=["documents"])
            return "\n\n".join(res.get("documents", [])[:max_chunks])
        except Exception as e:
            logger.error("Failed to load chunks for sampling: %s", e)
            return ""


async def summarize(doc_hash: str, *, request_id: str | None = None) -> str:
    if not artifacts_exist(doc_hash):
        raise FileNotFoundError(f"doc_hash {doc_hash} not indexed")
    request_id = request_id or new_request_id()
    start = time.perf_counter()
    loaded = load_artifacts(doc_hash)

    content = _get_document_sample(loaded, max_chunks=8)

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[{"role": "user", "content": DOCUMENT_SUMMARY_PROMPT.format(content=content)}],
            temperature=0.2,
        )
    except Exception as e:
        record_trace(
            request_id,
            doc_hash=doc_hash,
            query="[summary]",
            total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
            error=str(e),
        )
        raise
    record_trace(
        request_id,
        doc_hash=doc_hash,
        query="[summary]",
        total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
        total_tokens_in=r.tokens_in,
        total_tokens_out=r.tokens_out,
        total_cost_usd=r.cost_usd,
        answer_text=r.content,
    )
    return r.content


class QuizQuestion(BaseModel):
    id: int
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer: str
    explanation: str = ""


async def generate_quiz_cards(doc_hash: str, *, request_id: str | None = None) -> dict[str, Any]:
    if not artifacts_exist(doc_hash):
        return {"success": False, "error": "doc_hash not indexed", "data": {"total_questions": 0, "cards": []}}
    request_id = request_id or new_request_id()
    start = time.perf_counter()
    loaded = load_artifacts(doc_hash)
    
    # Sample 12 chunks to allow quiz questions to be created from across the whole document
    content = _get_document_sample(loaded, max_chunks=12)

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[{"role": "user", "content": QUIZ_PROMPT.format(content=content)}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(r.content)
        cards = _format_for_frontend(data.get("quiz", []))
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        if not cards:
            record_trace(
                request_id, doc_hash=doc_hash, query="[quiz]",
                total_latency_ms=latency_ms, error="No valid questions",
            )
            return {"success": False, "error": "No valid questions", "data": {"total_questions": 0, "cards": []}}
        record_trace(
            request_id,
            doc_hash=doc_hash,
            query="[quiz]",
            total_latency_ms=latency_ms,
            total_tokens_in=r.tokens_in,
            total_tokens_out=r.tokens_out,
            total_cost_usd=r.cost_usd,
        )
        return {"success": True, "data": {"total_questions": len(cards), "cards": cards}}
    except Exception as e:
        logger.error("quiz failed: %s", e)
        record_trace(
            request_id,
            doc_hash=doc_hash,
            query="[quiz]",
            total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
            error=str(e),
        )
        return {"success": False, "error": str(e), "data": {"total_questions": 0, "cards": []}}


def _format_for_frontend(items: list[dict]) -> list[dict]:
    cards = []
    for i, q in enumerate(items):
        try:
            QuizQuestion(**q)
        except Exception:
            continue
        if q["correct_answer"] not in q["options"]:
            continue
        cards.append({
            "id": q.get("id", i + 1),
            "type": "multiple-choice",
            "title": f"Question {q.get('id', i + 1)}",
            "question": q["question"],
            "options": [
                {"id": f"option_{j}", "text": opt, "correct": opt == q["correct_answer"]}
                for j, opt in enumerate(q["options"])
            ],
            "correctAnswer": q["correct_answer"],
            "explanation": q.get("explanation", ""),
            "metadata": {
                "difficulty": "easy" if i < 3 else "medium" if i < 9 else "hard",
                "category": "auto-generated",
            },
        })
    return cards
