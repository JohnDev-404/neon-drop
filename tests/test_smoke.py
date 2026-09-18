"""Sanity checks that the package imports and config loads."""

from neon_drop import __version__, config


def test_version_is_string() -> None:
    assert isinstance(__version__, str)
    assert __version__


def test_board_dimensions_are_consistent() -> None:
    assert config.TOTAL_ROWS == config.VISIBLE_ROWS + config.HIDDEN_ROWS
    assert config.BOARD_WIDTH == config.COLS * config.CELL_SIZE
    assert config.BOARD_HEIGHT == config.VISIBLE_ROWS * config.CELL_SIZE


def test_every_piece_has_a_color() -> None:
    for letter in "IJLOSTZ":
        assert letter in config.PIECE_COLORS
