"""Visual theme: colors, fonts, panels, neon text, background."""

from __future__ import annotations

from pathlib import Path

import pygame

from neon_drop import config

# --- Palette --------------------------------------------------------------

BG         = config.BG_COLOR
SURFACE    = (24, 20, 48)
SURFACE_HI = (40, 34, 76)
FIELD_BG   = (14, 11, 34)
GRID       = config.GRID_COLOR
BORDER     = config.BORDER_COLOR
BORDER_HI  = (120, 215, 255)
TEXT       = config.TEXT_COLOR
TEXT_DIM   = (150, 145, 180)
ACCENT     = config.ACCENT_COLOR
DANGER     = (255, 90, 120)


def cell_color(kind: str) -> tuple[int, int, int]:
    return config.PIECE_COLORS[kind]


def cell_highlight(kind: str) -> tuple[int, int, int]:
    r, g, b = config.PIECE_COLORS[kind]
    return (min(255, r + 80), min(255, g + 80), min(255, b + 80))


def cell_shadow(kind: str) -> tuple[int, int, int]:
    r, g, b = config.PIECE_COLORS[kind]
    return (max(0, int(r * 0.5)), max(0, int(g * 0.5)), max(0, int(b * 0.5)))


# --- Panels ---------------------------------------------------------------

def panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill: tuple[int, int, int] = SURFACE,
    border: tuple[int, int, int] = BORDER,
    radius: int = 8,
    width: int = 1,
) -> None:
    """Standard rounded panel: fill then 1px border."""
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width=width, border_radius=radius)


# --- Fonts ----------------------------------------------------------------

_ASSET_FONTS = Path(__file__).resolve().parents[3] / "assets" / "fonts"


def _load_font(name: str, size: int, *, bold: bool = False) -> pygame.font.Font:
    path = _ASSET_FONTS / name
    if path.exists():
        font = pygame.font.Font(str(path), size)
        if bold:
            font.set_bold(True)
        return font
    # Graceful fallback so the game still runs without bundled .ttf files.
    return pygame.font.SysFont("arial,helvetica,sans", size, bold=bold)


class Fonts:
    """Bundle of fonts used across the UI.

    Drop these into assets/fonts/ to unlock the intended look:
        Inter-Regular.ttf, Inter-SemiBold.ttf,
        JetBrainsMono-Bold.ttf, Orbitron-Bold.ttf
    Without them, SysFont fallbacks keep everything working.
    """

    def __init__(self) -> None:
        pygame.font.init()
        self.tiny  = _load_font("Inter-Regular.ttf", 13)
        self.small = _load_font("Inter-Regular.ttf", 16)
        self.label = _load_font("Inter-SemiBold.ttf", 13, bold=True)
        self.value = _load_font("JetBrainsMono-Bold.ttf", 30, bold=True)
        self.big   = _load_font("JetBrainsMono-Bold.ttf", 46, bold=True)
        self.title = _load_font("Orbitron-Bold.ttf", 72, bold=True)


# --- Neon text (cached) ---------------------------------------------------

_NEON_CACHE: dict = {}


def render_neon(
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    glow: tuple[int, int, int] = (60, 200, 255),
    glow_alpha: int = 110,
) -> pygame.Surface:
    """Render text with a soft neon halo. Cached — safe to call per frame."""
    # id(font) is stable because Fonts lives for the whole app lifetime.
    key = (id(font), font.get_height(), text, color, glow, glow_alpha)
    cached = _NEON_CACHE.get(key)
    if cached is not None:
        return cached

    main = font.render(text, True, color)
    glow_surf = font.render(text, True, glow)
    w, h = main.get_size()
    pad = 6
    out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                   (2, 0), (-2, 0), (0, 2), (0, -2),
                   (3, 3), (-3, -3), (3, -3), (-3, 3)):
        ghost = glow_surf.copy()
        ghost.set_alpha(glow_alpha)
        out.blit(ghost, (pad + dx, pad + dy))
    out.blit(main, (pad, pad))

    if len(_NEON_CACHE) > 512:
        _NEON_CACHE.clear()
    _NEON_CACHE[key] = out
    return out


# --- Gradient background (cached) -----------------------------------------

_BG_CACHE: dict = {}


def background(w: int, h: int) -> pygame.Surface:
    """Pre-rendered vertical gradient. Blit instead of flat fill."""
    key = (w, h)
    surf = _BG_CACHE.get(key)
    if surf is not None:
        return surf

    surf = pygame.Surface((w, h))
    top = (14, 12, 34)
    bot = (4, 3, 12)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (w, y))
    _BG_CACHE[key] = surf
    return surf