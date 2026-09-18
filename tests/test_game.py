"""Tests for the Game state machine."""

from neon_drop import config
from neon_drop.core.game import Game, GameState
from neon_drop.core.piece import Piece


def test_new_game_has_piece_and_queue() -> None:
    game = Game(rng_seed=0)
    assert game.current is not None
    assert game.state == GameState.PLAYING
    assert len(game.next_queue) >= 5


def test_move_left_shifts_piece() -> None:
    game = Game(rng_seed=0)
    assert game.current is not None
    x0 = game.current.x
    assert game.move(-1)
    assert game.current.x == x0 - 1


def test_move_left_blocked_at_wall() -> None:
    game = Game(rng_seed=0)
    while game.move(-1):
        pass
    assert not game.move(-1)


def test_hard_drop_locks_and_spawns_next() -> None:
    game = Game(rng_seed=0)
    assert game.current is not None
    first_kind = game.current.kind
    first_x = game.current.x
    game.hard_drop()
    # A fresh piece is now active.
    assert game.current is not None
    # The first kind's cells appear somewhere on the board.
    found = any(first_kind in row for row in game.board.grid)
    assert found
    assert first_x >= 0  # x doesn't matter after lock; just a smoke check


def test_tick_moves_piece_down_eventually() -> None:
    game = Game(rng_seed=0)
    assert game.current is not None
    y0 = game.current.y
    # Tick for more than one gravity interval.
    game.tick(game.gravity_interval + 0.001)
    assert game.current.y == y0 + 1


def test_clearing_a_row_increments_lines_and_score() -> None:
    game = Game(rng_seed=0)
    bottom = game.board.rows - 1
    for x in range(config.COLS):
        game.board.grid[bottom][x] = "I"
    game.board.grid[bottom][4] = None
    # Vertical I (rotation 1) spans columns piece.x+3, so set piece.x=1
    # to target column 4.
    game.current = Piece("I", rotation=1, x=1, y=bottom - 3)
    game.hard_drop()
    assert game.lines == 1
    assert game.score == 100


def test_game_over_when_spawn_blocked() -> None:
    game = Game(rng_seed=0)
    # Fill the spawn region completely.
    for y in range(config.HIDDEN_ROWS):
        for x in range(config.COLS):
            game.board.grid[y][x] = "I"
    game._spawn_next()
    assert game.state == GameState.GAME_OVER
    assert game.current is None


def test_pause_toggle() -> None:
    game = Game(rng_seed=0)
    game.toggle_pause()
    assert game.state == GameState.PAUSED
    game.toggle_pause()
    assert game.state == GameState.PLAYING


def test_reset_clears_state() -> None:
    game = Game(rng_seed=0)
    game.hard_drop()
    game.reset()
    assert game.lines == 0
    assert game.score == 0
    assert game.state == GameState.PLAYING
    assert game.current is not None
    assert all(c is None for row in game.board.grid for c in row)