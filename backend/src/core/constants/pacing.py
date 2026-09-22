"""Pacing rules and arc role definitions."""

from src.core.domain.session_plan import ArcRole

ARC_ROLE_DEFINITIONS = {
    ArcRole.OPENER: {
        "description": "Low-effort entry point to ease into the session",
        "typical_runtime_range": (15, 35),
        "energy_level": "low",
        "position": "first",
    },
    ArcRole.MAIN_EVENT: {
        "description": "The centrepiece — the most engaging or demanding title",
        "typical_runtime_range": (40, 150),
        "energy_level": "high",
        "position": "middle",
    },
    ArcRole.BRIDGE: {
        "description": "Transition between tones — palate cleanser",
        "typical_runtime_range": (15, 30),
        "energy_level": "medium",
        "position": "middle",
    },
    ArcRole.NIGHTCAP: {
        "description": "Wind-down closer — calming, familiar, or light",
        "typical_runtime_range": (15, 45),
        "energy_level": "low",
        "position": "last",
    },
}

# Arc shapes by energy direction
ARC_SHAPES = {
    "declining": ["opener", "main_event", "nightcap"],
    "ascending": ["opener", "bridge", "main_event"],
    "sustaining": ["opener", "main_event", "bridge", "main_event"],
    "variable": ["opener", "main_event", "bridge", "nightcap"],
}

# Default session sizes by time budget
SESSION_SIZE_BY_BUDGET = {
    60: 2,   # 1 hour → 2 picks
    120: 3,  # 2 hours → 3 picks
    180: 4,  # 3+ hours → 4 picks
}


def get_session_size(time_budget_minutes: int | None) -> int:
    """Determine number of picks based on time budget."""
    if time_budget_minutes is None:
        return 3  # default
    for threshold, size in sorted(SESSION_SIZE_BY_BUDGET.items()):
        if time_budget_minutes <= threshold:
            return size
    return 4
