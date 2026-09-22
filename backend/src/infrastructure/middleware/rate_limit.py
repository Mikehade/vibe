"""Per-device rate limiting via in-memory store (Redis upgrade later)."""

import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter per device ID."""

    def __init__(self, app, rate_limit_per_minute: int = 30):
        super().__init__(app)
        self._calls_per_minute = rate_limit_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        device_id = getattr(request.state, "device_id", None)
        if not device_id:
            return await call_next(request)

        now = time.time()
        window_start = now - 60

        # Clean old entries
        self._requests[device_id] = [
            t for t in self._requests[device_id] if t > window_start
        ]

        if len(self._requests[device_id]) >= self._calls_per_minute:
            logger.warning("Rate limit exceeded for device %s", device_id[:8])
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Rate limit exceeded. Try again in a moment.",
                    "code": "RATE_LIMITED",
                },
            )

        self._requests[device_id].append(now)
        return await call_next(request)
