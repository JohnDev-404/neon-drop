"""The right-hand HUD: score, lines, level, combo/B2B, next queue."""

from __future__ import annotations

import pygame

from neon_drop import config
from neon_drop.core.game import Game
from neon_drop.core.piece import SHAPES
from neon_drop.core.scoring import ClearType
from neon_drop.ui import theme
from neon_drop.ui.renderer import draw_cell
from neon_drop.ui.theme import Fonts

_CELL = config.CELL_SIZE

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


def draw_hud(surface: pygame.Surface, game: Game, fonts: Fonts) -> None:
    x = config.HUD_X
    y = config.HUD_Y

    y = _draw_stat(surface, "SCORE", str(game.score), x, y, fonts)
    y = _draw_stat(surface, "LINES", str(game.lines), x, y, fonts)
    y = _draw_stat(surface, "LEVEL", str(game.level), x, y, fonts)
    y = _draw_status(surface, game, x, y, fonts)

    y += 20
    _draw_next_queue(surface, game, x, y, fonts)


def _draw_stat(
    surface: pygame.Surface,
    label: str,
    value: str,
    x: int,
    y: int,
    fonts: Fonts,
) -> int:
    label_surf = theme.render_neon(
        fonts.label, label, theme.ACCENT, glow=theme.ACCENT, glow_alpha=80
    )
    value_surf = theme.render_neon(fonts.value, value, theme.TEXT, glow=theme.BORDER)
    surface.blit(label_surf, (x, y))
    surface.blit(value_surf, (x, y + 22))
    return y + 90


def _draw_status(surface: pygame.Surface, game: Game, x: int, y: int, fonts: Fonts) -> int:
    """Combo / B2B / last clear label, drawn under the stat stack."""
    if game.combo_state.combo >= 1:
        combo_surf = theme.render_neon(
            fonts.label,
            f"COMBO x{game.combo_state.combo + 1}",
            theme.ACCENT,
            glow=theme.ACCENT,
            glow_alpha=90,
        )
        surface.blit(combo_surf, (x, y))
        y += 28

    if game.combo_state.b2b_active:
        b2b_surf = theme.render_neon(
            fonts.label,
            "B2B",
            theme.BORDER,
            glow=theme.BORDER,
            glow_alpha=90,
        )
        surface.blit(b2b_surf, (x, y))
        y += 28

    if game.last_clear is not None and game.last_clear.clear_type is not ClearType.NONE:
        label = _CLEAR_LABELS[game.last_clear.clear_type]
        color = theme.ACCENT if game.last_clear.is_b2b else theme.TEXT
        clear_surf = theme.render_neon(fonts.label, label, color, glow=theme.BORDER, glow_alpha=70)
        surface.blit(clear_surf, (x, y))
        y += 28

    return y


def _draw_next_queue(
    surface: pygame.Surface,
    game: Game,
    x: int,
    y: int,
    fonts: Fonts,
) -> None:
    label = theme.render_neon(fonts.label, "NEXT", theme.ACCENT, glow=theme.ACCENT, glow_alpha=80)
    surface.blit(label, (x, y))
    y += 34

    preview_kinds = game.next_queue[:3]
    for i, kind in enumerate(preview_kinds):
        _draw_mini_piece(surface, kind, x, y + i * (_CELL * 3 + 10), fonts)


def _draw_mini_piece(
    surface: pygame.Surface,
    kind: str,
    x: int,
    y: int,
    fonts: Fonts,
) -> None:
    state = SHAPES[kind][0]
    # Center the piece in a 4x4 cell box.
    box_w = 4 * (_CELL - 4)
    box_h = 4 * (_CELL - 4)
    panel = pygame.Rect(x, y, box_w, box_h)
    pygame.draw.rect(surface, theme.FIELD_BG, panel)
    pygame.draw.rect(surface, theme.GRID, panel, width=1)

    min_x = min(cx for cx, _ in state)
    max_x = max(cx for cx, _ in state)
    min_y = min(cy for _, cy in state)
    max_y = max(cy for _, cy in state)
    span_x = max_x - min_x + 1
    span_y = max_y - min_y + 1
    cell = _CELL - 4
    offset_x = panel.x + (panel.width - span_x * cell) // 2
    offset_y = panel.y + (panel.height - span_y * cell) // 2

    for cx, cy in state:
        rect = pygame.Rect(
            offset_x + (cx - min_x) * cell,
            offset_y + (cy - min_y) * cell,
            cell,
            cell,
        )
        draw_cell(surface, rect, kind, glow=False)
