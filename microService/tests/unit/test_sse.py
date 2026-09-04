import json
from app.core.sse import sse_event


def test_sse_event_formats_with_event_name_and_json_data():
    out = sse_event("progress", {"step": "chunking", "n": 12})
    assert out.startswith("event: progress\n")
    assert "data: " in out
    body = out.split("data: ", 1)[1].rstrip("\n\n")
    assert json.loads(body) == {"step": "chunking", "n": 12}
    assert out.endswith("\n\n")


def test_sse_event_handles_done_with_empty_data():
    out = sse_event("done", {})
    assert "event: done" in out
    assert "data: {}" in out
