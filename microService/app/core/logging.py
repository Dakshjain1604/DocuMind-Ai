"""Lightweight structured logging — stdout JSON per request stage."""
import json
import sys
import time
import uuid
from contextlib import contextmanager


def log_event(event: str, **fields) -> None:
    line = json.dumps({"ts": time.time(), "event": event, **fields}, default=str)
    print(line, file=sys.stdout, flush=True)


@contextmanager
def timed_stage(stage: str, request_id: str, **extra):
    start = time.perf_counter()
    try:
        yield
        duration_ms = (time.perf_counter() - start) * 1000
        log_event("stage_ok", stage=stage, request_id=request_id, duration_ms=round(duration_ms, 1), **extra)
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        log_event("stage_err", stage=stage, request_id=request_id, duration_ms=round(duration_ms, 1), error=str(e), **extra)
        raise


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]
