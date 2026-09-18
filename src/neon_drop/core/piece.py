"""Tetromino definitions and the Piece class.

Shapes follow the Super Rotation System (SRS). Each piece is defined
in its spawn orientation inside a bounding box (3x3 for most pieces,
4x4 for I), and the three subsequent rotation states are derived by
rotating cells 90 degrees clockwise within that box.

Coordinates are (x, y) with +x right and +y DOWN. Row 0 is the top
of the buffer, the last row is the floor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from neon_drop import config

PIECES: Final = ("I", "J", "L", "O", "S", "T", "Z")

# Spawn orientations within the SRS bounding box, y-down.
_SPAWN: Final[dict[str, tuple[tuple[int, int], ...]]] = {
    "I": ((0, 1), (1, 1), (2, 1), (3, 1)),
    "J": ((0, 0), (0, 1), (1, 1), (2, 1)),
    "L": ((2, 0), (0, 1), (1, 1), (2, 1)),
    "O": ((1, 0), (2, 0), (1, 1), (2, 1)),
    "S": ((1, 0), (2, 0), (0, 1), (1, 1)),
    "T": ((1, 0), (0, 1), (1, 1), (2, 1)),
    "Z": ((0, 0), (1, 0), (1, 1), (2, 1)),
}

_BOX_SIZE: Final = {"I": 4}
_DEFAULT_BOX: Final = 3


def _rotate_cw_within_box(
    cells: tuple[tuple[int, int], ...], size: int
) -> tuple[tuple[int, int], ...]:
    """Rotate cells 90 degrees clockwise within a square box."""
    return tuple((size - 1 - y, x) for (x, y) in cells)


def _build_shapes() -> dict[str, tuple[tuple[tuple[int, int], ...], ...]]:
    shapes: dict[str, tuple[tuple[tuple[int, int], ...], ...]] = {}
    for kind in PIECES:
        spawn = _SPAWN[kind]
        if kind == "O":
            # O looks identical in all four rotation states.
            shapes[kind] = (spawn, spawn, spawn, spawn)
            continue
        size = _BOX_SIZE.get(kind, _DEFAULT_BOX)
        states = [spawn]
        for _ in range(3):
            states.append(_rotate_cw_within_box(states[-1], size))
        shapes[kind] = tuple(states)
    return shapes


SHAPES: Final = _build_shapes()

# All pieces spawn with their bounding box at x=3, and with their
# topmost filled row just inside the hidden buffer above the playfield.
SPAWN_X: Final = 3
SPAWN_Y: Final = config.HIDDEN_ROWS - 2


@dataclass
class Piece:
    """A tetromino at a specific position and rotation state."""

    kind: str
    rotation: int = 0
    x: int = SPAWN_X
    y: int = SPAWN_Y

    def __post_init__(self) -> None:
        if self.kind not in PIECES:
            raise ValueError(f"unknown piece kind: {self.kind!r}")
        if not 0 <= self.rotation <= 3:
            raise ValueError(f"rotation must be 0..3, got {self.rotation}")

    def cells(self) -> tuple[tuple[int, int], ...]:
        """Board coordinates occupied by this piece."""
        return tuple((self.x + cx, self.y + cy) for (cx, cy) in SHAPES[self.kind][self.rotation])

    def copy(self) -> Piece:
        return Piece(self.kind, self.rotation, self.x, self.y)


def spawn(kind: str) -> Piece:
    """Create a fresh piece at the spawn position."""
    return Piece(kind)
