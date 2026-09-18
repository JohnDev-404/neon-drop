"""Game state machine: board + bag + piece + gravity + lock delay."""

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


# Seconds between automatic downward steps. Single fixed value for now;
# a level-based curve lands with scoring in M5.
BASE_GRAVITY: float = 0.5

# Score for clearing N rows at once.
_CLEAR_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}

# How many pieces to keep queued for the preview.
_NEXT_QUEUE_SIZE = 5

# Lock delay: how long a landed piece waits before locking. Successful
# moves/rotations reset the timer, up to MAX_LOCK_RESETS times.
LOCK_DELAY_SECONDS: float = 0.5
MAX_LOCK_RESETS: int = 15

# Line clear animation duration. The board freezes for this long while
# full rows flash; then they vanish and the next piece spawns.
CLEAR_ANIMATION_SECONDS: float = 0.30


# --- Events -------------------------------------------------------------
# The Game emits these each frame via drain_events(). The UI layer reads
# them to trigger particles, shake, and sound. Core logic stays agnostic
# of visuals.


@dataclass
class LockEvent:
    cells: tuple[tuple[int, int], ...]
    kind: str


@dataclass
class LineClearEvent:
    rows: tuple[int, ...]
    count: int


@dataclass
class HardDropEvent:
    distance: int
    cells: tuple[tuple[int, int], ...]
    kind: str


GameEvent = LockEvent | LineClearEvent | HardDropEvent


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

    # Lock delay state.
    lock_timer: float = LOCK_DELAY_SECONDS
    lock_resets: int = 0
    lowest_y: int = 0

    # Line clear animation state.
    clearing: bool = False
    clearing_rows: tuple[int, ...] = ()
    clear_timer: float = 0.0
    _pending_clear_rows: tuple[int, ...] = ()

    lines: int = 0
    score: int = 0
    events: list[GameEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.rng_seed is not None:
            self.bag = Bag(random.Random(self.rng_seed))
        self._refill_queue()
        self._spawn_next()

    # --- setup -----------------------------------------------------------

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
        self.gravity_timer = 0.0
        self.lock_timer = LOCK_DELAY_SECONDS
        self.lock_resets = 0
        self.lowest_y = piece.y

    # --- movement --------------------------------------------------------

    def _can_act(self) -> bool:
        return self.state == GameState.PLAYING and not self.clearing and self.current is not None

    def _reset_lock_timer(self) -> None:
        if self.lock_resets < MAX_LOCK_RESETS:
            self.lock_timer = LOCK_DELAY_SECONDS
            self.lock_resets += 1

    def _try_move(self, dx: int, dy: int) -> bool:
        if not self._can_act():
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
        if candidate.y > self.lowest_y:
            # Reached a new lowest row — reset the lock-reset budget.
            self.lowest_y = candidate.y
            self.lock_resets = 0
            self.lock_timer = LOCK_DELAY_SECONDS
        else:
            # Sideways or upward move — counts against the budget.
            self._reset_lock_timer()
        return True

    def move(self, dx: int) -> bool:
        return self._try_move(dx, 0)

    def soft_drop(self) -> bool:
        return self._try_move(0, 1)

    def rotate(self, direction: int) -> bool:
        if not self._can_act():
            return False
        result = rotate(self.current, direction, self.board)
        if result is None:
            return False
        self.current = result
        self._reset_lock_timer()
        return True

    def hard_drop(self) -> int:
        if not self._can_act():
            return 0
        start_y = self.current.y
        while self._try_move(0, 1):
            pass
        distance = self.current.y - start_y
        cells = self.current.cells()
        kind = self.current.kind
        self.events.append(HardDropEvent(distance, cells, kind))
        # Hard drop bypasses lock delay.
        self._lock_piece()
        return distance

    # --- locking and clearing --------------------------------------------

    def _lock_piece(self) -> None:
        if self.current is None:
            return
        cells = self.current.cells()
        kind = self.current.kind
        self.board.lock(cells, kind)
        self.events.append(LockEvent(cells, kind))

        full = self.board.full_rows()
        if full:
            self.clearing = True
            self.clearing_rows = tuple(full)
            self.clear_timer = CLEAR_ANIMATION_SECONDS
            self._pending_clear_rows = tuple(full)
            self.current = None
        else:
            self._spawn_next()

    def _finish_clear(self) -> None:
        rows = self._pending_clear_rows
        count = self.board.clear_rows(list(rows))
        self.events.append(LineClearEvent(rows, count))
        self.lines += count
        self.score += _CLEAR_SCORES.get(count, 0)
        self.clearing = False
        self.clearing_rows = ()
        self._pending_clear_rows = ()
        self._spawn_next()

    # --- per-frame update ------------------------------------------------

    def tick(self, dt: float) -> None:
        if self.state != GameState.PLAYING:
            return

        if self.clearing:
            self.clear_timer -= dt
            if self.clear_timer <= 0:
                self._finish_clear()
            return

        if self.current is None:
            return

        # Gravity: step down every gravity_interval seconds. Slow frames
        # may need multiple steps.
        self.gravity_timer += dt
        while self.gravity_timer >= self.gravity_interval:
            self.gravity_timer -= self.gravity_interval
            if not self._try_move(0, 1):
                break

        # Lock delay: if the piece cannot move down, count down toward
        # locking it. Any successful move/rotation reset the timer
        # (bounded by MAX_LOCK_RESETS).
        below = Piece(
            self.current.kind,
            self.current.rotation,
            self.current.x,
            self.current.y + 1,
        )
        if not self.board.is_valid(below.cells()):
            self.lock_timer -= dt
            if self.lock_timer <= 0:
                self._lock_piece()
        else:
            self.lock_timer = LOCK_DELAY_SECONDS

    # --- event drain -----------------------------------------------------

    def drain_events(self) -> list[GameEvent]:
        """Return and clear the event queue. UI calls this each frame."""
        events = self.events
        self.events = []
        return events

    # --- pause / restart -------------------------------------------------

    def toggle_pause(self) -> None:
        if self.state == GameState.PLAYING:
            self.state = GameState.PAUSED
        elif self.state == GameState.PAUSED:
            self.state = GameState.PLAYING

    def reset(self) -> None:
        self.board.reset()
        self.current = None
        self.next_queue = []
        self.gravity_timer = 0.0
        self.lock_timer = LOCK_DELAY_SECONDS
        self.lock_resets = 0
        self.lowest_y = 0
        self.clearing = False
        self.clearing_rows = ()
        self.clear_timer = 0.0
        self._pending_clear_rows = ()
        self.lines = 0
        self.score = 0
        self.state = GameState.PLAYING
        self.events = []
        self._refill_queue()
        self._spawn_next()
