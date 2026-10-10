"""Pydantic schemas for profile endpoints."""

from pydantic import BaseModel, Field


class GenrePreference(BaseModel):
    genre: str
    action: str = Field(..., description="One of: like, dislike, skip")


class ProviderRef(BaseModel):
    id: int
    name: str = ""
    logo_path: str | None = None


class OnboardingRequest(BaseModel):
    name: str | None = Field(None, max_length=60)
    is_kids: bool = False
    region: str | None = Field(None, min_length=2, max_length=4)
    genre_preferences: list[GenrePreference] = Field(default_factory=list)
    streaming_services: list[ProviderRef] = Field(default_factory=list)
    new_profile: bool = False


class SettingsRequest(BaseModel):
    name: str | None = Field(None, max_length=60)
    is_kids: bool | None = None
    region: str | None = Field(None, min_length=2, max_length=4)
    streaming_services: list[ProviderRef] | None = None
    reset_exclusions: bool = False


class ProfileResponse(BaseModel):
    id: str | None = None
    device_id: str | None = None
    name: str | None = None
    is_kids: bool = False
    region: str | None = None
    genre_weights: dict[str, float] = {}
    pacing_preference: str | None = None
    disliked_genres: list[str] = []
    preferred_providers: list[ProviderRef] = []
    avg_session_length_minutes: int | None = None
    onboarding_completed: bool = False


class ProfileListResponse(BaseModel):
    profiles: list[ProfileResponse]


class MoodHistoryEntry(BaseModel):
    mood: str
    day_of_week: int | None = None
    hour_of_day: int | None = None
    created_at: str | None = None


class MoodHistoryResponse(BaseModel):
    history: list[MoodHistoryEntry]
    count: int
