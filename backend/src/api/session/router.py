"""Session endpoints — plan generation and management."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.api.session.models import (
    GeneratePlanRequest,
    PlanListResponse,
    PlanResponse,
    UpdatePickStatusRequest,
)
from src.config.dependency_injection.container import Container
from src.infrastructure.middleware.device_auth import get_device_id
from src.infrastructure.services.session import SessionService

router = APIRouter(prefix="/session", tags=["session"])


@router.post("/plan", response_class=StreamingResponse)
@inject
async def generate_plan(
    body: GeneratePlanRequest,
    device_id: str = Depends(get_device_id),
    session_service: SessionService = Depends(Provide[Container.session_service]),
):
    """Generate a session plan — streams NDJSON events."""
    return StreamingResponse(
        session_service.generate_plan(
            device_id=device_id,
            mood=body.mood,
            time_budget_minutes=body.time_budget_minutes,
            voice_transcript=body.voice_transcript,
        ),
        media_type="application/x-ndjson",
    )


@router.get("/plan/{plan_id}", response_model=PlanResponse)
@inject
async def get_plan(
    plan_id: str,
    session_service: SessionService = Depends(Provide[Container.session_service]),
):
    """Retrieve a specific session plan."""
    plan = await session_service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.get("/plans", response_model=PlanListResponse)
@inject
async def list_plans(
    device_id: str = Depends(get_device_id),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    session_service: SessionService = Depends(Provide[Container.session_service]),
):
    """List session plans for this device."""
    plans = await session_service.list_plans(device_id, limit=limit, offset=offset)
    return {"plans": plans, "count": len(plans)}


@router.patch("/plan/{plan_id}/pick/{pick_id}")
@inject
async def update_pick_status(
    plan_id: str,
    pick_id: str,
    body: UpdatePickStatusRequest,
    session_service: SessionService = Depends(Provide[Container.session_service]),
):
    """Update a pick's watch status (queued → watching → watched / skipped)."""
    result = await session_service.update_pick_status(pick_id, body.status)
    return {"success": True, "data": result}
