"""Vibe — Session Architect API entry point."""
import os
from dotenv import load_dotenv, find_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.base import get_settings
from src.config.dependency_injection.container import Container
from src.infrastructure.middleware.device_auth import DeviceAuthMiddleware
from src.infrastructure.middleware.rate_limit import RateLimitMiddleware
from src.api.health.router import router as health_router
from src.api.session.router import router as session_router
from src.api.mood.router import router as mood_router
from src.api.profile.router import router as profile_router
from src.api.content.router import router as content_router
from src.api.feedback.router import router as feedback_router
from utils.logger import get_logger

logger = get_logger(__name__)

#  Load .env and pick the right Settings class
load_dotenv(find_dotenv())
FASTAPI_ENV = os.getenv("ENV", "development").lower()

# ── Settings ─────────────────────────────────────────────────────────────────
from src.config.development import DevelopmentSettings
from src.config.staging import StagingSettings
from src.config.production import ProductionSettings

_settings_map = {
    "development": DevelopmentSettings,
    "staging":     StagingSettings,
    "production":  ProductionSettings,
}

if FASTAPI_ENV not in _settings_map:
    raise ValueError(f"Unknown ENV: '{FASTAPI_ENV}'. Must be one of: {list(_settings_map)}")

settings = _settings_map[FASTAPI_ENV]()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    settings = get_settings()
    logger.info("Starting Vibe API — env=%s", settings.ENV)

    # Initialize DI container
    container = Container()
    app.state.container = container

    # Initialize database
    db = container.database()
    # await db.create_all()
    logger.info("Database tables ensured")

    yield

    # Shutdown
    logger.info("Shutting down Vibe API")
    await db.engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Vibe — Session Architect",
        description="AI-powered movie night planner for Fire TV",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/v1/docs" if settings.ENV != "production" else None,
        redoc_url="/api/v1/redoc" if settings.ENV != "production" else None,
    )

    # ── Middleware (order matters — outermost first) ─────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(DeviceAuthMiddleware)
    app.add_middleware(RateLimitMiddleware, rate_limit_per_minute=settings.RATE_LIMIT_PER_MINUTE or 60)

    # ── Routers ─────────────────────────────────────────
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(session_router, prefix="/api/v1")
    app.include_router(mood_router, prefix="/api/v1")
    app.include_router(profile_router, prefix="/api/v1")
    app.include_router(content_router, prefix="/api/v1")
    app.include_router(feedback_router, prefix="/api/v1")

    return app


app = create_app()

# Uvicorn entrypoint
if __name__ == "__main__":
    import uvicorn
    logger.info("About to start API")
    is_dev = FASTAPI_ENV == "development"

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=(FASTAPI_ENV == "development"),
        workers=None if is_dev else 2,
    )