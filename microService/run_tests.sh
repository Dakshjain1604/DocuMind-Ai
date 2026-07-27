#!/usr/bin/env bash
# Run the backend test suite against the project virtualenv.
#
# Uses .venv/bin/python -m pytest when the venv exists so the suite always runs
# against the interpreter the dependencies were installed into, rather than
# whatever `pytest` happens to be first on PATH.
set -euo pipefail
cd "$(dirname "$0")"

if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python -m pytest "$@"
fi

if ! command -v pytest >/dev/null 2>&1; then
  echo "error: no .venv/ and pytest is not on PATH." >&2
  echo "       create the venv first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

exec pytest "$@"
