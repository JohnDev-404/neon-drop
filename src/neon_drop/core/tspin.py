"""T-spin detection using the 3-corner rule.

A lock is a T-spin if:
  1. The piece is a T
  2. The last action was a rotation (not a move or drop)
  3. At least 3 of the 4 corners of the T's 3x3 bounding box are
     occupied (out of bounds counts as occupied)

Full vs mini:
  - If the rotation used the last SRS kick offset (index 4), always
    a full T-spin — the piece was kicked hard enough that it must
    be intentional
  - Otherwise, full if both "front" corners are occupied; mini if
    only one is

"Front" corners are the two opposite the T's stem. Rotation 0 points
the stem up, so front corners are at the bottom. Rotation 1 points
right, so front corners are on the left. Etc.
"""

from __future__ import annotations

from neon_drop.core.board import Board
from neon_drop.core.piece import Piece

# Corners of the 3x3 bounding box, in (dx, dy) from piece origin.
_ALL_CORNERS = ((0, 0), (2, 0), (0, 2), (2, 2))

# Front corners by rotation state.
_FRONT_CORNERS = {
    0: ((0, 2), (2, 2)),
    1: ((0, 0), (0, 2)),
    2: ((0, 0), (2, 0)),
    3: ((2, 0), (2, 2)),
}

# SRS kick tables have 5 offsets (indices 0-4). The last one promotes
# any T-spin to full.
_LAST_KICK_INDEX = 4


def _is_occupied(board: Board, x: int, y: int) -> bool:
    if x < 0 or x >= board.cols:
        return True
    if y >= board.rows:
        return True
    if y < 0:
        return False
    return board.grid[y][x] is not None


def detect_tspin(
    board: Board,
    piece: Piece,
    last_action_was_rotation: bool,
    last_kick_index: int,
) -> tuple[bool, bool]:
    """Return (is_tspin, is_mini). Both False if not a T-spin."""
    if piece.kind != "T":
        return False, False
    if not last_action_was_rotation:
        return False, False

    occupied = sum(1 for dx, dy in _ALL_CORNERS if _is_occupied(board, piece.x + dx, piece.y + dy))
    if occupied < 3:
        return False, False

    if last_kick_index >= _LAST_KICK_INDEX:
        return True, False

    front_hits = sum(
        1
        for dx, dy in _FRONT_CORNERS[piece.rotation]
        if _is_occupied(board, piece.x + dx, piece.y + dy)
    )
    return True, front_hits < 2
