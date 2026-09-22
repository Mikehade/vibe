"""Feedback endpoints — session and pick-level ratings that feed the learning loop."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.api.feedback.models import PickFeedbackRequest, SessionFeedbackRequest
from src.config.dependency_injection.container import Container
from src.infrastructure.services.feedback import FeedbackService

router = APIRouter(prefix="/session", tags=["feedback"])


@router.post("/plan/{plan_id}/feedback")
@inject
async def submit_session_feedback(
    plan_id: str,
    body: SessionFeedbackRequest,
    feedback_service: FeedbackService = Depends(Provide[Container.feedback_service]),
):
    """Submit feedback for an entire session plan."""
    result = await feedback_service.submit_session_feedback(
        plan_id=plan_id,
        overall_rating=body.overall_rating,
        pacing_rating=body.pacing_rating,
        comment=body.comment,
    )
    return {"success": True, "data": result}


@router.post("/pick/{pick_id}/feedback")
@inject
async def submit_pick_feedback(
    pick_id: str,
    body: PickFeedbackRequest,
    feedback_service: FeedbackService = Depends(Provide[Container.feedback_service]),
):
    """Submit feedback for a single pick — triggers genre weight learning loop."""
    result = await feedback_service.submit_pick_feedback(
        pick_id=pick_id,
        rating=body.rating,
    )
    return {"success": True, "data": result}
