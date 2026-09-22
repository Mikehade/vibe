"""Content service — wraps TMDB + JustWatch."""

from src.core.domain.interfaces import IContentClient
from utils.logger import get_logger

logger = get_logger(__name__)


class ContentService:
    def __init__(self, tmdb_client: IContentClient, justwatch_client):
        self._tmdb = tmdb_client
        self._justwatch = justwatch_client

    async def search(self, query: str, page: int = 1) -> dict:
        return await self._tmdb.search(query, page=page)

    async def get_details(self, tmdb_id: int) -> dict:
        details = await self._tmdb.get_details(tmdb_id)
        if not details:
            return {}

        # Enrich with provider info
        providers = await self._justwatch.check_availability(tmdb_id, [])
        details["streaming_providers"] = providers.get("providers", [])
        return details

    async def get_providers(self, tmdb_id: int) -> dict:
        return await self._justwatch.check_availability(tmdb_id, [])
