"""Device repository — queries only, no business logic."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.domain.interfaces import IDeviceRepository
from src.infrastructure.db.models.user import Device


class DeviceRepository(IDeviceRepository):
    def __init__(self, session_factory: async_sessionmaker):
        self._session_factory = session_factory

    async def get_by_device_id(self, session: AsyncSession, device_id: str) -> Device | None:
        result = await session.execute(
            select(Device).where(Device.device_id == device_id, Device.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def upsert(self, session: AsyncSession, device_id: str, **kwargs) -> Device:
        existing = await self.get_by_device_id(session, device_id)
        if existing:
            existing.last_seen_at = datetime.now(timezone.utc)
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await session.flush()
            return existing

        device = Device(device_id=device_id, **kwargs)
        session.add(device)
        await session.flush()
        return device

    async def get_by_id(self, session: AsyncSession, id: str) -> Device | None:
        result = await session.execute(
            select(Device).where(Device.id == id, Device.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
