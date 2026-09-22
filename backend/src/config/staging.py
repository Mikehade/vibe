from src.config.base import BaseSettings


class StagingSettings(BaseSettings):
    ENV: str = "staging"
    CORS_ORIGINS: list[str] = ["https://staging.vibe-tv.app"]
