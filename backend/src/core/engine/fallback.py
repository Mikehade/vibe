"""Deterministic planner — used to fill any slot the model did not (timeout, error, bad id).

It never leaves the viewer with an empty lineup.
"""

from __future__ import annotations

from src.core.domain.catalog import Candidate
from src.core.engine.arc import ArcSlot

_ROLE_TEMPLATES = {
    "opener": "An easy {genre} start — {runtime} minutes to settle in before the main event.",
    "main_event": "The centrepiece: a {rating}-rated {genre} pick that earns your full attention.",
    "bridge": "A lighter {genre} palate cleanser to reset between bigger moments.",
    "nightcap": "A gentle {genre} closer — {runtime} minutes to land the night softly.",
}


def runtime_for(c: Candidate, slot: ArcSlot) -> tuple[int, int | None]:
    """Total minutes for a pick, and episodes if it is a series."""
    base = c.runtime or 30
    if c.media_type == "tv":
        eps = max(1, min(4, round(slot.target_minutes / max(base, 10))))
        return base * eps, eps
    return base, None


def fit_score(c: Candidate, slot: ArcSlot, previous: Candidate | None) -> float:
    total, _ = runtime_for(c, slot)
    diff = abs(total - slot.target_minutes) / max(slot.target_minutes, 20)
    score = c.score - diff * 12
    if slot.role in ("opener", "bridge", "nightcap") and c.media_type == "tv":
        score += 3
    if slot.role == "main_event" and c.media_type == "movie":
        score += 4
    if previous and set(previous.genre_ids) == set(c.genre_ids):
        score -= 6
    if slot.role == "nightcap" and {27, 53}.intersection(c.genre_ids):
        score -= 15  # nothing scary right before bed
    return score


def slot_limit(slot: ArcSlot) -> float:
    return max(slot.target_minutes * 1.8, slot.target_minutes + 40)


def choose(pool: list[Candidate], slot: ArcSlot, used: set[str], previous: Candidate | None) -> Candidate | None:
    options = [c for c in pool if c.key not in used]
    if not options:
        return None
    fitting = [c for c in options if runtime_for(c, slot)[0] <= slot_limit(slot)]
    return max(fitting or options, key=lambda c: fit_score(c, slot, previous))


def template_reason(c: Candidate, slot: ArcSlot) -> str:
    total, eps = runtime_for(c, slot)
    genre = (c.genres[0] if c.genres else "feel-good").lower()
    rating = f"{c.rating:.1f}" if c.rating else "well"
    text = _ROLE_TEMPLATES.get(slot.role, _ROLE_TEMPLATES["main_event"]).format(genre=genre, runtime=total, rating=rating)
    if eps and eps > 1:
        text = text.rstrip(".") + f" ({eps} episodes)."
    return text
