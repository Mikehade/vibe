"""Session Architect — the 4-step Bedrock reasoning pipeline."""

import json
import re
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from src.core.constants.moods import MOOD_GENRE_MAP, get_genre_ids_for_mood
from src.core.constants.pacing import get_session_size
from src.core.domain.interfaces import ILanguageModel
from src.core.domain.session_plan import (
    ArcRole,
    EnergyTrajectory,
    Mood,
    SessionPickEntity,
    SessionPlanEntity,
)
from src.core.prompts.session_reasoning import (
    STEP1_ENERGY_TRAJECTORY,
    STEP2_CANDIDATE_EVALUATION,
    STEP3_SESSION_ASSEMBLY,
    STEP4_JUSTIFICATION,
    SYSTEM_PROMPT,
)
from src.core.tools.base import ToolRegistry
from utils.logger import get_logger

logger = get_logger(__name__)


class SessionArchitect:
    """Orchestrates the 4-step Bedrock chain for session plan generation."""

    def __init__(self, llm: ILanguageModel, tool_registry: ToolRegistry):
        self._llm = llm
        self._tool_registry = tool_registry

    async def generate_plan(
        self,
        mood: Mood,
        device_id: str,
        time_budget_minutes: int | None = None,
        voice_notes: str | None = None,
        taste_profile: dict | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Generate a session plan, yielding NDJSON events as each step completes.

        Yields dicts with type: "trajectory" | "pick" | "summary"
        """
        now = datetime.now(timezone.utc)
        num_picks = get_session_size(time_budget_minutes)
        mood_config = MOOD_GENRE_MAP[mood]

        taste_context = ""
        if taste_profile:
            top = sorted(taste_profile.get("genre_weights", {}).items(), key=lambda x: x[1], reverse=True)[:5]
            taste_context = f"\nTaste profile: likes {', '.join(g for g, _ in top)}"
            if taste_profile.get("disliked_genres"):
                taste_context += f", dislikes {', '.join(taste_profile['disliked_genres'])}"

        # ── Step 1: Energy Trajectory ──
        logger.info("Step 1: Inferring energy trajectory for mood=%s", mood.value)
        trajectory = await self._step1_energy_trajectory(
            mood=mood,
            now=now,
            num_picks=num_picks,
            time_budget=time_budget_minutes or 120,
            taste_context=taste_context,
        )
        yield {"type": "trajectory", "data": trajectory}

        # ── Step 2: Get candidates via tools ──
        logger.info("Step 2: Fetching and evaluating candidates")
        genre_ids = get_genre_ids_for_mood(mood)
        candidates = await self._get_candidates(genre_ids, mood, taste_profile)

        evaluated = await self._step2_evaluate_candidates(
            mood=mood,
            arc_shape=trajectory.get("arc_shape", "variable"),
            energy_trajectory=trajectory.get("energy_trajectory", ""),
            candidates=candidates,
            time_budget=time_budget_minutes or 120,
            taste_profile=taste_profile,
        )

        # ── Step 3: Assemble session ──
        logger.info("Step 3: Assembling session plan")
        assembled = await self._step3_assemble(
            num_picks=num_picks,
            arc_shape=trajectory.get("arc_shape", "variable"),
            energy_trajectory=trajectory.get("energy_trajectory", ""),
            evaluated=evaluated,
            time_budget=time_budget_minutes or 120,
        )

        # ── Step 4: Generate justifications ──
        logger.info("Step 4: Generating justifications")
        justified = await self._step4_justify(
            mood=mood,
            energy_trajectory=trajectory.get("energy_trajectory", ""),
            session_plan=assembled.get("session_plan", []),
        )

        # Merge justifications into picks and yield each
        plan_picks = assembled.get("session_plan", [])
        justifications = {j["position"]: j["reason"] for j in justified.get("justifications", [])}

        for pick in plan_picks:
            pick["reason"] = justifications.get(pick["position"], "A great choice for this moment.")
            yield {"type": "pick", "data": pick}

        # Yield summary
        yield {
            "type": "summary",
            "data": {
                "total_runtime_minutes": assembled.get("total_runtime_minutes", 0),
                "plan_summary": justified.get("plan_summary", "Your evening is planned."),
            },
        }

    async def _step1_energy_trajectory(
        self, mood: Mood, now: datetime, num_picks: int, time_budget: int, taste_context: str
    ) -> dict:
        prompt = STEP1_ENERGY_TRAJECTORY.format(
            mood=mood.value,
            time_of_day=now.strftime("%H:%M"),
            day_of_week=now.strftime("%A"),
            hours_until_sleep=max(1, 23 - now.hour),
            session_hours=round(time_budget / 60, 1),
            num_picks=num_picks,
            taste_context=taste_context,
        )
        return await self._invoke_json(prompt)

    async def _get_candidates(
        self, genre_ids: list[int], mood: Mood, taste_profile: dict | None
    ) -> list[dict]:
        """Fetch candidate titles from TMDB via content tools."""
        try:
            genres_str = ",".join(str(g) for g in genre_ids)
            result = await self._tool_registry.execute(
                "content_search_tmdb",
                {"query": mood.value, "genres": genres_str},
            )
            return result.get("results", [])[:30]
        except Exception as e:
            logger.warning("Tool-based candidate fetch failed: %s. Using fallback.", e)
            return []

    async def _step2_evaluate_candidates(
        self, mood: Mood, arc_shape: str, energy_trajectory: str,
        candidates: list[dict], time_budget: int, taste_profile: dict | None,
    ) -> list[dict]:
        taste = taste_profile or {}
        prompt = STEP2_CANDIDATE_EVALUATION.format(
            mood=mood.value,
            arc_shape=arc_shape,
            energy_trajectory=energy_trajectory,
            preferred_genres=", ".join(taste.get("genre_weights", {}).keys()) or "none set",
            disliked_genres=", ".join(taste.get("disliked_genres", [])) or "none",
            recently_watched="none",
            candidates_json=json.dumps(candidates[:15], indent=2),
            time_budget=time_budget,
        )
        result = await self._invoke_json(prompt)
        return result if isinstance(result, list) else result.get("candidates", [])

    async def _step3_assemble(
        self, num_picks: int, arc_shape: str, energy_trajectory: str,
        evaluated: list[dict], time_budget: int,
    ) -> dict:
        prompt = STEP3_SESSION_ASSEMBLY.format(
            num_picks=num_picks,
            arc_shape=arc_shape,
            energy_trajectory=energy_trajectory,
            evaluated_candidates_json=json.dumps(evaluated, indent=2),
            time_budget=time_budget,
        )
        return await self._invoke_json(prompt)

    async def _step4_justify(
        self, mood: Mood, energy_trajectory: str, session_plan: list[dict],
    ) -> dict:
        prompt = STEP4_JUSTIFICATION.format(
            mood=mood.value,
            energy_trajectory=energy_trajectory,
            session_plan_json=json.dumps(session_plan, indent=2),
        )
        return await self._invoke_json(prompt)

    @staticmethod
    def _extract_json(text: str) -> Any:
        """Extract JSON from a Bedrock response that may contain surrounding prose."""
        text = text.strip()

        # Try 1: entire text is valid JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try 2: extract from markdown code block (```json ... ``` or ``` ... ```)
        code_block = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", text)
        if code_block:
            try:
                return json.loads(code_block.group(1))
            except json.JSONDecodeError:
                pass

        # Try 3: find the first [ ... ] or { ... } at the top level
        for start_char, end_char in [("[", "]"), ("{", "}")]:
            start = text.find(start_char)
            if start == -1:
                continue
            depth = 0
            in_string = False
            escape = False
            for i in range(start, len(text)):
                c = text[i]
                if escape:
                    escape = False
                    continue
                if c == "\\":
                    escape = True
                    continue
                if c == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == start_char:
                    depth += 1
                elif c == end_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start : i + 1])
                        except json.JSONDecodeError:
                            break
            # If we get here, balanced-bracket search failed for this pair

        raise json.JSONDecodeError("No valid JSON found in response", text, 0)

    async def _invoke_json(self, user_prompt: str) -> Any:
        """Invoke Bedrock and parse the JSON response."""
        messages = [
            {"role": "user", "content": [{"text": user_prompt}]},
        ]
        try:
            response = await self._llm.invoke(
                messages=messages,
                system=[{"text": SYSTEM_PROMPT}],
                tools=self._tool_registry.get_all_specs(),
                tool_handler=self._tool_registry.execute,
            )
            # Extract text from response
            text = ""
            for block in response.get("output", {}).get("message", {}).get("content", []):
                if "text" in block:
                    text = block["text"]
                    break

            if not text.strip():
                logger.error("Bedrock returned empty text. Full response: %s", response)
                return {}

            return self._extract_json(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Bedrock response: %s", e)
            logger.debug("Bedrock response text was: %s", text[:500])
            return {}
        except (KeyError, IndexError) as e:
            logger.error("Failed to extract Bedrock response: %s", e)
            return {}