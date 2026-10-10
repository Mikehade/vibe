"""Session Architect — streaming, tool-using planner.

Pipeline (every step is surfaced to the TV as an NDJSON event):

1. Context   — local time, deterministic energy arc  → `trajectory` (instant)
2. Shortlist — TMDB discover pool (often prefetched) → `status`, `candidates`
3. Plan      — ONE streamed Bedrock conversation; the model may call tools
               (`tool` events), then writes one PICK line per slot. Each line
               is hydrated with posters/runtime/providers and emitted as `pick`
               the moment it is complete.
4. Safety    — heartbeat `status` every few seconds; a hard deadline; any slot the
               model did not fill is completed by the deterministic planner.
"""

from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncGenerator

from src.core.domain.catalog import Candidate
from src.core.domain.interfaces import IContentClient, ILanguageModel
from src.core.domain.session_plan import Mood
from src.core.engine import fallback
from src.core.engine.arc import ROLE_LABELS, Arc, ArcSlot, build_arc, part_of_day
from src.core.engine.candidate_pool import CandidatePool, CandidatePoolBuilder, PoolRequest
from src.core.engine.stream_parser import LineProtocolParser
from src.core.prompts.session_reasoning import PLAN_USER_PROMPT, SWAP_REASON_PROMPT, SYSTEM_PROMPT
from src.core.tools.planner_tools import TOOL_SPECS, PlannerTools
from utils.logger import get_logger

logger = get_logger(__name__)

HEARTBEAT_SECONDS = 3.5
_HEARTBEATS = [
    "Weighing the opener against your mood",
    "Balancing runtimes against your time",
    "Making sure neighbouring picks don't clash",
    "Double-checking it all fits tonight",
]


@dataclass
class PlanRequest:
    mood: Mood
    local_time: datetime
    budget_minutes: int | None
    pool_request: PoolRequest
    notes: str | None = None
    audience: str = "one viewer"
    likes: list[str] = field(default_factory=list)
    dislikes: list[str] = field(default_factory=list)
    shift: str | None = None
    start_position: int = 1
    max_slots: int | None = None
    already_watched: list[str] = field(default_factory=list)
    exclude_keys: set[str] = field(default_factory=set)


class SessionArchitect:
    def __init__(
        self,
        llm: ILanguageModel,
        content: IContentClient,
        pool_builder: CandidatePoolBuilder,
        timeout_seconds: int = 45,
        max_turns: int = 4,
        fast_model_id: str | None = None,
    ):
        self._llm = llm
        self._content = content
        self._pools = pool_builder
        self._timeout = timeout_seconds
        self._max_turns = max_turns
        self._fast_model_id = fast_model_id

    @property
    def pools(self) -> CandidatePoolBuilder:
        return self._pools

    # ── main entry ─────────────────────────────────────────────────────────

    async def generate(self, req: PlanRequest) -> AsyncGenerator[dict, None]:
        loop = asyncio.get_running_loop()
        started = loop.time()

        # 1. Arc — instant
        arc = build_arc(req.mood, req.local_time, req.budget_minutes, req.shift, req.start_position, req.max_slots)
        yield _status("context", f"{req.local_time.strftime('%A %-I:%M %p')} · {req.mood.value} · {arc.budget_minutes} minutes")
        yield {"type": "trajectory", "data": {**arc.to_dict(), "provisional": True}}

        # 2. Shortlist — progress events are forwarded through a queue
        progress_q: asyncio.Queue = asyncio.Queue()

        async def progress(stage: str, message: str):
            await progress_q.put(_status(stage, message))

        pool_task = asyncio.create_task(self._pools.get(req.pool_request, progress))
        while not pool_task.done() or not progress_q.empty():
            try:
                yield await asyncio.wait_for(progress_q.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue
        try:
            pool = pool_task.result()
        except Exception as e:  # noqa: BLE001
            logger.exception("pool build failed")
            yield {"type": "error", "data": {"message": f"Could not reach the catalogue ({e.__class__.__name__}). Try again."}}
            return

        available = [c for c in pool.candidates if c.key not in req.exclude_keys]
        if not available:
            yield {"type": "error", "data": {"message": "Nothing matched those filters. Try another mood or add a service."}}
            return
        yield {
            "type": "candidates",
            "data": {
                "count": len(available),
                "outside_services": pool.outside_services,
                "sample": [
                    {"tmdb_id": c.tmdb_id, "media_type": c.media_type, "title": c.title, "poster_path": c.poster_path}
                    for c in available[:18]
                ],
            },
        }

        # 3. Model
        yield _status("thinking", "Planning your night")
        slots_by_pos = {s.position: s for s in arc.slots}
        filled: dict[int, dict] = {}
        used: set[str] = set(req.exclude_keys)
        summary_text: str | None = None

        queue: asyncio.Queue = asyncio.Queue()
        producer = asyncio.create_task(self._run_model(req, arc, pool, available, queue))
        deadline = started + self._timeout
        beats = itertools.cycle(_HEARTBEATS)

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                producer.cancel()
                yield _status("fallback", "Taking longer than usual — finishing with our best matches")
                break
            try:
                kind, payload = await asyncio.wait_for(queue.get(), timeout=min(HEARTBEAT_SECONDS, remaining))
            except asyncio.TimeoutError:
                yield _status("thinking", f"{next(beats)} · {int(loop.time() - started)}s")
                continue

            if kind == "done":
                break
            if kind == "error":
                yield _status("fallback", "The planner hit a snag — finishing with our best matches")
                break
            if kind == "tool":
                yield {"type": "tool", "data": payload}
                continue
            if kind == "rec":
                tag, data = payload
                if tag == "TRAJECTORY" and data.get("energy_trajectory"):
                    yield {
                        "type": "trajectory",
                        "data": {**arc.to_dict(), "energy_trajectory": str(data["energy_trajectory"])[:300], "provisional": False},
                    }
                elif tag == "PICK":
                    pick = self._accept_pick(data, slots_by_pos, filled, used, pool)
                    if pick:
                        filled[pick["position"]] = pick
                        yield {"type": "pick", "data": pick}
                elif tag == "SUMMARY" and data.get("plan_summary"):
                    summary_text = str(data["plan_summary"])[:400]

        if not producer.done():
            producer.cancel()

        # 4. Fill gaps deterministically
        for slot in arc.slots:
            if slot.position in filled:
                continue
            prev = filled.get(slot.position - 1)
            prev_c = pool.find(prev["tmdb_id"], prev["media_type"]) if prev else None
            c = fallback.choose(available, slot, used, prev_c)
            if not c:
                continue
            pick = self._hydrate(c, slot, fallback.template_reason(c, slot), 0.6, None, pool, source="fallback")
            used.add(c.key)
            filled[slot.position] = pick
            yield {"type": "pick", "data": pick}

        total = sum(p["runtime_minutes"] for p in filled.values())
        if not summary_text:
            titles = [filled[p]["title"] for p in sorted(filled)]
            summary_text = f"{len(titles)} picks, {total} minutes: " + ", then ".join(titles) + "."
        yield {"type": "summary", "data": {"plan_summary": summary_text, "total_runtime_minutes": total}}

    # ── model producer ─────────────────────────────────────────────────────

    async def _run_model(self, req: PlanRequest, arc: Arc, pool: CandidatePool, available: list[Candidate], queue):
        try:
            tools = PlannerTools(self._content, pool)
            messages = [{"role": "user", "content": [{"text": self._user_prompt(req, arc, available)}]}]
            system = [{"text": SYSTEM_PROMPT}]
            for turn in range(self._max_turns):
                parser = LineProtocolParser()
                stop = None
                async for ev in self._llm.stream_turn(messages, system, TOOL_SPECS, temperature=0.6, max_tokens=1600):
                    if ev["type"] == "text":
                        for rec in parser.feed(ev["text"]):
                            await queue.put(("rec", rec))
                    elif ev["type"] == "tool_use":
                        await queue.put(("tool", {"name": ev["name"], "message": PlannerTools.describe(ev["name"], ev["input"], pool)}))
                    elif ev["type"] == "stop":
                        stop = ev
                for rec in parser.flush():
                    await queue.put(("rec", rec))
                if not stop or stop["reason"] != "tool_use":
                    break
                tool_uses = [b["toolUse"] for b in stop["message"]["content"] if "toolUse" in b]
                results = await asyncio.gather(
                    *(tools.execute(tu["name"], tu.get("input") or {}) for tu in tool_uses), return_exceptions=True
                )
                messages.append(stop["message"])
                content = []
                for tu, res in zip(tool_uses, results):
                    if isinstance(res, Exception):
                        content.append({"toolResult": {"toolUseId": tu["toolUseId"], "content": [{"json": {"error": str(res)}}], "status": "error"}})
                    else:
                        content.append({"toolResult": {"toolUseId": tu["toolUseId"], "content": [{"json": res}]}})
                if turn == self._max_turns - 2:
                    content.append({"text": "No more tool calls. Write the remaining lines now."})
                messages.append({"role": "user", "content": content})
            await queue.put(("done", None))
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception("planner model failed: %s", e)
            await queue.put(("error", str(e)))

    def _user_prompt(self, req: PlanRequest, arc: Arc, available: list[Candidate]) -> str:
        slots = "\n".join(
            f"  slot {s.position}: {s.label} ({s.role}) — ~{s.target_minutes} min, energy {s.energy:.1f}" for s in arc.slots
        )
        watched = ""
        if req.already_watched:
            watched = "- Already watched tonight: " + "; ".join(req.already_watched) + "\n"
        bedtime = ""
        end_hour = (req.local_time.hour * 60 + req.local_time.minute + arc.budget_minutes) // 60 % 24
        if end_hour in (0, 1, 2, 3):
            bedtime = " (ends after midnight — keep the close gentle)"
        return PLAN_USER_PROMPT.format(
            local_time_label=req.local_time.strftime("%A %-I:%M %p"),
            part_of_day=part_of_day(req.local_time),
            mood=req.mood.value,
            intensity="",
            notes=req.notes or "none",
            budget=arc.budget_minutes,
            bedtime=bedtime,
            audience=req.audience,
            likes=", ".join(req.likes) or "not set",
            dislikes=", ".join(req.dislikes) or "none",
            already_watched=watched,
            direction=arc.direction,
            slots=slots,
            candidates="\n".join(c.compact_line() for c in available),
            slot_numbers=", ".join(str(s.position) for s in arc.slots),
        )

    # ── picks ──────────────────────────────────────────────────────────────

    def _accept_pick(self, data: dict, slots: dict[int, ArcSlot], filled: dict, used: set[str], pool: CandidatePool) -> dict | None:
        try:
            pos = int(data.get("slot") or data.get("position"))
            tmdb_id = int(data.get("tmdb_id"))
        except (TypeError, ValueError):
            return None
        slot = slots.get(pos)
        if not slot or pos in filled:
            return None
        c = pool.find(tmdb_id, data.get("media_type"))
        if not c or c.key in used:
            logger.info("model pick rejected (unknown or duplicate): %s", data)
            return None
        episodes = data.get("episodes")
        try:
            episodes = int(episodes) if episodes and c.media_type == "tv" else None
        except (TypeError, ValueError):
            episodes = None
        # Guard the time budget: trim series episodes to fit, reject films that blow the slot.
        limit = fallback.slot_limit(slot)
        if c.media_type == "tv":
            ep_len = max(c.runtime or 30, 5)
            if episodes and episodes * ep_len > limit:
                episodes = max(1, int(limit // ep_len))
        elif (c.runtime or 0) > limit:
            logger.info("model pick rejected (too long for %s slot): %s", slot.role, c.title)
            return None
        used.add(c.key)
        conf = data.get("confidence")
        try:
            conf = max(0.0, min(1.0, float(conf)))
        except (TypeError, ValueError):
            conf = 0.75
        reason = str(data.get("reason") or "").strip()[:240] or fallback.template_reason(c, slot)
        return self._hydrate(c, slot, reason, conf, episodes, pool, source="ai")

    @staticmethod
    def _hydrate(
        c: Candidate, slot: ArcSlot, reason: str, confidence: float, episodes: int | None, pool: CandidatePool, source: str
    ) -> dict:
        if c.media_type == "tv":
            if not episodes:
                _, episodes = fallback.runtime_for(c, slot)
            episodes = max(1, min(6, episodes or 1))
            total = (c.runtime or 30) * episodes
        else:
            episodes = None
            total = c.runtime or 100
        preferred = set(pool.request.provider_ids)
        provider = next((p for p in c.providers if p.id in preferred), None) or (c.providers[0] if c.providers else None)
        return {
            "position": slot.position,
            "role": slot.role,
            "role_label": ROLE_LABELS[slot.role],
            "energy": slot.energy,
            "tmdb_id": c.tmdb_id,
            "media_type": c.media_type,
            "title": c.title,
            "year": c.year,
            "overview": c.overview,
            "poster_path": c.poster_path,
            "backdrop_path": c.backdrop_path,
            "runtime_minutes": total,
            "episode_runtime": c.runtime if c.media_type == "tv" else None,
            "episodes": episodes,
            "rating": round(c.rating, 1) if c.rating else None,
            "certification": c.certification,
            "genre_ids": c.genre_ids,
            "genres": c.genres,
            "reason": reason,
            "confidence": round(confidence, 2),
            "streaming_provider": provider.name if provider else None,
            "provider_logo_path": provider.logo_path if provider else None,
            "deep_link_url": c.watch_link,
            "source": source,
        }

    # ── swap one slot ──────────────────────────────────────────────────────

    async def replacement(
        self,
        pool: CandidatePool,
        slot: ArcSlot,
        used_keys: set[str],
        previous_key: str | None,
        mood: Mood,
        replaced_title: str,
    ) -> dict | None:
        prev = None
        if previous_key:
            mt, _, tid = previous_key.partition(":")
            prev = pool.find(int(tid), mt) if tid.isdigit() else None
        c = fallback.choose(pool.candidates, slot, used_keys, prev)
        if not c:
            return None
        total, _ = fallback.runtime_for(c, slot)
        reason = fallback.template_reason(c, slot)
        prompt = SWAP_REASON_PROMPT.format(
            title=c.title, year=c.year or "", genres=", ".join(c.genres[:2]), runtime=total,
            role_label=ROLE_LABELS[slot.role].lower(), mood=mood.value, replaced=replaced_title,
        )
        try:
            resp = await asyncio.wait_for(
                self._llm.invoke(
                    [{"role": "user", "content": [{"text": prompt}]}],
                    model_id=self._fast_model_id, temperature=0.7, max_tokens=80,
                ),
                timeout=6,
            )
            for block in resp.get("output", {}).get("message", {}).get("content", []):
                if block.get("text", "").strip():
                    reason = block["text"].strip().strip('"')[:240]
                    break
        except Exception as e:  # noqa: BLE001
            logger.info("swap reason fell back to template: %s", e)
        return self._hydrate(c, slot, reason, 0.7, None, pool, source="swap")


def _status(stage: str, message: str) -> dict:
    return {"type": "status", "data": {"stage": stage, "message": message}}
