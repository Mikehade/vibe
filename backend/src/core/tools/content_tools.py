"""Content tools for Bedrock — TMDB queries."""

from src.core.domain.interfaces import IContentClient
from src.core.tools.base import BaseTool


class ContentTools(BaseTool):
    tool_name = "content"

    def __init__(self, tmdb_client: IContentClient):
        self._tmdb = tmdb_client

    async def _search_tmdb(self, query: str, genres: str = "", exclude_ids: str = "") -> dict:
        """Search TMDB for titles matching a query, optionally filtered by genre IDs.

        Args:
            query: Search query string
            genres: Comma-separated genre IDs to filter by
            exclude_ids: Comma-separated TMDB IDs to exclude from results
        """
        genre_list = [int(g.strip()) for g in genres.split(",") if g.strip()] if genres else None
        exclude_list = [int(i.strip()) for i in exclude_ids.split(",") if i.strip()] if exclude_ids else []

        results = await self._tmdb.search(query, genres=genre_list)
        if exclude_list:
            results["results"] = [r for r in results.get("results", []) if r.get("id") not in exclude_list]

        return results

    async def _get_title_details(self, tmdb_id: int) -> dict:
        """Get full metadata for a TMDB title including runtime, genres, overview.

        Args:
            tmdb_id: The TMDB ID of the movie or TV show
        """
        return await self._tmdb.get_details(tmdb_id)

    async def _get_providers(self, tmdb_id: int, country: str = "US") -> dict:
        """Get streaming availability for a title.

        Args:
            tmdb_id: The TMDB ID of the movie or TV show
            country: ISO country code for regional availability
        """
        return await self._tmdb.get_providers(tmdb_id)
