from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base
from src.infrastructure.db.mixins import SoftDeleteMixin


class TasteProfile(SoftDeleteMixin, Base):
    __tablename__ = "taste_profiles"

    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    genre_weights: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    pacing_preference: Mapped[str] = mapped_column(String(20), default="balanced")  # ease_in / start_heavy / balanced
    disliked_genres: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    avg_session_length_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_providers: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    onboarding_completed: Mapped[bool] = mapped_column(default=False)

    # Relationships
    device = relationship("Device", back_populates="taste_profiles")

    def __repr__(self) -> str:
        return f"<TasteProfile device={self.device_id}>"
