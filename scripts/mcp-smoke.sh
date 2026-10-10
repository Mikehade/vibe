#!/usr/bin/env bash
# Exercise the MCP server like Alexa+ would: initialize (spec 2025-11-25), list tools, link a TV,
# plan a night, read what's next.
#   ./scripts/mcp-smoke.sh                                  # local (http://localhost:8000/mcp)
#   ./scripts/mcp-smoke.sh https://dxxxx.cloudfront.net/mcp # deployed
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -d "$ROOT/backend/.venv" ] || "$ROOT/scripts/setup.sh"
"$ROOT/backend/.venv/bin/python" "$ROOT/scripts/mcp_smoke.py" "${1:-http://localhost:8000/mcp}"
