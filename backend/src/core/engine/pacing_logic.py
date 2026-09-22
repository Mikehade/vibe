"""Pacing logic — assigns arc roles and validates session structure."""

from src.core.constants.pacing import ARC_SHAPES, ARC_ROLE_DEFINITIONS
from src.core.domain.session_plan import ArcRole


def assign_roles(num_picks: int, arc_shape: str) -> list[ArcRole]:
    """Determine the sequence of arc roles for a given session size and shape."""
    shape_roles = ARC_SHAPES.get(arc_shape, ARC_SHAPES["variable"])

    if num_picks <= len(shape_roles):
        roles = shape_roles[:num_picks]
    else:
        roles = shape_roles + ["bridge"] * (num_picks - len(shape_roles))

    return [ArcRole(r) for r in roles]


def validate_pacing(picks: list[dict]) -> list[str]:
    """Validate a session plan's pacing. Returns list of issues (empty = valid)."""
    issues = []

    if not picks:
        issues.append("Empty session plan")
        return issues

    # First pick should be opener
    if picks[0].get("role") != "opener":
        issues.append("First pick should be an opener")

    # Check runtime ranges
    for pick in picks:
        role = pick.get("role")
        runtime = pick.get("runtime_minutes", 0)
        if role in ARC_ROLE_DEFINITIONS:
            low, high = ARC_ROLE_DEFINITIONS[ArcRole(role)]["typical_runtime_range"]
            if runtime < low * 0.5 or runtime > high * 1.5:
                issues.append(f"Pick {pick.get('position')}: runtime {runtime}min unusual for {role}")

    # Check for adjacent genre repetition
    for i in range(len(picks) - 1):
        genres_a = set(picks[i].get("genre_ids", []))
        genres_b = set(picks[i + 1].get("genre_ids", []))
        if genres_a and genres_b and genres_a == genres_b:
            issues.append(f"Picks {picks[i].get('position')} and {picks[i+1].get('position')} share all genres")

    return issues
