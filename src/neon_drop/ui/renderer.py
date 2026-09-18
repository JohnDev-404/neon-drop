"""Drawing routines for the board, cells, and pieces."""

from __future__ import annotations

import math

import pygame

from neon_drop import config
from neon_drop.core.board import Board
from neon_drop.core.piece import Piece
from neon_drop.ui import theme

CELL = config.CELL_SIZE
_GLOW_PAD = 4
_FIRST_VISIBLE_ROW = config.HIDDEN_ROWS


def _cell_rect(col: int, visible_row: int, origin_x: int, origin_y: int) -> pygame.Rect:
    return pygame.Rect(
        origin_x + col * CELL,
        origin_y + visible_row * CELL,
        CELL,
        CELL,
    )


def _visible_cells(piece: Piece):
    for col, row in piece.cells():
        if row >= _FIRST_VISIBLE_ROW:
            yield col, row - _FIRST_VISIBLE_ROW


def draw_cell(
    surface: pygame.Surface,
    rect: pygame.Rect,
    kind: str,
    *,
    glow: bool = True,
) -> None:
    """Draw one pixel-art tetromino cell with a neon halo."""
    color = theme.cell_color(kind)

    if glow:
        glow_rect = rect.inflate(_GLOW_PAD * 2, _GLOW_PAD * 2)
        glow_surf = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*color, 70), glow_surf.get_rect())
        surface.blit(glow_surf, glow_rect.topleft, special_flags=pygame.BLEND_RGBA_ADD)

    pygame.draw.rect(surface, color, rect)
    hi = theme.cell_highlight(kind)
    sh = theme.cell_shadow(kind)
    pygame.draw.line(surface, hi, rect.topleft, rect.topright, 3)
    pygame.draw.line(surface, hi, rect.topleft, rect.bottomleft, 3)
    pygame.draw.line(surface, sh, rect.bottomleft, rect.bottomright, 3)
    pygame.draw.line(surface, sh, rect.topright, rect.bottomright, 3)


def draw_ghost_cell(
    surface: pygame.Surface,
    rect: pygame.Rect,
    kind: str,
    pulse: float,
) -> None:
    """Ghost outline. `pulse` is 0..1 and modulates brightness."""
    r, g, b = theme.cell_color(kind)
    boost = 0.6 + 0.4 * pulse
    dim = (int(r * boost // 3), int(g * boost // 3), int(b * boost // 3))
    pygame.draw.rect(surface, dim, rect, width=2)


def draw_playfield(
    surface: pygame.Surface,
    board: Board,
    *,
    offset: tuple[int, int] = (0, 0),
    clearing_rows: tuple[int, ...] = (),
    flash_amount: float = 0.0,
    hide_clearing: bool = False,
) -> None:
    """Draw grid, background, border, and every locked cell.

    `clearing_rows` are rows currently in the clear animation; when
    `flash_amount > 0` they get a white additive overlay. When
    `hide_clearing` is True, their cells are skipped entirely (used
    during the second half of the animation, when they've visually
    vanished but haven't been removed from the model yet).
    """
    ox, oy = offset
    x = config.BOARD_X + ox
    y = config.BOARD_Y + oy
    w = board.cols * CELL
    h = config.VISIBLE_ROWS * CELL
    field = pygame.Rect(x, y, w, h)

    pygame.draw.rect(surface, theme.FIELD_BG, field)

    for col in range(board.cols + 1):
        px = x + col * CELL
        pygame.draw.line(surface, theme.GRID, (px, y), (px, y + h))
    for row in range(config.VISIBLE_ROWS + 1):
        py = y + row * CELL
        pygame.draw.line(surface, theme.GRID, (x, py), (x + w, py))

    pygame.draw.rect(surface, theme.BORDER, field, width=2)

    clearing_set = set(clearing_rows)
    for row in range(_FIRST_VISIBLE_ROW, board.rows):
        if hide_clearing and row in clearing_set:
            continue
        for col in range(board.cols):
            kind = board.grid[row][col]
            if kind is not None:
                rect = _cell_rect(col, row - _FIRST_VISIBLE_ROW, x, y)
                draw_cell(surface, rect, kind)

    if clearing_rows and flash_amount > 0:
        for row in clearing_rows:
            visible_row = row - _FIRST_VISIBLE_ROW
            if visible_row < 0:
                continue
            flash_rect = pygame.Rect(x, y + visible_row * CELL, w, CELL)
            alpha = int(220 * max(0.0, min(1.0, flash_amount)))
            flash_surf = pygame.Surface(flash_rect.size, pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, alpha))
            surface.blit(flash_surf, flash_rect.topleft, special_flags=pygame.BLEND_RGBA_ADD)


def draw_piece(
    surface: pygame.Surface,
    piece: Piece,
    *,
    offset: tuple[int, int] = (0, 0),
) -> None:
    ox, oy = offset
    for col, visible_row in _visible_cells(piece):
        rect = _cell_rect(col, visible_row, config.BOARD_X + ox, config.BOARD_Y + oy)
        draw_cell(surface, rect, piece.kind)


def draw_ghost(
    surface: pygame.Surface,
    piece: Piece,
    board: Board,
    *,
    offset: tuple[int, int] = (0, 0),
) -> None:
    ghost = piece.copy()
    while True:
        candidate = Piece(ghost.kind, ghost.rotation, ghost.x, ghost.y + 1)
        if not board.is_valid(candidate.cells()):
            break
        ghost = candidate

    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.006)
    ox, oy = offset
    for col, visible_row in _visible_cells(ghost):
        rect = _cell_rect(col, visible_row, config.BOARD_X + ox, config.BOARD_Y + oy)
        draw_ghost_cell(surface, rect, piece.kind, pulse)
