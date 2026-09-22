"""Pydantic schemas for mood endpoints."""

from pydantic import BaseModel, Field


class ParseMoodRequest(BaseModel):
    transcript: str = Field(..., min_length=1, max_length=2000, description="Voice or text transcript to parse into a mood")


class ParseMoodResponse(BaseModel):
    mood: str
    intensity: float = 0.5
    notes: str = ""
