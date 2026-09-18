"""Persistent high scores stored in the user's home directory.

We store in ~/.neon_drop_scores.json rather than the project folder so
the repo stays clean and the data survives a re-clone.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

_SCORES_PATH = Path.home() / ".neon_drop_scores.json"
_MAX_ENTRIES = 5


@dataclass
class ScoreEntry:
    score: int
    lines: int
    level: int
    timestamp: float  # Unix time


class HighScores:
    """The player's top N scores, sorted descending."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else _SCORES_PATH
        self.entries: list[ScoreEntry] = self._load()

    def _load(self) -> list[ScoreEntry]:
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text())
            return [ScoreEntry(**e) for e in raw]
        except (json.JSONDecodeError, OSError, TypeError):
            # Corrupt or unreadable — start fresh rather than crash.
            return []

    def _save(self) -> None:
        try:
            self._path.write_text(json.dumps([asdict(e) for e in self.entries], indent=2))
        except OSError:
            pass  # best effort; never crash the game on a save failure

    def submit(self, score: int, lines: int, level: int) -> bool:
        """Record a new score. Returns True if it made the top list."""
        entry = ScoreEntry(score, lines, level, time.time())
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.score, reverse=True)
        made_it = entry in self.entries[:_MAX_ENTRIES]
        self.entries = self.entries[:_MAX_ENTRIES]
        self._save()
        return made_it

    def best(self) -> int:
        return self.entries[0].score if self.entries else 0
