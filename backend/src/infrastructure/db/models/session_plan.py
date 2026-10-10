from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base
from src.infrastructure.db.mixins import SoftDeleteMixin
from src.infrastructure.db.types import JSONType


class SessionPlan(SoftDeleteMixin, Base):
    __tablename__ = "session_plans"

    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    mood: Mapped[str] = mapped_column(String(20), nullable=False)
    energy_trajectory: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_budget_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plan_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="generated")
    # Free-form planning context: arc points, local time, notes, pool ids, room code...
    context: Mapped[dict] = mapped_column(JSONType, default=dict, server_default="{}")

    device = relationship("Device", back_populates="session_plans")
    picks = relationship(
        "SessionPick",
        back_populates="session_plan",
        order_by="SessionPick.position",
        lazy="selectin",
        primaryjoin="and_(SessionPlan.id == SessionPick.session_plan_id, SessionPick.deleted_at.is_(None))",
        viewonly=True,
    )
    feedback = relationship("SessionFeedback", back_populates="session_plan", uselist=False, lazy="selectin")

    def __repr__(self) -> str:
        return f"<SessionPlan {self.id} mood={self.mood}>"


class SessionPick(SoftDeleteMixin, Base):
    __tablename__ = "session_picks"

    session_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("session_plans.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String(10), default="movie", server_default="movie")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    backdrop_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    runtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    episodes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    certification: Mapped[str | None] = mapped_column(String(16), nullable=True)
    genre_ids: Mapped[list] = mapped_column(JSONType, default=list, server_default="[]")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    streaming_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_logo_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    deep_link_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    session_plan = relationship("SessionPlan")
    feedback = relationship("PickFeedback", back_populates="session_pick", uselist=False, lazy="selectin")

    def __repr__(self) -> str:
        return f"<SessionPick {self.position}: {self.title}>"
