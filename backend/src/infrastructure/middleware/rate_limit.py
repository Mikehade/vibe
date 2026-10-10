"""Per-device rate limiting for expensive endpoints (pure ASGI, in-memory, single instance)."""

import json
import time
from collections import defaultdict

LIMITED = ("/api/v1/session/plan", "/api/v1/mood/parse")


class RateLimitMiddleware:
    def __init__(self, app, rate_limit_per_minute: int = 30):
        self.app = app
        self._limit = rate_limit_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "POST" or not scope.get("path", "").startswith(LIMITED):
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        key = headers.get("x-device-id") or (scope.get("client") or ("anon",))[0]
        now = time.time()
        window = [t for t in self._hits[key] if t > now - 60]
        if len(window) >= self._limit:
            self._hits[key] = window
            body = json.dumps({"success": False, "message": "Too many requests. Try again in a moment.", "code": "RATE_LIMITED"}).encode()
            await send({"type": "http.response.start", "status": 429, "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": body})
            return
        window.append(now)
        self._hits[key] = window
        return await self.app(scope, receive, send)
