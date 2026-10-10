"""Pydantic schemas for session endpoints."""

from typing import Literal

from pydantic import BaseModel, Field

MoodLiteral = Literal["tired", "energised", "stressed", "social", "bored", "adventurous"]


class GeneratePlanRequest(BaseModel):
    mood: MoodLiteral
    time_budget_minutes: int | None = Field(None, ge=30, le=480)
    voice_transcript: str | None = Field(None, max_length=2000, description="Free-text or voice notes")
    local_time: str | None = Field(None, description="Viewer's local time, ISO-8601 with offset")
    tz_offset_minutes: int | None = Field(None, ge=-840, le=840)
    kids_mode: bool | None = None
    room_code: str | None = Field(None, max_length=8)


class PrefetchRequest(BaseModel):
    mood: MoodLiteral
    kids_mode: bool | None = None


class ReplanRequest(BaseModel):
    after_position: int = Field(..., ge=1, le=10)
    shift: Literal["wind_down", "steady", "lift"]
    local_time: str | None = None
    tz_offset_minutes: int | None = Field(None, ge=-840, le=840)


class UpdatePickStatusRequest(BaseModel):
    status: Literal["pending", "watching", "completed", "skipped"]


class PickResponse(BaseModel):
    id: str
    plan_id: str | None = None
    position: int
    role: str
    role_label: str | None = None
    energy: float | None = None
    tmdb_id: int
    media_type: str = "movie"
    title: str
    year: int | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    runtime_minutes: int
    episodes: int | None = None
    rating: float | None = None
    certification: str | None = None
    genre_ids: list[int] = []
    reason: str | None = ""
    confidence: float | None = 0.0
    streaming_provider: str | None = None
    provider_logo_path: str | None = None
    deep_link_url: str | None = None
    status: str = "pending"


class PlanResponse(BaseModel):
    id: str
    mood: str
    energy_trajectory: str | None = None
    time_budget_minutes: int | None = None
    total_runtime_minutes: int | None = None
    plan_summary: str | None = None
    status: str
    created_at: str | None = None
    local_time: str | None = None
    arc: dict | None = None
    notes: str | None = None
    audience: str | None = None
    picks: list[PickResponse] = []


class PlanListResponse(BaseModel):
    plans: list[PlanResponse]
    count: int
