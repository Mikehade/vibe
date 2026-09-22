"""Async TMDB v3 client with genre filtering."""

import httpx

from src.core.domain.interfaces import IContentClient
from utils.logger import get_logger

logger = get_logger(__name__)


class TMDBClient(IContentClient):
    def __init__(self, api_key: str, base_url: str = "https://api.themoviedb.org/3"):
        self._api_key = api_key
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                params={"api_key": self._api_key},
                timeout=10.0,
            )
        return self._client

    async def search(self, query: str, genres: list[int] | None = None, page: int = 1) -> dict:
        client = await self._get_client()
        try:
            # Search both movies and TV shows
            params = {"query": query, "page": page, "include_adult": "false"}
            resp = await client.get("/search/multi", params=params)
            resp.raise_for_status()
            data = resp.json()

            # Filter by genres if specified
            if genres:
                genre_set = set(genres)
                data["results"] = [
                    r for r in data.get("results", [])
                    if set(r.get("genre_ids", [])) & genre_set
                ]
            return data
        except httpx.HTTPError as e:
            logger.error("TMDB search failed: %s", e)
            return {"results": [], "total_results": 0}

    async def get_details(self, tmdb_id: int) -> dict:
        client = await self._get_client()
        try:
            # Try movie first, then TV
            resp = await client.get(f"/movie/{tmdb_id}", params={"append_to_response": "watch/providers"})
            if resp.status_code == 404:
                resp = await client.get(f"/tv/{tmdb_id}", params={"append_to_response": "watch/providers"})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error("TMDB details failed for %d: %s", tmdb_id, e)
            return {}

    async def get_providers(self, tmdb_id: int) -> dict:
        client = await self._get_client()
        try:
            resp = await client.get(f"/movie/{tmdb_id}/watch/providers")
            if resp.status_code == 404:
                resp = await client.get(f"/tv/{tmdb_id}/watch/providers")
            resp.raise_for_status()
            return resp.json().get("results", {})
        except httpx.HTTPError as e:
            logger.error("TMDB providers failed for %d: %s", tmdb_id, e)
            return {}

    async def discover_by_genres(
        self, genre_ids: list[int], exclude_ids: list[int] | None = None, page: int = 1
    ) -> list[dict]:
        client = await self._get_client()
        try:
            params = {
                "with_genres": ",".join(str(g) for g in genre_ids),
                "sort_by": "popularity.desc",
                "page": page,
                "include_adult": "false",
                "vote_average.gte": "5",
            }
            resp = await client.get("/discover/movie", params=params)
            resp.raise_for_status()
            results = resp.json().get("results", [])

            if exclude_ids:
                exclude_set = set(exclude_ids)
                results = [r for r in results if r["id"] not in exclude_set]

            return results
        except httpx.HTTPError as e:
            logger.error("TMDB discover failed: %s", e)
            return []

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
