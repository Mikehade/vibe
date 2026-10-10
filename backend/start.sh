#!/bin/sh
# Production entrypoint: apply migrations, then serve (single worker — Couch Mode rooms,
# live plan streams and prefetch caches are in-process state).
set -e
if [ -z "$FAKE_SERVICES" ] || [ "$FAKE_SERVICES" = "false" ]; then
  case "$DATABASE_URL$DB_HOST" in
    *sqlite*) ;;
    *) alembic upgrade head ;;
  esac
fi
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --proxy-headers --forwarded-allow-ips '*' --timeout-keep-alive 75
