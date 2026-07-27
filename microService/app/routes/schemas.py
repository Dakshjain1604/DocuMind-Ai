"""Shared response envelope for the generation ("studio") endpoints.

Three states, deliberately distinct — the previous code conflated the last two,
which is how an LLM outage came to render as a plausible-looking result:

    ok(audit=[...], coverage={...})   -> success, with findings
    ok(audit=[],    coverage={...})   -> success, nothing found (an answer!)
    fail("llm_unavailable", "...")    -> the request did not produce an answer

Callers must be able to tell "the document has no compliance findings" from
"we could not reach the model", so no endpoint may substitute invented content
for either.
"""
from __future__ import annotations

from typing import Any, Final

# Error codes clients may branch on. Keep this list short and stable.
NOT_INDEXED: Final = "not_indexed"
LLM_UNAVAILABLE: Final = "llm_unavailable"
INVALID_LLM_OUTPUT: Final = "invalid_llm_output"


def ok(**data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


def fail(code: str, message: str, **data: Any) -> dict[str, Any]:
    """Failure envelope. `data` carries empty collections so clients can render
    without null-checking every field."""
    return {"success": False, "error": {"code": code, "message": message}, "data": data}
