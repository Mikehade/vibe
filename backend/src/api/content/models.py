"""Pydantic schemas for content endpoints."""

from pydantic import BaseModel


class ContentSearchResponse(BaseModel):
    results: list[dict]
    page: int = 1
    total_results: int = 0


class ContentDetailResponse(BaseModel):
    id: int | None = None
    title: str = ""
    overview: str = ""
    poster_path: str | None = None
    backdrop_path: str | None = None
    genre_ids: list[int] = []
    runtime: int | None = None
    vote_average: float = 0.0
    release_date: str | None = None
    streaming_providers: list[dict] = []


class ProviderResponse(BaseModel):
    providers: list[dict] = []
    tmdb_id: int
