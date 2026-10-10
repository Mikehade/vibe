import os
from functools import lru_cache
from pathlib import Path

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

    # ── AWS / Bedrock ───────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = Field(default="", validation_alias="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = Field(default="", validation_alias="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="us-east-1", validation_alias="AWS_REGION")
    BEDROCK_MODEL_ID: str = Field(
        default="us.anthropic.claude-sonnet-4-6",
        validation_alias="BEDROCK_MODEL_ID",
    )

    # Faster model for short tasks (swap reasons, mood parsing). Falls back to BEDROCK_MODEL_ID on error.
    BEDROCK_FAST_MODEL_ID: str = Field(
        default="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        validation_alias="BEDROCK_FAST_MODEL_ID",
    )
    # Hard ceiling for one plan generation; after this we finish with the deterministic planner.
    PLAN_TIMEOUT_SECONDS: int = Field(default=45, validation_alias="PLAN_TIMEOUT_SECONDS")
    # Max agent turns (each turn may call tools) in one plan generation.
    MAX_AGENT_TURNS: int = Field(default=4, validation_alias="MAX_AGENT_TURNS")

    # ── Demo / offline mode ─────────────────────────────────────────────────
    # When true, TMDB and Bedrock are replaced with built-in fakes (no keys needed).
    FAKE_SERVICES: bool = Field(default=False, validation_alias="FAKE_SERVICES")

    # Public URL of the web app, used for Couch Mode QR links (e.g. https://d123.cloudfront.net)
    PUBLIC_WEB_URL: str = Field(default="http://localhost:5173", validation_alias="PUBLIC_WEB_URL")

    # ── TMDB ────────────────────────────────────────────────────────────────
    TMDB_API_KEY: str = Field(default="", validation_alias="TMDB_API_KEY")
    TMDB_BASE_URL: str = Field(
        default="https://api.themoviedb.org/3",
        validation_alias="TMDB_BASE_URL",
    )

    # Default watch region when a profile has none (ISO 3166-1, e.g. US, GB, NG)
    DEFAULT_REGION: str = Field(default="US", validation_alias="DEFAULT_REGION")

    # ── CORS ────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default=["*"],
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
    settings = _load_settings()
    from src.config.db_url import resolve_database_url

    if os.getenv("DB_HOST"):
        settings.DATABASE_URL = resolve_database_url()
    return settings


def _load_settings() -> BaseSettings:
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