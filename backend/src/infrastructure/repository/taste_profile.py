"""Taste profile repository — a device (TV) holds one or more household profiles."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.domain.interfaces import ITasteProfileRepository
from src.infrastructure.db.models.taste_profile import TasteProfile


class TasteProfileRepository(ITasteProfileRepository):
    def __init__(self, session_factory: async_sessionmaker):
        self._session_factory = session_factory

    async def get_by_device_id(self, session: AsyncSession, device_id: str, profile_id: str | None = None) -> TasteProfile | None:
        """Selected profile if given (and owned by the device), otherwise the most recently updated one."""
        if profile_id:
            result = await session.execute(
                select(TasteProfile).where(
                    TasteProfile.id == profile_id,
                    TasteProfile.device_id == device_id,
                    TasteProfile.deleted_at.is_(None),
                )
            )
            found = result.scalar_one_or_none()
            if found:
                return found
        result = await session.execute(
            select(TasteProfile)
            .where(TasteProfile.device_id == device_id, TasteProfile.deleted_at.is_(None))
            .order_by(TasteProfile.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_device(self, session: AsyncSession, device_id: str) -> list[TasteProfile]:
        result = await session.execute(
            select(TasteProfile)
            .where(TasteProfile.device_id == device_id, TasteProfile.deleted_at.is_(None))
            .order_by(TasteProfile.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, profile_id: str) -> TasteProfile | None:
        result = await session.execute(select(TasteProfile).where(TasteProfile.id == profile_id))
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, device_id: str, **kwargs) -> TasteProfile:
        profile = TasteProfile(device_id=device_id, **kwargs)
        session.add(profile)
        await session.flush()
        return profile

    async def update(self, session: AsyncSession, profile_id: str, **kwargs) -> TasteProfile:
        result = await session.execute(select(TasteProfile).where(TasteProfile.id == profile_id))
        profile = result.scalar_one()
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        await session.flush()
        return profile
