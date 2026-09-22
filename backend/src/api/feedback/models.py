"""Pydantic schemas for feedback endpoints."""

from pydantic import BaseModel, Field


class SessionFeedbackRequest(BaseModel):
    overall_rating: str = Field(..., description="thumbs_up or thumbs_down")
    pacing_rating: str | None = Field(None, description="slow, balanced, or fast")
    comment: str | None = Field(None, max_length=1000)


class PickFeedbackRequest(BaseModel):
    rating: str = Field(..., description="thumbs_up or thumbs_down")


class FeedbackResponse(BaseModel):
    id: str
    rating: str
