"""Quiz generation — reuses indexed artifacts."""
import json
import logging
from typing import Any
from pydantic import BaseModel, Field

from app.core.llm import get_llm
from app.indexing.store import load_artifacts, artifacts_exist
from langchain_chroma import Chroma
from app.core.embeddings import get_embeddings

logger = logging.getLogger(__name__)


class QuizQuestion(BaseModel):
    id: int
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer: str
    explanation: str = ""


QUIZ_PROMPT = """Generate exactly 12 multiple-choice questions from the document content.

Rules:
- Each question has exactly 4 options.
- correct_answer must match one of the options character-for-character.
- Questions 1-3 easy; 4-9 medium; 10-12 hard.
- Cover different aspects of the content.

Return JSON of the form:
{{"quiz": [{{"id":1,"question":"...","options":["A","B","C","D"],"correct_answer":"B","explanation":"..."}}]}}

Document content:
{content}
"""


async def generate_quiz_cards(doc_hash: str) -> dict[str, Any]:
    if not artifacts_exist(doc_hash):
        return {"success": False, "error": "doc_hash not indexed", "data": {"total_questions": 0, "cards": []}}
    loaded = load_artifacts(doc_hash)
    chroma = Chroma(persist_directory=loaded["chroma_dir"], embedding_function=get_embeddings())
    res = chroma.get(include=["documents"])
    content = "\n\n".join(res.get("documents", [])[:8])

    try:
        r = await get_llm().complete(
            role="answer",
            messages=[{"role": "user", "content": QUIZ_PROMPT.format(content=content)}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(r.content)
        cards = _format_for_frontend(data.get("quiz", []))
        if not cards:
            return {"success": False, "error": "No valid questions", "data": {"total_questions": 0, "cards": []}}
        return {"success": True, "data": {"total_questions": len(cards), "cards": cards}}
    except Exception as e:
        logger.error("quiz failed: %s", e)
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
