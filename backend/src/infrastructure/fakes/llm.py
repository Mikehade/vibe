"""Offline stand-in for Bedrock that follows the planner's line protocol."""

import asyncio
import json
import random
import re
from typing import AsyncGenerator

from src.core.domain.interfaces import ILanguageModel

_SLOT_RE = re.compile(r"slot (\d+): .*?\((\w+)\) — ~(\d+) min")
_CAND_RE = re.compile(r"^(\d+) \| (movie|tv) \| (.+?) \((\d{4}|\?)\) \| (\d+)m")


class FakeLanguageModel(ILanguageModel):
    def __init__(self, delay: float | None = None):
        import os

        self._delay = delay if delay is not None else float(os.getenv("FAKE_LLM_DELAY", "0.35"))

    @property
    def model_id(self) -> str:
        return "fake"

    async def invoke(self, messages: list[dict], tools=None, **kwargs) -> dict:
        await asyncio.sleep(self._delay)
        return {"output": {"message": {"content": [{"text": "A fresh pick with the same energy, chosen to keep the night flowing."}]}}}

    async def prompt(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        yield "ok"

    async def stream_turn(self, messages, system, tools=None, **kwargs) -> AsyncGenerator[dict, None]:
        prompt = messages[0]["content"][0]["text"]
        already_used_tools = any("toolResult" in b for m in messages for b in m.get("content", []))
        notes = re.search(r"Viewer notes: (.*)", prompt)
        wants_like = notes and "like " in notes.group(1).lower() and not already_used_tools and tools
        if wants_like:
            query = notes.group(1).lower().split("like ", 1)[1].split(",")[0].strip()[:40]
            await asyncio.sleep(self._delay)
            msg = {"role": "assistant", "content": [{"toolUse": {"toolUseId": "t1", "name": "search_titles", "input": {"query": query}}}]}
            yield {"type": "tool_use", "id": "t1", "name": "search_titles", "input": {"query": query}}
            yield {"type": "stop", "reason": "tool_use", "message": msg}
            return

        slots = [(int(a), b, int(c)) for a, b, c in _SLOT_RE.findall(prompt)]
        cands = []
        for line in prompt.splitlines():
            m = _CAND_RE.match(line.strip())
            if m:
                cands.append((int(m.group(1)), m.group(2), m.group(3), int(m.group(5))))
        rng = random.Random(len(prompt))
        lines = ['TRAJECTORY {"energy_trajectory": "Start easy, settle into something absorbing, then drift somewhere warm."}']
        used = set()
        for pos, role, target in slots:
            options = [c for c in cands if c[0] not in used]
            if not options:
                break
            options.sort(key=lambda c: abs((c[3] * (max(1, round(target / c[3])) if c[1] == "tv" else 1)) - target) + rng.random() * 25)
            pick = options[0]
            used.add(pick[0])
            eps = max(1, round(target / pick[3])) if pick[1] == "tv" else None
            reason = {
                "opener": f"{pick[2]} is an easy way in — nothing to catch up on, just settle into the evening.",
                "main_event": f"{pick[2]} is the one to give your full attention; it rewards it.",
                "bridge": f"A short change of tone with {pick[2]} before the next stretch.",
                "nightcap": f"{pick[2]} is warm and low-stakes, the right note to end on.",
            }.get(role, "A good fit for this point in the night.")
            lines.append("PICK " + json.dumps({"slot": pos, "tmdb_id": pick[0], "media_type": pick[1], "episodes": eps, "reason": reason, "confidence": 0.82}))
        lines.append('SUMMARY {"plan_summary": "An easy start, one proper centrepiece and a soft landing."}')

        text = "\n".join(lines) + "\n"
        for i in range(0, len(text), 60):
            await asyncio.sleep(self._delay / 4)
            yield {"type": "text", "text": text[i : i + 60]}
        yield {"type": "stop", "reason": "end_turn", "message": {"role": "assistant", "content": [{"text": text}]}}
