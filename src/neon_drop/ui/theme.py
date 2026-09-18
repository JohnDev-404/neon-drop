"""Visual theme: colors, fonts, and derived tints."""

from __future__ import annotations

import pygame

from neon_drop import config

BG = config.BG_COLOR
GRID = config.GRID_COLOR
BORDER = config.BORDER_COLOR
TEXT = config.TEXT_COLOR
ACCENT = config.ACCENT_COLOR

# Slightly lighter than BG so the playfield reads as a distinct panel.
FIELD_BG: tuple[int, int, int] = (14, 11, 34)


def cell_color(kind: str) -> tuple[int, int, int]:
    return config.PIECE_COLORS[kind]


def cell_highlight(kind: str) -> tuple[int, int, int]:
    """Lighter tint for the top and left edges of a cell."""
    r, g, b = config.PIECE_COLORS[kind]
    return (min(255, r + 90), min(255, g + 90), min(255, b + 90))


def cell_shadow(kind: str) -> tuple[int, int, int]:
    """Darker tint for the bottom and right edges."""
    r, g, b = config.PIECE_COLORS[kind]
    return (max(0, r - 90), max(0, g - 90), max(0, b - 90))


class Fonts:
    """Bundle of fonts used across the UI."""

    def __init__(self) -> None:
        pygame.font.init()
        # Fall back to the default font for now; we can add a pixel
        # font later by dropping a .ttf into assets/fonts/.
        self.small = pygame.font.SysFont("consolas,couriernew,monospace", 18)
        self.label = pygame.font.SysFont("consolas,couriernew,monospace", 16, bold=True)
        self.value = pygame.font.SysFont("consolas,couriernew,monospace", 32, bold=True)
        self.title = pygame.font.SysFont("consolas,couriernew,monospace", 56, bold=True)


def render_neon(
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    glow: tuple[int, int, int] = (60, 200, 255),
    glow_alpha: int = 110,
) -> pygame.Surface:
    """Render text with a soft neon halo behind it."""
    main = font.render(text, True, color)
    glow_surf = font.render(text, True, glow)
    w, h = main.get_size()
    pad = 6
    out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
        ghost = glow_surf.copy()
        ghost.set_alpha(glow_alpha)
        out.blit(ghost, (pad + dx, pad + dy))
    out.blit(main, (pad, pad))
    return out
