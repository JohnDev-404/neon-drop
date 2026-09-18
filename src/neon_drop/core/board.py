"""The playfield grid: collision, locking, and line clears."""

from __future__ import annotations

from neon_drop import config


class Board:
    """A grid of cells, each empty (None) or holding a piece kind letter.

    Row 0 is the topmost buffer row; row TOTAL_ROWS-1 is the floor.
    Only the bottom VISIBLE_ROWS rows are drawn to the screen.
    """

    def __init__(self, cols: int = config.COLS, rows: int = config.TOTAL_ROWS) -> None:
        self.cols = cols
        self.rows = rows
        self.grid: list[list[str | None]] = [[None] * cols for _ in range(rows)]

    def is_valid(self, cells) -> bool:
        """True if every (x, y) is in-bounds and unoccupied.

        Cells with y < 0 are treated as above the board and allowed,
        so kicks that push a piece partly off the top still work.
        """
        for x, y in cells:
            if x < 0 or x >= self.cols:
                return False
            if y >= self.rows:
                return False
            if y >= 0 and self.grid[y][x] is not None:
                return False
        return True

    def lock(self, cells, kind: str) -> None:
        """Permanently place a piece's cells onto the board."""
        for x, y in cells:
            if 0 <= y < self.rows and 0 <= x < self.cols:
                self.grid[y][x] = kind

    def full_rows(self) -> list[int]:
        return [y for y in range(self.rows) if all(c is not None for c in self.grid[y])]

    def clear_rows(self, rows: list[int]) -> int:
        """Remove the given rows and insert empty rows at the top.

        Rows are treated as original grid positions; the entire grid is
        rebuilt in one pass so that shift order never matters.
        """
        if not rows:
            return 0
        to_clear = set(rows)
        kept = [row for y, row in enumerate(self.grid) if y not in to_clear]
        blanks = [[None] * self.cols for _ in range(len(rows))]
        self.grid = blanks + kept
        return len(rows)

    def clear_full_rows(self) -> int:
        """Convenience: find and clear every full row. Returns count."""
        return self.clear_rows(self.full_rows())

    def reset(self) -> None:
        for y in range(self.rows):
            for x in range(self.cols):
                self.grid[y][x] = None
