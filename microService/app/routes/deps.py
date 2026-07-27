"""Shared request models and route dependencies."""
from __future__ import annotations

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.indexing.store import artifacts_exist


class DocHashBody(BaseModel):
    """Body for every endpoint that operates on one indexed document."""

    doc_hash: str = Field(..., description="sha256 hex digest of the indexed document")


class QueryBody(DocHashBody):
    query: str = Field(..., min_length=1, max_length=4000)
    # Prior turns, as {"role": "user"|"assistant", "content": str}. Roles are
    # constrained in the orchestrator so a client cannot inject a system turn.
    history: list[dict] | None = None


def require_indexed(doc_hash: str) -> str:
    """404 unless the document has complete artifacts on disk.

    One policy in one place — endpoints previously disagreed, some returning
    404 and others 200 with success:false for the same condition.
    """
    if not artifacts_exist(doc_hash):
        raise HTTPException(status_code=404, detail="doc_hash not indexed")
    return doc_hash
