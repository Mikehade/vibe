"""Content service — provider lists and title details for the UI."""

from src.core.domain.catalog import Candidate
from src.core.domain.interfaces import IContentClient


class ContentService:
    def __init__(self, tmdb_client: IContentClient, default_region: str = "US"):
        self._tmdb = tmdb_client
        self._default_region = default_region

    async def providers(self, region: str | None) -> list[dict]:
        region = (region or self._default_region).upper()
        return (await self._tmdb.watch_providers(region))[:24]

    async def search(self, query: str) -> list[dict]:
        items = await self._tmdb.search_multi(query)
        out = []
        for i in items[:12]:
            c = Candidate.from_tmdb_list_item(i)
            if c:
                out.append(c.to_dict())
        return out

    async def title(self, media_type: str, tmdb_id: int, region: str | None) -> dict:
        details = await self._tmdb.details(media_type, tmdb_id)
        if not details:
            return {}
        c = Candidate(tmdb_id=tmdb_id, media_type=media_type, title=details.get("title") or details.get("name") or "")
        c.enrich_from_details(details, (region or self._default_region).upper())
        date = details.get("release_date") or details.get("first_air_date") or ""
        c.year = int(date[:4]) if date[:4].isdigit() else None
        c.rating = details.get("vote_average")
        d = c.to_dict()
        d["tagline"] = details.get("tagline")
        return d
