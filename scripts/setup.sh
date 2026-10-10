#!/usr/bin/env bash
# One-time local setup: Python venv + backend deps, frontend deps, .env files.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || { echo "Python 3.11+ is required (brew install python@3.12)"; exit 1; }
command -v npm >/dev/null || { echo "Node.js 18+ is required (brew install node)"; exit 1; }

echo "→ Backend virtualenv"
cd "$ROOT/backend"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo "  created backend/.env — add TMDB_API_KEY (and AWS keys if you don't use ~/.aws)"; }

echo "→ Frontend packages"
cd "$ROOT/frontend"
npm install --silent
[ -f .env ] || cp .env.example .env

echo "✓ Setup done. Next: ./scripts/check-aws.sh   then   ./scripts/dev.sh"
