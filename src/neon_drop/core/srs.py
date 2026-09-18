"""Super Rotation System: wall-kick tables and the rotate function.

Kick tables are copied verbatim from the SRS documentation, which uses
a y-UP coordinate system. Our grid is y-DOWN, so we negate the y
component of every offset when applying a kick. Keeping the tables in
canonical form makes them verifiable against any reference online.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class RotationResult:
    """The result of a successful rotation, including which kick was used."""

    piece: Piece
    kick_index: int


def attempt_rotation(piece: Piece, direction: int, board: Board) -> RotationResult | None:
    """Like rotate(), but also returns the index of the kick used.

    The kick index matters for T-spin detection: the last offset in the
    SRS tables (index 4) promotes a mini T-spin to a full one.
    """
    if direction not in (CW, CCW):
        raise ValueError(f"direction must be {CW} or {CCW}, got {direction}")

    new_rotation = (piece.rotation + direction) % 4
    table = _kick_table(piece.kind)

    if table is None:
        # O piece: cells identical across rotations, (0, 0) always fits.
        return RotationResult(Piece(piece.kind, new_rotation, piece.x, piece.y), 0)

    for idx, (dx, dy_up) in enumerate(table[(piece.rotation, new_rotation)]):
        dy = -dy_up  # convert from doc y-up to our y-down grid
        candidate = Piece(piece.kind, new_rotation, piece.x + dx, piece.y + dy)
        if board.is_valid(candidate.cells()):
            return RotationResult(candidate, idx)
    return None


def rotate(piece: Piece, direction: int, board: Board) -> Piece | None:
    """Backwards-compatible wrapper around attempt_rotation."""
    result = attempt_rotation(piece, direction, board)
    return result.piece if result else None
