"""Domain interfaces — ABCs for all repositories and external services.

The core layer NEVER imports from infrastructure. All external dependencies
are expressed as protocols/ABCs here and injected via the DI container.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession


class IDeviceRepository(ABC):
    @abstractmethod
    async def get_by_device_id(self, session: AsyncSession, device_id: str) -> Any | None: ...

    @abstractmethod
    async def upsert(self, session: AsyncSession, device_id: str, **kwargs) -> Any: ...


class ITasteProfileRepository(ABC):
    @abstractmethod
    async def get_by_device_id(self, session: AsyncSession, device_id: str) -> Any | None: ...

    @abstractmethod
    async def create(self, session: AsyncSession, device_id: str, **kwargs) -> Any: ...

    @abstractmethod
    async def update(self, session: AsyncSession, profile_id: str, **kwargs) -> Any: ...


class ISessionPlanRepository(ABC):
    @abstractmethod
    async def create(self, session: AsyncSession, **kwargs) -> Any: ...

    @abstractmethod
    async def get_by_id(self, session: AsyncSession, plan_id: str) -> Any | None: ...

    @abstractmethod
    async def list_by_device(
        self, session: AsyncSession, device_id: str, limit: int = 10, offset: int = 0
    ) -> list[Any]: ...

    @abstractmethod
    async def update(self, session: AsyncSession, plan_id: str, **kwargs) -> Any: ...

    @abstractmethod
    async def add_pick(self, session: AsyncSession, **kwargs) -> Any: ...

    @abstractmethod
    async def update_pick(self, session: AsyncSession, pick_id: str, **kwargs) -> Any: ...


class IFeedbackRepository(ABC):
    @abstractmethod
    async def create_session_feedback(self, session: AsyncSession, **kwargs) -> Any: ...

    @abstractmethod
    async def create_pick_feedback(self, session: AsyncSession, **kwargs) -> Any: ...

    @abstractmethod
    async def get_mood_history(
        self, session: AsyncSession, device_id: str, limit: int = 50
    ) -> list[Any]: ...

    @abstractmethod
    async def add_mood_entry(self, session: AsyncSession, **kwargs) -> Any: ...


class IContentClient(ABC):
    @abstractmethod
    async def search(self, query: str, genres: list[int] | None = None, page: int = 1) -> dict: ...

    @abstractmethod
    async def get_details(self, tmdb_id: int) -> dict: ...

    @abstractmethod
    async def get_providers(self, tmdb_id: int) -> dict: ...

    @abstractmethod
    async def discover_by_genres(
        self, genre_ids: list[int], exclude_ids: list[int] | None = None, page: int = 1
    ) -> list[dict]: ...


class ILanguageModel(ABC):
    @abstractmethod
    async def invoke(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> dict: ...

    @abstractmethod
    async def prompt(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]: ...
