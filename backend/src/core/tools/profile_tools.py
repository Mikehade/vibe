"""Profile tools for Bedrock — taste profile and watch history reads."""

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.domain.interfaces import ITasteProfileRepository
from src.core.tools.base import BaseTool


class ProfileTools(BaseTool):
    tool_name = "profile"

    def __init__(
        self,
        taste_profile_repository: ITasteProfileRepository,
        session_factory: async_sessionmaker,
    ):
        self._repo = taste_profile_repository
        self._session_factory = session_factory

    async def _get_taste_profile(self, device_id: str) -> dict:
        """Get the taste profile for a device including genre weights and preferences.

        Args:
            device_id: The device's internal ID
        """
        async with self._session_factory() as session:
            profile = await self._repo.get_by_device_id(session, device_id)
            if not profile:
                return {"genre_weights": {}, "pacing_preference": "balanced", "disliked_genres": []}
            return {
                "genre_weights": profile.genre_weights or {},
                "pacing_preference": profile.pacing_preference or "balanced",
                "disliked_genres": profile.disliked_genres or [],
                "preferred_providers": profile.preferred_providers or [],
            }

    async def _get_watch_history(self, device_id: str, limit: int = 20) -> list:
        """Get recent watch history for a device.

        Args:
            device_id: The device's internal ID
            limit: Maximum number of entries to return
        """
        # This will be implemented via the watch history repository
        # For now return empty list — Bedrock handles this gracefully
        return []

    async def _get_resume_candidates(self, device_id: str) -> list:
        """Get partially-watched titles that can be resumed.

        Args:
            device_id: The device's internal ID
        """
        return []
