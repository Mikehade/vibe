"""Feedback service — processes ratings and updates taste profiles."""

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.domain.interfaces import IFeedbackRepository, ISessionPlanRepository, ITasteProfileRepository
from src.core.constants.genres import TMDB_GENRE_MAP
from utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackService:
    def __init__(
        self,
        feedback_repository: IFeedbackRepository,
        taste_profile_repository: ITasteProfileRepository,
        session_plan_repository: ISessionPlanRepository,
        session_factory: async_sessionmaker,
    ):
        self._feedback_repo = feedback_repository
        self._profile_repo = taste_profile_repository
        self._plan_repo = session_plan_repository
        self._session_factory = session_factory

    async def submit_session_feedback(
        self, plan_id: str, overall_rating: str, pacing_rating: str | None = None, comment: str | None = None
    ) -> dict:
        async with self._session_factory() as session:
            feedback = await self._feedback_repo.create_session_feedback(
                session,
                session_plan_id=plan_id,
                overall_rating=overall_rating,
                pacing_rating=pacing_rating,
                comment=comment,
            )

            # Update taste profile based on session feedback
            plan = await self._plan_repo.get_by_id(session, plan_id)
            if plan:
                await self._update_profile_from_session(session, plan, overall_rating, pacing_rating)
                await self._plan_repo.update(session, plan_id, status="completed")

            await session.commit()
            return {"id": feedback.id, "rating": overall_rating}

    async def submit_pick_feedback(self, pick_id: str, rating: str) -> dict:
        async with self._session_factory() as session:
            feedback = await self._feedback_repo.create_pick_feedback(
                session,
                session_pick_id=pick_id,
                rating=rating,
            )

            # Update taste profile based on pick feedback
            pick = await self._plan_repo.get_pick_by_id(session, pick_id)
            if pick:
                plan = await self._plan_repo.get_by_id(session, pick.session_plan_id)
                if plan:
                    await self._update_profile_from_pick(session, plan.device_id, pick, rating)

            await session.commit()
            return {"id": feedback.id, "rating": rating}

    async def _update_profile_from_session(self, session, plan, rating: str, pacing_rating: str | None):
        """Learning loop: session-level feedback updates pacing preferences."""
        profile = await self._profile_repo.get_by_device_id(session, plan.device_id)
        if not profile:
            return

        if rating == "thumbs_up" and pacing_rating:
            # Boost the pacing pattern that worked
            await self._profile_repo.update(session, profile.id, pacing_preference=pacing_rating)
            logger.info("Updated pacing preference for device %s", plan.device_id)

    async def _update_profile_from_pick(self, session, device_id: str, pick, rating: str):
        """Learning loop: pick-level feedback updates genre weights."""
        profile = await self._profile_repo.get_by_device_id(session, device_id)
        if not profile:
            return

        genre_weights = dict(profile.genre_weights or {})
        genre_ids = pick.genre_ids or []

        for genre_id in genre_ids:
            genre_name = TMDB_GENRE_MAP.get(genre_id, "").lower()
            if not genre_name:
                continue

            current = genre_weights.get(genre_name, 0.5)
            if rating == "thumbs_up":
                genre_weights[genre_name] = min(1.0, current + 0.1)
            elif rating == "thumbs_down":
                genre_weights[genre_name] = max(0.0, current - 0.1)

        disliked = [g for g, w in genre_weights.items() if w < 0.3]

        await self._profile_repo.update(
            session, profile.id,
            genre_weights=genre_weights,
            disliked_genres=disliked,
        )
        logger.info("Updated genre weights for device %s based on pick feedback", device_id)
