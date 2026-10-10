"""Build the database URL.

Either DATABASE_URL is set directly, or (on AWS) it is composed from DB_HOST / DB_PORT /
DB_NAME / DB_USER / DB_PASSWORD, where DB_PASSWORD is injected from Secrets Manager.
"""

import os
from urllib.parse import quote_plus


def resolve_database_url(default: str | None = None) -> str:
    host = os.getenv("DB_HOST")
    if host:
        user = os.getenv("DB_USER", "vibe")
        password = quote_plus(os.getenv("DB_PASSWORD", ""))
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME", "vibe")
        ssl = "?ssl=require" if os.getenv("DB_SSL", "true").lower() == "true" else ""
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}{ssl}"
    return os.getenv("DATABASE_URL") or default or "postgresql+asyncpg://vibe:vibe_dev_password@localhost:5432/vibe"


def sync_url(async_url: str) -> str:
    """Alembic runs synchronously with psycopg2."""
    url = async_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    return url.replace("?ssl=require", "?sslmode=require")
