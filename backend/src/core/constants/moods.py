"""Mood-to-genre mappings from the PRD."""

from src.core.domain.session_plan import Mood

# TMDB genre IDs
GENRE_IDS = {
    "action": 28,
    "adventure": 12,
    "animation": 16,
    "comedy": 35,
    "crime": 80,
    "documentary": 99,
    "drama": 18,
    "family": 10751,
    "fantasy": 14,
    "history": 36,
    "horror": 27,
    "music": 10402,
    "mystery": 9648,
    "romance": 10749,
    "science_fiction": 878,
    "thriller": 53,
    "tv_movie": 10770,
    "war": 10752,
    "western": 37,
}

MOOD_GENRE_MAP: dict[Mood, dict] = {
    Mood.TIRED: {
        "preferred_genres": ["comedy", "animation", "family", "romance"],
        "excluded_genres": ["horror", "thriller", "war"],
        "max_runtime_per_pick": 45,
        "energy_direction": "declining",
    },
    Mood.ENERGISED: {
        "preferred_genres": ["action", "adventure", "science_fiction", "thriller"],
        "excluded_genres": [],
        "max_runtime_per_pick": 150,
        "energy_direction": "sustaining",
    },
    Mood.STRESSED: {
        "preferred_genres": ["comedy", "animation", "documentary", "family"],
        "excluded_genres": ["horror", "thriller", "crime", "war"],
        "max_runtime_per_pick": 35,
        "energy_direction": "declining",
    },
    Mood.SOCIAL: {
        "preferred_genres": ["comedy", "action", "adventure", "horror", "mystery"],
        "excluded_genres": ["documentary"],
        "max_runtime_per_pick": 120,
        "energy_direction": "variable",
    },
    Mood.BORED: {
        "preferred_genres": ["thriller", "mystery", "science_fiction", "crime", "horror"],
        "excluded_genres": ["documentary", "history"],
        "max_runtime_per_pick": 120,
        "energy_direction": "ascending",
    },
    Mood.ADVENTUROUS: {
        "preferred_genres": ["science_fiction", "fantasy", "adventure", "mystery", "documentary"],
        "excluded_genres": [],
        "max_runtime_per_pick": 150,
        "energy_direction": "variable",
    },
}


def get_genre_ids_for_mood(mood: Mood) -> list[int]:
    """Convert mood's preferred genres to TMDB genre IDs."""
    mapping = MOOD_GENRE_MAP[mood]
    return [GENRE_IDS[g] for g in mapping["preferred_genres"] if g in GENRE_IDS]


def get_excluded_genre_ids_for_mood(mood: Mood) -> list[int]:
    """Convert mood's excluded genres to TMDB genre IDs."""
    mapping = MOOD_GENRE_MAP[mood]
    return [GENRE_IDS[g] for g in mapping["excluded_genres"] if g in GENRE_IDS]
