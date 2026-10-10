"""TV endpoints — voice-assistant pairing code and inbox polling."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from src.config.dependency_injection.container import Container
from src.infrastructure.middleware.device_auth import get_device_id
from src.infrastructure.services.tv_link import TvLinkService

router = APIRouter(prefix="/tv", tags=["tv"])


@router.post("/pair-code")
@inject
async def pair_code(
    tz_offset_minutes: int | None = Query(None, ge=-840, le=840),
    device_id: str = Depends(get_device_id),
    links: TvLinkService = Depends(Provide[Container.tv_link_service]),
):
    """A 6-digit code the viewer reads to Alexa: "link my TV, code 123456"."""
    links.remember_tz(device_id, tz_offset_minutes)
    return {**links.create_code(device_id), "linked": links.is_linked(device_id)}


@router.get("/inbox")
@inject
async def inbox(
    tz_offset_minutes: int | None = Query(None, ge=-840, le=840),
    device_id: str = Depends(get_device_id),
    links: TvLinkService = Depends(Provide[Container.tv_link_service]),
):
    """Events pushed to this TV (e.g. a plan started by voice). Poll every few seconds."""
    links.remember_tz(device_id, tz_offset_minutes)
    return {"events": links.drain(device_id), "linked": links.is_linked(device_id)}
