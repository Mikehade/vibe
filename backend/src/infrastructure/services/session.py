"""Session service — orchestrates plan generation, persistence, swaps and re-plans.

Generation runs in the background and publishes to the LiveHub; HTTP responses
(and MCP tools, and phones in Couch Mode) follow the hub.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.domain.interfaces import IDeviceRepository, ISessionPlanRepository, ITasteProfileRepository
from src.core.domain.session_plan import Mood
from src.core.engine.arc import ROLE_LABELS, ArcSlot
from src.core.engine.candidate_pool import PoolRequest
from src.core.engine.session_architect import PlanRequest, SessionArchitect
from src.infrastructure.services.live import LiveHub
from utils.logger import get_logger

logger = get_logger(__name__)

PICK_FIELDS = (
    "position", "role", "tmdb_id", "media_type", "title", "year", "overview", "poster_path", "backdrop_path",
    "runtime_minutes", "episodes", "rating", "certification", "genre_ids", "reason", "confidence",
    "streaming_provider", "provider_logo_path", "deep_link_url",
)


def parse_local_time(value: str | None, tz_offset_minutes: int | None = None) -> datetime:
    if value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None and tz_offset_minutes is not None:
                dt = dt.replace(tzinfo=timezone(timedelta(minutes=tz_offset_minutes)))
            return dt
        except ValueError:
            pass
    now = datetime.now(timezone.utc)
    if tz_offset_minutes is not None:
        return now.astimezone(timezone(timedelta(minutes=tz_offset_minutes)))
    return now


def providers_of(profile) -> tuple[list[int], list[str]]:
    ids, names = [], []
    for p in (profile.preferred_providers or []) if profile else []:
        if isinstance(p, dict) and p.get("id") is not None:
            ids.append(int(p["id"]))
            names.append(p.get("name") or "")
    return ids, names


class SessionService:
    def __init__(
        self,
        session_architect: SessionArchitect,
        session_plan_repository: ISessionPlanRepository,
        taste_profile_repository: ITasteProfileRepository,
        device_repository: IDeviceRepository,
        session_factory: async_sessionmaker,
        live_hub: LiveHub,
        default_region: str = "US",
    ):
        self._architect = session_architect
        self._plan_repo = session_plan_repository
        self._profile_repo = taste_profile_repository
        self._device_repo = device_repository
        self._session_factory = session_factory
        self._hub = live_hub
        self._default_region = default_region

    @property
    def hub(self) -> LiveHub:
        return self._hub

    # ── helpers ────────────────────────────────────────────────────────────

    async def _device_and_profile(self, device_id: str, profile_id: str | None):
        async with self._session_factory() as session:
            device = await self._device_repo.upsert(session, device_id)
            profile = await self._profile_repo.get_by_device_id(session, device.id, profile_id)
            await session.commit()
            return device, profile

    def _pool_request(self, mood: Mood, profile, kids: bool | None = None, extra_excluded_genres: list[int] | None = None) -> PoolRequest:
        ids, names = providers_of(profile)
        return PoolRequest(
            mood=mood,
            region=(getattr(profile, "region", None) or self._default_region).upper(),
            provider_ids=ids,
            provider_names=names,
            kids=bool(kids) if kids is not None else bool(getattr(profile, "is_kids", False)),
            excluded_ids=list((getattr(profile, "excluded_tmdb_ids", None) or [])[-200:]),
            genre_weights=dict(getattr(profile, "genre_weights", None) or {}),
            disliked_genres=list(getattr(profile, "disliked_genres", None) or []),
            extra_excluded_genres=extra_excluded_genres or [],
        )

    @staticmethod
    def _pool_request_from_dict(d: dict) -> PoolRequest:
        return PoolRequest(
            mood=Mood(d["mood"]),
            region=d.get("region", "US"),
            provider_ids=d.get("provider_ids", []),
            provider_names=d.get("provider_names", []),
            kids=d.get("kids", False),
            excluded_ids=d.get("excluded_ids", []),
            genre_weights=d.get("genre_weights", {}),
            disliked_genres=d.get("disliked_genres", []),
            extra_excluded_genres=d.get("extra_excluded_genres", []),
        )

    @staticmethod
    def _pool_request_to_dict(r: PoolRequest) -> dict:
        return {
            "mood": r.mood.value, "region": r.region, "provider_ids": r.provider_ids, "provider_names": r.provider_names,
            "kids": r.kids, "excluded_ids": r.excluded_ids, "genre_weights": r.genre_weights,
            "disliked_genres": r.disliked_genres, "extra_excluded_genres": r.extra_excluded_genres,
        }

    # ── prefetch ───────────────────────────────────────────────────────────

    async def prefetch(self, device_id: str, profile_id: str | None, mood: str, kids: bool | None = None) -> dict:
        _, profile = await self._device_and_profile(device_id, profile_id)
        req = self._pool_request(Mood(mood), profile, kids)
        self._architect.pools.prefetch(req)
        return {"prefetching": True, "signature": req.signature()}

    # ── generate ───────────────────────────────────────────────────────────

    async def start_plan(
        self,
        device_id: str,
        profile_id: str | None,
        mood: str,
        time_budget_minutes: int | None = None,
        notes: str | None = None,
        local_time: str | None = None,
        tz_offset_minutes: int | None = None,
        kids: bool | None = None,
        audience: str | None = None,
        extra_excluded_genres: list[int] | None = None,
        room_code: str | None = None,
    ) -> str:
        """Create the plan row, start generation in the background, return plan_id."""
        mood_enum = Mood(mood)
        device, profile = await self._device_and_profile(device_id, profile_id)
        lt = parse_local_time(local_time, tz_offset_minutes)
        pool_req = self._pool_request(mood_enum, profile, kids, extra_excluded_genres)

        likes = [g for g, w in sorted((getattr(profile, "genre_weights", None) or {}).items(), key=lambda x: -x[1]) if w >= 0.65][:5]
        req = PlanRequest(
            mood=mood_enum,
            local_time=lt,
            budget_minutes=time_budget_minutes,
            pool_request=pool_req,
            notes=notes,
            audience=audience or (f"{profile.name}" + (" (kids profile)" if profile.is_kids else "") if profile else "one viewer"),
            likes=likes,
            dislikes=list(getattr(profile, "disliked_genres", None) or []),
        )

        async with self._session_factory() as session:
            plan = await self._plan_repo.create(
                session,
                device_id=device.id,
                profile_id=getattr(profile, "id", None),
                mood=mood,
                time_budget_minutes=time_budget_minutes,
                status="generating",
                context={
                    "local_time": lt.isoformat(),
                    "notes": notes,
                    "audience": req.audience,
                    "pool_request": self._pool_request_to_dict(pool_req),
                    "room_code": room_code,
                },
            )
            plan_id = plan.id
            await session.commit()

        self._hub.open(plan_id)
        self._hub.run(self._run(plan_id, req, first_event={"type": "plan", "data": {"plan_id": plan_id, "mood": mood}}))
        return plan_id

    async def generate_plan(self, device_id: str, profile_id: str | None = None, **kwargs) -> AsyncGenerator[str, None]:
        plan_id = await self.start_plan(device_id, profile_id, **kwargs)
        async for line in self._hub.follow(plan_id):
            yield line

    async def _run(self, plan_id: str, req: PlanRequest, first_event: dict | None = None, final_status: str = "generated"):
        started = time.monotonic()
        try:
            if first_event:
                await self._hub.publish(plan_id, first_event)
            async for event in self._architect.generate(req):
                await self._persist(plan_id, event)
                await self._hub.publish(plan_id, event)
            await self._set_plan(plan_id, status=final_status)
            await self._hub.publish(plan_id, {"type": "done", "data": {"plan_id": plan_id, "elapsed_ms": int((time.monotonic() - started) * 1000)}})
        except Exception as e:  # noqa: BLE001
            logger.exception("plan generation failed")
            await self._hub.publish(plan_id, {"type": "error", "data": {"message": f"Planning failed: {e.__class__.__name__}"}})
            await self._set_plan(plan_id, status="abandoned")
        finally:
            await self._hub.close(plan_id)

    async def _set_plan(self, plan_id: str, **kwargs):
        async with self._session_factory() as session:
            await self._plan_repo.update(session, plan_id, **kwargs)
            await session.commit()

    async def _persist(self, plan_id: str, event: dict) -> None:
        et = event["type"]
        data = event.get("data", {})
        if et == "trajectory":
            async with self._session_factory() as session:
                plan = await self._plan_repo.get_by_id(session, plan_id)
                ctx = dict(plan.context or {})
                ctx["arc"] = {k: data[k] for k in ("direction", "arc_shape", "budget_minutes", "slots") if k in data}
                await self._plan_repo.update(session, plan_id, energy_trajectory=data.get("energy_trajectory"), context=ctx)
                await session.commit()
        elif et == "pick":
            async with self._session_factory() as session:
                row = await self._plan_repo.add_pick(session, session_plan_id=plan_id, **{k: data.get(k) for k in PICK_FIELDS})
                await session.commit()
                data["id"] = row.id
                data["status"] = "pending"
                data["plan_id"] = plan_id
        elif et == "summary":
            async with self._session_factory() as session:
                plan = await self._plan_repo.get_by_id(session, plan_id)
                total = sum(p.runtime_minutes for p in plan.picks)
                data["total_runtime_minutes"] = total
                await self._plan_repo.update(session, plan_id, total_runtime_minutes=total, plan_summary=data.get("plan_summary"))
                await session.commit()
            data["plan_id"] = plan_id

    def follow(self, plan_id: str) -> AsyncGenerator[str, None]:
        return self._hub.follow(plan_id)

    # ── re-plan the rest of the night ──────────────────────────────────────

    async def start_replan(
        self, plan_id: str, device_id: str, after_position: int, shift: str, local_time: str | None = None,
        tz_offset_minutes: int | None = None,
    ) -> str:
        async with self._session_factory() as session:
            plan = await self._plan_repo.get_by_id(session, plan_id)
            if not plan:
                raise LookupError("plan not found")
            device = await self._device_repo.get_by_device_id(session, device_id)
            if not device or device.id != plan.device_id:
                raise PermissionError("not your plan")
            watched = [p for p in plan.picks if p.position <= after_position]
            later = [p for p in plan.picks if p.position > after_position]
            for p in watched:
                if p.status == "pending":
                    await self._plan_repo.update_pick(session, p.id, status="completed")
            await self._plan_repo.soft_delete_picks_after(session, plan_id, after_position)
            ctx = dict(plan.context or {})
            budget = plan.time_budget_minutes or ctx.get("arc", {}).get("budget_minutes") or 150
            used = sum(p.runtime_minutes for p in watched)
            remaining = max(30, budget - used)
            remaining_slots = max(1, len(later)) if later else 1
            ctx.setdefault("replans", []).append({"after": after_position, "shift": shift})
            await self._plan_repo.update(session, plan_id, status="generating", context=ctx)
            await session.commit()
            pool_req = self._pool_request_from_dict(ctx["pool_request"])
            exclude = {f"{p.media_type}:{p.tmdb_id}" for p in plan.picks} | set(ctx.get("swapped_out", []))
            req = PlanRequest(
                mood=Mood(plan.mood),
                local_time=parse_local_time(local_time, tz_offset_minutes),
                budget_minutes=remaining,
                pool_request=pool_req,
                notes=ctx.get("notes"),
                audience=ctx.get("audience", "one viewer"),
                shift=shift,
                start_position=after_position + 1,
                max_slots=remaining_slots,
                already_watched=[f"{p.title} ({ROLE_LABELS.get(p.role, p.role)})" for p in watched],
                exclude_keys=exclude,
            )
        self._hub.open(plan_id)
        self._hub.run(
            self._run(plan_id, req, first_event={"type": "replan", "data": {"plan_id": plan_id, "after_position": after_position, "shift": shift}})
        )
        return plan_id

    # ── swap one pick ──────────────────────────────────────────────────────

    async def swap_pick(self, plan_id: str, pick_id: str, device_id: str, remember: bool = True) -> dict:
        async with self._session_factory() as session:
            plan = await self._plan_repo.get_by_id(session, plan_id)
            if not plan:
                raise LookupError("plan not found")
            device = await self._device_repo.get_by_device_id(session, device_id)
            if not device or device.id != plan.device_id:
                raise PermissionError("not your plan")
            ctx = dict(plan.context or {})
            picks = list(plan.picks)
            old = next((p for p in picks if p.id == pick_id), None)
            if not old:
                raise LookupError("pick not found")

        pool_req = self._pool_request_from_dict(ctx["pool_request"])
        pool = await self._architect.pools.get(pool_req)
        slot_info = next((s for s in ctx.get("arc", {}).get("slots", []) if s["position"] == old.position), None)
        slot = ArcSlot(
            position=old.position,
            role=old.role,
            label=ROLE_LABELS.get(old.role, old.role),
            energy=(slot_info or {}).get("energy", 0.5),
            target_minutes=(slot_info or {}).get("target_minutes", old.runtime_minutes),
        )
        used = {f"{p.media_type}:{p.tmdb_id}" for p in picks} | set(ctx.get("swapped_out", []))
        prev = next((p for p in picks if p.position == old.position - 1), None)
        new = await self._architect.replacement(
            pool, slot, used, f"{prev.media_type}:{prev.tmdb_id}" if prev else None, Mood(plan.mood), old.title
        )
        if not new:
            raise LookupError("no alternatives left in this shortlist")

        async with self._session_factory() as session:
            await self._plan_repo.update_pick(session, pick_id, deleted_at=datetime.now(timezone.utc), status="skipped")
            row = await self._plan_repo.add_pick(session, session_plan_id=plan_id, **{k: new.get(k) for k in PICK_FIELDS})
            ctx.setdefault("swapped_out", []).append(f"{old.media_type}:{old.tmdb_id}")
            plan_row = await self._plan_repo.get_by_id(session, plan_id)
            total = sum(p.runtime_minutes for p in plan_row.picks)
            await self._plan_repo.update(session, plan_id, context=ctx, total_runtime_minutes=total)
            if remember and plan_row.profile_id:
                profile = await self._profile_repo.get_by_id(session, plan_row.profile_id)
                if profile:
                    excluded = list(profile.excluded_tmdb_ids or [])
                    if old.tmdb_id not in excluded:
                        excluded.append(old.tmdb_id)
                    await self._profile_repo.update(session, profile.id, excluded_tmdb_ids=excluded[-300:])
            await session.commit()
            new.update(id=row.id, status="pending", plan_id=plan_id)
        return {"pick": new, "replaced_pick_id": pick_id, "total_runtime_minutes": total}

    # ── reads ──────────────────────────────────────────────────────────────

    async def get_plan(self, plan_id: str) -> dict | None:
        async with self._session_factory() as session:
            plan = await self._plan_repo.get_by_id(session, plan_id)
            return self._plan_to_dict(plan) if plan else None

    async def list_plans(self, device_id: str, limit: int = 10, offset: int = 0) -> list[dict]:
        async with self._session_factory() as session:
            device = await self._device_repo.get_by_device_id(session, device_id)
            if not device:
                return []
            plans = await self._plan_repo.list_by_device(session, device.id, limit, offset)
            return [self._plan_to_dict(p) for p in plans]

    async def latest_plan(self, device_id: str) -> dict | None:
        async with self._session_factory() as session:
            device = await self._device_repo.get_by_device_id(session, device_id)
            if not device:
                return None
            plan = await self._plan_repo.latest_for_device(session, device.id)
            return self._plan_to_dict(plan) if plan else None

    async def update_pick_status(self, pick_id: str, status: str) -> dict:
        async with self._session_factory() as session:
            pick = await self._plan_repo.update_pick(session, pick_id, status=status)
            await session.commit()
            return {"id": pick.id, "status": pick.status}

    @staticmethod
    def _plan_to_dict(plan) -> dict:
        ctx = plan.context or {}
        slots = {s["position"]: s for s in ctx.get("arc", {}).get("slots", [])}
        return {
            "id": plan.id,
            "mood": plan.mood,
            "energy_trajectory": plan.energy_trajectory,
            "time_budget_minutes": plan.time_budget_minutes,
            "total_runtime_minutes": plan.total_runtime_minutes,
            "plan_summary": plan.plan_summary,
            "status": plan.status,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "local_time": ctx.get("local_time"),
            "arc": ctx.get("arc"),
            "notes": ctx.get("notes"),
            "audience": ctx.get("audience"),
            "picks": [
                {
                    "id": p.id,
                    "plan_id": plan.id,
                    "position": p.position,
                    "role": p.role,
                    "role_label": ROLE_LABELS.get(p.role, p.role),
                    "energy": slots.get(p.position, {}).get("energy"),
                    "tmdb_id": p.tmdb_id,
                    "media_type": p.media_type,
                    "title": p.title,
                    "year": p.year,
                    "overview": p.overview,
                    "poster_path": p.poster_path,
                    "backdrop_path": p.backdrop_path,
                    "runtime_minutes": p.runtime_minutes,
                    "episodes": p.episodes,
                    "rating": p.rating,
                    "certification": p.certification,
                    "genre_ids": p.genre_ids or [],
                    "reason": p.reason,
                    "confidence": p.confidence,
                    "streaming_provider": p.streaming_provider,
                    "provider_logo_path": p.provider_logo_path,
                    "deep_link_url": p.deep_link_url,
                    "status": p.status,
                }
                for p in sorted(plan.picks or [], key=lambda x: x.position)
            ],
        }
