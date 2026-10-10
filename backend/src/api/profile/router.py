"""Profile, household and onboarding endpoints."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from src.api.profile.models import OnboardingRequest, ProfileListResponse, ProfileResponse, SettingsRequest
from src.config.dependency_injection.container import Container
from src.infrastructure.middleware.device_auth import get_device_id, get_profile_id
from src.infrastructure.services.profile import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
@inject
async def get_profile(
    device_id: str = Depends(get_device_id),
    profile_id: str | None = Depends(get_profile_id),
    profile_service: ProfileService = Depends(Provide[Container.profile_service]),
):
    """The active profile (X-Profile-ID) or the most recent one on this TV."""
    return await profile_service.get_profile(device_id, profile_id)


@router.get("/all", response_model=ProfileListResponse)
@inject
async def list_profiles(
    device_id: str = Depends(get_device_id),
    profile_service: ProfileService = Depends(Provide[Container.profile_service]),
):
    """Everyone in the household on this TV."""
    return {"profiles": await profile_service.list_profiles(device_id)}


@router.patch("/onboarding", response_model=ProfileResponse)
@inject
async def save_onboarding(
    body: OnboardingRequest,
    device_id: str = Depends(get_device_id),
    profile_id: str | None = Depends(get_profile_id),
    profile_service: ProfileService = Depends(Provide[Container.profile_service]),
):
    """Create or complete a profile (set new_profile=true to add another household member)."""
    return await profile_service.save_onboarding(device_id, body.model_dump(), profile_id, create_new=body.new_profile)


@router.patch("/settings", response_model=ProfileResponse)
@inject
async def update_settings(
    body: SettingsRequest,
    device_id: str = Depends(get_device_id),
    profile_id: str | None = Depends(get_profile_id),
    profile_service: ProfileService = Depends(Provide[Container.profile_service]),
):
    try:
        return await profile_service.update_settings(device_id, profile_id, body.model_dump(exclude_unset=True))
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
