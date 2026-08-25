"""Per-client-IP rate limiting via slowapi.

Limit values are callables (not static strings) so they re-read Settings on
every check, consistent with the rest of the app's env > retrieval.json >
default precedence — and so tests can override RAG_RATE_LIMIT_*_PER_MIN
without needing a fresh process.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config.settings import get_settings

limiter = Limiter(key_func=get_remote_address)


def query_limit() -> str:
    return f"{get_settings().rate_limit_query_per_min}/minute"


def index_limit() -> str:
    return f"{get_settings().rate_limit_index_per_min}/minute"


def studio_limit() -> str:
    return f"{get_settings().rate_limit_studio_per_min}/minute"
