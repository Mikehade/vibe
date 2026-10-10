"""Offline stand-in for TMDB."""

import asyncio

from src.core.domain.interfaces import IContentClient
from src.infrastructure.fakes.catalog import LOGOS, TITLES


def _art(kind: str, tid: int) -> str:
    return f"/fake-art/{kind}/{tid}.svg"


def _list_item(t) -> dict:
    tid, mt, title, year, genres, runtime, rating, votes, cert, providers, overview = t
    d = {
        "id": tid,
        "media_type": mt,
        "genre_ids": genres,
        "vote_average": rating,
        "vote_count": votes,
        "popularity": votes / 50,
        "overview": overview,
        "poster_path": _art("poster", tid),
        "backdrop_path": _art("backdrop", tid),
    }
    if mt == "movie":
        d.update(title=title, release_date=f"{year}-06-01")
    else:
        d.update(name=title, first_air_date=f"{year}-06-01")
    return d


class FakeContentClient(IContentClient):
    def __init__(self, latency: float = 0.05):
        self._latency = latency
        self._by_id = {t[0]: t for t in TITLES}

    async def discover(self, media_type: str, params: dict) -> list[dict]:
        await asyncio.sleep(self._latency)
        want = {int(g) for g in str(params.get("with_genres", "")).split("|") if g.strip().isdigit()}
        without = {int(g) for g in str(params.get("without_genres", "")).split(",") if g.strip().isdigit()}
        providers = {int(p) for p in str(params.get("with_watch_providers", "")).split("|") if p.strip().isdigit()}
        page = int(params.get("page", 1))
        out = []
        for t in TITLES:
            if t[1] != media_type:
                continue
            if want and not want.intersection(t[4]):
                continue
            if without.intersection(t[4]):
                continue
            if providers and not providers.intersection(p[0] for p in t[9]):
                continue
            out.append(_list_item(t))
        if params.get("sort_by") == "vote_average.desc":
            out.sort(key=lambda d: d["vote_average"], reverse=True)
        return out[(page - 1) * 20 : page * 20]

    async def details(self, media_type: str, tmdb_id: int) -> dict:
        await asyncio.sleep(self._latency)
        t = self._by_id.get(tmdb_id)
        if not t or t[1] != media_type:
            return {}
        tid, mt, title, year, genres, runtime, rating, votes, cert, providers, overview = t
        d = _list_item(t)
        d["genres"] = [{"id": g} for g in genres]
        d["watch/providers"] = {
            "results": {
                region: {
                    "link": f"https://www.themoviedb.org/{mt}/{tid}/watch",
                    "flatrate": [{"provider_id": pid, "provider_name": name, "logo_path": LOGOS.get(pid)} for pid, name in providers],
                }
                for region in ("US", "GB", "NG", "CA", "DE", "IN")
            }
        }
        if mt == "movie":
            d["runtime"] = runtime
            d["release_dates"] = {"results": [{"iso_3166_1": "US", "release_dates": [{"certification": cert}]}]}
        else:
            d["episode_run_time"] = [runtime]
            d["number_of_seasons"] = 3
            d["content_ratings"] = {"results": [{"iso_3166_1": "US", "rating": cert}]}
        return d

    async def recommendations(self, media_type: str, tmdb_id: int) -> list[dict]:
        t = self._by_id.get(tmdb_id)
        if not t:
            return []
        g = set(t[4])
        return [_list_item(o) for o in TITLES if o[0] != tmdb_id and g.intersection(o[4])][:8]

    async def search_multi(self, query: str, page: int = 1) -> list[dict]:
        q = query.lower()
        hits = [_list_item(t) for t in TITLES if q in t[2].lower() or q in t[10].lower()]
        return hits or [_list_item(t) for t in TITLES[:5]]

    async def watch_providers(self, region: str) -> list[dict]:
        seen = {}
        for t in TITLES:
            for pid, name in t[9]:
                seen[pid] = {"id": pid, "name": name, "logo_path": LOGOS.get(pid), "priority": len(seen)}
        return list(seen.values())
