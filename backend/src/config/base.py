import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings as PydanticBaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root
ENV_FILE = BASE_DIR / ".env"


class BaseSettings(PydanticBaseSettings):
    ENV: str = Field(default="development", validation_alias="ENV")

    # ── Database ────────────────────────────────────────────────────────────
    # Kept as a full URL (your existing pattern) rather than split PG_* parts.
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://vibe:vibe_dev_password@localhost:5432/vibe",
        validation_alias="DATABASE_URL",
    )

    # ── Redis ───────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )

    # ── AWS / Bedrock ───────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = Field(default="", validation_alias="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = Field(default="", validation_alias="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="us-east-1", validation_alias="AWS_REGION")
    BEDROCK_MODEL_ID: str = Field(
        default="us.anthropic.claude-sonnet-4-6",
        validation_alias="BEDROCK_MODEL_ID",
    )

    # ── TMDB ────────────────────────────────────────────────────────────────
    TMDB_API_KEY: str = Field(default="", validation_alias="TMDB_API_KEY")
    TMDB_BASE_URL: str = Field(
        default="https://api.themoviedb.org/3",
        validation_alias="TMDB_BASE_URL",
    )

    # ── JustWatch ───────────────────────────────────────────────────────────
    JUSTWATCH_COUNTRY: str = Field(default="US", validation_alias="JUSTWATCH_COUNTRY")

    # ── CORS ────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173"],
        validation_alias="CORS_ORIGINS",
    )

    # ── Rate limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=30,
        validation_alias="RATE_LIMIT_PER_MINUTE",
    )

    # ── Caching ──────────────────────────────────────────────────────────────
    SESSION_PLAN_CACHE_TTL: int = Field(
        default=3600,
        validation_alias="SESSION_PLAN_CACHE_TTL",
    )

    # ── Bedrock / agentic loop ───────────────────────────────────────────────
    MAX_TOOL_ITERATIONS: int = Field(
        default=11,
        validation_alias="MAX_TOOL_ITERATIONS",
    )

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        populate_by_name=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> BaseSettings:
    env = os.getenv("ENV", "development").lower()

    if env == "production":
        from src.config.production import ProductionSettings
        return ProductionSettings()
    elif env == "staging":
        from src.config.staging import StagingSettings
        return StagingSettings()
    else:
        from src.config.development import DevelopmentSettings
        return DevelopmentSettings()