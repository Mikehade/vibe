"""Content search and detail endpoints — wraps TMDB + JustWatch."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from src.config.dependency_injection.container import Container
from src.infrastructure.services.content import ContentService

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/search")
@inject
async def search_content(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    page: int = Query(1, ge=1, le=500),
    content_service: ContentService = Depends(Provide[Container.content_service]),
):
    """Search TMDB for movies and TV shows."""
    results = await content_service.search(q, page=page)
    return results


@router.get("/{tmdb_id}")
@inject
async def get_content_details(
    tmdb_id: int,
    content_service: ContentService = Depends(Provide[Container.content_service]),
):
    """Get detailed info for a specific title, enriched with streaming providers."""
    details = await content_service.get_details(tmdb_id)
    if not details:
        return {"error": "Title not found"}
    return details


@router.get("/{tmdb_id}/providers")
@inject
async def get_providers(
    tmdb_id: int,
    content_service: ContentService = Depends(Provide[Container.content_service]),
):
    """Get streaming providers for a title."""
    providers = await content_service.get_providers(tmdb_id)
    return providers
