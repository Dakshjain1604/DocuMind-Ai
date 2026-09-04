"""The hybrid retrieval query endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.auth import get_current_user
from app.core.observability import new_request_id
from app.core.rate_limit import limiter, query_limit
from app.core.sse import sse_stream_response
from app.retrieval.orchestrator import answer
from app.routes.deps import QueryBody, require_indexed, require_owned

router = APIRouter(tags=["query"])


@router.post("/query")
@limiter.limit(query_limit)
async def post_query(request: Request, body: QueryBody, user: dict = Depends(get_current_user)):
    """Answer a question against one indexed document, streamed over SSE."""
    require_indexed(body.doc_hash)
    require_owned(body.doc_hash, user)
    request_id = new_request_id()

    def events():
        return answer(
            doc_hash=body.doc_hash,
            query=body.query,
            history=body.history,
            request_id=request_id,
        )

    # partial_on_error: tokens may already have reached the client, so a late
    # failure is a truncated answer rather than no answer.
    return sse_stream_response(events, request_id=request_id, partial_on_error=True)
