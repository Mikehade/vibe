#!/usr/bin/env bash
# Run Vibe locally: API on :8000 and the TV web app on :5173.
#
#   ./scripts/dev.sh            real Bedrock + TMDB (keys from backend/.env), SQLite database
#   ./scripts/dev.sh --fake     offline demo data, no keys needed
#   ./scripts/dev.sh --postgres use docker compose Postgres instead of SQLite
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAKE=false; PG=false
for a in "$@"; do case "$a" in --fake) FAKE=true;; --postgres) PG=true;; esac; done

[ -d "$ROOT/backend/.venv" ] || "$ROOT/scripts/setup.sh"

if $PG; then
  (cd "$ROOT" && docker compose up -d postgres)
  DB_URL="postgresql+asyncpg://vibe:vibe_dev_password@localhost:5432/vibe"
  (cd "$ROOT/backend" && DATABASE_URL="$DB_URL" .venv/bin/alembic upgrade head)
else
  DB_URL="sqlite+aiosqlite:///./dev.db"
fi

LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo localhost)"

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "→ API        http://localhost:8000/api/v1/docs  (fake services: $FAKE)"
(cd "$ROOT/backend" && FAKE_SERVICES=$FAKE DATABASE_URL="$DB_URL" .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload) &
sleep 2
echo "→ TV web app http://localhost:5173"
echo "  Phones / Vega simulator on your network: http://$LAN_IP:5173"
echo "  MCP endpoint: http://localhost:8000/mcp"
(cd "$ROOT/frontend" && VITE_PROXY_TARGET=http://localhost:8000 npx vite --host 0.0.0.0 --port 5173) &
wait
