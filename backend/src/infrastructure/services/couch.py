"""Couch Mode — everyone in the room joins from their phone.

Rooms live in memory (the API runs as a single instance). Each member sends a
mood, optional notes ("nothing scary", "something like Paddington") and hard
no's. The TV blends them into one planning request and phones can vote to
skip a pick once the lineup is on screen.
"""

from __future__ import annotations

import random
import string
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field

from src.core.constants.genres import GENRE_NAME_TO_ID
from src.core.domain.session_plan import Mood

ROOM_TTL = 6 * 3600
_CODE_ALPHABET = "".join(c for c in string.ascii_uppercase if c not in "IOQ")

# lower = calmer; used to break ties toward the gentler mood
_CALM_ORDER = [Mood.TIRED, Mood.STRESSED, Mood.SOCIAL, Mood.BORED, Mood.ADVENTUROUS, Mood.ENERGISED]


@dataclass
class Member:
    id: str
    name: str
    device_id: str
    mood: str | None = None
    notes: str = ""
    vetoes: list[str] = field(default_factory=list)
    ready: bool = False
    joined_at: float = field(default_factory=time.time)


@dataclass
class Room:
    code: str
    host_device_id: str
    members: dict[str, Member] = field(default_factory=dict)
    status: str = "lobby"  # lobby | planning | ready
    plan_id: str | None = None
    skip_votes: dict[str, set[str]] = field(default_factory=dict)  # pick_id -> member ids
    created: float = field(default_factory=time.time)
    version: int = 0

    def touch(self) -> None:
        self.version += 1


class CouchService:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def _gc(self) -> None:
        now = time.time()
        for code in [c for c, r in self._rooms.items() if now - r.created > ROOM_TTL]:
            self._rooms.pop(code, None)

    def create_room(self, host_device_id: str) -> Room:
        self._gc()
        for room in self._rooms.values():
            if room.host_device_id == host_device_id and room.status != "closed":
                return room
        while True:
            code = "".join(random.choices(_CODE_ALPHABET, k=4))
            if code not in self._rooms:
                break
        room = Room(code=code, host_device_id=host_device_id)
        self._rooms[code] = room
        return room

    def get(self, code: str) -> Room | None:
        return self._rooms.get(code.upper())

    def close(self, code: str) -> None:
        self._rooms.pop(code.upper(), None)

    def join(self, code: str, device_id: str, name: str) -> Member:
        room = self._require(code)
        for m in room.members.values():
            if m.device_id == device_id:
                m.name = name[:30] or m.name
                room.touch()
                return m
        if len(room.members) >= 8:
            raise ValueError("Room is full")
        member = Member(id=uuid.uuid4().hex[:10], name=name[:30] or f"Guest {len(room.members) + 1}", device_id=device_id)
        room.members[member.id] = member
        room.touch()
        return member

    def update_member(self, code: str, member_id: str, device_id: str, mood: str | None, notes: str | None, vetoes: list[str] | None) -> Member:
        room = self._require(code)
        m = room.members.get(member_id)
        if not m or m.device_id != device_id:
            raise PermissionError("not your seat")
        if mood is not None:
            Mood(mood)  # validate
            m.mood = mood
        if notes is not None:
            m.notes = notes[:200]
        if vetoes is not None:
            m.vetoes = [v.lower()[:30] for v in vetoes][:6]
        m.ready = bool(m.mood)
        room.touch()
        return m

    def set_status(self, code: str, status: str, plan_id: str | None = None) -> Room:
        room = self._require(code)
        room.status = status
        if plan_id:
            room.plan_id = plan_id
            room.skip_votes = {}
        room.touch()
        return room

    def vote_skip(self, code: str, member_id: str, device_id: str, pick_id: str) -> dict:
        room = self._require(code)
        m = room.members.get(member_id)
        if not m or m.device_id != device_id:
            raise PermissionError("not your seat")
        voters = room.skip_votes.setdefault(pick_id, set())
        if member_id in voters:
            voters.discard(member_id)
        else:
            voters.add(member_id)
        room.touch()
        needed = max(1, (len(room.members) // 2) + 1)
        return {"pick_id": pick_id, "votes": len(voters), "needed": needed, "passed": len(voters) >= needed}

    def blend(self, code: str, host_mood: str | None = None) -> dict:
        """Turn the room into one planning request."""
        room = self._require(code)
        moods = [m.mood for m in room.members.values() if m.mood]
        if host_mood:
            moods.append(host_mood)
        if not moods:
            mood = Mood.SOCIAL
        else:
            counts = Counter(moods)
            top = max(counts.values())
            tied = [Mood(m) for m, c in counts.items() if c == top]
            mood = min(tied, key=_CALM_ORDER.index)
        names = [m.name for m in room.members.values()]
        notes = "; ".join(f"{m.name}: {m.notes}" for m in room.members.values() if m.notes)
        mix = ", ".join(f"{m.name} feels {m.mood}" for m in room.members.values() if m.mood)
        vetoes = sorted({v for m in room.members.values() for v in m.vetoes})
        excluded = [GENRE_NAME_TO_ID[v] for v in vetoes if v in GENRE_NAME_TO_ID]
        audience = f"a group of {len(names) + 1} (the host plus {', '.join(names)})" if names else "the host"
        if mix:
            notes = (mix + ". " + notes).strip()
        return {
            "mood": mood.value,
            "notes": notes or None,
            "audience": audience,
            "excluded_genre_ids": excluded,
            "vetoes": vetoes,
        }

    def public(self, room: Room) -> dict:
        needed = max(1, (len(room.members) // 2) + 1)
        return {
            "code": room.code,
            "status": room.status,
            "plan_id": room.plan_id,
            "version": room.version,
            "members": [
                {"id": m.id, "name": m.name, "mood": m.mood, "notes": m.notes, "vetoes": m.vetoes, "ready": m.ready}
                for m in room.members.values()
            ],
            "skip_votes": {pid: {"votes": len(v), "needed": needed} for pid, v in room.skip_votes.items()},
        }

    def _require(self, code: str) -> Room:
        room = self.get(code)
        if not room:
            raise LookupError("Room not found — check the code on the TV")
        return room
