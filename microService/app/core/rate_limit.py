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


def _client_key(request) -> str:
    """Rate-limit key: the client IP as seen at the trusted edge.

    Behind a reverse proxy the socket peer is the proxy itself, so every
    request would otherwise collapse into one shared bucket. With
    RAG_TRUST_PROXY=true the leftmost (original client) hop of
    X-Forwarded-For is used. That header is only trustworthy when a proxy you
    control actually sets it, which is why the default is "off" — a
    directly-exposed service must not let callers rotate buckets with a
    spoofed header.
    """
    if get_settings().trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_client_key)


def query_limit() -> str:
    return f"{get_settings().rate_limit_query_per_min}/minute"


def index_limit() -> str:
    return f"{get_settings().rate_limit_index_per_min}/minute"


def studio_limit() -> str:
    return f"{get_settings().rate_limit_studio_per_min}/minute"
