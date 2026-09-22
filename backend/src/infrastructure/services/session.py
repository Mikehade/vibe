"""Session service — orchestrates plan generation and persistence."""

import json
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.domain.interfaces import IDeviceRepository, ISessionPlanRepository, ITasteProfileRepository
from src.core.domain.session_plan import Mood
from src.core.engine.session_architect import SessionArchitect
from utils.logger import get_logger

logger = get_logger(__name__)


class SessionService:
    def __init__(
        self,
        session_architect: SessionArchitect,
        session_plan_repository: ISessionPlanRepository,
        taste_profile_repository: ITasteProfileRepository,
        device_repository: IDeviceRepository,
        session_factory: async_sessionmaker,
    ):
        self._architect = session_architect
        self._plan_repo = session_plan_repository
        self._profile_repo = taste_profile_repository
        self._device_repo = device_repository
        self._session_factory = session_factory

    async def generate_plan(
        self,
        device_id: str,
        mood: str,
        time_budget_minutes: int | None = None,
        voice_transcript: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a session plan, yielding NDJSON lines."""
        mood_enum = Mood(mood)

        # Get device and taste profile
        async with self._session_factory() as session:
            device = await self._device_repo.upsert(session, device_id)
            profile = await self._profile_repo.get_by_device_id(session, device.id)
            await session.commit()

        taste_dict = None
        if profile:
            taste_dict = {
                "genre_weights": profile.genre_weights or {},
                "disliked_genres": profile.disliked_genres or [],
                "pacing_preference": profile.pacing_preference or "balanced",
            }

        # Create the plan record
        async with self._session_factory() as session:
            device = await self._device_repo.get_by_device_id(session, device_id)
            plan = await self._plan_repo.create(
                session,
                device_id=device.id,
                mood=mood,
                time_budget_minutes=time_budget_minutes,
                status="generated",
            )
            plan_id = plan.id
            await session.commit()

        # Stream from the architect engine
        pick_position = 0
        async for event in self._architect.generate_plan(
            mood=mood_enum,
            device_id=device_id,
            time_budget_minutes=time_budget_minutes,
            voice_notes=voice_transcript,
            taste_profile=taste_dict,
        ):
            if event["type"] == "trajectory":
                async with self._session_factory() as session:
                    await self._plan_repo.update(
                        session,
                        plan_id,
                        energy_trajectory=event["data"].get("energy_trajectory", ""),
                    )
                    await session.commit()

            elif event["type"] == "pick":
                pick_data = event["data"]
                async with self._session_factory() as session:
                    await self._plan_repo.add_pick(
                        session,
                        session_plan_id=plan_id,
                        position=pick_data.get("position", pick_position + 1),
                        role=pick_data.get("role", "opener"),
                        tmdb_id=pick_data.get("tmdb_id", 0),
                        title=pick_data.get("title", "Unknown"),
                        runtime_minutes=pick_data.get("runtime_minutes", 0),
                        reason=pick_data.get("reason", ""),
                        confidence=pick_data.get("confidence", 0.0),
                        poster_path=pick_data.get("poster_path"),
                        genre_ids=pick_data.get("genre_ids", []),
                        streaming_provider=pick_data.get("streaming_provider"),
                        deep_link_url=pick_data.get("deep_link_url"),
                    )
                    await session.commit()
                pick_position += 1
                # Add plan_id to the event for the frontend
                event["data"]["plan_id"] = plan_id

            elif event["type"] == "summary":
                async with self._session_factory() as session:
                    await self._plan_repo.update(
                        session,
                        plan_id,
                        total_runtime_minutes=event["data"].get("total_runtime_minutes", 0),
                        plan_summary=event["data"].get("plan_summary", ""),
                    )
                    await session.commit()
                event["data"]["plan_id"] = plan_id

            yield json.dumps(event) + "\n"

    async def get_plan(self, plan_id: str) -> dict | None:
        async with self._session_factory() as session:
            plan = await self._plan_repo.get_by_id(session, plan_id)
            if not plan:
                return None
            return self._plan_to_dict(plan)

    async def list_plans(self, device_id: str, limit: int = 10, offset: int = 0) -> list[dict]:
        async with self._session_factory() as session:
            device = await self._device_repo.get_by_device_id(session, device_id)
            if not device:
                return []
            plans = await self._plan_repo.list_by_device(session, device.id, limit, offset)
            return [self._plan_to_dict(p) for p in plans]

    async def update_pick_status(self, pick_id: str, status: str) -> dict:
        async with self._session_factory() as session:
            pick = await self._plan_repo.update_pick(session, pick_id, status=status)
            await session.commit()
            return {"id": pick.id, "status": pick.status}

    @staticmethod
    def _plan_to_dict(plan) -> dict:
        return {
            "id": plan.id,
            "mood": plan.mood,
            "energy_trajectory": plan.energy_trajectory,
            "time_budget_minutes": plan.time_budget_minutes,
            "total_runtime_minutes": plan.total_runtime_minutes,
            "plan_summary": plan.plan_summary,
            "status": plan.status,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "picks": [
                {
                    "id": pick.id,
                    "position": pick.position,
                    "role": pick.role,
                    "tmdb_id": pick.tmdb_id,
                    "title": pick.title,
                    "poster_path": pick.poster_path,
                    "runtime_minutes": pick.runtime_minutes,
                    "genre_ids": pick.genre_ids,
                    "reason": pick.reason,
                    "confidence": pick.confidence,
                    "streaming_provider": pick.streaming_provider,
                    "deep_link_url": pick.deep_link_url,
                    "status": pick.status,
                }
                for pick in (plan.picks or [])
            ],
        }
