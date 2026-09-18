"""Tests for scoring, combo, B2B, perfect clear, level, gravity."""

from neon_drop.core.scoring import (
    ClearType,
    ComboState,
    classify,
    evaluate,
    gravity_for_level,
    level_for_lines,
)


def _eval(lines, *, is_tspin=False, is_mini=False, pc=False, level=1, state=None):
    if state is None:
        state = ComboState()
    return evaluate(lines, is_tspin, is_mini, pc, level, state)


# --- classify -----------------------------------------------------------


def test_classify_basics() -> None:
    assert classify(0, False, False) is ClearType.NONE
    assert classify(1, False, False) is ClearType.SINGLE
    assert classify(2, False, False) is ClearType.DOUBLE
    assert classify(3, False, False) is ClearType.TRIPLE
    assert classify(4, False, False) is ClearType.TETRIS


def test_classify_tspins() -> None:
    assert classify(0, True, False) is ClearType.T_SPIN
    assert classify(1, True, False) is ClearType.T_SPIN_SINGLE
    assert classify(2, True, False) is ClearType.T_SPIN_DOUBLE
    assert classify(3, True, False) is ClearType.T_SPIN_TRIPLE
    assert classify(1, True, True) is ClearType.T_SPIN_MINI_SINGLE
    assert classify(2, True, True) is ClearType.T_SPIN_MINI_DOUBLE


# --- base scoring -------------------------------------------------------


def test_single_at_level_1() -> None:
    result, _ = _eval(1)
    assert result.points == 100
    assert result.clear_type is ClearType.SINGLE


def test_tetris_at_level_1() -> None:
    result, _ = _eval(4)
    assert result.points == 800


def test_score_scales_with_level() -> None:
    result, _ = _eval(4, level=3)
    assert result.points == 2400  # 800 * 3


def test_tspin_single_scores_higher_than_tetris_at_same_level() -> None:
    tspin, _ = _eval(1, is_tspin=True)
    tetris, _ = _eval(4)
    assert tspin.points == 800
    assert tetris.points == 800


# --- combo --------------------------------------------------------------


def test_first_clear_has_no_combo_bonus() -> None:
    result, state = _eval(1)
    assert result.points == 100
    assert state.combo == 0


def test_second_consecutive_clear_gets_combo_bonus() -> None:
    _, state = _eval(1)
    result, state = _eval(1, state=state)
    # base 100 + 50 * 1 * 1 = 150
    assert result.points == 150
    assert state.combo == 1


def test_combo_resets_on_plain_lock() -> None:
    _, state = _eval(1)
    _, state = _eval(1, state=state)
    assert state.combo == 1
    _, state = _eval(0, state=state)
    assert state.combo == -1


# --- back-to-back -------------------------------------------------------


def test_b2b_tetris() -> None:
    # First tetris: no b2b bonus, chain becomes active.
    r1, state = _eval(4)
    assert r1.points == 800
    assert state.b2b_active

    # Second tetris: 1.5x bonus.
    r2, state = _eval(4, state=state)
    assert r2.points == int(800 * 1.5) + 50 * 1 * 1  # b2b + combo
    assert r2.is_b2b


def test_b2b_broken_by_single() -> None:
    _, state = _eval(4)  # tetris → b2b active
    assert state.b2b_active
    _, state = _eval(1, state=state)  # single → b2b broken
    assert not state.b2b_active


# --- perfect clear ------------------------------------------------------


def test_perfect_clear_single() -> None:
    result, _ = _eval(1, pc=True)
    # base 100 + PC bonus 800 = 900
    assert result.points == 900
    assert result.is_perfect_clear


# --- level and gravity --------------------------------------------------


def test_level_for_lines() -> None:
    assert level_for_lines(0) == 1
    assert level_for_lines(9) == 1
    assert level_for_lines(10) == 2
    assert level_for_lines(25) == 3


def test_gravity_decreases_with_level() -> None:
    assert gravity_for_level(1) > gravity_for_level(5) > gravity_for_level(15)


def test_gravity_at_level_1_matches_previous_default() -> None:
    assert gravity_for_level(1) == 0.5
