"""Super Rotation System: wall-kick tables and the rotate function.

Kick tables are copied verbatim from the SRS documentation, which uses
a y-UP coordinate system. Our grid is y-DOWN, so we negate the y
component of every offset when applying a kick. Keeping the tables in
canonical form makes them verifiable against any reference online.
"""

from __future__ import annotations

from typing import Final

from neon_drop.core.board import Board
from neon_drop.core.piece import Piece

# Keys are (from_rotation, to_rotation). Values are the offsets to try
# in order; the first that produces a legal position wins.
_JLSTZ_KICKS: Final[dict[tuple[int, int], tuple[tuple[int, int], ...]]] = {
    (0, 1): ((0, 0), (-1, 0), (-1, +1), (0, -2), (-1, -2)),
    (1, 0): ((0, 0), (+1, 0), (+1, -1), (0, +2), (+1, +2)),
    (1, 2): ((0, 0), (+1, 0), (+1, -1), (0, +2), (+1, +2)),
    (2, 1): ((0, 0), (-1, 0), (-1, +1), (0, -2), (-1, -2)),
    (2, 3): ((0, 0), (+1, 0), (+1, +1), (0, -2), (+1, -2)),
    (3, 2): ((0, 0), (-1, 0), (-1, -1), (0, +2), (-1, +2)),
    (3, 0): ((0, 0), (-1, 0), (-1, -1), (0, +2), (-1, +2)),
    (0, 3): ((0, 0), (+1, 0), (+1, +1), (0, -2), (+1, -2)),
}

_I_KICKS: Final[dict[tuple[int, int], tuple[tuple[int, int], ...]]] = {
    (0, 1): ((0, 0), (-2, 0), (+1, 0), (-2, -1), (+1, +2)),
    (1, 0): ((0, 0), (+2, 0), (-1, 0), (+2, +1), (-1, -2)),
    (1, 2): ((0, 0), (-1, 0), (+2, 0), (-1, +2), (+2, -1)),
    (2, 1): ((0, 0), (+1, 0), (-2, 0), (+1, -2), (-2, +1)),
    (2, 3): ((0, 0), (+2, 0), (-1, 0), (+2, +1), (-1, -2)),
    (3, 2): ((0, 0), (-2, 0), (+1, 0), (-2, -1), (+1, +2)),
    (3, 0): ((0, 0), (+1, 0), (-2, 0), (+1, -2), (-2, +1)),
    (0, 3): ((0, 0), (-1, 0), (+2, 0), (-1, +2), (+2, -1)),
}

CW: Final = 1
CCW: Final = -1


def _kick_table(kind: str):
    if kind == "I":
        return _I_KICKS
    if kind == "O":
        return None
    return _JLSTZ_KICKS


def rotate(piece: Piece, direction: int, board: Board) -> Piece | None:
    """Attempt to rotate `piece`. +1 is clockwise, -1 is counterclockwise.

    Returns a new Piece at the first legal kick offset, or None if every
    offset is blocked.
    """
    if direction not in (CW, CCW):
        raise ValueError(f"direction must be {CW} or {CCW}, got {direction}")

    new_rotation = (piece.rotation + direction) % 4
    table = _kick_table(piece.kind)

    if table is None:
        # O piece: cells identical across rotations, (0, 0) always fits.
        return Piece(piece.kind, new_rotation, piece.x, piece.y)

    for dx, dy_up in table[(piece.rotation, new_rotation)]:
        dy = -dy_up  # convert from doc y-up to our y-down grid
        candidate = Piece(piece.kind, new_rotation, piece.x + dx, piece.y + dy)
        if board.is_valid(candidate.cells()):
            return candidate
    return None
