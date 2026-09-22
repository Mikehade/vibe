"""JustWatch client — streaming availability with TMDB fallback."""

from utils.logger import get_logger

logger = get_logger(__name__)


class JustWatchClient:
    """Provides streaming availability info.

    Uses TMDB's watch/providers endpoint as the primary data source
    (more reliable than unofficial JustWatch API for a hackathon).
    """

    def __init__(self, country: str = "US", tmdb_client=None):
        self._country = country
        self._tmdb = tmdb_client

    async def get_deep_link(self, tmdb_id: int, provider: str = "") -> dict:
        """Get streaming deep link for a title."""
        providers = await self._get_providers(tmdb_id)
        country_data = providers.get(self._country, {})

        # Check flatrate (subscription) providers
        for p in country_data.get("flatrate", []):
            if not provider or provider.lower() in p.get("provider_name", "").lower():
                return {
                    "provider": p.get("provider_name"),
                    "deep_link": country_data.get("link", ""),
                    "logo_path": p.get("logo_path"),
                    "available": True,
                }

        # Check other availability types
        for avail_type in ["buy", "rent", "free"]:
            for p in country_data.get(avail_type, []):
                if not provider or provider.lower() in p.get("provider_name", "").lower():
                    return {
                        "provider": p.get("provider_name"),
                        "deep_link": country_data.get("link", ""),
                        "logo_path": p.get("logo_path"),
                        "available": True,
                        "type": avail_type,
                    }

        return {"available": False, "provider": provider or "unknown"}

    async def check_availability(self, tmdb_id: int, provider_names: list[str]) -> dict:
        """Check which providers have a title available."""
        providers = await self._get_providers(tmdb_id)
        country_data = providers.get(self._country, {})

        results = {}
        all_providers = []
        for avail_type in ["flatrate", "buy", "rent", "free"]:
            for p in country_data.get(avail_type, []):
                all_providers.append({
                    "name": p.get("provider_name"),
                    "type": avail_type,
                    "logo": p.get("logo_path"),
                })

        if provider_names:
            for name in provider_names:
                match = next((p for p in all_providers if name.lower() in p["name"].lower()), None)
                results[name] = {"available": match is not None, **(match or {})}
        else:
            results = {"providers": all_providers}

        return results

    async def _get_providers(self, tmdb_id: int) -> dict:
        """Fetch providers via TMDB client."""
        if self._tmdb:
            return await self._tmdb.get_providers(tmdb_id)
        return {}
