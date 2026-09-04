"""Observability: structured per-stage logging, token/cost accounting, and a
queryable SQLite trace store (one row per query, GET /trace/{request_id})."""
from __future__ import annotations
import json
import logging
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import tiktoken

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


def count_tokens(text: str, model_name: str = "gpt-3.5-turbo") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def log_event(event: str, **fields) -> None:
    # Structured event line on the standard logging system (was print() to
    # stdout, which bypassed configure_logging entirely and couldn't be
    # levelled/redirected). INFO keeps the per-stage diagnostics visible under
    # the default RAG_LOG_LEVEL; operators can silence them by raising it.
    line = json.dumps({"event": event, **fields}, default=str)
    logger.info("%s", line)


@contextmanager
def timed_stage(stage: str, request_id: str, *, sink: list[dict] | None = None, **extra):
    """Times a block, logs a structured stage_ok/stage_err event, and — when
    a sink list is passed — appends a matching record for trace persistence."""
    start = time.perf_counter()
    try:
        yield
        duration_ms = (time.perf_counter() - start) * 1000
        log_event("stage_ok", stage=stage, request_id=request_id, duration_ms=round(duration_ms, 1), **extra)
        if sink is not None:
            sink.append({"stage": stage, "latency_ms": round(duration_ms, 1), **extra})
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        log_event("stage_err", stage=stage, request_id=request_id, duration_ms=round(duration_ms, 1), error=str(e), **extra)
        if sink is not None:
            sink.append({"stage": stage, "latency_ms": round(duration_ms, 1), "error": str(e), **extra})
        raise


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


# $ per 1K tokens, (input, output). Best-effort snapshot of public list prices
# for the non-":free" models named in .env.example's fallback chains — good
# enough to keep /telemetry/stats cost figures from being unconditionally
# null/zero, not a billing-accurate source of truth. Anything not listed here
# (including every ":free"-suffixed OpenRouter model, handled separately
# below) returns None rather than a guessed number.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "openai/gpt-4o-mini": (0.00015, 0.00060),
    "llama-3.3-70b-versatile": (0.00059, 0.00079),
    "llama-3.1-8b-instant": (0.00005, 0.00008),
    "deepseek-r1-distill-llama-70b": (0.00075, 0.00099),
}


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float | None:
    if model in MODEL_PRICING:
        price_in, price_out = MODEL_PRICING[model]
        return (tokens_in / 1000) * price_in + (tokens_out / 1000) * price_out
    if model.endswith(":free"):
        return 0.0
    return None


def _trace_db_path(db_path: str | None) -> Path:
    return Path(db_path) if db_path else Path(get_settings().trace_db_path)


def init_trace_db(db_path: str | None = None) -> None:
    p = _trace_db_path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    try:
        # WAL lets the read path (GET /trace, /telemetry/stats) and the write
        # path (every query/index) run without serializing on each other's
        # locks — cheap and meaningful under even modest load.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS traces (
                request_id TEXT PRIMARY KEY,
                doc_hash TEXT NOT NULL,
                query TEXT NOT NULL,
                created_at REAL NOT NULL,
                total_latency_ms REAL,
                total_tokens_in INTEGER,
                total_tokens_out INTEGER,
                total_cost_usd REAL,
                cache_hit INTEGER DEFAULT 0,
                stages_json TEXT,
                context_json TEXT,
                answer_text TEXT,
                error TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_doc_hash ON traces(doc_hash)")
        conn.commit()
    finally:
        conn.close()


_INITIALIZED_DBS: set[str] = set()


def record_trace(
    request_id: str,
    *,
    doc_hash: str,
    query: str,
    total_latency_ms: float | None = None,
    total_tokens_in: int | None = None,
    total_tokens_out: int | None = None,
    total_cost_usd: float | None = None,
    cache_hit: bool = False,
    stages: list[dict] | None = None,
    context: list[dict] | None = None,
    answer_text: str | None = None,
    error: str | None = None,
    db_path: str | None = None,
) -> None:
    p = _trace_db_path(db_path)
    # init_trace_db() runs once in the app lifespan. Calling it here meant a
    # CREATE TABLE plus a second sqlite connection on every single write.
    # Tests and scripts that write traces without starting the app still need
    # the schema, so create it lazily the first time only.
    if str(p) not in _INITIALIZED_DBS:
        init_trace_db(str(p))
        _INITIALIZED_DBS.add(str(p))
    conn = sqlite3.connect(p)
    try:
        conn.execute(
            """INSERT OR REPLACE INTO traces
               (request_id, doc_hash, query, created_at, total_latency_ms,
                total_tokens_in, total_tokens_out, total_cost_usd, cache_hit,
                stages_json, context_json, answer_text, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request_id,
                doc_hash,
                query,
                time.time(),
                total_latency_ms,
                total_tokens_in,
                total_tokens_out,
                total_cost_usd,
                int(cache_hit),
                json.dumps(stages or [], default=str),
                json.dumps(context or [], default=str),
                answer_text,
                error,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_trace(request_id: str, *, db_path: str | None = None) -> dict[str, Any] | None:
    p = _trace_db_path(db_path)
    if not p.exists():
        return None
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM traces WHERE request_id = ?", (request_id,)).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["stages"] = json.loads(out.pop("stages_json") or "[]")
        out["context"] = json.loads(out.pop("context_json") or "[]")
        out["cache_hit"] = bool(out["cache_hit"])
        return out
    finally:
        conn.close()


def get_telemetry_stats(*, db_path: str | None = None) -> dict[str, Any]:
    p = _trace_db_path(db_path)
    if not p.exists():
        return {
            "total_requests": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0.0,
            "error_count": 0,
            "recent_traces": [],
        }
    init_trace_db(str(p))
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    try:
        total_requests = conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
        total_tokens_in = conn.execute("SELECT SUM(total_tokens_in) FROM traces").fetchone()[0] or 0
        total_tokens_out = conn.execute("SELECT SUM(total_tokens_out) FROM traces").fetchone()[0] or 0
        total_cost = conn.execute("SELECT SUM(total_cost_usd) FROM traces").fetchone()[0] or 0.0
        avg_latency = conn.execute("SELECT AVG(total_latency_ms) FROM traces").fetchone()[0] or 0.0
        error_count = conn.execute("SELECT COUNT(*) FROM traces WHERE error IS NOT NULL").fetchone()[0]

        recent = conn.execute(
            "SELECT request_id, doc_hash, query, created_at, total_latency_ms, error FROM traces ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
        recent_list = [dict(r) for r in recent]

        return {
            "total_requests": total_requests,
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_cost_usd": round(total_cost, 4),
            "avg_latency_ms": round(avg_latency, 1),
            "error_count": error_count,
            "recent_traces": recent_list,
        }
    finally:
        conn.close()
