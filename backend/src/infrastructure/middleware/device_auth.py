"""Device-ID-based auth middleware — no user accounts, just anonymous device tokens."""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from utils.logger import get_logger

logger = get_logger(__name__)


class DeviceAuthMiddleware(BaseHTTPMiddleware):
    """Validates X-Device-ID header and attaches it to request state."""

    EXEMPT_PATHS = {"/api/v1/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        # Skip auth for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip non-API paths
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Skip CORS preflight requests (browser sends OPTIONS without custom headers)
        if request.method == "OPTIONS":
            return await call_next(request)

        device_id = request.headers.get("X-Device-ID")
        if not device_id:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "X-Device-ID header is required",
                    "code": "MISSING_DEVICE_ID",
                },
            )

        if len(device_id) > 255 or len(device_id) < 4:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Invalid X-Device-ID format",
                    "code": "INVALID_DEVICE_ID",
                },
            )

        # Attach device_id to request state for downstream use
        request.state.device_id = device_id
        logger.debug("Request from device %s: %s %s", device_id[:8], request.method, request.url.path)

        return await call_next(request)


async def get_device_id(request: Request) -> str:
    """FastAPI dependency to extract device_id from request state."""
    device_id = getattr(request.state, "device_id", None)
    if not device_id:
        raise HTTPException(status_code=400, detail="X-Device-ID header is required")
    return device_id