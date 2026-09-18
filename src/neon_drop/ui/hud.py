"""HUD: HOLD + stats on the left, NEXT queue on the right, plus a
floating combo/B2B banner over the playfield."""

from __future__ import annotations

import pygame

from neon_drop import config
from neon_drop.core.game import Game
from neon_drop.core.piece import SHAPES
from neon_drop.core.scoring import ClearType
from neon_drop.ui import theme
from neon_drop.ui.renderer import draw_cell, CELL
from neon_drop.ui.theme import Fonts

_CLEAR_LABELS = {
    ClearType.SINGLE: "SINGLE",
    ClearType.DOUBLE: "DOUBLE",
    ClearType.TRIPLE: "TRIPLE",
    ClearType.TETRIS: "TETRIS",
    ClearType.T_SPIN: "T-SPIN",
    ClearType.T_SPIN_SINGLE: "T-SPIN SINGLE",
    ClearType.T_SPIN_DOUBLE: "T-SPIN DOUBLE",
    ClearType.T_SPIN_TRIPLE: "T-SPIN TRIPLE",
    ClearType.T_SPIN_MINI: "T-SPIN MINI",
    ClearType.T_SPIN_MINI_SINGLE: "T-SPIN MINI SINGLE",
    ClearType.T_SPIN_MINI_DOUBLE: "T-SPIN MINI DOUBLE",
}

_PANEL_W = 4 * (CELL - 4) + 16  # width used by HOLD and NEXT slots
_HOLD_H = 3 * CELL - 8


# --------------------------------------------------------------------------
# Public entry
# --------------------------------------------------------------------------

def draw_hud(
    surface: pygame.Surface,
    game: Game,
    fonts: Fonts,
    *,
    banner_progress: float = 0.0,
) -> None:
    _draw_left_column(surface, game, fonts)
    _draw_right_column(surface, game, fonts)
    if banner_progress > 0.0:
        _draw_status_banner(surface, game, fonts, banner_progress)


# --------------------------------------------------------------------------
# Left column: HOLD, SCORE, LINES / LEVEL
# --------------------------------------------------------------------------

def _draw_left_column(surface: pygame.Surface, game: Game, fonts: Fonts) -> None:
    x = config.HOLD_X
    y = config.HUD_Y

    y = _section_label(surface, "HOLD", x, y, fonts)
    y = _hold_panel(surface, game, x, y)

    y += 28
    y = _stat_big(surface, "SCORE", f"{game.score:,}", x, y, fonts)

    y += 10
    _stat_small(surface, "LINES", str(game.lines), x, y, fonts)
    _stat_small(surface, "LEVEL", str(game.level), x + 118, y, fonts)


def _hold_panel(surface: pygame.Surface, game: Game, x: int, y: int) -> int:
    rect = pygame.Rect(x, y, _PANEL_W, _HOLD_H)
    theme.panel(surface, rect, fill=theme.FIELD_BG, border=theme.GRID, radius=6)

    if game.held_kind is not None:
        _draw_piece_in_box(
            surface,
            game.held_kind,
            rect,
            dimmed=game.hold_used_this_piece,
        )
    return y + rect.height


# --------------------------------------------------------------------------
# Right column: NEXT queue
# --------------------------------------------------------------------------

def _draw_right_column(surface: pygame.Surface, game: Game, fonts: Fonts) -> None:
    x = config.NEXT_X
    y = config.HUD_Y

    y = _section_label(surface, "NEXT", x, y, fonts)
    for kind in game.next_queue[:5]:
        y = _next_slot(surface, kind, x, y)
        y += 6


def _next_slot(surface: pygame.Surface, kind: str, x: int, y: int) -> int:
    h = 3 * CELL - 12
    rect = pygame.Rect(x, y, _PANEL_W, h)
    theme.panel(surface, rect, fill=theme.FIELD_BG, border=theme.GRID, radius=6)
    _draw_piece_in_box(surface, kind, rect, dimmed=False, show_panel=False)
    return y + h


# --------------------------------------------------------------------------
# Floating combo / B2B banner over the playfield
# --------------------------------------------------------------------------

def _draw_status_banner(
    surface: pygame.Surface,
    game: Game,
    fonts: Fonts,
    progress: float,
) -> None:
    # progress: 1.0 = just triggered, 0.0 = done. Fade + slight rise.
    alpha = int(255 * min(1.0, progress * 1.6))
    rise = int((1.0 - progress) * 18)

    messages: list[tuple[str, tuple[int, int, int]]] = []
    if game.combo_state.combo >= 1:
        messages.append((f"COMBO ×{game.combo_state.combo + 1}", theme.ACCENT))
    if game.combo_state.b2b_active:
        messages.append(("BACK-TO-BACK", theme.BORDER_HI))
    if game.last_clear is not None and game.last_clear.clear_type is not ClearType.NONE:
        messages.append((_CLEAR_LABELS[game.last_clear.clear_type], theme.TEXT))

    if not messages:
        return

    cx = config.BOARD_X + (config.COLS * CELL) // 2
    cy = config.BOARD_Y + 90

    for i, (text, color) in enumerate(messages):
        surf = theme.render_neon(fonts.small, text, color, glow=color, glow_alpha=140)
        surf = surf.copy()
        surf.set_alpha(alpha)
        rect = surf.get_rect(center=(cx, cy + i * 34 - rise))
        surface.blit(surf, rect)


# --------------------------------------------------------------------------
# Shared primitives
# --------------------------------------------------------------------------

def _section_label(
    surface: pygame.Surface, text: str, x: int, y: int, fonts: Fonts
) -> int:
    surf = fonts.label.render(text, True, theme.TEXT_DIM)
    surface.blit(surf, (x, y))
    return y + surf.get_height() + 8


def _stat_big(
    surface: pygame.Surface,
    label: str,
    value: str,
    x: int,
    y: int,
    fonts: Fonts,
) -> int:
    l = fonts.label.render(label, True, theme.TEXT_DIM)
    v = theme.render_neon(fonts.value, value, theme.TEXT, glow=theme.BORDER, glow_alpha=60)
    surface.blit(l, (x, y))
    surface.blit(v, (x - 6, y + l.get_height() + 2))  # -6 offset compensates for glow pad
    return y + l.get_height() + v.get_height() - 4


def _stat_small(
    surface: pygame.Surface,
    label: str,
    value: str,
    x: int,
    y: int,
    fonts: Fonts,
) -> None:
    l = fonts.label.render(label, True, theme.TEXT_DIM)
    v = fonts.value.render(value, True, theme.TEXT)
    surface.blit(l, (x, y))
    surface.blit(v, (x, y + l.get_height() + 2))


def _draw_piece_in_box(
    surface: pygame.Surface,
    kind: str,
    panel_rect: pygame.Rect,
    *,
    dimmed: bool = False,
    show_panel: bool = True,
) -> None:
    """Center a rotation-0 piece inside a bounding panel."""
    state = SHAPES[kind][0]
    min_x = min(cx for cx, _ in state)
    max_x = max(cx for cx, _ in state)
    min_y = min(cy for _, cy in state)
    max_y = max(cy for _, cy in state)
    span_x = max_x - min_x + 1
    span_y = max_y - min_y + 1

    cell = CELL - 4
    offset_x = panel_rect.x + (panel_rect.width - span_x * cell) // 2
    offset_y = panel_rect.y + (panel_rect.height - span_y * cell) // 2

    for cx, cy in state:
        rect = pygame.Rect(
            offset_x + (cx - min_x) * cell,
            offset_y + (cy - min_y) * cell,
            cell,
            cell,
        )
        if dimmed:
            r, g, b = theme.cell_color(kind)
            dim = (r // 3, g // 3, b // 3)
            pygame.draw.rect(surface, dim, rect, border_radius=3)
            pygame.draw.rect(surface, theme.GRID, rect, width=1, border_radius=3)
        else:
            draw_cell(surface, rect, kind, glow=False)