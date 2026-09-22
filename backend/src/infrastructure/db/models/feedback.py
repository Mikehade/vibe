from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class SessionFeedback(Base):
    __tablename__ = "session_feedback"

    session_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("session_plans.id"), unique=True, nullable=False
    )
    overall_rating: Mapped[str] = mapped_column(String(20), nullable=False)  # thumbs_up / thumbs_down
    pacing_rating: Mapped[str | None] = mapped_column(String(20), nullable=True)  # too_slow / just_right / too_fast
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    session_plan = relationship("SessionPlan", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<SessionFeedback plan={self.session_plan_id} rating={self.overall_rating}>"


class PickFeedback(Base):
    __tablename__ = "pick_feedback"

    session_pick_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("session_picks.id"), unique=True, nullable=False
    )
    rating: Mapped[str] = mapped_column(String(20), nullable=False)  # thumbs_up / thumbs_down

    # Relationships
    session_pick = relationship("SessionPick", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<PickFeedback pick={self.session_pick_id} rating={self.rating}>"


class MoodHistory(Base):
    __tablename__ = "mood_history"

    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    mood: Mapped[str] = mapped_column(String(20), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday
    hour_of_day: Mapped[int] = mapped_column(Integer, nullable=False)
    session_plan_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("session_plans.id"), nullable=True
    )

    # Relationships
    device = relationship("Device", back_populates="mood_history")

    def __repr__(self) -> str:
        return f"<MoodHistory device={self.device_id} mood={self.mood}>"


class WatchHistory(Base):
    __tablename__ = "watch_history"

    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    episodes_watched: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_episodes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    completion_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    device = relationship("Device", back_populates="watch_history")

    def __repr__(self) -> str:
        return f"<WatchHistory device={self.device_id} title={self.title}>"
