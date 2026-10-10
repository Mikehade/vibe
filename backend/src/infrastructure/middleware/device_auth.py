"""Device-ID-based auth middleware (pure ASGI, streaming-safe).

Every TV (and every phone in Couch Mode) generates a random id on first launch.
An optional X-Profile-ID header selects a household profile on that device.
"""

import json

from fastapi import HTTPException, Request

EXEMPT_PREFIXES = ("/api/v1/health", "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json", "/api/v1/content/art/")


def is_exempt(path: str) -> bool:
    """Public paths: health/docs, generated artwork, and read-only live plan follow (for phones)."""
    return path.startswith(EXEMPT_PREFIXES) or (path.startswith("/api/v1/session/plan/") and path.endswith("/live"))


async def _reject(send, code: str, message: str):
    body = json.dumps({"success": False, "message": message, "code": code}).encode()
    await send({"type": "http.response.start", "status": 400, "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})


class DeviceAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        if not path.startswith("/api/") or scope.get("method") == "OPTIONS":
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        device_id = headers.get("x-device-id")
        if not device_id:
            if is_exempt(path):
                return await self.app(scope, receive, send)
            return await _reject(send, "MISSING_DEVICE_ID", "X-Device-ID header is required")
        if len(device_id) > 255 or len(device_id) < 4:
            return await _reject(send, "INVALID_DEVICE_ID", "Invalid X-Device-ID format")
        state = scope.setdefault("state", {})
        state["device_id"] = device_id
        state["profile_id"] = headers.get("x-profile-id") or None
        return await self.app(scope, receive, send)


async def get_device_id(request: Request) -> str:
    device_id = getattr(request.state, "device_id", None)
    if not device_id:
        raise HTTPException(status_code=400, detail="X-Device-ID header is required")
    return device_id


async def get_profile_id(request: Request) -> str | None:
    return getattr(request.state, "profile_id", None)
