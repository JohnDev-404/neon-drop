"""Tests for tetromino definitions and the Piece class."""

import pytest

from neon_drop.core.piece import PIECES, SHAPES, Piece


def test_every_piece_has_four_states() -> None:
    for kind in PIECES:
        assert len(SHAPES[kind]) == 4


def test_every_state_has_four_distinct_cells() -> None:
    for kind in PIECES:
        for state in SHAPES[kind]:
            assert len(state) == 4
            assert len(set(state)) == 4


def test_cells_translate_by_piece_position() -> None:
    piece = Piece("T", rotation=0, x=5, y=3)
    assert set(piece.cells()) == {
        (6, 3),
        (5, 4),
        (6, 4),
        (7, 4),
    }


def test_o_rotation_states_are_identical() -> None:
    assert SHAPES["O"][0] == SHAPES["O"][1] == SHAPES["O"][2] == SHAPES["O"][3]


def test_invalid_kind_raises() -> None:
    with pytest.raises(ValueError):
        Piece("Q")


def test_invalid_rotation_raises() -> None:
    with pytest.raises(ValueError):
        Piece("T", rotation=4)
