from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base
from src.infrastructure.db.mixins import SoftDeleteMixin


class SessionPlan(SoftDeleteMixin, Base):
    __tablename__ = "session_plans"

    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    mood: Mapped[str] = mapped_column(String(20), nullable=False)
    energy_trajectory: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_budget_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plan_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="generated")  # generated / active / completed / abandoned

    # Relationships
    device = relationship("Device", back_populates="session_plans")
    picks = relationship("SessionPick", back_populates="session_plan", order_by="SessionPick.position", lazy="selectin")
    feedback = relationship("SessionFeedback", back_populates="session_plan", uselist=False, lazy="selectin")

    def __repr__(self) -> str:
        return f"<SessionPlan {self.id} mood={self.mood}>"


class SessionPick(SoftDeleteMixin, Base):
    __tablename__ = "session_picks"

    session_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("session_plans.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # opener / main_event / bridge / nightcap
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    poster_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    runtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    genre_ids: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    streaming_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deep_link_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / watching / completed / skipped

    # Relationships
    session_plan = relationship("SessionPlan", back_populates="picks")
    feedback = relationship("PickFeedback", back_populates="session_pick", uselist=False, lazy="selectin")

    def __repr__(self) -> str:
        return f"<SessionPick {self.position}: {self.title}>"
