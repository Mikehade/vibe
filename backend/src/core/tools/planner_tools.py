"""Tools the Session Architect can call mid-plan. Bound to one request's candidate pool.

Every title a tool surfaces is added to the pool, so any pick the model makes from
tool results can be hydrated with posters, runtime and providers.
"""

from __future__ import annotations

import asyncio

from src.core.domain.catalog import Candidate
from src.core.domain.interfaces import IContentClient
from src.core.engine.candidate_pool import CandidatePool

TOOL_SPECS = [
    {
        "toolSpec": {
            "name": "search_titles",
            "description": "Search movies and series by title, person or theme. Use when the viewer mentions something specific.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "e.g. 'Paddington' or 'heist comedy'"}},
                    "required": ["query"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "more_like_this",
            "description": "Get titles similar to a given title. Use for 'something like X'.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "tmdb_id": {"type": "integer"},
                        "media_type": {"type": "string", "enum": ["movie", "tv"]},
                    },
                    "required": ["tmdb_id", "media_type"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "title_details",
            "description": "Full details for one title: runtime, certification, providers, full overview.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "tmdb_id": {"type": "integer"},
                        "media_type": {"type": "string", "enum": ["movie", "tv"]},
                    },
                    "required": ["tmdb_id", "media_type"],
                }
            },
        }
    },
]


class PlannerTools:
    def __init__(self, content: IContentClient, pool: CandidatePool):
        self._content = content
        self._pool = pool

    @staticmethod
    def describe(name: str, args: dict, pool: CandidatePool) -> str:
        """Human-readable status line for the TV while a tool runs."""
        if name == "search_titles":
            return f"Searching for “{args.get('query', '')}”"
        if name == "more_like_this":
            c = pool.find(int(args.get("tmdb_id", 0) or 0))
            return f"Finding titles like {c.title}" if c else "Finding similar titles"
        if name == "title_details":
            c = pool.find(int(args.get("tmdb_id", 0) or 0))
            return f"Checking the details on {c.title}" if c else "Checking title details"
        return "Working"

    async def execute(self, name: str, args: dict) -> dict:
        if name == "search_titles":
            items = await self._content.search_multi(str(args.get("query", ""))[:120])
            return {"results": await self._enrich_and_add([Candidate.from_tmdb_list_item(i) for i in items[:8]])}
        if name == "more_like_this":
            mt = args.get("media_type", "movie")
            items = await self._content.recommendations(mt, int(args["tmdb_id"]))
            return {"results": await self._enrich_and_add([Candidate.from_tmdb_list_item(i, mt) for i in items[:8]])}
        if name == "title_details":
            mt = args.get("media_type", "movie")
            tid = int(args["tmdb_id"])
            c = self._pool.find(tid, mt) or Candidate(tmdb_id=tid, media_type=mt, title="")
            details = await self._content.details(mt, tid)
            if not details:
                return {"error": "not found"}
            c.title = c.title or details.get("title") or details.get("name") or ""
            c.enrich_from_details(details, self._pool.request.region)
            self._pool.add(c)
            return {
                "title": c.title,
                "line": c.compact_line(),
                "overview": c.overview,
                "certification": c.certification,
                "providers": c.provider_names(),
            }
        return {"error": f"unknown tool {name}"}

    async def _enrich_and_add(self, cands: list[Candidate | None]) -> list[str]:
        cands = [c for c in cands if c]
        region = self._pool.request.region

        async def enrich(c: Candidate):
            c.enrich_from_details(await self._content.details(c.media_type, c.tmdb_id), region)

        await asyncio.gather(*(enrich(c) for c in cands), return_exceptions=True)
        lines = []
        excluded = set(self._pool.request.excluded_ids)
        for c in cands:
            if not c.poster_path or not c.runtime or c.tmdb_id in excluded:
                continue
            if self._pool.request.kids and not c.is_kids_safe():
                continue
            if c.score == 0:
                c.score = 20.0
            self._pool.add(c)
            lines.append(c.compact_line())
        return lines
