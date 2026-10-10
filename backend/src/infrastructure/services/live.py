"""LiveHub — plan generation runs as a background task and publishes events here.

Any number of listeners (the TV that asked, a phone in Couch Mode, the Alexa+ MCP
tool) can replay and follow the same generation. A dropped connection never
cancels the work.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator

KEEP_SECONDS = 15 * 60


@dataclass
class LivePlan:
    plan_id: str
    events: list[dict] = field(default_factory=list)
    done: bool = False
    created: float = field(default_factory=time.monotonic)
    cond: asyncio.Condition = field(default_factory=asyncio.Condition)


class LiveHub:
    def __init__(self) -> None:
        self._plans: dict[str, LivePlan] = {}
        self._tasks: set[asyncio.Task] = set()

    def open(self, plan_id: str) -> LivePlan:
        self._gc()
        lp = LivePlan(plan_id)
        self._plans[plan_id] = lp
        return lp

    def get(self, plan_id: str) -> LivePlan | None:
        return self._plans.get(plan_id)

    async def publish(self, plan_id: str, event: dict) -> None:
        lp = self._plans.get(plan_id)
        if not lp:
            return
        async with lp.cond:
            lp.events.append(event)
            lp.cond.notify_all()

    async def close(self, plan_id: str) -> None:
        lp = self._plans.get(plan_id)
        if not lp:
            return
        async with lp.cond:
            lp.done = True
            lp.cond.notify_all()

    def run(self, coro) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def follow(self, plan_id: str, keepalive: float = 10.0) -> AsyncGenerator[str, None]:
        """Replay everything so far, then stream new events until the plan is done (NDJSON lines)."""
        lp = self._plans.get(plan_id)
        if not lp:
            return
        idx = 0
        while True:
            async with lp.cond:
                if idx >= len(lp.events) and not lp.done:
                    try:
                        await asyncio.wait_for(lp.cond.wait(), timeout=keepalive)
                    except asyncio.TimeoutError:
                        pass
                batch = lp.events[idx:]
                idx = len(lp.events)
                done = lp.done
            if not batch and not done:
                yield json.dumps({"type": "keepalive", "data": {}}) + "\n"
            for ev in batch:
                yield json.dumps(ev) + "\n"
            if done and idx >= len(lp.events):
                return

    async def wait_done(self, plan_id: str, timeout: float) -> LivePlan | None:
        lp = self._plans.get(plan_id)
        if not lp:
            return None
        end = time.monotonic() + timeout
        async with lp.cond:
            while not lp.done:
                remaining = end - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    await asyncio.wait_for(lp.cond.wait(), timeout=remaining)
                except asyncio.TimeoutError:
                    break
        return lp

    def _gc(self) -> None:
        now = time.monotonic()
        for pid in [p for p, lp in self._plans.items() if lp.done and now - lp.created > KEEP_SECONDS]:
            self._plans.pop(pid, None)
