#!/usr/bin/env bash
# All automated checks: backend unit + integration tests (offline fakes, SQLite), frontend type-check + build.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -d "$ROOT/backend/.venv" ] || "$ROOT/scripts/setup.sh"
echo "→ Backend tests"
(cd "$ROOT/backend" && .venv/bin/python -m pytest tests -q)
echo "→ Frontend type-check and production build"
(cd "$ROOT/frontend" && npx tsc --noEmit && npx vite build --logLevel warn)
echo "✓ All checks passed"
