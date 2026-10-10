"""Async TMDB v3 client with response caching.

Accepts either a v3 API key or a v4 read-access token (starts with "eyJ").
"""

import asyncio
import json

import httpx

from src.core.domain.interfaces import IContentClient
from utils.logger import get_logger
from utils.ttl_cache import TTLCache

logger = get_logger(__name__)


class TMDBClient(IContentClient):
    def __init__(self, api_key: str, base_url: str = "https://api.themoviedb.org/3"):
        self._api_key = api_key.strip()
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None
        self._cache = TTLCache(ttl_seconds=6 * 3600, max_items=5000)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {"Accept": "application/json"}
            params = {}
            if self._api_key.startswith("eyJ"):
                headers["Authorization"] = f"Bearer {self._api_key}"
            else:
                params["api_key"] = self._api_key
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                params=params,
                headers=headers,
                timeout=httpx.Timeout(8.0, connect=4.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=20),
            )
        return self._client

    async def _get(self, path: str, params: dict | None = None, ttl: float | None = None) -> dict:
        key = path + "?" + json.dumps(params or {}, sort_keys=True)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        client = await self._get_client()
        for attempt in range(3):
            try:
                resp = await client.get(path, params=params)
                if resp.status_code == 429:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                if resp.status_code == 404:
                    return {}
                resp.raise_for_status()
                data = resp.json()
                self._cache.set(key, data, ttl)
                return data
            except httpx.HTTPError as e:
                if attempt == 2:
                    logger.error("TMDB %s failed: %s", path, e)
                    return {}
                await asyncio.sleep(0.3 * (attempt + 1))
        return {}

    # ── IContentClient ─────────────────────────────────────────────────────

    async def discover(self, media_type: str, params: dict) -> list[dict]:
        base = {"include_adult": "false", "language": "en-US"}
        data = await self._get(f"/discover/{media_type}", {**base, **params})
        return data.get("results", []) if data else []

    async def details(self, media_type: str, tmdb_id: int) -> dict:
        extra = "watch/providers,release_dates" if media_type == "movie" else "watch/providers,content_ratings"
        return await self._get(f"/{media_type}/{tmdb_id}", {"append_to_response": extra, "language": "en-US"}, ttl=24 * 3600)

    async def recommendations(self, media_type: str, tmdb_id: int) -> list[dict]:
        data = await self._get(f"/{media_type}/{tmdb_id}/recommendations", {"language": "en-US"})
        return data.get("results", []) if data else []

    async def search_multi(self, query: str, page: int = 1) -> list[dict]:
        data = await self._get("/search/multi", {"query": query, "page": page, "include_adult": "false"})
        return [r for r in data.get("results", []) if r.get("media_type") in ("movie", "tv")] if data else []

    async def watch_providers(self, region: str) -> list[dict]:
        movie, tv = await asyncio.gather(
            self._get("/watch/providers/movie", {"watch_region": region}, ttl=24 * 3600),
            self._get("/watch/providers/tv", {"watch_region": region}, ttl=24 * 3600),
        )
        merged: dict[int, dict] = {}
        for src in (movie, tv):
            for p in (src or {}).get("results", []):
                pid = p.get("provider_id")
                prio = (p.get("display_priorities") or {}).get(region, p.get("display_priority", 999))
                if pid not in merged or prio < merged[pid]["priority"]:
                    merged[pid] = {
                        "id": pid,
                        "name": p.get("provider_name"),
                        "logo_path": p.get("logo_path"),
                        "priority": prio,
                    }
        return sorted(merged.values(), key=lambda p: p["priority"])

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
