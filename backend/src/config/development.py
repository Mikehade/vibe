from src.config.base import BaseSettings


class DevelopmentSettings(BaseSettings):
    ENV: str = "development"
    LOG_LEVEL: str = "DEBUG"
    RATE_LIMIT_PER_MINUTE: int = 100
