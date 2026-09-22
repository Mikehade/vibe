"""Profile and onboarding endpoints."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from src.api.profile.models import MoodHistoryResponse, OnboardingRequest, ProfileResponse
from src.config.dependency_injection.container import Container
from src.infrastructure.middleware.device_auth import get_device_id
from src.infrastructure.services.profile import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
@inject
async def get_profile(
    device_id: str = Depends(get_device_id),
    profile_service: ProfileService = Depends(Provide[Container.profile_service]),
):
    """Get the taste profile for this device."""
    return await profile_service.get_profile(device_id)


@router.patch("/onboarding")
@inject
async def save_onboarding(
    body: OnboardingRequest,
    device_id: str = Depends(get_device_id),
    profile_service: ProfileService = Depends(Provide[Container.profile_service]),
):
    """Save onboarding preferences."""
    result = await profile_service.save_onboarding(device_id, body.model_dump())
    return {"success": True, "data": result}


@router.get("/mood-history", response_model=MoodHistoryResponse)
@inject
async def get_mood_history(
    device_id: str = Depends(get_device_id),
    limit: int = Query(50, ge=1, le=200),
    profile_service: ProfileService = Depends(Provide[Container.profile_service]),
):
    """Get mood history for this device."""
    history = await profile_service.get_mood_history(device_id, limit=limit)
    return {"history": history, "count": len(history)}
