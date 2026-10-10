"""Portable column types: JSONB on Postgres, plain JSON elsewhere (SQLite for tests / quick local runs)."""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

JSONType = JSON().with_variant(JSONB(), "postgresql")
