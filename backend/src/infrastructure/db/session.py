from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    """Async database connection manager."""

    def __init__(self, database_url: str, echo: bool = False):
        kwargs = {"echo": echo, "pool_pre_ping": True}
        if database_url.startswith("postgresql"):
            kwargs.update(pool_size=10, max_overflow=20)
        self._engine = create_async_engine(database_url, **kwargs)
        self.is_sqlite = database_url.startswith("sqlite")
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @property
    def engine(self):
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_all(self) -> None:
        """Create tables directly (SQLite / quick local runs). Postgres uses Alembic migrations."""
        from src.infrastructure.db.base import Base
        import src.infrastructure.db.models  # noqa: F401

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self._engine.dispose()
        logger.info("Database connections disposed")