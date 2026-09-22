"""Feedback repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.domain.interfaces import IFeedbackRepository
from src.infrastructure.db.models.feedback import MoodHistory, PickFeedback, SessionFeedback


class FeedbackRepository(IFeedbackRepository):
    def __init__(self, session_factory: async_sessionmaker):
        self._session_factory = session_factory

    async def create_session_feedback(self, session: AsyncSession, **kwargs) -> SessionFeedback:
        feedback = SessionFeedback(**kwargs)
        session.add(feedback)
        await session.flush()
        return feedback

    async def create_pick_feedback(self, session: AsyncSession, **kwargs) -> PickFeedback:
        feedback = PickFeedback(**kwargs)
        session.add(feedback)
        await session.flush()
        return feedback

    async def get_mood_history(
        self, session: AsyncSession, device_id: str, limit: int = 50
    ) -> list[MoodHistory]:
        result = await session.execute(
            select(MoodHistory)
            .where(MoodHistory.device_id == device_id)
            .order_by(MoodHistory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_mood_entry(self, session: AsyncSession, **kwargs) -> MoodHistory:
        entry = MoodHistory(**kwargs)
        session.add(entry)
        await session.flush()
        return entry
