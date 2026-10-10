from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base
from src.infrastructure.db.mixins import SoftDeleteMixin
from src.infrastructure.db.types import JSONType


class TasteProfile(SoftDeleteMixin, Base):
    """One viewer in a household. A device (TV) can hold several profiles."""

    __tablename__ = "taste_profiles"

    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(60), default="Me", server_default="Me")
    is_kids: Mapped[bool] = mapped_column(default=False, server_default="false")
    region: Mapped[str] = mapped_column(String(4), default="US", server_default="US")
    genre_weights: Mapped[dict] = mapped_column(JSONType, default=dict, server_default="{}")
    pacing_preference: Mapped[str] = mapped_column(String(20), default="balanced")
    disliked_genres: Mapped[list] = mapped_column(JSONType, default=list, server_default="[]")
    excluded_tmdb_ids: Mapped[list] = mapped_column(JSONType, default=list, server_default="[]")
    avg_session_length_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # List of {"id": int, "name": str, "logo_path": str | None}
    preferred_providers: Mapped[list] = mapped_column(JSONType, default=list, server_default="[]")
    onboarding_completed: Mapped[bool] = mapped_column(default=False)

    device = relationship("Device", back_populates="taste_profiles")

    def __repr__(self) -> str:
        return f"<TasteProfile {self.name} device={self.device_id}>"
