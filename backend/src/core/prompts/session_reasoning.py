"""Prompt templates for the 4-step session reasoning pipeline."""

SYSTEM_PROMPT = """You are the Session Architect — an AI that designs perfect TV viewing sessions.
You plan multi-show evenings that match the viewer's mood, energy trajectory, and taste.
Your plans are intentional sequences, not random playlists. Every pick has a role in the arc."""

STEP1_ENERGY_TRAJECTORY = """Based on the viewer's current state, infer their energy trajectory for this session.

Current mood: {mood}
Time of day: {time_of_day}
Day of week: {day_of_week}
Hours until typical sleep: {hours_until_sleep}
{taste_context}

Reason about:
1. Where they are emotionally RIGHT NOW
2. Where their energy is heading over the next {session_hours} hours
3. What kind of content pacing matches that arc

Respond with a JSON object:
{{
  "energy_trajectory": "one sentence describing the energy arc",
  "arc_shape": "one of: light-heavy-light, ascending, declining, sustaining, variable",
  "suggested_picks": {num_picks},
  "reasoning": "2-3 sentences explaining your reasoning"
}}"""

STEP2_CANDIDATE_EVALUATION = """Evaluate these candidates for a {mood} mood session with {arc_shape} pacing.

Energy trajectory: {energy_trajectory}

Taste profile:
- Preferred genres: {preferred_genres}
- Disliked genres: {disliked_genres}
- Recently watched (avoid repeats): {recently_watched}

Candidates (from TMDB):
{candidates_json}

For each viable candidate, assess:
1. Individual fit for this mood
2. How it would function in a sequence (opener, main_event, bridge, or nightcap)
3. Runtime compatibility with {time_budget} minute budget

Respond with a JSON array of evaluated candidates:
[
  {{
    "tmdb_id": 12345,
    "title": "...",
    "role_fit": ["opener", "nightcap"],
    "mood_score": 0.85,
    "sequence_notes": "why this works at this position"
  }}
]"""

STEP3_SESSION_ASSEMBLY = """Assemble a session plan from these evaluated candidates.

Target: {num_picks} picks, {arc_shape} pacing, {time_budget} minute budget.

Energy trajectory: {energy_trajectory}

Evaluated candidates:
{evaluated_candidates_json}

Rules:
- Each pick gets exactly ONE role: opener, main_event, bridge, or nightcap
- Opener is always position 1 (low-effort entry point)
- Total runtime must stay within the time budget
- No duplicate genres in adjacent positions (variety matters)
- If a "bridge" role is needed, it separates different tonal sections

Respond with a JSON object:
{{
  "session_plan": [
    {{
      "position": 1,
      "role": "opener",
      "tmdb_id": 12345,
      "title": "...",
      "runtime_minutes": 22,
      "confidence": 0.85
    }}
  ],
  "total_runtime_minutes": 142
}}"""

STEP4_JUSTIFICATION = """Write viewer-facing justifications for each pick in this session plan.

Mood: {mood}
Energy trajectory: {energy_trajectory}

Session plan:
{session_plan_json}

For each pick, write a plain-English justification (max 25 words) that explains:
1. Why THIS title
2. Why at THIS position in the sequence

The tone should be conversational — like a friend explaining their recommendation.
Example: "22 minutes of zero-effort laughs to shake off the workday before something longer."

Respond with a JSON object:
{{
  "justifications": [
    {{
      "position": 1,
      "reason": "..."
    }}
  ],
  "plan_summary": "one sentence describing the overall evening arc"
}}"""
