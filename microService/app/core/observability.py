"""Observability: structured per-stage logging, token/cost accounting, and a
queryable SQLite trace store (one row per query, GET /trace/{request_id})."""
from __future__ import annotations
import json
import sqlite3
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import tiktoken

from app.config.settings import get_settings


def count_tokens(text: str, model_name: str = "gpt-3.5-turbo") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def log_event(event: str, **fields) -> None:
    line = json.dumps({"ts": time.time(), "event": event, **fields}, default=str)
    print(line, file=sys.stdout, flush=True)


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


MODEL_PRICING: dict[str, tuple[float, float]] = {}


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
    init_trace_db(str(p))
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
