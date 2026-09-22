"""Shared test fixtures."""

import pytest
import sys
import os

# Ensure backend root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_taste_profile():
    return {
        "genre_weights": {"action": 0.8, "comedy": 0.6, "horror": 0.2},
        "disliked_genres": ["horror"],
        "pacing_preference": "balanced",
    }


@pytest.fixture
def sample_plan_data():
    return {
        "mood": "chill",
        "time_budget_minutes": 120,
        "energy_trajectory": "low-to-medium",
    }


@pytest.fixture
def sample_pick_data():
    return {
        "position": 1,
        "role": "opener",
        "tmdb_id": 550,
        "title": "Fight Club",
        "runtime_minutes": 139,
        "reason": "A genre-bending thriller that starts slow and builds.",
        "confidence": 0.85,
        "poster_path": "/pB8BM7pdSp6B6Ih7QI4S2t0POoO.jpg",
        "genre_ids": [18, 53],
        "streaming_provider": "Netflix",
        "deep_link_url": None,
    }
