"""FastAPI app — DocuMind AI hybrid GraphRAG.

Composition root only: configuration, lifespan, middleware, error handlers and
router wiring. Request handling lives in app/routes/, business logic in
app/services/.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.middleware import SlowAPIMiddleware  # noqa: E402

from app.core.logging_config import configure_logging  # noqa: E402
from app.core.observability import init_trace_db, log_event  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.indexing.store import InvalidDocHash  # noqa: E402
from app.routes import documents, masterclass, query, studio, telemetry  # noqa: E402

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Both of these used to be missing entirely: logging was never configured,
    # and the trace table was created on every single write instead of once.
    configure_logging()
    init_trace_db()
    logger.info("DocuMind service starting")
    yield
    logger.info("DocuMind service stopping")


app = FastAPI(
    title="DocuMind",
    version="1.0.0",
    description="Hybrid GraphRAG document intelligence: vector + BM25 + knowledge-graph retrieval.",
    lifespan=lifespan,
)

# Browser origins allowed to call this service. Defaults to the local Next.js
# dev server rather than "*", which previously let any page on the internet
# drive the whole API from a visitor's browser. Value comes from Settings
# (RAG_CORS_ORIGINS) so there's a single config surface.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(InvalidDocHash)
async def _invalid_doc_hash_handler(_request: Request, exc: InvalidDocHash) -> JSONResponse:
    """A malformed doc_hash is a client error, not a server fault."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort catch-all: never let a raw traceback reach the client.

    Every route-specific error path (404s, validation, InvalidDocHash, the
    fail() envelope) is handled closer to its source; this only fires for
    genuinely unexpected failures, which still get logged in full server-side.
    """
    log_event(
        "unhandled_exception",
        path=str(request.url.path),
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
    )
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "internal_error", "message": "Internal server error"}},
    )


from fastapi import Depends
from app.core.auth import get_current_user

app.include_router(telemetry.router)
app.include_router(documents.router, dependencies=[Depends(get_current_user)])
app.include_router(query.router, dependencies=[Depends(get_current_user)])
app.include_router(studio.router, dependencies=[Depends(get_current_user)])
app.include_router(masterclass.router, dependencies=[Depends(get_current_user)])
