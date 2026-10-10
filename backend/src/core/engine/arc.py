"""Deterministic energy arc — computed instantly, before any model call.

The arc gives every slot a role, an energy level (0–1, used for the on-screen curve)
and a runtime target, so the screen has structure within milliseconds and the model
only has to fill slots, not invent the shape.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from src.core.constants.moods import MOOD_GENRE_MAP
from src.core.domain.session_plan import Mood

ROLE_LABELS = {
    "opener": "Opener",
    "main_event": "Main event",
    "bridge": "Palate cleanser",
    "nightcap": "Nightcap",
}

# role sequences and energy levels by direction and slot count
_SHAPES: dict[str, dict[int, list[tuple[str, float]]]] = {
    "declining": {
        1: [("main_event", 0.55)],
        2: [("opener", 0.45), ("main_event", 0.6)],
        3: [("opener", 0.45), ("main_event", 0.65), ("nightcap", 0.25)],
        4: [("opener", 0.45), ("main_event", 0.7), ("bridge", 0.4), ("nightcap", 0.2)],
    },
    "ascending": {
        1: [("main_event", 0.8)],
        2: [("opener", 0.4), ("main_event", 0.85)],
        3: [("opener", 0.35), ("bridge", 0.6), ("main_event", 0.9)],
        4: [("opener", 0.35), ("bridge", 0.55), ("main_event", 0.9), ("nightcap", 0.5)],
    },
    "sustaining": {
        1: [("main_event", 0.85)],
        2: [("opener", 0.65), ("main_event", 0.9)],
        3: [("opener", 0.65), ("main_event", 0.9), ("bridge", 0.7)],
        4: [("opener", 0.65), ("main_event", 0.9), ("bridge", 0.65), ("main_event", 0.85)],
    },
    "variable": {
        1: [("main_event", 0.7)],
        2: [("opener", 0.5), ("main_event", 0.8)],
        3: [("opener", 0.5), ("main_event", 0.85), ("nightcap", 0.4)],
        4: [("opener", 0.5), ("main_event", 0.85), ("bridge", 0.55), ("nightcap", 0.35)],
    },
}

# Closing runs used when re-planning the rest of a night (tail is taken)
_REPLAN_TAILS: dict[str, list[tuple[str, float]]] = {
    "declining": [("main_event", 0.6), ("bridge", 0.4), ("nightcap", 0.2)],
    "ascending": [("main_event", 0.75), ("bridge", 0.6), ("main_event", 0.9)],
    "sustaining": [("main_event", 0.85), ("bridge", 0.7), ("main_event", 0.9)],
    "variable": [("main_event", 0.8), ("bridge", 0.55), ("nightcap", 0.35)],
}

_ROLE_WEIGHT = {"opener": 0.22, "main_event": 0.55, "bridge": 0.16, "nightcap": 0.2}

SHIFTS = {
    "wind_down": "declining",
    "steady": None,
    "lift": "ascending",
}


@dataclass
class ArcSlot:
    position: int
    role: str
    label: str
    energy: float
    target_minutes: int


@dataclass
class Arc:
    direction: str
    arc_shape: str
    description: str
    budget_minutes: int
    slots: list[ArcSlot]

    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "arc_shape": self.arc_shape,
            "energy_trajectory": self.description,
            "budget_minutes": self.budget_minutes,
            "slots": [asdict(s) for s in self.slots],
        }


def slot_count(budget: int) -> int:
    if budget <= 50:
        return 1
    if budget <= 90:
        return 2
    if budget <= 170:
        return 3
    return 4


def part_of_day(dt: datetime) -> str:
    h = dt.hour
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "afternoon"
    if 17 <= h < 21:
        return "evening"
    return "late night" if (h >= 23 or h < 5) else "night"


def build_arc(
    mood: Mood,
    local_time: datetime,
    budget_minutes: int | None,
    shift: str | None = None,
    start_position: int = 1,
    max_slots: int | None = None,
) -> Arc:
    budget = budget_minutes or 150
    direction = MOOD_GENRE_MAP[mood]["energy_direction"]
    late = local_time.hour >= 22 or local_time.hour < 5
    if late and direction in ("ascending", "sustaining", "variable"):
        direction = "declining"
    if shift and SHIFTS.get(shift):
        direction = SHIFTS[shift]

    n = slot_count(budget)
    if max_slots is not None:
        n = max(1, min(n, max_slots))
    if start_position > 1:
        # Re-plan mid-evening: no new opener — take the tail of the direction's closing run.
        shape = _REPLAN_TAILS[direction][-min(n, 3):]
    else:
        shape = _SHAPES[direction][n]

    total_w = sum(_ROLE_WEIGHT[r] for r, _ in shape)
    slots = []
    for i, (role, energy) in enumerate(shape):
        target = int(round(budget * _ROLE_WEIGHT[role] / total_w / 5.0) * 5) or 10
        slots.append(ArcSlot(start_position + i, role, ROLE_LABELS[role], energy, max(10, target)))

    shape_name = {
        "declining": "light-heavy-light",
        "ascending": "ascending",
        "sustaining": "sustaining",
        "variable": "variable",
    }[direction]

    pod = part_of_day(local_time)
    phrasing = {
        "declining": f"Ease in, peak early, then land softly — a {pod} that winds down, not up.",
        "ascending": f"Start light and build — the {pod} has room for momentum.",
        "sustaining": f"Keep the energy high the whole way through this {pod}.",
        "variable": f"A warm-up, a centrepiece, then something lighter to close the {pod}.",
    }[direction]
    return Arc(direction, shape_name, phrasing, budget, slots)
