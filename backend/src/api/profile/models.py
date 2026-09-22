"""Pydantic schemas for profile endpoints."""

from pydantic import BaseModel, Field


class GenrePreference(BaseModel):
    genre: str
    action: str = Field(..., description="One of: like, dislike, skip")


class OnboardingRequest(BaseModel):
    genre_preferences: list[GenrePreference] = Field(default_factory=list)
    streaming_services: list[str] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    id: str | None = None
    device_id: str | None = None
    genre_weights: dict[str, float] = {}
    pacing_preference: str | None = None
    disliked_genres: list[str] = []
    preferred_providers: list[str] = []
    avg_session_length_minutes: int | None = None
    onboarding_completed: bool = False


class MoodHistoryEntry(BaseModel):
    mood: str
    day_of_week: int | None = None
    hour_of_day: int | None = None
    created_at: str | None = None


class MoodHistoryResponse(BaseModel):
    history: list[MoodHistoryEntry]
    count: int
