from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base
from src.infrastructure.db.mixins import SoftDeleteMixin


class Device(SoftDeleteMixin, Base):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fire_os_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    taste_profiles = relationship("TasteProfile", back_populates="device", lazy="selectin")
    session_plans = relationship("SessionPlan", back_populates="device", lazy="selectin")
    mood_history = relationship("MoodHistory", back_populates="device", lazy="selectin")
    watch_history = relationship("WatchHistory", back_populates="device", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Device {self.device_id}>"
