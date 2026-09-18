"""Game state machine: board + bag + current piece + gravity."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto

from neon_drop.core.bag import Bag
from neon_drop.core.board import Board
from neon_drop.core.piece import Piece, spawn
from neon_drop.core.srs import rotate


class GameState(Enum):
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()


# Seconds between automatic downward steps. Single fixed value for M3;
# a level-based speed curve lands with the real scoring in M5.
BASE_GRAVITY: float = 0.5

# Score for clearing N rows at once (single/double/triple/tetris).
_CLEAR_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}

# How many pieces to keep queued up for the preview.
_NEXT_QUEUE_SIZE = 5


@dataclass
class Game:
    """The full game state and the rules that drive it."""

    board: Board = field(default_factory=Board)
    bag: Bag = field(default_factory=Bag)
    rng_seed: int | None = None

    state: GameState = GameState.PLAYING
    current: Piece | None = None
    next_queue: list[str] = field(default_factory=list)

    gravity_timer: float = 0.0
    gravity_interval: float = BASE_GRAVITY

    lines: int = 0
    score: int = 0

    def __post_init__(self) -> None:
        if self.rng_seed is not None:
            self.bag = Bag(random.Random(self.rng_seed))
        self._refill_queue()
        self._spawn_next()

    # --- setup ----------------------------------------------------------

    def _refill_queue(self) -> None:
        while len(self.next_queue) < _NEXT_QUEUE_SIZE:
            self.next_queue.append(self.bag.next())

    def _spawn_next(self) -> None:
        kind = self.next_queue.pop(0)
        self._refill_queue()
        piece = spawn(kind)
        if not self.board.is_valid(piece.cells()):
            self.current = None
            self.state = GameState.GAME_OVER
            return
        self.current = piece

    # --- movement -------------------------------------------------------

    def _try_move(self, dx: int, dy: int) -> bool:
        if self.current is None:
            return False
        candidate = Piece(
            self.current.kind,
            self.current.rotation,
            self.current.x + dx,
            self.current.y + dy,
        )
        if not self.board.is_valid(candidate.cells()):
            return False
        self.current = candidate
        return True

    def move(self, dx: int) -> bool:
        return self._try_move(dx, 0)

    def soft_drop(self) -> bool:
        return self._try_move(0, 1)

    def rotate(self, direction: int) -> bool:
        if self.current is None:
            return False
        result = rotate(self.current, direction, self.board)
        if result is None:
            return False
        self.current = result
        return True

    def hard_drop(self) -> int:
        """Drop the piece to the floor, lock it, spawn the next one."""
        dropped = 0
        while self._try_move(0, 1):
            dropped += 1
        self._lock_piece()
        return dropped

    # --- locking and clearing ------------------------------------------

    def _lock_piece(self) -> None:
        if self.current is None:
            return
        self.board.lock(self.current.cells(), self.current.kind)
        cleared = self.board.clear_full_rows()
        if cleared:
            self.lines += cleared
            self.score += _CLEAR_SCORES.get(cleared, 0)
        self._spawn_next()
        self.gravity_timer = 0.0

    # --- per-frame update ----------------------------------------------

    def tick(self, dt: float) -> None:
        """Advance gravity by dt seconds. Handles multi-step drops."""
        if self.state != GameState.PLAYING or self.current is None:
            return
        self.gravity_timer += dt
        while self.gravity_timer >= self.gravity_interval:
            self.gravity_timer -= self.gravity_interval
            if not self._try_move(0, 1):
                self._lock_piece()
                return

    # --- pause / restart ------------------------------------------------

    def toggle_pause(self) -> None:
        if self.state == GameState.PLAYING:
            self.state = GameState.PAUSED
        elif self.state == GameState.PAUSED:
            self.state = GameState.PLAYING

    def reset(self) -> None:
        """Wipe the board and start a fresh game with the same bag."""
        self.board.reset()
        self.current = None
        self.next_queue = []
        self.gravity_timer = 0.0
        self.lines = 0
        self.score = 0
        self.state = GameState.PLAYING
        self._refill_queue()
        self._spawn_next()
