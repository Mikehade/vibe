"""Unit tests for Pydantic API schemas — validation rules."""

import pytest
from pydantic import ValidationError

from src.api.session.models import GeneratePlanRequest, UpdatePickStatusRequest
from src.api.mood.models import ParseMoodRequest
from src.api.profile.models import OnboardingRequest, GenrePreference
from src.api.feedback.models import SessionFeedbackRequest, PickFeedbackRequest


class TestGeneratePlanRequest:
    def test_valid_minimal(self):
        req = GeneratePlanRequest(mood="chill")
        assert req.mood == "chill"
        assert req.time_budget_minutes is None

    def test_valid_full(self):
        req = GeneratePlanRequest(mood="excited", time_budget_minutes=120, voice_transcript="feeling pumped")
        assert req.time_budget_minutes == 120

    def test_time_budget_too_low(self):
        with pytest.raises(ValidationError):
            GeneratePlanRequest(mood="chill", time_budget_minutes=10)

    def test_time_budget_too_high(self):
        with pytest.raises(ValidationError):
            GeneratePlanRequest(mood="chill", time_budget_minutes=500)

    def test_mood_required(self):
        with pytest.raises(ValidationError):
            GeneratePlanRequest()


class TestParseMoodRequest:
    def test_valid(self):
        req = ParseMoodRequest(transcript="I'm feeling lazy tonight")
        assert len(req.transcript) > 0

    def test_empty_transcript(self):
        with pytest.raises(ValidationError):
            ParseMoodRequest(transcript="")


class TestOnboardingRequest:
    def test_valid(self):
        req = OnboardingRequest(
            genre_preferences=[GenrePreference(genre="action", action="like")],
            streaming_services=["netflix"],
        )
        assert len(req.genre_preferences) == 1

    def test_empty_defaults(self):
        req = OnboardingRequest()
        assert req.genre_preferences == []
        assert req.streaming_services == []


class TestFeedbackSchemas:
    def test_session_feedback(self):
        req = SessionFeedbackRequest(overall_rating="thumbs_up", pacing_rating="balanced")
        assert req.overall_rating == "thumbs_up"

    def test_pick_feedback(self):
        req = PickFeedbackRequest(rating="thumbs_down")
        assert req.rating == "thumbs_down"

    def test_session_feedback_required(self):
        with pytest.raises(ValidationError):
            SessionFeedbackRequest()

    def test_pick_feedback_required(self):
        with pytest.raises(ValidationError):
            PickFeedbackRequest()
