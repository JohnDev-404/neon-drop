"""Global configuration constants.

Anything tunable lives here so we can retune the game's feel without
digging through logic or rendering code.
"""

from __future__ import annotations

from typing import Final

# --- Window ---------------------------------------------------------------

WINDOW_TITLE: Final = "Neon Drop"
WINDOW_WIDTH: Final = 900
WINDOW_HEIGHT: Final = 920
FPS: Final = 60

# --- Board ----------------------------------------------------------------
# Playfield is 10 columns wide, 20 rows visible, 4 rows of buffer above
# (standard "guideline" Tetris dimensions).

COLS: Final = 10
VISIBLE_ROWS: Final = 20
HIDDEN_ROWS: Final = 4
TOTAL_ROWS: Final = VISIBLE_ROWS + HIDDEN_ROWS

CELL_SIZE: Final = 36

BOARD_WIDTH: Final = COLS * CELL_SIZE
BOARD_HEIGHT: Final = VISIBLE_ROWS * CELL_SIZE

# --- Theme (retro pixel + neon) -------------------------------------------

BG_COLOR: Final = (8, 6, 20)
GRID_COLOR: Final = (28, 24, 56)
BORDER_COLOR: Final = (60, 200, 255)
TEXT_COLOR: Final = (232, 232, 255)
ACCENT_COLOR: Final = (255, 60, 180)

# Tetromino palette — indexed by piece letter.
PIECE_COLORS: Final = {
    "I": (0, 240, 255),
    "J": (60, 100, 255),
    "L": (255, 150, 40),
    "O": (255, 220, 60),
    "S": (60, 255, 120),
    "T": (200, 80, 255),
    "Z": (255, 60, 90),
}

# --- Layout ---------------------------------------------------------------
# Three-column composition: HOLD | BOARD | NEXT, all vertically aligned.

BOARD_X: Final = 275
BOARD_Y: Final = 100

HOLD_X: Final = 95
NEXT_X: Final = 675

# Kept for backwards compatibility with existing imports.
HUD_X: Final = HOLD_X
HUD_Y: Final = BOARD_Y