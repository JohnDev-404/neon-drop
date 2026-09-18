"""Game state machine: board + bag + piece + gravity + scoring."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto

from neon_drop.core import scoring
from neon_drop.core.bag import Bag
from neon_drop.core.board import Board
from neon_drop.core.piece import Piece, spawn
from neon_drop.core.scoring import ClearType, ComboState, ScoreResult
from neon_drop.core.srs import attempt_rotation
from neon_drop.core.tspin import detect_tspin


class GameState(Enum):
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()


BASE_GRAVITY: float = scoring.gravity_for_level(1)
_NEXT_QUEUE_SIZE = 5
LOCK_DELAY_SECONDS: float = 0.5
MAX_LOCK_RESETS: int = 15
CLEAR_ANIMATION_SECONDS: float = 0.30


# --- Events ------------------------------------------------------------


@dataclass
class LockEvent:
    cells: tuple[tuple[int, int], ...]
    kind: str


@dataclass
class LineClearEvent:
    rows: tuple[int, ...]
    count: int
    clear_type: ClearType


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

    lock_timer: float = LOCK_DELAY_SECONDS
    lock_resets: int = 0
    lowest_y: int = 0

    clearing: bool = False
    clearing_rows: tuple[int, ...] = ()
    clear_timer: float = 0.0
    _pending_clear_rows: tuple[int, ...] = ()
    _pending_clear_type: ClearType = ClearType.NONE

    # T-spin tracking.
    last_action_was_rotation: bool = False
    last_kick_index: int = 0

    # Scoring.
    lines: int = 0
    score: int = 0
    level: int = 1
    combo_state: ComboState = field(default_factory=ComboState)
    last_clear: ScoreResult | None = None

    events: list[GameEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.rng_seed is not None:
            self.bag = Bag(random.Random(self.rng_seed))
        self.gravity_interval = scoring.gravity_for_level(self.level)
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
        self.gravity_timer = 0.0
        self.lock_timer = LOCK_DELAY_SECONDS
        self.lock_resets = 0
        self.lowest_y = piece.y
        self.last_action_was_rotation = False
        self.last_kick_index = 0

    # --- movement -------------------------------------------------------

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
            self.lowest_y = candidate.y
            self.lock_resets = 0
            self.lock_timer = LOCK_DELAY_SECONDS
        else:
            self._reset_lock_timer()
        return True

    def move(self, dx: int) -> bool:
        if self._try_move(dx, 0):
            self.last_action_was_rotation = False
            return True
        return False

    def soft_drop(self) -> bool:
        if self._try_move(0, 1):
            self.last_action_was_rotation = False
            return True
        return False

    def rotate(self, direction: int) -> bool:
        if not self._can_act():
            return False
        result = attempt_rotation(self.current, direction, self.board)
        if result is None:
            return False
        self.current = result.piece
        self.last_action_was_rotation = True
        self.last_kick_index = result.kick_index
        self._reset_lock_timer()
        return True

    def hard_drop(self) -> int:
        if not self._can_act():
            return 0
        self.last_action_was_rotation = False
        start_y = self.current.y
        while self._try_move(0, 1):
            pass
        distance = self.current.y - start_y
        cells = self.current.cells()
        kind = self.current.kind
        self.events.append(HardDropEvent(distance, cells, kind))
        self._lock_piece()
        return distance

    # --- locking and clearing -------------------------------------------

    def _lock_piece(self) -> None:
        if self.current is None:
            return

        cells = self.current.cells()
        kind = self.current.kind

        # T-spin check uses the piece's pre-lock position.
        is_tspin, is_mini = detect_tspin(
            self.board,
            self.current,
            self.last_action_was_rotation,
            self.last_kick_index,
        )

        self.board.lock(cells, kind)
        self.events.append(LockEvent(cells, kind))

        full = self.board.full_rows()
        line_count = len(full)

        # Perfect clear: after removing full rows, is the board empty?
        full_set = set(full)
        will_be_empty = all(
            all(cell is None for cell in self.board.grid[y])
            for y in range(self.board.rows)
            if y not in full_set
        )

        result, new_combo = scoring.evaluate(
            lines_cleared=line_count,
            is_tspin=is_tspin,
            is_mini=is_mini,
            board_is_empty_after=will_be_empty,
            level=self.level,
            combo_state=self.combo_state,
        )
        self.combo_state = new_combo
        self.score += result.points
        self.last_clear = result

        if line_count:
            self.lines += line_count
            new_level = scoring.level_for_lines(self.lines)
            if new_level != self.level:
                self.level = new_level
                self.gravity_interval = scoring.gravity_for_level(self.level)

            self.clearing = True
            self.clearing_rows = tuple(full)
            self.clear_timer = CLEAR_ANIMATION_SECONDS
            self._pending_clear_rows = tuple(full)
            self._pending_clear_type = result.clear_type
            self.current = None
        else:
            self._spawn_next()

    def _finish_clear(self) -> None:
        rows = self._pending_clear_rows
        count = self.board.clear_rows(list(rows))
        self.events.append(LineClearEvent(rows, count, self._pending_clear_type))
        self.clearing = False
        self.clearing_rows = ()
        self._pending_clear_rows = ()
        self._pending_clear_type = ClearType.NONE
        self._spawn_next()

    # --- per-frame update -----------------------------------------------

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

        self.gravity_timer += dt
        while self.gravity_timer >= self.gravity_interval:
            self.gravity_timer -= self.gravity_interval
            if not self._try_move(0, 1):
                break

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

    # --- events ---------------------------------------------------------

    def drain_events(self) -> list[GameEvent]:
        events = self.events
        self.events = []
        return events

    # --- pause / restart ------------------------------------------------

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
        self._pending_clear_type = ClearType.NONE
        self.last_action_was_rotation = False
        self.last_kick_index = 0
        self.lines = 0
        self.score = 0
        self.level = 1
        self.gravity_interval = scoring.gravity_for_level(1)
        self.combo_state = ComboState()
        self.last_clear = None
        self.state = GameState.PLAYING
        self.events = []
        self._refill_queue()
        self._spawn_next()
