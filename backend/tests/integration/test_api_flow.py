"""End-to-end API flow with FAKE_SERVICES + SQLite (no keys, no Postgres needed)."""

import json
import os
import tempfile

import pytest

os.environ["FAKE_SERVICES"] = "true"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/test.db"

from fastapi.testclient import TestClient  # noqa: E402

from src.config.base import get_settings  # noqa: E402

get_settings.cache_clear()
import main  # noqa: E402

TV = {"X-Device-ID": "tv-int-1"}


@pytest.fixture(scope="module")
def client():
    with TestClient(main.create_app()) as c:
        yield c


def _events(resp):
    return [json.loads(line) for line in resp.text.splitlines() if line.strip()]


def test_health(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_device_header_required(client):
    assert client.get("/api/v1/profile").status_code == 400


def test_onboarding_plan_swap_replan(client):
    r = client.patch("/api/v1/profile/onboarding", headers=TV, json={
        "name": "Seun", "region": "NG",
        "genre_preferences": [{"genre": "comedy", "action": "like"}],
        "streaming_services": [{"id": 8, "name": "Netflix"}, {"id": 9, "name": "Prime Video"}],
    })
    assert r.status_code == 200 and r.json()["onboarding_completed"]

    assert client.post("/api/v1/session/prefetch", headers=TV, json={"mood": "tired"}).status_code == 202
    r = client.post("/api/v1/session/plan", headers=TV, json={
        "mood": "tired", "time_budget_minutes": 150, "local_time": "2026-09-27T21:10:00+01:00",
    })
    events = _events(r)
    assert events[0]["type"] == "plan" and events[-1]["type"] == "done"
    picks = [e["data"] for e in events if e["type"] == "pick"]
    assert len(picks) == 3 and all(p["id"] and p["poster_path"] for p in picks)
    plan_id = events[0]["data"]["plan_id"]

    plan = client.get(f"/api/v1/session/plan/{plan_id}", headers=TV).json()
    assert plan["status"] == "generated" and len(plan["picks"]) == 3 and plan["arc"]["slots"]

    swap = client.post(f"/api/v1/session/plan/{plan_id}/pick/{picks[1]['id']}/swap", headers=TV).json()
    assert swap["pick"]["tmdb_id"] not in {p["tmdb_id"] for p in picks}

    events = _events(client.post(f"/api/v1/session/plan/{plan_id}/replan", headers=TV, json={"after_position": 1, "shift": "wind_down"}))
    assert events[0]["type"] == "replan" and events[-1]["type"] == "done"
    plan = client.get(f"/api/v1/session/plan/{plan_id}", headers=TV).json()
    assert plan["picks"][0]["status"] == "completed"
    assert all(p["position"] > 1 for p in plan["picks"][1:])

    # someone else cannot swap
    other = client.post(f"/api/v1/session/plan/{plan_id}/pick/{plan['picks'][1]['id']}/swap", headers={"X-Device-ID": "intruder"})
    assert other.status_code == 403


def test_household_profiles(client):
    dev = {"X-Device-ID": "tv-house"}
    a = client.patch("/api/v1/profile/onboarding", headers=dev, json={"name": "Parent"}).json()
    k = client.patch("/api/v1/profile/onboarding", headers=dev, json={"name": "Kid", "is_kids": True, "new_profile": True}).json()
    assert a["id"] != k["id"]
    profiles = client.get("/api/v1/profile/all", headers=dev).json()["profiles"]
    assert {p["name"] for p in profiles} == {"Parent", "Kid"}
    active = client.get("/api/v1/profile", headers={**dev, "X-Profile-ID": k["id"]}).json()
    assert active["is_kids"] is True
    events = _events(client.post("/api/v1/session/plan", headers={**dev, "X-Profile-ID": k["id"]}, json={"mood": "adventurous", "time_budget_minutes": 90}))
    titles = [e["data"]["title"] for e in events if e["type"] == "pick"]
    assert titles and "Get Out" not in titles


def test_couch_mode(client):
    room = client.post("/api/v1/couch/rooms", headers=TV).json()
    code = room["code"]
    m = client.post(f"/api/v1/couch/rooms/{code}/join", headers={"X-Device-ID": "phone-1"}, json={"name": "Ada"}).json()["member_id"]
    client.patch(f"/api/v1/couch/rooms/{code}/members/{m}", headers={"X-Device-ID": "phone-1"}, json={"mood": "stressed", "vetoes": ["horror"]})
    blend = client.get(f"/api/v1/couch/rooms/{code}/blend", headers=TV).json()
    assert blend["mood"] == "stressed" and 27 in blend["excluded_genre_ids"]
    events = _events(client.post("/api/v1/session/plan", headers=TV, json={"mood": "stressed", "room_code": code}))
    assert any(e["type"] == "pick" for e in events)
    assert client.get(f"/api/v1/couch/rooms/{code}", headers=TV).json()["plan_id"]


def test_pair_code_and_inbox(client):
    code = client.post("/api/v1/tv/pair-code?tz_offset_minutes=60", headers=TV).json()["code"]
    assert len(code) == 6
    assert client.get("/api/v1/tv/inbox", headers=TV).json()["events"] == []


def test_mcp_endpoint_initializes(client):
    r = client.post(
        "/mcp",
        headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}},
    )
    assert r.status_code == 200
    assert "2025-11-25" in r.text
