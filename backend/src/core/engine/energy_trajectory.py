"""Energy trajectory inference helpers."""

from src.core.constants.moods import MOOD_GENRE_MAP
from src.core.domain.session_plan import Mood


def infer_default_trajectory(mood: Mood, hour: int) -> dict:
    """Fallback energy trajectory when Bedrock is unavailable."""
    mood_config = MOOD_GENRE_MAP[mood]
    direction = mood_config["energy_direction"]

    late_night = hour >= 22 or hour < 5
    if late_night:
        direction = "declining"

    shape_map = {
        "declining": "light-heavy-light",
        "ascending": "light-heavy-heavy",
        "sustaining": "heavy-heavy-heavy",
        "variable": "light-heavy-light",
    }

    return {
        "energy_trajectory": f"Energy is {direction} — {'winding down' if direction == 'declining' else 'building up'}",
        "arc_shape": shape_map.get(direction, "light-heavy-light"),
    }
