"""Profile service — manages taste profiles and onboarding."""

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.domain.interfaces import IDeviceRepository, ITasteProfileRepository
from utils.logger import get_logger

logger = get_logger(__name__)


class ProfileService:
    def __init__(
        self,
        taste_profile_repository: ITasteProfileRepository,
        device_repository: IDeviceRepository,
        session_factory: async_sessionmaker,
    ):
        self._profile_repo = taste_profile_repository
        self._device_repo = device_repository
        self._session_factory = session_factory

    async def get_profile(self, device_id: str) -> dict:
        async with self._session_factory() as session:
            device = await self._device_repo.get_by_device_id(session, device_id)
            if not device:
                return {"onboarding_completed": False}

            profile = await self._profile_repo.get_by_device_id(session, device.id)
            if not profile:
                return {"device_id": device_id, "onboarding_completed": False}

            return {
                "id": profile.id,
                "device_id": device_id,
                "genre_weights": profile.genre_weights or {},
                "pacing_preference": profile.pacing_preference,
                "disliked_genres": profile.disliked_genres or [],
                "preferred_providers": profile.preferred_providers or [],
                "avg_session_length_minutes": profile.avg_session_length_minutes,
                "onboarding_completed": profile.onboarding_completed,
            }

    async def save_onboarding(self, device_id: str, data: dict) -> dict:
        async with self._session_factory() as session:
            device = await self._device_repo.upsert(session, device_id)
            existing = await self._profile_repo.get_by_device_id(session, device.id)

            genre_weights = {}
            for genre_pref in data.get("genre_preferences", []):
                genre = genre_pref.get("genre", "")
                action = genre_pref.get("action", "skip")
                if action == "like":
                    genre_weights[genre] = 0.8
                elif action == "dislike":
                    genre_weights[genre] = 0.1
                else:
                    genre_weights[genre] = 0.5

            disliked = [g for g, w in genre_weights.items() if w < 0.3]

            if existing:
                profile = await self._profile_repo.update(
                    session,
                    existing.id,
                    genre_weights=genre_weights,
                    disliked_genres=disliked,
                    preferred_providers=data.get("streaming_services", []),
                    onboarding_completed=True,
                )
            else:
                profile = await self._profile_repo.create(
                    session,
                    device_id=device.id,
                    genre_weights=genre_weights,
                    disliked_genres=disliked,
                    preferred_providers=data.get("streaming_services", []),
                    onboarding_completed=True,
                )

            await session.commit()
            return {"id": profile.id, "onboarding_completed": True}

    async def get_mood_history(self, device_id: str, limit: int = 50) -> list[dict]:
        # This will be populated from feedback repository
        return []
