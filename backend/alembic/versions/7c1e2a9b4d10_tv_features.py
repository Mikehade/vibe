"""TV features: household profiles, richer picks, plan context.

Revision ID: 7c1e2a9b4d10
Revises: 400f5e41446d
Create Date: 2026-09-28 10:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7c1e2a9b4d10"
down_revision: Union[str, None] = "400f5e41446d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    # taste_profiles → household profiles
    op.add_column("taste_profiles", sa.Column("name", sa.String(60), server_default="Me", nullable=False))
    op.add_column("taste_profiles", sa.Column("is_kids", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("taste_profiles", sa.Column("region", sa.String(4), server_default="US", nullable=False))
    op.add_column("taste_profiles", sa.Column("excluded_tmdb_ids", JSONB, server_default="[]", nullable=False))

    # session_plans
    op.add_column("session_plans", sa.Column("profile_id", sa.String(36), nullable=True))
    op.add_column("session_plans", sa.Column("context", JSONB, server_default="{}", nullable=False))

    # session_picks
    op.add_column("session_picks", sa.Column("media_type", sa.String(10), server_default="movie", nullable=False))
    op.add_column("session_picks", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("session_picks", sa.Column("overview", sa.Text(), nullable=True))
    op.add_column("session_picks", sa.Column("backdrop_path", sa.String(500), nullable=True))
    op.add_column("session_picks", sa.Column("episodes", sa.Integer(), nullable=True))
    op.add_column("session_picks", sa.Column("rating", sa.Float(), nullable=True))
    op.add_column("session_picks", sa.Column("certification", sa.String(16), nullable=True))
    op.add_column("session_picks", sa.Column("provider_logo_path", sa.String(300), nullable=True))


def downgrade() -> None:
    for col in ("provider_logo_path", "certification", "rating", "episodes", "backdrop_path", "overview", "year", "media_type"):
        op.drop_column("session_picks", col)
    op.drop_column("session_plans", "context")
    op.drop_column("session_plans", "profile_id")
    for col in ("excluded_tmdb_ids", "region", "is_kids", "name"):
        op.drop_column("taste_profiles", col)
