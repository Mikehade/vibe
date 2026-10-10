"""Vibe MCP server — lets Alexa+ (or any MCP client) plan movie night on the TV.

Spec: MCP 2025-11-25, Streamable HTTP transport, mounted at /mcp on the API.

Typical conversation:
  "Alexa, link Vibe to my TV, code 482913"   → link_tv
  "Plan a chill movie night, about two hours" → plan_movie_night  (lineup appears on the TV live)
  "What's next?"                              → whats_next
  "Swap the second one"                       → swap_pick
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field

from src.core.domain.session_plan import Mood
from utils.logger import get_logger

logger = get_logger(__name__)

MoodName = Literal["tired", "energised", "stressed", "social", "bored", "adventurous"]

INSTRUCTIONS = """Vibe plans a whole evening of TV (an opener, a main event, a closer) from the viewer's mood,
time and streaming services, and shows it on their Fire TV. Link the TV once with the 6-digit code shown
in Vibe's settings. Keep spoken answers short: say the titles and when the night will end."""


def _session_id(ctx: Context) -> str | None:
    try:
        req = ctx.request_context.request
        return req.headers.get("mcp-session-id") if req is not None else None
    except Exception:  # noqa: BLE001
        return None


def _fmt_minutes(m: int) -> str:
    h, mm = divmod(int(m or 0), 60)
    return f"{h}h {mm:02d}m" if h else f"{mm} min"


def _spoken_lineup(plan: dict, tz_offset: int | None) -> str:
    picks = plan.get("picks", [])
    if not picks:
        return "I couldn't put a lineup together this time."
    lines = []
    for p in picks:
        where = f" on {p['streaming_provider']}" if p.get("streaming_provider") else ""
        eps = f", {p['episodes']} episodes" if p.get("episodes") and p["episodes"] > 1 else ""
        lines.append(f"{p['position']}. {p.get('role_label') or p['role']}: {p['title']} ({p['runtime_minutes']} min{eps}{where}). {p.get('reason') or ''}")
    total = sum(p["runtime_minutes"] for p in picks)
    end = ""
    if tz_offset is not None:
        finish = datetime.now(timezone.utc).astimezone(timezone(timedelta(minutes=tz_offset))) + timedelta(minutes=total)
        end = f", done by about {finish.strftime('%-I:%M %p')}"
    head = f"Tonight: {len(picks)} picks, {_fmt_minutes(total)}{end}."
    return head + "\n" + "\n".join(lines) + (f"\n{plan.get('plan_summary')}" if plan.get("plan_summary") else "")


def build_mcp(container) -> FastMCP:
    mcp = FastMCP(
        name="Vibe — Session Architect",
        instructions=INSTRUCTIONS,
        streamable_http_path="/mcp",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    def services():
        return container.session_service(), container.tv_link_service(), container.mood_service()

    def device_for(ctx: Context, tv_code: str | None = None) -> tuple[str, bool]:
        _, links, _ = services()
        sid = _session_id(ctx)
        if tv_code:
            linked = links.link(tv_code, sid)
            if linked:
                return linked, True
        dev = links.device_for(sid)
        if dev:
            return dev, True
        return f"mcp-guest-{(sid or 'anon')[:24]}", False

    @mcp.tool(
        title="Link a TV",
        description="Link this assistant to the viewer's Vibe TV app using the 6-digit code shown on screen.",
        annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def link_tv(code: Annotated[str, Field(description="6-digit code from the TV, e.g. 482913")], ctx: Context) -> str:
        _, links, _ = services()
        device = links.link(code, _session_id(ctx))
        if not device:
            return "That code didn't match. Open Vibe on the TV, go to Settings, and read me the 6-digit code."
        return "Linked. Plans you ask for will now appear on the TV."

    @mcp.tool(
        title="Plan movie night",
        description=(
            "Plan an evening of viewing (2–4 picks with an energy arc) for the viewer's mood and time, "
            "using their streaming services. If a TV is linked, the lineup appears on it live."
        ),
        annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, openWorldHint=True),
    )
    async def plan_movie_night(
        ctx: Context,
        mood: Annotated[MoodName | None, Field(description="Closest mood. Omit if unsure and pass `request` instead.")] = None,
        minutes: Annotated[int | None, Field(ge=30, le=480, description="Time available, in minutes")] = None,
        request: Annotated[str | None, Field(max_length=300, description="What the viewer said, e.g. 'something funny, nothing scary'")] = None,
        tv_code: Annotated[str | None, Field(description="Optional 6-digit TV code if not linked yet")] = None,
    ) -> str:
        session_service, links, mood_service = services()
        device, linked = device_for(ctx, tv_code)
        if mood is None:
            parsed = await mood_service.parse_mood(request or "a relaxed evening")
            mood = parsed.get("mood", "bored")
            if mood not in {m.value for m in Mood}:
                mood = "bored"
        tz = links.tz_offset(device)
        plan_id = await session_service.start_plan(
            device, None, mood=mood, time_budget_minutes=minutes, notes=request, tz_offset_minutes=tz,
        )
        if linked:
            links.push(device, {"type": "watch_plan", "data": {"plan_id": plan_id}})
        # Relay progress to the assistant while the plan streams
        progress = 0
        async for line in session_service.follow(plan_id):
            ev = json.loads(line)
            if ev["type"] in ("status", "tool", "pick"):
                progress += 1
                msg = ev["data"].get("message") or (f"Picked {ev['data'].get('title')}" if ev["type"] == "pick" else "")
                try:
                    await ctx.report_progress(progress, None, msg)
                except Exception:  # noqa: BLE001
                    pass
            if ev["type"] == "error":
                return "Sorry — " + ev["data"].get("message", "planning failed.")
        plan = await session_service.get_plan(plan_id)
        text = _spoken_lineup(plan or {}, tz)
        if linked:
            text += "\nIt's on your TV now."
        else:
            text += "\n(Tip: link your TV with its 6-digit code to see this on screen.)"
        return text

    @mcp.tool(
        title="Tonight's lineup",
        description="Read back the current plan on the linked TV.",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    async def tonight_lineup(ctx: Context) -> str:
        session_service, links, _ = services()
        device, linked = device_for(ctx)
        plan = await session_service.latest_plan(device)
        if not plan:
            return "There's no plan yet. Ask me to plan movie night."
        return _spoken_lineup(plan, links.tz_offset(device))

    @mcp.tool(
        title="What's next",
        description="The next unwatched pick in tonight's plan.",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    async def whats_next(ctx: Context) -> str:
        session_service, _, _ = services()
        device, _ = device_for(ctx)
        plan = await session_service.latest_plan(device)
        if not plan:
            return "There's no plan yet."
        nxt = next((p for p in plan["picks"] if p["status"] in ("pending", "watching")), None)
        if not nxt:
            return "That's everything for tonight."
        where = f" It's on {nxt['streaming_provider']}." if nxt.get("streaming_provider") else ""
        return f"Next up: {nxt['title']}, {nxt['runtime_minutes']} minutes.{where} {nxt.get('reason') or ''}"

    @mcp.tool(
        title="Swap a pick",
        description="Replace one pick in tonight's plan (1 = first) with the best alternative for that slot.",
        annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, openWorldHint=False),
    )
    async def swap_pick(ctx: Context, position: Annotated[int, Field(ge=1, le=6)]) -> str:
        session_service, links, _ = services()
        device, linked = device_for(ctx)
        plan = await session_service.latest_plan(device)
        if not plan:
            return "There's no plan to change yet."
        old = next((p for p in plan["picks"] if p["position"] == position), None)
        if not old:
            return f"There's no pick number {position}."
        try:
            result = await session_service.swap_pick(plan["id"], old["id"], device)
        except LookupError as e:
            return str(e)
        new = result["pick"]
        if linked:
            links.push(device, {"type": "plan_updated", "data": {"plan_id": plan["id"]}})
        return f"Swapped {old['title']} for {new['title']} ({new['runtime_minutes']} min). {new.get('reason') or ''}"

    @mcp.tool(
        title="Mark as watched",
        description="Mark a pick as watched so 'what's next' moves on.",
        annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def mark_watched(ctx: Context, position: Annotated[int, Field(ge=1, le=6)]) -> str:
        session_service, links, _ = services()
        device, linked = device_for(ctx)
        plan = await session_service.latest_plan(device)
        pick = next((p for p in (plan or {}).get("picks", []) if p["position"] == position), None)
        if not pick:
            return "I couldn't find that pick."
        await session_service.update_pick_status(pick["id"], "completed")
        if linked:
            links.push(device, {"type": "plan_updated", "data": {"plan_id": plan["id"]}})
        return f"Marked {pick['title']} as watched."

    return mcp
