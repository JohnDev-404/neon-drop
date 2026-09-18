"""Scoring: clear types, base values, bonuses, level and gravity curves."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

# Base points per clear type, before level multiplier.
_BASE = {
    "single": 100,
    "double": 300,
    "triple": 500,
    "tetris": 800,
    "tspin": 400,
    "tspin_single": 800,
    "tspin_double": 1200,
    "tspin_triple": 1600,
    "tspin_mini": 100,
    "tspin_mini_single": 200,
    "tspin_mini_double": 400,
}

# Clear types that continue the back-to-back chain.
_DIFFICULT = {
    "tetris",
    "tspin",
    "tspin_single",
    "tspin_double",
    "tspin_triple",
    "tspin_mini",
    "tspin_mini_single",
    "tspin_mini_double",
}

# Perfect-clear bonus by clear type.
_PERFECT_CLEAR = {
    "single": 800,
    "double": 1200,
    "triple": 1800,
    "tetris": 2000,
    "tspin_single": 800,
    "tspin_double": 1200,
    "tspin_triple": 1800,
    "tspin_mini_single": 800,
    "tspin_mini_double": 1200,
}

LINES_PER_LEVEL = 10
_COMBO_BONUS_PER = 50
_B2B_MULTIPLIER = 1.5


class ClearType(Enum):
    NONE = auto()
    SINGLE = auto()
    DOUBLE = auto()
    TRIPLE = auto()
    TETRIS = auto()
    T_SPIN = auto()
    T_SPIN_SINGLE = auto()
    T_SPIN_DOUBLE = auto()
    T_SPIN_TRIPLE = auto()
    T_SPIN_MINI = auto()
    T_SPIN_MINI_SINGLE = auto()
    T_SPIN_MINI_DOUBLE = auto()


_CLEAR_TO_KEY = {
    ClearType.SINGLE: "single",
    ClearType.DOUBLE: "double",
    ClearType.TRIPLE: "triple",
    ClearType.TETRIS: "tetris",
    ClearType.T_SPIN: "tspin",
    ClearType.T_SPIN_SINGLE: "tspin_single",
    ClearType.T_SPIN_DOUBLE: "tspin_double",
    ClearType.T_SPIN_TRIPLE: "tspin_triple",
    ClearType.T_SPIN_MINI: "tspin_mini",
    ClearType.T_SPIN_MINI_SINGLE: "tspin_mini_single",
    ClearType.T_SPIN_MINI_DOUBLE: "tspin_mini_double",
}


@dataclass
class ComboState:
    """Tracks consecutive-clear streaks."""

    combo: int = -1  # -1 = no combo, 0 = first, 1+ = consecutive
    b2b_active: bool = False


@dataclass
class ScoreResult:
    points: int
    clear_type: ClearType
    is_b2b: bool
    is_perfect_clear: bool


def classify(lines: int, is_tspin: bool, is_mini: bool) -> ClearType:
    if is_tspin:
        if is_mini:
            if lines == 0:
                return ClearType.T_SPIN_MINI
            if lines == 1:
                return ClearType.T_SPIN_MINI_SINGLE
            return ClearType.T_SPIN_MINI_DOUBLE
        if lines == 0:
            return ClearType.T_SPIN
        if lines == 1:
            return ClearType.T_SPIN_SINGLE
        if lines == 2:
            return ClearType.T_SPIN_DOUBLE
        return ClearType.T_SPIN_TRIPLE
    if lines == 0:
        return ClearType.NONE
    if lines == 1:
        return ClearType.SINGLE
    if lines == 2:
        return ClearType.DOUBLE
    if lines == 3:
        return ClearType.TRIPLE
    return ClearType.TETRIS


def evaluate(
    lines_cleared: int,
    is_tspin: bool,
    is_mini: bool,
    board_is_empty_after: bool,
    level: int,
    combo_state: ComboState,
) -> tuple[ScoreResult, ComboState]:
    """Compute score and next combo state for a lock event.

    Returns the result and a *new* ComboState; the caller applies both.
    """
    clear_type = classify(lines_cleared, is_tspin, is_mini)
    key = _CLEAR_TO_KEY.get(clear_type)

    new_state = ComboState(combo=combo_state.combo, b2b_active=combo_state.b2b_active)

    is_tspin_no_lines = lines_cleared == 0 and is_tspin

    if lines_cleared == 0 and not is_tspin_no_lines:
        # Plain non-clearing lock: combo resets, b2b untouched.
        new_state.combo = -1
        return ScoreResult(0, clear_type, False, False), new_state

    if lines_cleared > 0:
        new_state.combo += 1

    points = _BASE.get(key, 0) * level

    is_difficult = key in _DIFFICULT
    is_b2b = is_difficult and combo_state.b2b_active
    if is_b2b:
        points = int(points * _B2B_MULTIPLIER)

    # Combo bonus uses the streak *before* this clear, so the first
    # clear in a streak earns nothing extra.
    if lines_cleared > 0 and new_state.combo >= 1:
        points += _COMBO_BONUS_PER * new_state.combo * level

    is_pc = lines_cleared > 0 and board_is_empty_after
    if is_pc:
        points += _PERFECT_CLEAR.get(key, 0) * level

    # B2B chain: difficult clears extend it, normal line clears break it,
    # no-line T-spins also extend it (they're "still" T-spins).
    if is_difficult:
        new_state.b2b_active = True
    elif lines_cleared > 0:
        new_state.b2b_active = False

    return ScoreResult(points, clear_type, is_b2b, is_pc), new_state


def level_for_lines(total_lines: int) -> int:
    """Level derived from total lines. Starts at 1."""
    return 1 + total_lines // LINES_PER_LEVEL


def gravity_for_level(level: int) -> float:
    """Seconds per row at the given level.

    Uses the modern guideline curve, halved so level 1 lands at 0.5 s
    per row (matching our pre-M5 default). Clamped to one frame so the
    game never stalls below rendering rate.
    """
    raw = (0.8 - (level - 1) * 0.007) ** (level - 1)
    return max(raw * 0.5, 1 / 60)
