"""7-bag randomizer.

Pieces are dealt from shuffled bags containing all seven tetrominoes.
Each kind appears exactly once per bag, so the longest possible run
without a specific piece is 12 (last of one bag + first 11 of next).
"""

from __future__ import annotations

import random

from neon_drop.core.piece import PIECES


class Bag:
    """Deals tetromino kinds using the 7-bag algorithm."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()
        self._queue: list[str] = []

    def _refill(self) -> None:
        bag = list(PIECES)
        self._rng.shuffle(bag)
        self._queue.extend(bag)

    def next(self) -> str:
        if not self._queue:
            self._refill()
        return self._queue.pop(0)

    def peek(self, n: int) -> list[str]:
        """Return the next n kinds without consuming them."""
        while len(self._queue) < n:
            self._refill()
        return self._queue[:n]
