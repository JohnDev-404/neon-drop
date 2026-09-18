"""Tests for SRS rotation and wall kicks."""

from neon_drop.core.board import Board
from neon_drop.core.piece import Piece
from neon_drop.core.srs import CCW, CW, rotate


def test_rotate_in_open_space_uses_zero_kick() -> None:
    board = Board()
    piece = Piece("T", rotation=0, x=4, y=5)
    result = rotate(piece, CW, board)
    assert result is not None
    assert result.rotation == 1
    assert (result.x, result.y) == (4, 5)


def test_rotate_counterclockwise_in_open_space() -> None:
    board = Board()
    piece = Piece("T", rotation=0, x=4, y=5)
    result = rotate(piece, CCW, board)
    assert result is not None
    assert result.rotation == 3
    assert (result.x, result.y) == (4, 5)


def test_t_piece_kicked_off_left_wall() -> None:
    """T at x=-1 rotates CW; the +1 x kick is the first that fits."""
    board = Board()
    piece = Piece("T", rotation=1, x=-1, y=5)
    result = rotate(piece, CW, board)
    assert result is not None
    assert result.rotation == 2
    assert result.x == 0


def test_i_piece_kicked_at_left_wall() -> None:
    """Vertical I at x=-2 rotates CW; only the +2 x kick fits."""
    board = Board()
    piece = Piece("I", rotation=1, x=-2, y=5)
    result = rotate(piece, CW, board)
    assert result is not None
    assert result.rotation == 2
    assert result.x == 0


def test_rotation_blocked_returns_none() -> None:
    """Fill the entire board except the piece's own cells."""
    board = Board()
    for y in range(board.rows):
        for x in range(board.cols):
            board.grid[y][x] = "I"
    piece = Piece("T", rotation=0, x=4, y=5)
    for x, y in piece.cells():
        board.grid[y][x] = None
    assert rotate(piece, CW, board) is None


def test_o_piece_rotation_preserves_cells() -> None:
    board = Board()
    piece = Piece("O", rotation=0, x=4, y=5)
    result = rotate(piece, CW, board)
    assert result is not None
    assert set(result.cells()) == set(piece.cells())
