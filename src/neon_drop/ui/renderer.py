"""Drawing routines for the board, cells, and pieces.

Cells are pre-rendered into a small cache; blitting a cached surface is
much cheaper than drawing bevels + glow every frame, and it keeps the
web (pygbag) build smooth.
"""

from __future__ import annotations

import math

import pygame

from neon_drop import config
from neon_drop.core.board import Board
from neon_drop.core.piece import Piece
from neon_drop.ui import theme
from neon_drop.ui.effects import DropAnimation

CELL = config.CELL_SIZE
_FIRST_VISIBLE_ROW = config.HIDDEN_ROWS
_RADIUS = 4
_PAD = 6

_CELL_CACHE: dict[tuple[str, int, bool], pygame.Surface] = {}


def _build_cell(kind: str, size: int, glow: bool) -> pygame.Surface:
    color = theme.cell_color(kind)
    hi = theme.cell_highlight(kind)
    sh = theme.cell_shadow(kind)

    surf = pygame.Surface((size + _PAD * 2, size + _PAD * 2), pygame.SRCALPHA)
    rect = pygame.Rect(_PAD, _PAD, size, size)

    if glow:
        glow_rect = rect.inflate(_PAD * 2, _PAD * 2)
        glow_surf = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            glow_surf,
            (*color, 60),
            glow_surf.get_rect(),
            border_radius=_RADIUS + 2,
        )
        surf.blit(glow_surf, glow_rect.topleft, special_flags=pygame.BLEND_RGBA_ADD)

    # Chunky rounded cell: shadow base, inset main fill, top highlight strip.
    pygame.draw.rect(surf, sh, rect, border_radius=_RADIUS)
    inner = rect.inflate(-4, -4)
    pygame.draw.rect(surf, color, inner, border_radius=_RADIUS - 1)
    if inner.height >= 6:
        top = pygame.Rect(inner.x + 1, inner.y + 1, inner.width - 2, max(2, inner.height // 3))
        pygame.draw.rect(surf, hi, top, border_radius=_RADIUS - 1)
    return surf


def _get_cell(kind: str, size: int, glow: bool) -> pygame.Surface:
    key = (kind, size, glow)
    surf = _CELL_CACHE.get(key)
    if surf is None:
        surf = _build_cell(kind, size, glow)
        _CELL_CACHE[key] = surf
    return surf


def draw_cell(
    surface: pygame.Surface,
    rect: pygame.Rect,
    kind: str,
    *,
    glow: bool = True,
) -> None:
    surf = _get_cell(kind, rect.width, glow)
    surface.blit(surf, (rect.x - _PAD, rect.y - _PAD))


def draw_ghost_cell(
    surface: pygame.Surface,
    rect: pygame.Rect,
    kind: str,
    pulse: float,
) -> None:
    r, g, b = theme.cell_color(kind)
    boost = 0.55 + 0.45 * pulse
    col = (int(r * boost * 0.45), int(g * boost * 0.45), int(b * boost * 0.45))
    pygame.draw.rect(surface, col, rect, width=2, border_radius=_RADIUS)


def _cell_rect(
    col: int, visible_row: int, origin_x: int, origin_y: int
) -> pygame.Rect:
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


def draw_playfield(
    surface: pygame.Surface,
    board: Board,
    *,
    offset: tuple[int, int] = (0, 0),
    clearing_rows: tuple[int, ...] = (),
    flash_amount: float = 0.0,
    hide_clearing: bool = False,
) -> None:
    ox, oy = offset
    x = config.BOARD_X + ox
    y = config.BOARD_Y + oy
    w = board.cols * CELL
    h = config.VISIBLE_ROWS * CELL
    field = pygame.Rect(x, y, w, h)

    pygame.draw.rect(surface, theme.FIELD_BG, field, border_radius=6)

    for col in range(board.cols + 1):
        px = x + col * CELL
        pygame.draw.line(surface, theme.GRID, (px, y), (px, y + h))
    for row in range(config.VISIBLE_ROWS + 1):
        py = y + row * CELL
        pygame.draw.line(surface, theme.GRID, (x, py), (x + w, py))

    pygame.draw.rect(surface, theme.BORDER, field, width=2, border_radius=6)

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
            alpha = int(230 * max(0.0, min(1.0, flash_amount)))
            flash_surf = pygame.Surface(flash_rect.size, pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, alpha))
            surface.blit(
                flash_surf, flash_rect.topleft, special_flags=pygame.BLEND_RGBA_ADD
            )


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

    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
    ox, oy = offset
    for col, visible_row in _visible_cells(ghost):
        rect = _cell_rect(col, visible_row, config.BOARD_X + ox, config.BOARD_Y + oy)
        draw_ghost_cell(surface, rect, piece.kind, pulse)


def draw_drop_animations(
    surface: pygame.Surface,
    animations: list[DropAnimation],
    *,
    offset: tuple[int, int] = (0, 0),
) -> None:
    """Interpolated hard-drop ghosts. Purely visual — the model already
    committed the landing; this just sells the motion."""
    ox, oy = offset
    for a in animations:
        t = a.progress
        e = 1 - (1 - t) ** 3  # ease-out cubic
        cx = a.start_x + (a.end_x - a.start_x) * e
        cy = a.start_y + (a.end_y - a.start_y) * e
        alpha = int(220 * (1 - t * 0.7))

        color = theme.cell_color(a.kind)
        size = CELL - 8

        glow = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
        glow.fill((*color, alpha // 4))
        surface.blit(
            glow,
            (int(cx + ox) - size * 3 // 2, int(cy + oy) - size * 3 // 2),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        core = pygame.Surface((size, size), pygame.SRCALPHA)
        core.fill((*color, alpha))
        surface.blit(
            core,
            (int(cx + ox) - size // 2, int(cy + oy) - size // 2),
            special_flags=pygame.BLEND_RGBA_ADD,
        )