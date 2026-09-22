"""Domain entities for session plans — plain dataclasses, no ORM coupling."""

from dataclasses import dataclass, field
from enum import Enum


class Mood(str, Enum):
    TIRED = "tired"
    ENERGISED = "energised"
    STRESSED = "stressed"
    SOCIAL = "social"
    BORED = "bored"
    ADVENTUROUS = "adventurous"


class ArcRole(str, Enum):
    OPENER = "opener"
    MAIN_EVENT = "main_event"
    BRIDGE = "bridge"
    NIGHTCAP = "nightcap"


class PlanStatus(str, Enum):
    GENERATED = "generated"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class PickStatus(str, Enum):
    PENDING = "pending"
    WATCHING = "watching"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class EnergyTrajectory:
    description: str
    arc_shape: str  # e.g. "light-heavy-light"


@dataclass
class SessionPickEntity:
    position: int
    role: ArcRole
    tmdb_id: int
    title: str
    runtime_minutes: int
    reason: str
    confidence: float = 0.0
    poster_path: str | None = None
    genre_ids: list[int] = field(default_factory=list)
    streaming_provider: str | None = None
    deep_link_url: str | None = None
    status: PickStatus = PickStatus.PENDING


@dataclass
class SessionPlanEntity:
    mood: Mood
    energy_trajectory: EnergyTrajectory | None = None
    picks: list[SessionPickEntity] = field(default_factory=list)
    total_runtime_minutes: int = 0
    plan_summary: str = ""
    time_budget_minutes: int | None = None
    status: PlanStatus = PlanStatus.GENERATED
