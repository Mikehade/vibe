"""Unit tests for core domain logic — no DB or network needed."""

import pytest
from src.core.domain.session_plan import Mood, ArcRole, PlanStatus, PickStatus
from src.core.domain.taste_profile import TasteProfileEntity
from src.core.constants.moods import MOOD_GENRE_MAP, get_genre_ids_for_mood, get_excluded_genre_ids_for_mood
from src.core.constants.genres import TMDB_GENRE_MAP, GENRE_NAME_TO_ID
from src.core.constants.pacing import get_session_size, ARC_ROLE_DEFINITIONS
from src.core.engine.energy_trajectory import infer_default_trajectory
from src.core.engine.pacing_logic import assign_roles, validate_pacing


class TestMoodEnum:
    def test_all_moods_in_genre_map(self):
        for mood in Mood:
            assert mood in MOOD_GENRE_MAP, f"{mood.value} missing from MOOD_GENRE_MAP"

    def test_mood_values(self):
        assert set(m.value for m in Mood) == {"tired", "energised", "stressed", "social", "bored", "adventurous"}


class TestTasteProfile:
    def test_boost_genre(self):
        profile = TasteProfileEntity(
            device_id="dev-1",
            genre_weights={"action": 0.5, "comedy": 0.3},
        )
        profile.boost_genre("action", amount=0.2)
        assert profile.genre_weights["action"] == pytest.approx(0.7)

    def test_boost_genre_max_cap(self):
        profile = TasteProfileEntity(
            device_id="dev-1",
            genre_weights={"action": 0.95},
        )
        profile.boost_genre("action", amount=0.2)
        assert profile.genre_weights["action"] == pytest.approx(1.0)

    def test_suppress_genre(self):
        profile = TasteProfileEntity(
            device_id="dev-1",
            genre_weights={"horror": 0.4},
        )
        profile.suppress_genre("horror", amount=0.2)
        assert profile.genre_weights["horror"] == pytest.approx(0.2)

    def test_suppress_genre_min_floor(self):
        profile = TasteProfileEntity(
            device_id="dev-1",
            genre_weights={"horror": 0.05},
        )
        profile.suppress_genre("horror", amount=0.2)
        assert profile.genre_weights["horror"] == pytest.approx(0.0)

    def test_get_top_genres(self):
        profile = TasteProfileEntity(
            device_id="dev-1",
            genre_weights={"action": 0.9, "comedy": 0.7, "horror": 0.1, "drama": 0.8},
        )
        top = profile.get_top_genres(n=2)
        assert top == ["action", "drama"]

    def test_boost_new_genre_starts_at_default(self):
        profile = TasteProfileEntity(device_id="dev-1")
        profile.boost_genre("western", amount=0.1)
        # Default is 0.5, boosted by 0.1 = 0.6
        assert profile.genre_weights["western"] == pytest.approx(0.6)


class TestMoodGenreMapping:
    def test_tired_excludes_horror(self):
        excluded = get_excluded_genre_ids_for_mood(Mood.TIRED)
        assert 27 in excluded  # Horror

    def test_energised_includes_action(self):
        ids = get_genre_ids_for_mood(Mood.ENERGISED)
        assert 28 in ids  # Action

    def test_stressed_excludes_thriller(self):
        excluded = get_excluded_genre_ids_for_mood(Mood.STRESSED)
        assert 53 in excluded  # Thriller

    def test_all_mood_configs_have_required_keys(self):
        for mood, config in MOOD_GENRE_MAP.items():
            assert "preferred_genres" in config
            assert "excluded_genres" in config
            assert "energy_direction" in config


class TestGenreConstants:
    def test_reverse_map_matches(self):
        for genre_id, name in TMDB_GENRE_MAP.items():
            # GENRE_NAME_TO_ID uses lowercase keys
            assert GENRE_NAME_TO_ID.get(name.lower()) == genre_id

    def test_known_genres(self):
        assert TMDB_GENRE_MAP[28] == "Action"
        assert TMDB_GENRE_MAP[35] == "Comedy"
        assert TMDB_GENRE_MAP[27] == "Horror"


class TestPacing:
    def test_session_size_short(self):
        size = get_session_size(60)
        assert size >= 1

    def test_session_size_long(self):
        size = get_session_size(240)
        assert size >= 3

    def test_session_size_default(self):
        size = get_session_size(None)
        assert size == 3

    def test_arc_role_definitions(self):
        for role in ArcRole:
            assert role in ARC_ROLE_DEFINITIONS


class TestEnergyTrajectory:
    def test_default_trajectory_for_moods(self):
        for mood in Mood:
            traj = infer_default_trajectory(mood, hour=20)
            assert isinstance(traj, dict)
            assert "energy_trajectory" in traj
            assert "arc_shape" in traj

    def test_late_night_forces_declining(self):
        traj = infer_default_trajectory(Mood.ENERGISED, hour=23)
        assert "winding down" in traj["energy_trajectory"]


class TestPacingLogic:
    def test_assign_roles_basic(self):
        roles = assign_roles(3, "ascending")
        assert len(roles) == 3
        assert roles[0] == ArcRole.OPENER

    def test_assign_roles_large_session(self):
        roles = assign_roles(6, "variable")
        assert len(roles) == 6
        assert roles[0] == ArcRole.OPENER

    def test_validate_pacing_valid(self):
        picks = [
            {"role": "opener", "runtime_minutes": 25, "position": 1},
            {"role": "main_event", "runtime_minutes": 120, "position": 2},
            {"role": "nightcap", "runtime_minutes": 30, "position": 3},
        ]
        issues = validate_pacing(picks)
        assert len(issues) == 0

    def test_validate_pacing_empty(self):
        issues = validate_pacing([])
        assert len(issues) > 0

    def test_validate_pacing_wrong_first_role(self):
        picks = [
            {"role": "main_event", "runtime_minutes": 120, "position": 1},
        ]
        issues = validate_pacing(picks)
        assert any("opener" in issue for issue in issues)
