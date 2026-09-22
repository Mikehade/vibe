"""Mood service — voice/text to structured mood parsing."""

import json

from src.core.domain.interfaces import ILanguageModel
from src.core.prompts.mood_parsing import MOOD_PARSE_PROMPT
from utils.logger import get_logger

logger = get_logger(__name__)


class MoodService:
    def __init__(self, llm: ILanguageModel, session_factory=None):
        self._llm = llm
        self._session_factory = session_factory

    async def parse_mood(self, transcript: str) -> dict:
        """Parse a voice/text transcript into a structured mood."""
        prompt = MOOD_PARSE_PROMPT.format(transcript=transcript)
        messages = [{"role": "user", "content": [{"text": prompt}]}]

        try:
            response = await self._llm.invoke(messages=messages, temperature=0.3, max_tokens=256)
            text = ""
            for block in response.get("output", {}).get("message", {}).get("content", []):
                if "text" in block:
                    text = block["text"]
                    break

            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]

            return json.loads(text)
        except Exception as e:
            logger.error("Mood parsing failed: %s", e)
            return {"mood": "bored", "intensity": 0.5, "notes": "Failed to parse — defaulting"}
