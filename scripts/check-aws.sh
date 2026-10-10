#!/usr/bin/env bash
# Verifies your credentials before you demo or deploy: AWS identity, Bedrock model access
# (one tiny call per model), and the TMDB key.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -d "$ROOT/backend/.venv" ] || "$ROOT/scripts/setup.sh"
cd "$ROOT/backend" && .venv/bin/python "$ROOT/scripts/check_services.py"
