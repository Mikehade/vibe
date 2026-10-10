"""TV link — pairs a voice assistant (Alexa+ via MCP) with a TV, and a TV inbox.

The TV shows a 6-digit code; the assistant calls `link_tv(code)`. From then on
plans requested by voice appear on that TV (the TV polls its inbox).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

CODE_TTL = 15 * 60


@dataclass
class _Pairing:
    code: str
    device_id: str
    created: float = field(default_factory=time.time)


class TvLinkService:
    def __init__(self) -> None:
        self._codes: dict[str, _Pairing] = {}
        self._sessions: dict[str, str] = {}  # assistant session id -> device id
        self._last_linked: tuple[str, float] | None = None
        self._inbox: dict[str, list[dict]] = {}
        self._tz: dict[str, int] = {}

    def remember_tz(self, device_id: str, offset_minutes: int | None) -> None:
        if offset_minutes is not None:
            self._tz[device_id] = offset_minutes

    def tz_offset(self, device_id: str) -> int | None:
        return self._tz.get(device_id)

    def create_code(self, device_id: str) -> dict:
        now = time.time()
        for code in [c for c, p in self._codes.items() if now - p.created > CODE_TTL]:
            self._codes.pop(code, None)
        for p in self._codes.values():
            if p.device_id == device_id:
                return {"code": p.code, "expires_in": int(CODE_TTL - (now - p.created))}
        while True:
            code = f"{random.randint(0, 999999):06d}"
            if code not in self._codes:
                break
        self._codes[code] = _Pairing(code, device_id)
        return {"code": code, "expires_in": CODE_TTL}

    def link(self, code: str, session_id: str | None) -> str | None:
        p = self._codes.get(code.strip().replace(" ", ""))
        if not p or time.time() - p.created > CODE_TTL:
            return None
        if session_id:
            self._sessions[session_id] = p.device_id
        self._last_linked = (p.device_id, time.time())
        self.push(p.device_id, {"type": "linked", "data": {}})
        return p.device_id

    def device_for(self, session_id: str | None) -> str | None:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        # Single-household demo fallback: the most recently linked TV (for assistants that drop sessions)
        if self._last_linked and time.time() - self._last_linked[1] < 12 * 3600:
            return self._last_linked[0]
        return None

    def is_linked(self, device_id: str) -> bool:
        return device_id in self._sessions.values() or bool(self._last_linked and self._last_linked[0] == device_id)

    def push(self, device_id: str, event: dict) -> None:
        box = self._inbox.setdefault(device_id, [])
        box.append({**event, "at": time.time()})
        del box[:-20]

    def drain(self, device_id: str) -> list[dict]:
        return self._inbox.pop(device_id, [])
