"""Availability tools for Bedrock — streaming links and provider checks."""

from src.core.tools.base import BaseTool


class AvailabilityTools(BaseTool):
    tool_name = "availability"

    def __init__(self, justwatch_client):
        self._justwatch = justwatch_client

    async def _get_streaming_link(self, tmdb_id: int, provider: str = "") -> dict:
        """Get the streaming deep link URL for a title on a specific provider.

        Args:
            tmdb_id: The TMDB ID of the movie or TV show
            provider: Provider name (e.g. 'Netflix', 'Prime Video')
        """
        result = await self._justwatch.get_deep_link(tmdb_id, provider)
        return result

    async def _check_availability(self, tmdb_id: int, providers: str = "") -> dict:
        """Check which streaming providers have a title available.

        Args:
            tmdb_id: The TMDB ID of the movie or TV show
            providers: Comma-separated list of provider names to check
        """
        provider_list = [p.strip() for p in providers.split(",") if p.strip()] if providers else []
        result = await self._justwatch.check_availability(tmdb_id, provider_list)
        return result
