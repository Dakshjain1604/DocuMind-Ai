"""SSE event-stream helpers."""
import json
from typing import Any


def sse_event(name: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {name}\ndata: {payload}\n\n"


def sse_error(message: str, *, partial: bool = False) -> str:
    return sse_event("error", {"message": message, "partial": partial})


def sse_token(text: str) -> str:
    return sse_event("token", {"text": text})
