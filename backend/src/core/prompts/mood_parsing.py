"""Prompt template for parsing voice/text input into structured mood."""

MOOD_PARSE_PROMPT = """Parse this viewer's description of how they're feeling into a structured mood.

Input: "{transcript}"

Available moods: tired, energised, stressed, social, bored, adventurous

Respond with a JSON object:
{{
  "mood": "one of the available moods",
  "intensity": 0.0 to 1.0,
  "notes": "any additional context from their description that could help with planning"
}}

If the input is ambiguous, pick the closest mood and note the ambiguity.
If the input is unrelated to mood, default to "bored" with intensity 0.5."""
