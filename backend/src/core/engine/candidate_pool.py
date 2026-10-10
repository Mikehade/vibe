"""Candidate pool — the shortlist the planner reasons over.

Built with TMDB /discover (not free-text search), filtered by mood genres, the
viewer's streaming services and region, runtime, quality floor and kids safety,
then enriched in parallel with runtime, certification and where-to-watch.

Pools are cached by request signature and can be *prefetched* the moment a mood
is selected, so by the time the viewer picks a time budget the work is done.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from src.core.constants.genres import GENRE_NAME_TO_ID
from src.core.constants.moods import (
    MOOD_GENRE_MAP,
    get_excluded_genre_ids_for_mood,
    get_genre_ids_for_mood,
)
from src.core.domain.catalog import Candidate, genre_names, to_tv_genres
from src.core.domain.interfaces import IContentClient
from src.core.domain.session_plan import Mood
from utils.logger import get_logger
from utils.ttl_cache import TTLCache

logger = get_logger(__name__)

ProgressFn = Callable[[str, str], Awaitable[None] | None]

POOL_SIZE = 28
ENRICH_CONCURRENCY = 10


@dataclass
class PoolRequest:
    mood: Mood
    region: str = "US"
    provider_ids: list[int] = field(default_factory=list)
    provider_names: list[str] = field(default_factory=list)
    kids: bool = False
    excluded_ids: list[int] = field(default_factory=list)
    genre_weights: dict[str, float] = field(default_factory=dict)
    disliked_genres: list[str] = field(default_factory=list)
    extra_excluded_genres: list[int] = field(default_factory=list)

    def signature(self) -> str:
        payload = {
            "m": self.mood.value,
            "r": self.region,
            "p": sorted(self.provider_ids),
            "k": self.kids,
            "x": sorted(self.excluded_ids)[-50:],
            "d": sorted(self.disliked_genres),
            "g": sorted(self.extra_excluded_genres),
        }
        return hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


@dataclass
class CandidatePool:
    request: PoolRequest
    candidates: list[Candidate]
    outside_services: bool = False  # true if we had to relax the provider filter

    def by_key(self) -> dict[str, Candidate]:
        return {c.key: c for c in self.candidates}

    def find(self, tmdb_id: int, media_type: str | None = None) -> Candidate | None:
        for c in self.candidates:
            if c.tmdb_id == tmdb_id and (media_type is None or c.media_type == media_type):
                return c
        for c in self.candidates:
            if c.tmdb_id == tmdb_id:
                return c
        return None

    def add(self, cand: Candidate) -> None:
        if not self.find(cand.tmdb_id, cand.media_type):
            self.candidates.append(cand)


def _disliked_ids(names: list[str]) -> list[int]:
    ids = []
    for n in names:
        key = n.lower().replace("sci-fi", "science fiction").replace("_", " ")
        gid = GENRE_NAME_TO_ID.get(key)
        if gid:
            ids.append(gid)
    return ids


def score_candidate(c: Candidate, req: PoolRequest, mood_genres: set[int]) -> float:
    rating = c.rating or 5.0
    quality = rating * math.log10(max(c.vote_count, 10))  # ~ 12..35
    overlap = len(mood_genres.intersection(c.genre_ids))
    taste = 0.0
    for name in genre_names(c.genre_ids):
        w = req.genre_weights.get(name.lower())
        if w is None and name.lower() == "science fiction":
            w = req.genre_weights.get("sci-fi")
        if w is not None:
            taste += (w - 0.5) * 8
    popularity = math.log10(max(c.popularity, 1)) * 2
    return quality + overlap * 3 + taste + popularity


class CandidatePoolBuilder:
    def __init__(self, content: IContentClient):
        self._content = content
        self._cache = TTLCache(ttl_seconds=20 * 60, max_items=300)
        self._inflight: dict[str, asyncio.Task] = {}

    # ── prefetch / cache ───────────────────────────────────────────────────

    def prefetch(self, req: PoolRequest) -> None:
        sig = req.signature()
        if self._cache.get(sig) is not None or sig in self._inflight:
            return
        task = asyncio.create_task(self._build(req, None))
        self._inflight[sig] = task
        task.add_done_callback(lambda _t, s=sig: self._inflight.pop(s, None))

    def cached(self, sig: str) -> CandidatePool | None:
        return self._cache.get(sig)

    async def get(self, req: PoolRequest, progress: ProgressFn | None = None) -> CandidatePool:
        sig = req.signature()
        cached = self._cache.get(sig)
        if cached is not None:
            await _emit(progress, "pool", f"Shortlist ready — {len(cached.candidates)} titles (prepared while you were choosing)")
            return cached
        task = self._inflight.get(sig)
        if task is not None:
            await _emit(progress, "pool", "Finishing the shortlist we started when you picked your mood")
            return await asyncio.shield(task)
        return await self._build(req, progress)

    # ── build ──────────────────────────────────────────────────────────────

    async def _build(self, req: PoolRequest, progress: ProgressFn | None) -> CandidatePool:
        mood_cfg = MOOD_GENRE_MAP[req.mood]
        mood_genres = get_genre_ids_for_mood(req.mood)
        excluded = set(get_excluded_genre_ids_for_mood(req.mood)) | set(_disliked_ids(req.disliked_genres))
        excluded |= set(req.extra_excluded_genres)
        mood_genres = [g for g in mood_genres if g not in excluded] or get_genre_ids_for_mood(req.mood)
        if req.kids:
            excluded |= {27, 53, 80, 10752}
            mood_genres = list(dict.fromkeys([10751, 16] + [g for g in mood_genres if g in (35, 12, 14, 878, 99)]))

        genre_label = ", ".join(n.lower() for n in genre_names(mood_genres[:3]))
        where = ", ".join(req.provider_names[:3]) if req.provider_names else "all services"
        await _emit(progress, "pool", f"Looking for {genre_label} on {where}")

        raw = await self._discover(req, mood_genres, excluded, mood_cfg["max_runtime_per_pick"], with_providers=True)
        outside = False
        if len(raw) < 12 and req.provider_ids:
            await _emit(progress, "pool", "Slim pickings on your services — widening the search")
            raw += await self._discover(req, mood_genres, excluded, mood_cfg["max_runtime_per_pick"], with_providers=False)
            outside = True

        # de-dupe, drop excluded
        seen: set[str] = set()
        excluded_ids = set(req.excluded_ids)
        blocked_genres = excluded | set(to_tv_genres(list(excluded)))
        cands: list[Candidate] = []
        for c in raw:
            if c.key in seen or c.tmdb_id in excluded_ids:
                continue
            if blocked_genres.intersection(c.genre_ids):
                continue
            seen.add(c.key)
            c.score = score_candidate(c, req, set(mood_genres) | set(to_tv_genres(mood_genres)))
            cands.append(c)
        cands.sort(key=lambda c: c.score, reverse=True)
        await _emit(progress, "pool", f"Found {len(cands)} options — checking runtimes and where to watch")

        top = cands[: POOL_SIZE + 8]
        sem = asyncio.Semaphore(ENRICH_CONCURRENCY)

        async def enrich(c: Candidate):
            async with sem:
                try:
                    c.enrich_from_details(await self._content.details(c.media_type, c.tmdb_id), req.region)
                except Exception as e:  # noqa: BLE001
                    logger.warning("enrich failed for %s: %s", c.key, e)

        await asyncio.gather(*(enrich(c) for c in top))

        final = [c for c in top if c.poster_path and c.runtime]
        if req.kids:
            final = [c for c in final if c.is_kids_safe()]
        max_rt = mood_cfg["max_runtime_per_pick"]
        final = [c for c in final if (c.runtime or 0) <= max(max_rt, 100) + 30]
        final = final[:POOL_SIZE]

        pool = CandidatePool(request=req, candidates=final, outside_services=outside)
        self._cache.set(req.signature(), pool)
        await _emit(progress, "pool", f"Shortlisted {len(final)} titles")
        return pool

    async def _discover(
        self, req: PoolRequest, genres: list[int], excluded: set[int], max_runtime: int, with_providers: bool
    ) -> list[Candidate]:
        base: dict = {"watch_region": req.region, "sort_by": "popularity.desc"}
        if with_providers and req.provider_ids:
            base["with_watch_providers"] = "|".join(str(p) for p in req.provider_ids)
            base["with_watch_monetization_types"] = "flatrate|free|ads"
        floor = 60 if req.kids else 200

        movie = {
            **base,
            "with_genres": "|".join(str(g) for g in genres),
            "without_genres": ",".join(str(g) for g in sorted(excluded)),
            "vote_count.gte": floor,
            "vote_average.gte": 6.2,
            "with_runtime.gte": 20,
            "with_runtime.lte": max(max_runtime, 100) + 20,
        }
        if req.kids:
            movie["certification_country"] = "US"
            movie["certification.lte"] = "PG"
        tv_genres = to_tv_genres(genres)
        tv_excluded = to_tv_genres(list(excluded))
        tv = {
            **base,
            "with_genres": "|".join(str(g) for g in tv_genres) or "35",
            "without_genres": ",".join(str(g) for g in tv_excluded),
            "vote_count.gte": max(40, floor // 3),
            "vote_average.gte": 7.0,
            "with_runtime.lte": 65,
        }
        if req.kids:
            tv["with_genres"] = "10762|10751|16"

        jobs = [
            self._content.discover("movie", {**movie, "page": 1}),
            self._content.discover("movie", {**movie, "page": 2}),
            self._content.discover("movie", {**movie, "sort_by": "vote_average.desc", "vote_count.gte": floor * 3, "page": 1}),
            self._content.discover("tv", {**tv, "page": 1}),
        ]
        results = await asyncio.gather(*jobs, return_exceptions=True)
        out: list[Candidate] = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.warning("discover job %d failed: %s", i, res)
                continue
            mt = "tv" if i == 3 else "movie"
            for item in res:
                c = Candidate.from_tmdb_list_item(item, mt)
                if c:
                    out.append(c)
        return out


async def _emit(progress: ProgressFn | None, stage: str, message: str) -> None:
    if progress is None:
        return
    r = progress(stage, message)
    if asyncio.iscoroutine(r):
        await r
