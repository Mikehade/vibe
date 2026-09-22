from src.config.base import BaseSettings


class ProductionSettings(BaseSettings):
    ENV: str = "production"
    LOG_LEVEL: str = "WARNING"
    RATE_LIMIT_PER_MINUTE: int = 20
