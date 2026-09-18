"""Tests for T-spin detection."""

from neon_drop.core.board import Board
from neon_drop.core.piece import Piece
from neon_drop.core.tspin import detect_tspin


def _fill(board: Board, cells: list[tuple[int, int]]) -> None:
    for x, y in cells:
        board.grid[y][x] = "X"


def test_non_t_piece_never_spins() -> None:
    board = Board()
    _fill(board, [(4, 5), (6, 5), (4, 7)])
    piece = Piece("S", rotation=0, x=4, y=5)
    assert detect_tspin(board, piece, True, 0) == (False, False)


def test_rotation_required() -> None:
    board = Board()
    _fill(board, [(4, 5), (6, 5), (4, 7)])
    piece = Piece("T", rotation=0, x=4, y=5)
    assert detect_tspin(board, piece, False, 0) == (False, False)


def test_two_corners_is_not_a_tspin() -> None:
    board = Board()
    _fill(board, [(4, 5), (6, 5)])
    piece = Piece("T", rotation=0, x=4, y=5)
    assert detect_tspin(board, piece, True, 0) == (False, False)


def test_three_corners_one_front_is_mini() -> None:
    """Rotation 0 front corners are bottom-left and bottom-right.

    Fill both back corners and one front corner → mini.
    """
    board = Board()
    _fill(board, [(4, 5), (6, 5), (4, 7)])
    piece = Piece("T", rotation=0, x=4, y=5)
    is_tspin, is_mini = detect_tspin(board, piece, True, 0)
    assert is_tspin
    assert is_mini


def test_three_corners_two_front_is_full() -> None:
    """Both front corners plus one back corner → full T-spin."""
    board = Board()
    _fill(board, [(4, 5), (4, 7), (6, 7)])
    piece = Piece("T", rotation=0, x=4, y=5)
    is_tspin, is_mini = detect_tspin(board, piece, True, 0)
    assert is_tspin
    assert not is_mini


def test_all_four_corners_is_full() -> None:
    board = Board()
    _fill(board, [(4, 5), (6, 5), (4, 7), (6, 7)])
    piece = Piece("T", rotation=0, x=4, y=5)
    is_tspin, is_mini = detect_tspin(board, piece, True, 0)
    assert is_tspin
    assert not is_mini


def test_last_kick_promotes_mini_to_full() -> None:
    """Mini corner layout, but a 5th-offset kick forces full T-spin."""
    board = Board()
    _fill(board, [(4, 5), (6, 5), (4, 7)])
    piece = Piece("T", rotation=0, x=4, y=5)
    is_tspin, is_mini = detect_tspin(board, piece, True, 4)
    assert is_tspin
    assert not is_mini


def test_out_of_bounds_counts_as_occupied() -> None:
    """T piece pressed against the left wall with two top corners filled."""
    board = Board()
    # T at x=-1 — its left side is off-board.
    # Corners at (-1, 5), (1, 5), (-1, 7), (1, 7).
    _fill(board, [(1, 5), (1, 7)])
    piece = Piece("T", rotation=0, x=-1, y=5)
    is_tspin, is_mini = detect_tspin(board, piece, True, 0)
    # Left corners are off-board → 2 occupied; right corners filled → 2
    # more. Total 4 → full T-spin.
    assert is_tspin
    assert not is_mini
