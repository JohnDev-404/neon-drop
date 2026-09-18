"""Tests for the Board: collision, locking, line clears."""

from neon_drop import config
from neon_drop.core.board import Board


def test_new_board_is_empty() -> None:
    board = Board()
    assert board.cols == config.COLS
    assert board.rows == config.TOTAL_ROWS
    for row in board.grid:
        assert all(c is None for c in row)


def test_is_valid_accepts_empty_in_bounds_cells() -> None:
    board = Board()
    assert board.is_valid([(0, 0), (5, 5), (board.cols - 1, board.rows - 1)])


def test_is_valid_rejects_out_of_bounds() -> None:
    board = Board()
    assert not board.is_valid([(-1, 5)])
    assert not board.is_valid([(board.cols, 5)])
    assert not board.is_valid([(5, board.rows)])


def test_is_valid_allows_cells_above_board() -> None:
    board = Board()
    assert board.is_valid([(5, -1), (5, -100)])


def test_is_valid_rejects_occupied_cells() -> None:
    board = Board()
    board.grid[5][5] = "T"
    assert not board.is_valid([(5, 5)])


def test_lock_writes_cells() -> None:
    board = Board()
    board.lock([(1, 2), (3, 4)], "T")
    assert board.grid[2][1] == "T"
    assert board.grid[4][3] == "T"


def test_full_rows_lists_completed_lines() -> None:
    board = Board()
    board.grid[10] = ["I"] * board.cols
    board.grid[15] = ["I"] * board.cols
    assert board.full_rows() == [10, 15]


def test_clear_rows_shifts_above_content_down() -> None:
    board = Board()
    board.grid[9][0] = "T"
    board.grid[10] = ["I"] * board.cols
    removed = board.clear_rows([10])
    assert removed == 1
    # The lone cell at row 9 should now sit at row 10.
    assert board.grid[10][0] == "T"
    # A fresh empty row appears at the top.
    assert all(c is None for c in board.grid[0])


def test_clear_full_rows_removes_all() -> None:
    board = Board()
    board.grid[10] = ["I"] * board.cols
    board.grid[11] = ["I"] * board.cols
    board.grid[9][0] = "T"
    assert board.clear_full_rows() == 2
    # Row 9's content shifted down by two.
    assert board.grid[11][0] == "T"
