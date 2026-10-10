"""Catalog domain: a normalised title ("candidate") that the planner reasons over.

TMDB returns different shapes for movies and TV; everything downstream works on `Candidate`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from src.core.constants.genres import TMDB_GENRE_MAP, TMDB_TV_GENRE_MAP

# Movie genre id → equivalent TV genre id (TMDB uses different ids for some TV genres)
MOVIE_TO_TV_GENRE = {
    28: 10759,  # Action → Action & Adventure
    12: 10759,  # Adventure → Action & Adventure
    878: 10765,  # Sci-Fi → Sci-Fi & Fantasy
    14: 10765,  # Fantasy → Sci-Fi & Fantasy
    10752: 10768,  # War → War & Politics
    16: 16,
    35: 35,
    80: 80,
    99: 99,
    18: 18,
    10751: 10751,
    9648: 9648,
    37: 37,
}

KIDS_SAFE_MOVIE_CERTS = {"G", "PG", "U", "0", "6", "7", "TP", "All", "L", "AL"}
KIDS_BLOCKED_TV_RATINGS = {"TV-MA", "TV-14", "18", "16", "R", "NC-17", "18+", "16+", "15"}


def genre_names(genre_ids: list[int]) -> list[str]:
    names = []
    for gid in genre_ids:
        name = TMDB_GENRE_MAP.get(gid) or TMDB_TV_GENRE_MAP.get(gid)
        if name and name not in names:
            names.append(name)
    return names


def to_tv_genres(movie_genre_ids: list[int]) -> list[int]:
    out: list[int] = []
    for gid in movie_genre_ids:
        tv = MOVIE_TO_TV_GENRE.get(gid)
        if tv and tv not in out:
            out.append(tv)
    return out


@dataclass
class Provider:
    id: int
    name: str
    logo_path: str | None = None


@dataclass
class Candidate:
    tmdb_id: int
    media_type: str  # "movie" | "tv"
    title: str
    year: int | None = None
    overview: str = ""
    poster_path: str | None = None
    backdrop_path: str | None = None
    runtime: int | None = None  # movie runtime, or typical episode runtime for TV
    genre_ids: list[int] = field(default_factory=list)
    rating: float | None = None
    vote_count: int = 0
    popularity: float = 0.0
    providers: list[Provider] = field(default_factory=list)  # subscription/free providers in region
    watch_link: str | None = None
    certification: str | None = None
    seasons: int | None = None
    enriched: bool = False
    score: float = 0.0

    @property
    def key(self) -> str:
        return f"{self.media_type}:{self.tmdb_id}"

    @property
    def genres(self) -> list[str]:
        return genre_names(self.genre_ids)

    def provider_names(self) -> list[str]:
        return [p.name for p in self.providers]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["genres"] = self.genres
        return d

    # ── Builders from TMDB payloads ──────────────────────────────────────

    @classmethod
    def from_tmdb_list_item(cls, item: dict, media_type: str | None = None) -> Candidate | None:
        mt = media_type or item.get("media_type")
        if mt not in ("movie", "tv"):
            return None
        title = item.get("title") or item.get("name")
        if not title or not item.get("id"):
            return None
        date = item.get("release_date") or item.get("first_air_date") or ""
        year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
        return cls(
            tmdb_id=int(item["id"]),
            media_type=mt,
            title=title,
            year=year,
            overview=(item.get("overview") or "").strip(),
            poster_path=item.get("poster_path"),
            backdrop_path=item.get("backdrop_path"),
            genre_ids=list(item.get("genre_ids") or []),
            rating=item.get("vote_average"),
            vote_count=int(item.get("vote_count") or 0),
            popularity=float(item.get("popularity") or 0.0),
        )

    def enrich_from_details(self, details: dict, region: str) -> None:
        """Merge a TMDB details payload (with append_to_response) into this candidate."""
        if not details:
            return
        self.poster_path = details.get("poster_path") or self.poster_path
        self.backdrop_path = details.get("backdrop_path") or self.backdrop_path
        self.overview = (details.get("overview") or self.overview or "").strip()
        if details.get("genres"):
            self.genre_ids = [g["id"] for g in details["genres"] if "id" in g]
        if self.media_type == "movie":
            self.runtime = details.get("runtime") or self.runtime
            self.certification = _movie_certification(details, region)
        else:
            ep = details.get("episode_run_time") or []
            runtime = ep[0] if ep else None
            if not runtime:
                last = details.get("last_episode_to_air") or {}
                runtime = last.get("runtime")
            self.runtime = runtime or self.runtime or 30
            self.seasons = details.get("number_of_seasons")
            self.certification = _tv_rating(details, region)

        wp = (details.get("watch/providers") or {}).get("results", {}).get(region) or {}
        self.watch_link = wp.get("link")
        seen: set[int] = set()
        providers: list[Provider] = []
        for bucket in ("flatrate", "free", "ads"):
            for p in wp.get(bucket, []) or []:
                pid = p.get("provider_id")
                if pid in seen:
                    continue
                seen.add(pid)
                providers.append(Provider(id=pid, name=p.get("provider_name", ""), logo_path=p.get("logo_path")))
        self.providers = providers
        self.enriched = True

    def is_kids_safe(self) -> bool:
        if 27 in self.genre_ids or 53 in self.genre_ids:  # horror / thriller
            return False
        if self.media_type == "movie":
            if self.certification:
                return self.certification in KIDS_SAFE_MOVIE_CERTS
            return 10751 in self.genre_ids or 16 in self.genre_ids
        if self.certification and self.certification in KIDS_BLOCKED_TV_RATINGS:
            return False
        return 10762 in self.genre_ids or 10751 in self.genre_ids or 16 in self.genre_ids

    def compact_line(self) -> str:
        """One-line summary the LLM sees. Keep it short — tokens are latency."""
        overview = self.overview.replace("\n", " ")
        if len(overview) > 160:
            overview = overview[:157].rsplit(" ", 1)[0] + "..."
        runtime = f"{self.runtime}m" + ("/ep" if self.media_type == "tv" else "") if self.runtime else "?"
        rating = f"{self.rating:.1f}" if self.rating else "-"
        providers = ", ".join(self.provider_names()[:2]) or "not on your services"
        return (
            f"{self.tmdb_id} | {self.media_type} | {self.title} ({self.year or '?'}) | {runtime} | "
            f"{'/'.join(self.genres[:3])} | {rating} | {providers} | {overview}"
        )


def _movie_certification(details: dict, region: str) -> str | None:
    results = (details.get("release_dates") or {}).get("results", [])
    by_region = {r.get("iso_3166_1"): r for r in results}
    for code in (region, "US"):
        entry = by_region.get(code)
        if not entry:
            continue
        for rd in entry.get("release_dates", []):
            cert = (rd.get("certification") or "").strip()
            if cert:
                return cert
    return None


def _tv_rating(details: dict, region: str) -> str | None:
    results = (details.get("content_ratings") or {}).get("results", [])
    by_region = {r.get("iso_3166_1"): r.get("rating") for r in results}
    return by_region.get(region) or by_region.get("US") or None
