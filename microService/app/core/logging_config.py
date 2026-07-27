"""The one place logging is configured.

Before this existed the service had two disconnected logging systems: the
route modules called logging.getLogger(__name__) while nothing ever called
basicConfig (so those records fell through to the lastResort handler at
WARNING, unformatted), and observability.log_event wrote JSON straight to
stdout with print(). Neither could be levelled, filtered or redirected.
"""
from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def configure_logging(level: str | None = None) -> None:
    """Install a single stdout handler. Idempotent — safe to call from both the
    app lifespan and a test fixture."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    resolved = (level or os.environ.get("RAG_LOG_LEVEL") or "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(resolved)
    # Replace rather than append so repeated configuration (reload, tests)
    # cannot produce duplicated lines.
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)

    # These are chatty at INFO and drown out the application's own records.
    for noisy in ("httpx", "httpcore", "urllib3", "chromadb", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True
