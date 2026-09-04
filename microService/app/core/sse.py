"""SSE framing, heartbeats, and the standard streaming response.

Absorbs the old core/streaming.py. The response construction lives here
because main.py previously carried three verbatim copies of the same
headers dict + StreamingResponse(with_heartbeat(gen())) block.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator, Callable

from fastapi.responses import StreamingResponse

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


# ── Framing ──────────────────────────────────────────────────────────────────

def sse_event(name: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {name}\ndata: {payload}\n\n"


def sse_error(message: str, *, partial: bool = False) -> str:
    return sse_event("error", {"message": message, "partial": partial})


# ── Client disconnects ───────────────────────────────────────────────────────

def is_disconnect_error(e: BaseException) -> bool:
    """True when an exception means "the client went away", not "we failed"."""
    if isinstance(e, (BrokenPipeError, ConnectionResetError, asyncio.CancelledError)):
        return True
    msg = str(e).lower()
    return "broken pipe" in msg or "connection reset" in msg or "errno 32" in msg


# ── Heartbeat ────────────────────────────────────────────────────────────────

async def with_heartbeat(generator: AsyncIterator[str], interval_s: float | None = None):
    """Forward `generator`, emitting a ping whenever it goes quiet.

    Two things this has to get right, both of which the previous version did
    not:

    * The producer task handle is held. A bare asyncio.create_task() may be
      garbage-collected mid-flight, since the event loop keeps only a weak
      reference.
    * The producer is cancelled and the source generator closed when the
      consumer stops. Otherwise an abandoned request kept draining the
      generator into an unbounded queue — for /index that meant the entire
      LLM-heavy pipeline ran to completion for a client that had disconnected.
    """
    if interval_s is None:
        interval_s = get_settings().sse_heartbeat_s

    queue: asyncio.Queue = asyncio.Queue()

    async def producer() -> None:
        try:
            async for item in generator:
                await queue.put(item)
            await queue.put(None)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # surfaced to the consumer below
            await queue.put(e)

    task = asyncio.create_task(producer())
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=interval_s)
            except asyncio.TimeoutError:
                yield sse_event("ping", {"timestamp": time.time()})
                continue
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        aclose = getattr(generator, "aclose", None)
        if aclose is not None:
            try:
                await aclose()
            except Exception:
                pass


# ── Response ─────────────────────────────────────────────────────────────────

def sse_stream_response(
    event_source: Callable[[], AsyncIterator[dict]],
    *,
    request_id: str | None = None,
    partial_on_error: bool = False,
) -> StreamingResponse:
    """Wrap an event generator as a heartbeat-ed text/event-stream response.

    `event_source` yields {"event": name, "data": {...}} dicts. Disconnects end
    the stream silently; anything else is reported as an `error` frame.
    """

    async def framed() -> AsyncIterator[str]:
        try:
            async for ev in event_source():
                yield sse_event(ev["event"], ev["data"])
        except Exception as e:
            if is_disconnect_error(e):
                return
            logger.exception("SSE stream failed (request_id=%s)", request_id)
            yield sse_error(str(e), partial=partial_on_error)

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        # Stops nginx and friends buffering the stream, which makes it look
        # frozen to the client.
        "X-Accel-Buffering": "no",
    }
    if request_id:
        headers["X-Request-Id"] = request_id

    return StreamingResponse(
        with_heartbeat(framed()), media_type="text/event-stream", headers=headers
    )
