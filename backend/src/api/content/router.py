"""Content endpoints — streaming providers per region, title details, search, demo artwork."""

import hashlib
from html import escape

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from src.config.dependency_injection.container import Container
from src.infrastructure.services.content import ContentService

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/providers")
@inject
async def providers(
    region: str = Query("US", min_length=2, max_length=4),
    content_service: ContentService = Depends(Provide[Container.content_service]),
):
    """Top streaming services in a region (for onboarding)."""
    return {"region": region.upper(), "providers": await content_service.providers(region)}


@router.get("/search")
@inject
async def search(
    q: str = Query(..., min_length=1, max_length=120),
    content_service: ContentService = Depends(Provide[Container.content_service]),
):
    return {"results": await content_service.search(q)}


@router.get("/title/{media_type}/{tmdb_id}")
@inject
async def title(
    media_type: str,
    tmdb_id: int,
    region: str | None = Query(None, max_length=4),
    content_service: ContentService = Depends(Provide[Container.content_service]),
):
    if media_type not in ("movie", "tv"):
        raise HTTPException(400, "media_type must be movie or tv")
    data = await content_service.title(media_type, tmdb_id, region)
    if not data:
        raise HTTPException(404, "Title not found")
    return data


_PALETTES = [
    ("#1d2b53", "#7e2553", "#ffccaa"), ("#0b3d2e", "#2e8b57", "#f5e6c8"), ("#3b1e54", "#9b3675", "#f7d6e0"),
    ("#10202b", "#1f6f8b", "#e8f1f2"), ("#2b1a0f", "#b3541e", "#f9e0b0"), ("#1a1a2e", "#4f3b78", "#e0d8ff"),
]


@router.get("/art/{kind}/{tmdb_id}.svg")
async def demo_art(kind: str, tmdb_id: int):
    """Generated artwork for FAKE_SERVICES mode (no copyrighted posters needed for offline demos)."""
    from src.infrastructure.fakes.catalog import TITLES

    t = next((t for t in TITLES if t[0] == tmdb_id), None)
    title = escape(t[2]) if t else "Untitled"
    year = t[3] if t else ""
    h = int(hashlib.md5(str(tmdb_id).encode()).hexdigest(), 16)
    a, b, fg = _PALETTES[h % len(_PALETTES)]
    if kind == "backdrop":
        w, hgt = 1280, 720
        text = f'<text x="80" y="620" font-family="Georgia,serif" font-size="72" fill="{fg}" opacity="0.18">{title}</text>'
    else:
        w, hgt = 500, 750
        words = title.split(" ")
        lines, cur = [], ""
        for word in words:
            if len(cur) + len(word) > 12 and cur:
                lines.append(cur)
                cur = word
            else:
                cur = (cur + " " + word).strip()
        lines.append(cur)
        text = "".join(
            f'<text x="40" y="{520 + i * 58}" font-family="Georgia,serif" font-size="52" fill="{fg}">{ln}</text>'
            for i, ln in enumerate(lines[:3])
        ) + f'<text x="40" y="700" font-family="Helvetica,Arial" font-size="24" letter-spacing="6" fill="{fg}" opacity="0.7">{year}</text>'
    cx, cy = (h >> 8) % w, (h >> 16) % hgt
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{hgt}" viewBox="0 0 {w} {hgt}">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>
<radialGradient id="r" cx="{cx}" cy="{cy}" r="{w * 0.7}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{fg}" stop-opacity="0.35"/><stop offset="1" stop-color="{fg}" stop-opacity="0"/></radialGradient></defs>
<rect width="{w}" height="{hgt}" fill="url(#g)"/><rect width="{w}" height="{hgt}" fill="url(#r)"/>
<circle cx="{w * 0.72}" cy="{hgt * 0.3}" r="{w * 0.18}" fill="none" stroke="{fg}" stroke-opacity="0.25" stroke-width="2"/>
{text}</svg>"""
    return Response(content=svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})
