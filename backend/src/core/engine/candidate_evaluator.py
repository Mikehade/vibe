"""Candidate evaluation helpers — pre-filtering before Bedrock sees them."""

from src.core.constants.moods import MOOD_GENRE_MAP, get_excluded_genre_ids_for_mood
from src.core.domain.session_plan import Mood


def pre_filter_candidates(
    candidates: list[dict],
    mood: Mood,
    disliked_genres: list[int] | None = None,
    watched_ids: list[int] | None = None,
) -> list[dict]:
    """Filter TMDB candidates before sending to Bedrock for evaluation."""
    excluded = set(get_excluded_genre_ids_for_mood(mood))
    if disliked_genres:
        excluded.update(disliked_genres)

    watched = set(watched_ids or [])
    max_runtime = MOOD_GENRE_MAP[mood]["max_runtime_per_pick"]
    filtered = []

    for c in candidates:
        tmdb_id = c.get("id", 0)
        if tmdb_id in watched:
            continue

        genre_ids = set(c.get("genre_ids", []))
        if genre_ids & excluded:
            continue

        runtime = c.get("runtime", 0) or c.get("episode_run_time", [0])[0] if c.get("episode_run_time") else 0
        if runtime and runtime > max_runtime:
            continue

        filtered.append(c)

    return filtered[:30]
