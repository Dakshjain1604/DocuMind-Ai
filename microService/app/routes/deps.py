"""Shared request models and route dependencies."""
from __future__ import annotations

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_owner_id
from app.indexing.store import artifacts_exist, load_artifacts


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


def require_owned(doc_hash: str, user: dict | None) -> None:
    """403 unless the caller owns this document.

    Documents indexed before per-user ownership existed (or indexed by a
    request with no "owners" ever recorded) carry no "owners" key at all —
    those stay visible to everyone, matching the app's pre-existing
    single-tenant behavior, rather than retroactively orphaning them.

    A no-op when the doc isn't indexed at all — callers that report
    "not indexed" themselves (as a fail() envelope rather than a 404) rely on
    reaching that check, not on getting a FileNotFoundError from here first.
    """
    if not artifacts_exist(doc_hash):
        return
    manifest = load_artifacts(doc_hash)["manifest"]
    owners = manifest.get("owners")
    if not owners:
        return
    if get_owner_id(user) not in owners:
        raise HTTPException(status_code=403, detail="You do not have access to this document")
