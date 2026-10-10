"""Incremental parser for the planner's line protocol.

The model writes one record per line, e.g.

    TRAJECTORY {"energy_trajectory": "...", "arc_shape": "declining"}
    PICK {"slot": 1, "tmdb_id": 123, "media_type": "movie", "reason": "...", "confidence": 0.8}
    SUMMARY {"plan_summary": "..."}

Each record is surfaced the moment its line is complete, so picks reach the TV
while the model is still writing the next one.
"""

from __future__ import annotations

import json
import re

TAGS = ("TRAJECTORY", "PICK", "SUMMARY")
_LINE_RE = re.compile(r"^\W*(TRAJECTORY|PICK|SUMMARY)\W*\s*[:\-]?\s*(\{.*\})\s*$")


class LineProtocolParser:
    def __init__(self) -> None:
        self._buf = ""

    def feed(self, chunk: str) -> list[tuple[str, dict]]:
        self._buf += chunk
        out: list[tuple[str, dict]] = []
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            rec = parse_line(line)
            if rec:
                out.append(rec)
        return out

    def flush(self) -> list[tuple[str, dict]]:
        line, self._buf = self._buf, ""
        rec = parse_line(line)
        return [rec] if rec else []


def parse_line(line: str) -> tuple[str, dict] | None:
    line = line.strip().strip("`").strip()
    if not line:
        return None
    m = _LINE_RE.match(line)
    if not m:
        return None
    try:
        data = json.loads(m.group(2))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return m.group(1), data
