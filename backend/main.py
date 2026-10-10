"""Vibe — Session Architect API entry point."""

import contextlib
import os
from contextlib import asynccontextmanager

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from src.api.content.router import router as content_router  # noqa: E402
from src.api.couch.router import router as couch_router  # noqa: E402
from src.api.feedback.router import router as feedback_router  # noqa: E402
from src.api.health.router import router as health_router  # noqa: E402
from src.api.mood.router import router as mood_router  # noqa: E402
from src.api.profile.router import router as profile_router  # noqa: E402
from src.api.session.router import router as session_router  # noqa: E402
from src.api.tv.router import router as tv_router  # noqa: E402
from src.config.base import get_settings  # noqa: E402
from src.config.dependency_injection.container import Container  # noqa: E402
from src.infrastructure.middleware.device_auth import DeviceAuthMiddleware  # noqa: E402
from src.infrastructure.middleware.rate_limit import RateLimitMiddleware  # noqa: E402
from src.mcp_server.server import build_mcp  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

ENV = os.getenv("ENV", "development").lower()
if ENV not in ("development", "staging", "production"):
    raise ValueError(f"Unknown ENV: '{ENV}'")


def create_app() -> FastAPI:
    settings = get_settings()
    container = Container()
    mcp = build_mcp(container)
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "Starting Vibe API — env=%s fake_services=%s model=%s", settings.ENV, settings.FAKE_SERVICES, settings.BEDROCK_MODEL_ID
        )
        db = container.database()
        if db.is_sqlite:
            await db.create_all()
        async with contextlib.AsyncExitStack() as stack:
            await stack.enter_async_context(mcp.session_manager.run())
            yield
        logger.info("Shutting down Vibe API")
        with contextlib.suppress(Exception):
            await container.language_model().close()
        await db.engine.dispose()

    app = FastAPI(
        title="Vibe — Session Architect",
        description="AI movie-night planner for Fire TV, with an Alexa+ MCP server at /mcp",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/v1/docs",
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
    )
    app.state.container = container

    origins = settings.CORS_ORIGINS
    wildcard = "*" in origins
    app.add_middleware(RateLimitMiddleware, rate_limit_per_minute=settings.RATE_LIMIT_PER_MINUTE or 30)
    app.add_middleware(DeviceAuthMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if wildcard else origins,
        allow_credentials=not wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )

    for r in (health_router, session_router, mood_router, profile_router, content_router, feedback_router, couch_router, tv_router):
        app.include_router(r, prefix="/api/v1")

    # MCP (Streamable HTTP) — served at /mcp. Mounted last so API routes win.
    app.mount("/", mcp_app)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=ENV == "development")
