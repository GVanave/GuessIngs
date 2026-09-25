#!/usr/bin/env bash
# Starts an isolated backend for end-to-end tests (fresh SQLite DB, AI disabled).
set -euo pipefail
cd "$(dirname "$0")/../../backend"
DB="${E2E_DB:-/tmp/guessings-e2e.db}"
rm -f "$DB"
export DATABASE_URL="sqlite:///$DB" ENVIRONMENT=test AI_ENABLED=false ANTHROPIC_API_KEY= \
  SECRET_KEY=e2e-secret-key-0123456789abcdefghijklmnop \
  RATE_LIMIT_AUTH_PER_MINUTE=1000 RATE_LIMIT_ANALYZE_PER_MINUTE=1000 RATE_LIMIT_DEFAULT_PER_MINUTE=10000
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
exec $PY -m uvicorn app.main:app --host 127.0.0.1 --port 8000
