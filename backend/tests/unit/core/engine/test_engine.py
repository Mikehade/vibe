"""Engine unit tests: arc, line protocol, pool, fallback, and the full streaming planner (with fakes)."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from src.core.domain.catalog import Candidate
from src.core.domain.session_plan import Mood
from src.core.engine import fallback
from src.core.engine.arc import build_arc, slot_count
from src.core.engine.candidate_pool import CandidatePoolBuilder, PoolRequest
from src.core.engine.session_architect import PlanRequest, SessionArchitect
from src.core.engine.stream_parser import LineProtocolParser, parse_line
from src.infrastructure.fakes.content import FakeContentClient
from src.infrastructure.fakes.llm import FakeLanguageModel

LAGOS = timezone(timedelta(hours=1))


class TestArc:
    def test_slot_count_scales_with_budget(self):
        assert slot_count(45) == 1
        assert slot_count(90) == 2
        assert slot_count(150) == 3
        assert slot_count(240) == 4

    def test_late_night_forces_wind_down(self):
        arc = build_arc(Mood.ENERGISED, datetime(2026, 9, 27, 23, 30, tzinfo=LAGOS), 150)
        assert arc.direction == "declining"
        assert arc.slots[-1].role == "nightcap"

    def test_first_slot_is_opener_and_targets_fill_budget(self):
        arc = build_arc(Mood.TIRED, datetime(2026, 9, 27, 20, 0, tzinfo=LAGOS), 150)
        assert arc.slots[0].role == "opener"
        assert 120 <= sum(s.target_minutes for s in arc.slots) <= 180

    def test_shift_lift_ascends(self):
        arc = build_arc(Mood.TIRED, datetime(2026, 9, 27, 20, 0, tzinfo=LAGOS), 120, shift="lift", start_position=2)
        assert arc.direction == "ascending"
        assert arc.slots[0].position == 2


class TestLineProtocol:
    def test_parses_across_chunk_boundaries(self):
        p = LineProtocolParser()
        out = p.feed('TRAJECTORY {"energy_trajectory": "x"}\nPICK {"slot": 1, "tmd')
        assert out == [("TRAJECTORY", {"energy_trajectory": "x"})]
        out = p.feed('b_id": 5}\nSUMMARY {"plan_summary": "y"}')
        assert out == [("PICK", {"slot": 1, "tmdb_id": 5})]
        assert p.flush() == [("SUMMARY", {"plan_summary": "y"})]

    def test_tolerates_markdown_noise(self):
        assert parse_line('- **PICK** {"slot": 2, "tmdb_id": 9}') == ("PICK", {"slot": 2, "tmdb_id": 9})
        assert parse_line("Here is your plan:") is None
        assert parse_line("PICK {not json}") is None


@pytest.fixture
def builder():
    return CandidatePoolBuilder(FakeContentClient(latency=0))


class TestPool:
    async def test_pool_respects_providers_and_posters(self, builder):
        pool = await builder.get(PoolRequest(mood=Mood.SOCIAL, region="US", provider_ids=[8], provider_names=["Netflix"]))
        assert pool.candidates
        assert all(c.poster_path and c.runtime for c in pool.candidates)
        assert all(8 in [p.id for p in c.providers] for c in pool.candidates) or pool.outside_services

    async def test_kids_pool_is_safe(self, builder):
        pool = await builder.get(PoolRequest(mood=Mood.ADVENTUROUS, region="US", kids=True))
        assert pool.candidates
        assert all(c.is_kids_safe() for c in pool.candidates)
        assert "Get Out" not in [c.title for c in pool.candidates]

    async def test_excluded_ids_and_disliked_genres(self, builder):
        pool = await builder.get(PoolRequest(mood=Mood.SOCIAL, excluded_ids=[9101], disliked_genres=["horror"]))
        titles = [c.title for c in pool.candidates]
        assert "Ted Lasso" not in titles
        assert "Get Out" not in titles

    async def test_prefetch_is_reused(self, builder):
        req = PoolRequest(mood=Mood.BORED)
        builder.prefetch(req)
        msgs = []
        pool = await builder.get(req, lambda s, m: msgs.append(m))
        assert pool.candidates
        assert msgs and ("started" in msgs[0] or "prepared" in msgs[0])


class TestFallback:
    def test_never_repeats_and_prefers_fit(self):
        c1 = Candidate(1, "movie", "Long", runtime=150, score=30)
        c2 = Candidate(2, "movie", "Right", runtime=95, score=28)
        arc = build_arc(Mood.TIRED, datetime(2026, 9, 27, 20, 0, tzinfo=LAGOS), 150)
        main = next(s for s in arc.slots if s.role == "main_event")
        assert fallback.choose([c1, c2], main, set(), None).title == "Right"
        assert fallback.choose([c1, c2], main, {c2.key}, None).title == "Long"


async def _collect(architect, req):
    return [ev async for ev in architect.generate(req)]


class TestArchitect:
    async def test_streams_full_plan_in_order(self, builder):
        arch = SessionArchitect(FakeLanguageModel(delay=0.01), FakeContentClient(0), builder, timeout_seconds=10)
        req = PlanRequest(
            mood=Mood.TIRED, local_time=datetime(2026, 9, 27, 21, 0, tzinfo=LAGOS), budget_minutes=150,
            pool_request=PoolRequest(mood=Mood.TIRED),
        )
        events = await _collect(arch, req)
        types = [e["type"] for e in events]
        assert types[0] == "status" and types[1] == "trajectory"
        assert "candidates" in types and types[-1] == "summary"
        picks = [e["data"] for e in events if e["type"] == "pick"]
        assert [p["position"] for p in picks] == [1, 2, 3]
        assert all(p["poster_path"] and p["runtime_minutes"] > 0 for p in picks)
        assert len({p["tmdb_id"] for p in picks}) == 3

    async def test_timeout_falls_back_but_completes(self, builder):
        class SlowLLM(FakeLanguageModel):
            async def stream_turn(self, *a, **k):
                await asyncio.sleep(5)
                yield {"type": "stop", "reason": "end_turn", "message": {"role": "assistant", "content": []}}

        arch = SessionArchitect(SlowLLM(), FakeContentClient(0), builder, timeout_seconds=1)
        req = PlanRequest(
            mood=Mood.SOCIAL, local_time=datetime(2026, 9, 27, 20, 0, tzinfo=LAGOS), budget_minutes=120,
            pool_request=PoolRequest(mood=Mood.SOCIAL),
        )
        events = await _collect(arch, req)
        picks = [e["data"] for e in events if e["type"] == "pick"]
        assert len(picks) == 3 and all(p["source"] == "fallback" for p in picks)
        assert any(e["type"] == "status" and e["data"]["stage"] == "fallback" for e in events)

    async def test_rejects_hallucinated_ids(self, builder):
        class LyingLLM(FakeLanguageModel):
            async def stream_turn(self, *a, **k):
                text = 'PICK {"slot": 1, "tmdb_id": 424242, "media_type": "movie", "reason": "made up"}\n'
                yield {"type": "text", "text": text}
                yield {"type": "stop", "reason": "end_turn", "message": {"role": "assistant", "content": [{"text": text}]}}

        arch = SessionArchitect(LyingLLM(), FakeContentClient(0), builder, timeout_seconds=5)
        req = PlanRequest(
            mood=Mood.BORED, local_time=datetime(2026, 9, 27, 20, 0, tzinfo=LAGOS), budget_minutes=90,
            pool_request=PoolRequest(mood=Mood.BORED),
        )
        picks = [e["data"] for e in await _collect(arch, req) if e["type"] == "pick"]
        assert picks and all(p["tmdb_id"] != 424242 for p in picks)


class TestReplanArc:
    def test_wind_down_replan_ends_on_nightcap(self):
        arc = build_arc(Mood.SOCIAL, datetime(2026, 9, 27, 21, 0, tzinfo=LAGOS), 60, shift="wind_down", start_position=3, max_slots=1)
        assert [s.role for s in arc.slots] == ["nightcap"]
        assert arc.slots[0].position == 3

    def test_lift_replan_has_no_new_opener(self):
        arc = build_arc(Mood.TIRED, datetime(2026, 9, 27, 20, 0, tzinfo=LAGOS), 150, shift="lift", start_position=2, max_slots=2)
        assert "opener" not in [s.role for s in arc.slots]
