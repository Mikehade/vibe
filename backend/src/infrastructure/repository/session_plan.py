"""Session plan repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from src.core.domain.interfaces import ISessionPlanRepository
from src.infrastructure.db.models.session_plan import SessionPick, SessionPlan


class SessionPlanRepository(ISessionPlanRepository):
    def __init__(self, session_factory: async_sessionmaker):
        self._session_factory = session_factory

    async def create(self, session: AsyncSession, **kwargs) -> SessionPlan:
        plan = SessionPlan(**kwargs)
        session.add(plan)
        await session.flush()
        return plan

    async def get_by_id(self, session: AsyncSession, plan_id: str) -> SessionPlan | None:
        result = await session.execute(
            select(SessionPlan)
            .options(selectinload(SessionPlan.picks).selectinload(SessionPick.feedback))
            .options(selectinload(SessionPlan.feedback))
            .where(SessionPlan.id == plan_id, SessionPlan.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_by_device(
        self, session: AsyncSession, device_id: str, limit: int = 10, offset: int = 0
    ) -> list[SessionPlan]:
        result = await session.execute(
            select(SessionPlan)
            .options(selectinload(SessionPlan.picks))
            .where(SessionPlan.device_id == device_id, SessionPlan.deleted_at.is_(None))
            .order_by(SessionPlan.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, session: AsyncSession, plan_id: str, **kwargs) -> SessionPlan:
        result = await session.execute(select(SessionPlan).where(SessionPlan.id == plan_id))
        plan = result.scalar_one()
        for key, value in kwargs.items():
            if hasattr(plan, key):
                setattr(plan, key, value)
        await session.flush()
        return plan

    async def add_pick(self, session: AsyncSession, **kwargs) -> SessionPick:
        pick = SessionPick(**kwargs)
        session.add(pick)
        await session.flush()
        return pick

    async def update_pick(self, session: AsyncSession, pick_id: str, **kwargs) -> SessionPick:
        result = await session.execute(select(SessionPick).where(SessionPick.id == pick_id))
        pick = result.scalar_one()
        for key, value in kwargs.items():
            if hasattr(pick, key):
                setattr(pick, key, value)
        await session.flush()
        return pick

    async def get_pick_by_id(self, session: AsyncSession, pick_id: str) -> SessionPick | None:
        result = await session.execute(select(SessionPick).where(SessionPick.id == pick_id))
        return result.scalar_one_or_none()
