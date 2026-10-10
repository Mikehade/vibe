"""Session endpoints — plan generation (NDJSON streaming), follow, swap, re-plan."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.api.session.models import (
    GeneratePlanRequest,
    PlanListResponse,
    PlanResponse,
    PrefetchRequest,
    ReplanRequest,
    UpdatePickStatusRequest,
)
from src.config.dependency_injection.container import Container
from src.infrastructure.middleware.device_auth import get_device_id, get_profile_id
from src.infrastructure.services.couch import CouchService
from src.infrastructure.services.session import SessionService

router = APIRouter(prefix="/session", tags=["session"])

NDJSON_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"}


@router.post("/prefetch", status_code=202)
@inject
async def prefetch(
    body: PrefetchRequest,
    device_id: str = Depends(get_device_id),
    profile_id: str | None = Depends(get_profile_id),
    session_service: SessionService = Depends(Provide[Container.session_service]),
):
    """Start building the candidate shortlist as soon as a mood is chosen."""
    return await session_service.prefetch(device_id, profile_id, body.mood, body.kids_mode)


@router.post("/plan", response_class=StreamingResponse)
@inject
async def generate_plan(
    body: GeneratePlanRequest,
    device_id: str = Depends(get_device_id),
    profile_id: str | None = Depends(get_profile_id),
    session_service: SessionService = Depends(Provide[Container.session_service]),
    couch: CouchService = Depends(Provide[Container.couch_service]),
):
    """Generate a session plan — streams NDJSON events:
    plan, status, trajectory, candidates, tool, pick, summary, done (or error)."""
    kwargs = dict(
        mood=body.mood,
        time_budget_minutes=body.time_budget_minutes,
        notes=body.voice_transcript,
        local_time=body.local_time,
        tz_offset_minutes=body.tz_offset_minutes,
        kids=body.kids_mode,
    )
    if body.room_code:
        try:
            blended = couch.blend(body.room_code, host_mood=body.mood)
        except LookupError as e:
            raise HTTPException(404, str(e)) from e
        extra = " ".join(filter(None, [blended["notes"], body.voice_transcript]))
        kwargs.update(
            mood=blended["mood"], notes=extra or None, audience=blended["audience"],
            extra_excluded_genres=blended["excluded_genre_ids"], room_code=body.room_code.upper(),
        )
    plan_id = await session_service.start_plan(device_id, profile_id, **kwargs)
    if body.room_code:
        code = body.room_code.upper()
        couch.set_status(code, "planning", plan_id)

        async def _mark_ready():
            await session_service.hub.wait_done(plan_id, timeout=120)
            try:
                couch.set_status(code, "ready")
            except LookupError:
                pass

        session_service.hub.run(_mark_ready())
    return StreamingResponse(session_service.follow(plan_id), media_type="application/x-ndjson", headers=NDJSON_HEADERS)


@router.get("/plan/{plan_id}/live", response_class=StreamingResponse)
@inject
async def follow_plan(
    plan_id: str,
    session_service: SessionService = Depends(Provide[Container.session_service]),
):
    """Replay + follow a generation in progress (used by phones and voice-started plans)."""
    if not session_service.hub.get(plan_id):
        raise HTTPException(404, "No live generation for this plan")
    return StreamingResponse(session_service.follow(plan_id), media_type="application/x-ndjson", headers=NDJSON_HEADERS)


@router.post("/plan/{plan_id}/replan", response_class=StreamingResponse)
@inject
async def replan(
    plan_id: str,
    body: ReplanRequest,
    device_id: str = Depends(get_device_id),
    session_service: SessionService = Depends(Provide[Container.session_service]),
):
    """Adaptive check-in: keep what was watched, re-plan the rest with a new energy direction."""
    try:
        await session_service.start_replan(plan_id, device_id, body.after_position, body.shift, body.local_time, body.tz_offset_minutes)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    return StreamingResponse(session_service.follow(plan_id), media_type="application/x-ndjson", headers=NDJSON_HEADERS)


@router.post("/plan/{plan_id}/pick/{pick_id}/swap")
@inject
async def swap_pick(
    plan_id: str,
    pick_id: str,
    device_id: str = Depends(get_device_id),
    session_service: SessionService = Depends(Provide[Container.session_service]),
):
    """Replace one pick with the best alternative for the same slot."""
    try:
        return await session_service.swap_pick(plan_id, pick_id, device_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e


@router.get("/plan/latest")
@inject
async def latest_plan(
    device_id: str = Depends(get_device_id),
    session_service: SessionService = Depends(Provide[Container.session_service]),
):
    plan = await session_service.latest_plan(device_id)
    return {"plan": plan}


@router.get("/plan/{plan_id}", response_model=PlanResponse)
@inject
async def get_plan(
    plan_id: str,
    session_service: SessionService = Depends(Provide[Container.session_service]),
):
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
    result = await session_service.update_pick_status(pick_id, body.status)
    return {"success": True, "data": result}
