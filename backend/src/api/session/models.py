"""Pydantic schemas for session endpoints."""

from pydantic import BaseModel, Field


class GeneratePlanRequest(BaseModel):
    mood: str = Field(..., description="One of: chill, excited, nostalgic, adventurous, romantic, bored")
    time_budget_minutes: int | None = Field(None, ge=30, le=480, description="Optional time budget in minutes")
    voice_transcript: str | None = Field(None, max_length=2000, description="Optional voice transcript for mood parsing")


class UpdatePickStatusRequest(BaseModel):
    status: str = Field(..., description="One of: queued, watching, watched, skipped")


class PickResponse(BaseModel):
    id: str
    position: int
    role: str
    tmdb_id: int
    title: str
    poster_path: str | None = None
    runtime_minutes: int
    genre_ids: list[int] = []
    reason: str = ""
    confidence: float = 0.0
    streaming_provider: str | None = None
    deep_link_url: str | None = None
    status: str = "queued"


class PlanResponse(BaseModel):
    id: str
    mood: str
    energy_trajectory: str | None = None
    time_budget_minutes: int | None = None
    total_runtime_minutes: int | None = None
    plan_summary: str | None = None
    status: str
    created_at: str | None = None
    picks: list[PickResponse] = []


class PlanListResponse(BaseModel):
    plans: list[PlanResponse]
    count: int
