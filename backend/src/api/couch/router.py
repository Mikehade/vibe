"""Couch Mode — phones join the TV's room, share moods and veto picks."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.config.dependency_injection.container import Container
from src.core.domain.session_plan import Mood
from src.infrastructure.middleware.device_auth import get_device_id
from src.infrastructure.services.couch import CouchService

router = APIRouter(prefix="/couch", tags=["couch"])


class JoinRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=30)


class MemberUpdate(BaseModel):
    mood: str | None = None
    notes: str | None = Field(None, max_length=200)
    vetoes: list[str] | None = None


class VoteRequest(BaseModel):
    pick_id: str


def _guard(fn):
    try:
        return fn()
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/rooms")
@inject
async def create_room(device_id: str = Depends(get_device_id), couch: CouchService = Depends(Provide[Container.couch_service])):
    """TV opens (or re-opens) its room."""
    room = couch.create_room(device_id)
    return couch.public(room)


@router.get("/rooms/{code}")
@inject
async def get_room(code: str, couch: CouchService = Depends(Provide[Container.couch_service])):
    room = _guard(lambda: couch._require(code))
    return couch.public(room)


@router.delete("/rooms/{code}")
@inject
async def close_room(code: str, device_id: str = Depends(get_device_id), couch: CouchService = Depends(Provide[Container.couch_service])):
    room = couch.get(code)
    if room and room.host_device_id == device_id:
        couch.close(code)
    return {"closed": True}


@router.post("/rooms/{code}/join")
@inject
async def join(code: str, body: JoinRequest, device_id: str = Depends(get_device_id), couch: CouchService = Depends(Provide[Container.couch_service])):
    member = _guard(lambda: couch.join(code, device_id, body.name.strip()))
    return {"member_id": member.id, "room": couch.public(couch.get(code))}


@router.patch("/rooms/{code}/members/{member_id}")
@inject
async def update_member(
    code: str, member_id: str, body: MemberUpdate,
    device_id: str = Depends(get_device_id), couch: CouchService = Depends(Provide[Container.couch_service]),
):
    if body.mood is not None and body.mood not in {m.value for m in Mood}:
        raise HTTPException(400, "Unknown mood")
    _guard(lambda: couch.update_member(code, member_id, device_id, body.mood, body.notes, body.vetoes))
    return couch.public(couch.get(code))


@router.post("/rooms/{code}/members/{member_id}/skip")
@inject
async def vote_skip(
    code: str, member_id: str, body: VoteRequest,
    device_id: str = Depends(get_device_id), couch: CouchService = Depends(Provide[Container.couch_service]),
):
    return _guard(lambda: couch.vote_skip(code, member_id, device_id, body.pick_id))


@router.get("/rooms/{code}/blend")
@inject
async def blend(code: str, couch: CouchService = Depends(Provide[Container.couch_service])):
    """Preview how the room's moods combine."""
    return _guard(lambda: couch.blend(code))
