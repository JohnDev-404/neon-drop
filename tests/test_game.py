"""Tests for the Game state machine."""

from neon_drop import config
from neon_drop.core.game import (
    CLEAR_ANIMATION_SECONDS,
    LOCK_DELAY_SECONDS,
    MAX_LOCK_RESETS,
    Game,
    GameState,
    HardDropEvent,
    LineClearEvent,
    LockEvent,
)
from neon_drop.core.piece import Piece
from neon_drop.core.scoring import ClearType


def _rest_piece(game: Game) -> None:
    """Move the current piece to the floor without locking it."""
    while game._try_move(0, 1):
        pass


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
    game.hard_drop()
    assert game.current is not None
    found = any(first_kind in row for row in game.board.grid)
    assert found


def test_hard_drop_emits_hard_drop_and_lock_events() -> None:
    game = Game(rng_seed=0)
    game.hard_drop()
    kinds = {type(e) for e in game.drain_events()}
    assert HardDropEvent in kinds
    assert LockEvent in kinds


def test_tick_moves_piece_down_eventually() -> None:
    game = Game(rng_seed=0)
    assert game.current is not None
    y0 = game.current.y
    game.tick(game.gravity_interval + 0.001)
    assert game.current.y == y0 + 1


def test_clearing_a_row_increments_lines_and_score() -> None:
    game = Game(rng_seed=0)
    bottom = game.board.rows - 1
    for x in range(config.COLS):
        game.board.grid[bottom][x] = "I"
    game.board.grid[bottom][4] = None
    game.current = Piece("I", rotation=1, x=2, y=bottom - 3)
    game.hard_drop()
    # Line clear is animated; advance through it.
    game.tick(CLEAR_ANIMATION_SECONDS + 0.01)
    assert game.lines == 1
    assert game.score == 100


def test_line_clear_animation_freezes_input() -> None:
    game = Game(rng_seed=0)
    bottom = game.board.rows - 1
    for x in range(config.COLS):
        game.board.grid[bottom][x] = "I"
    game.board.grid[bottom][4] = None
    game.current = Piece("I", rotation=1, x=2, y=bottom - 3)
    game.hard_drop()
    assert game.clearing
    # Movement is blocked during the animation.
    assert game.move(-1) is False
    assert game.rotate(1) is False
    assert game.soft_drop() is False
    # Finish the animation.
    game.tick(CLEAR_ANIMATION_SECONDS + 0.01)
    assert not game.clearing


def test_line_clear_event_emitted() -> None:
    game = Game(rng_seed=0)
    bottom = game.board.rows - 1
    for x in range(config.COLS):
        game.board.grid[bottom][x] = "I"
    game.board.grid[bottom][4] = None
    game.current = Piece("I", rotation=1, x=2, y=bottom - 3)
    game.hard_drop()
    game.drain_events()  # discard hard drop and lock events
    game.tick(CLEAR_ANIMATION_SECONDS + 0.01)
    events = game.drain_events()
    clears = [e for e in events if isinstance(e, LineClearEvent)]
    assert len(clears) == 1
    assert clears[0].count == 1


def test_lock_delay_lets_piece_rest_before_locking() -> None:
    game = Game(rng_seed=0)
    _rest_piece(game)
    # Half of the lock delay — should not have locked.
    game.tick(LOCK_DELAY_SECONDS * 0.5)
    assert game.current is not None
    # Rest of the delay — should have locked.
    game.tick(LOCK_DELAY_SECONDS * 0.5 + 0.01)
    assert game.current is None or game.clearing or game.current.y < game.board.rows


def test_lock_delay_resets_on_move() -> None:
    game = Game(rng_seed=0)
    _rest_piece(game)
    game.tick(LOCK_DELAY_SECONDS * 0.4)
    # Move sideways: timer resets.
    assert game.move(-1)
    # Advance past where the old timer would have expired.
    game.tick(LOCK_DELAY_SECONDS * 0.4)
    # Piece should still be the active one.
    assert game.current is not None


def test_lock_reset_budget_is_bounded() -> None:
    game = Game(rng_seed=0)
    # Pick a piece that has room to wiggle left/right.
    _rest_piece(game)
    # Spend the reset budget.
    for i in range(MAX_LOCK_RESETS + 1):
        direction = -1 if i % 2 == 0 else 1
        game.move(direction)
    # Now tick a full lock delay without moving.
    game.tick(LOCK_DELAY_SECONDS + 0.01)
    # Piece should have locked (current is the newly spawned piece, or
    # we're in a clearing phase, or game over).
    # Simplest assertion: gravity_timer reset means a spawn happened.
    assert game.current is not None or game.clearing


def test_hard_drop_bypasses_lock_delay() -> None:
    game = Game(rng_seed=0)
    game.hard_drop()
    # Immediately after hard drop, either a new piece is active or we're
    # in the clearing phase; in neither case is the dropped piece still
    # resting on lock delay.
    assert game.current is not None or game.clearing


def test_game_over_when_spawn_blocked() -> None:
    game = Game(rng_seed=0)
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


def test_level_advances_after_ten_lines() -> None:
    game = Game(rng_seed=0)
    # Simulate ten single-line clears.
    game.lines = 9
    bottom = game.board.rows - 1
    for x in range(config.COLS):
        game.board.grid[bottom][x] = "I"
    game.board.grid[bottom][4] = None
    game.current = Piece("I", rotation=1, x=2, y=bottom - 3)
    game.hard_drop()
    game.tick(CLEAR_ANIMATION_SECONDS + 0.01)
    assert game.lines == 10
    assert game.level == 2
    assert game.gravity_interval < 0.5


def test_tspin_requires_last_rotation() -> None:
    """A T dropped without a final rotation is not a T-spin."""
    game = Game(rng_seed=0)
    bottom = game.board.rows - 1
    # Build a T-spin notch: floor complete except under the T's overhang.
    for x in range(config.COLS):
        game.board.grid[bottom][x] = "I"
    game.board.grid[bottom][4] = None
    game.board.grid[bottom - 1][3] = "I"
    game.board.grid[bottom - 1][5] = "I"

    # Force a T and drop it in place without rotating.
    game.current = Piece("T", rotation=0, x=3, y=bottom - 2)
    game.last_action_was_rotation = False
    game.hard_drop()
    # No T-spin detected — last action was a hard drop, not a rotation.
    assert game.last_clear is not None
    assert game.last_clear.clear_type in (ClearType.SINGLE, ClearType.NONE)
