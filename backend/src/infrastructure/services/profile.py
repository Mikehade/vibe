"""Profile service — household profiles, onboarding, preferences."""

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.domain.interfaces import IDeviceRepository, ITasteProfileRepository
from utils.logger import get_logger

logger = get_logger(__name__)


def profile_to_dict(profile, device_id: str | None = None) -> dict:
    return {
        "id": profile.id,
        "device_id": device_id,
        "name": profile.name,
        "is_kids": bool(profile.is_kids),
        "region": profile.region,
        "genre_weights": profile.genre_weights or {},
        "pacing_preference": profile.pacing_preference,
        "disliked_genres": profile.disliked_genres or [],
        "preferred_providers": [p for p in (profile.preferred_providers or []) if isinstance(p, dict)],
        "avg_session_length_minutes": profile.avg_session_length_minutes,
        "onboarding_completed": bool(profile.onboarding_completed),
    }


class ProfileService:
    def __init__(
        self,
        taste_profile_repository: ITasteProfileRepository,
        device_repository: IDeviceRepository,
        session_factory: async_sessionmaker,
        default_region: str = "US",
    ):
        self._profile_repo = taste_profile_repository
        self._device_repo = device_repository
        self._session_factory = session_factory
        self._default_region = default_region

    async def get_profile(self, device_id: str, profile_id: str | None = None) -> dict:
        async with self._session_factory() as session:
            device = await self._device_repo.get_by_device_id(session, device_id)
            if not device:
                return {"onboarding_completed": False}
            profile = await self._profile_repo.get_by_device_id(session, device.id, profile_id)
            if not profile:
                return {"device_id": device_id, "onboarding_completed": False}
            return profile_to_dict(profile, device_id)

    async def list_profiles(self, device_id: str) -> list[dict]:
        async with self._session_factory() as session:
            device = await self._device_repo.get_by_device_id(session, device_id)
            if not device:
                return []
            return [profile_to_dict(p, device_id) for p in await self._profile_repo.list_by_device(session, device.id)]

    async def save_onboarding(self, device_id: str, data: dict, profile_id: str | None = None, create_new: bool = False) -> dict:
        async with self._session_factory() as session:
            device = await self._device_repo.upsert(session, device_id)
            existing = None if create_new else await self._profile_repo.get_by_device_id(session, device.id, profile_id)

            genre_weights = dict(existing.genre_weights or {}) if existing else {}
            for gp in data.get("genre_preferences", []) or []:
                genre = (gp.get("genre") or "").lower()
                action = gp.get("action", "skip")
                if not genre:
                    continue
                genre_weights[genre] = 0.85 if action == "like" else 0.1 if action == "dislike" else 0.5
            disliked = [g for g, w in genre_weights.items() if w < 0.3]

            providers = []
            for p in data.get("streaming_services", []) or []:
                if isinstance(p, dict) and p.get("id") is not None:
                    providers.append({"id": int(p["id"]), "name": p.get("name", ""), "logo_path": p.get("logo_path")})

            fields = {
                "genre_weights": genre_weights,
                "disliked_genres": disliked,
                "preferred_providers": providers,
                "onboarding_completed": True,
                "name": (data.get("name") or (existing.name if existing else "Me"))[:60],
                "is_kids": bool(data.get("is_kids", existing.is_kids if existing else False)),
                "region": (data.get("region") or (existing.region if existing else self._default_region)).upper()[:4],
            }
            if existing:
                profile = await self._profile_repo.update(session, existing.id, **fields)
            else:
                profile = await self._profile_repo.create(session, device_id=device.id, **fields)
            await session.commit()
            return profile_to_dict(profile, device_id)

    async def update_settings(self, device_id: str, profile_id: str | None, data: dict) -> dict:
        async with self._session_factory() as session:
            device = await self._device_repo.upsert(session, device_id)
            profile = await self._profile_repo.get_by_device_id(session, device.id, profile_id)
            if not profile:
                raise LookupError("profile not found")
            fields = {}
            if "name" in data and data["name"]:
                fields["name"] = str(data["name"])[:60]
            if "is_kids" in data:
                fields["is_kids"] = bool(data["is_kids"])
            if "region" in data and data["region"]:
                fields["region"] = str(data["region"]).upper()[:4]
            if "streaming_services" in data:
                fields["preferred_providers"] = [
                    {"id": int(p["id"]), "name": p.get("name", ""), "logo_path": p.get("logo_path")}
                    for p in data["streaming_services"] if isinstance(p, dict) and p.get("id") is not None
                ]
            if data.get("reset_exclusions"):
                fields["excluded_tmdb_ids"] = []
            profile = await self._profile_repo.update(session, profile.id, **fields)
            await session.commit()
            return profile_to_dict(profile, device_id)

    async def get_mood_history(self, device_id: str, limit: int = 50) -> list[dict]:
        return []
