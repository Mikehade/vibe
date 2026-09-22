"""Mood parsing endpoint."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.api.mood.models import ParseMoodRequest, ParseMoodResponse
from src.config.dependency_injection.container import Container
from src.infrastructure.services.mood import MoodService

router = APIRouter(prefix="/mood", tags=["mood"])


@router.post("/parse", response_model=ParseMoodResponse)
@inject
async def parse_mood(
    body: ParseMoodRequest,
    mood_service: MoodService = Depends(Provide[Container.mood_service]),
):
    """Parse a voice/text transcript into a structured mood."""
    result = await mood_service.parse_mood(body.transcript)
    return result
