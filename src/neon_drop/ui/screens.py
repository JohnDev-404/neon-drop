"""Full-screen overlays: menu, pause, game over, level-up flash."""

from __future__ import annotations

import pygame

from neon_drop import config
from neon_drop.core.high_scores import HighScores
from neon_drop.ui import theme
from neon_drop.ui.theme import Fonts


def _dim(screen: pygame.Surface, alpha: int = 180) -> None:
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    screen.blit(overlay, (0, 0))


def _center_blit(screen: pygame.Surface, surf: pygame.Surface, y: int) -> pygame.Rect:
    w = screen.get_width()
    rect = surf.get_rect(midtop=(w // 2, y))
    screen.blit(surf, rect)
    return rect


# --------------------------------------------------------------------------
# Menu
# --------------------------------------------------------------------------

def draw_menu(screen: pygame.Surface, scores: HighScores, fonts: Fonts) -> None:
    w, h = screen.get_size()

    _dim(screen, 160)

    title = theme.render_neon(
        fonts.title, "NEON DROP", theme.ACCENT, glow=theme.ACCENT, glow_alpha=160
    )
    _center_blit(screen, title, 90)

    tagline = theme.render_neon(
        fonts.small,
        "a modern falling-block puzzler",
        theme.TEXT_DIM,
        glow=theme.BORDER,
        glow_alpha=60,
    )
    _center_blit(screen, tagline, 200)

    # Play prompt panel
    prompt_rect = pygame.Rect(0, 0, 420, 74)
    prompt_rect.center = (w // 2, 320)
    theme.panel(screen, prompt_rect, fill=theme.SURFACE_HI, border=theme.BORDER_HI, radius=10)
    prompt = theme.render_neon(
        fonts.value, "PRESS ENTER TO PLAY", theme.TEXT, glow=theme.BORDER_HI, glow_alpha=90
    )
    screen.blit(prompt, prompt.get_rect(center=prompt_rect.center))

    # Two-column lower area: controls | high scores
    col_y = 440
    col_gap = 60
    col_w = 300
    left_x = w // 2 - col_w - col_gap // 2
    right_x = w // 2 + col_gap // 2

    _draw_info_column(screen, "CONTROLS", [
        ("MOVE",       "← →  ·  A D"),
        ("ROTATE",     "↑ X  ·  Z"),
        ("SOFT DROP",  "↓"),
        ("HARD DROP",  "SPACE"),
        ("HOLD",       "C  ·  SHIFT"),
        ("PAUSE",      "ESC"),
        ("MUTE",       "M"),
    ], left_x, col_y, col_w, fonts)

    _draw_highscores_column(screen, scores, right_x, col_y, col_w, fonts)

    footer = fonts.small.render("Q to quit", True, theme.TEXT_DIM)
    screen.blit(footer, footer.get_rect(center=(w // 2, h - 30)))


def _draw_info_column(
    screen: pygame.Surface,
    title: str,
    rows: list[tuple[str, str]],
    x: int,
    y: int,
    width: int,
    fonts: Fonts,
) -> None:
    # Panel height depends on row count.
    row_h = 26
    height = 44 + row_h * len(rows)
    rect = pygame.Rect(x, y, width, height)
    theme.panel(screen, rect, fill=theme.SURFACE, border=theme.BORDER, radius=8)

    hdr = fonts.label.render(title, True, theme.TEXT_DIM)
    screen.blit(hdr, (rect.x + 16, rect.y + 14))

    ry = rect.y + 44
    for label, keys in rows:
        l = fonts.small.render(label, True, theme.TEXT_DIM)
        k = fonts.small.render(keys, True, theme.TEXT)
        screen.blit(l, (rect.x + 16, ry))
        screen.blit(k, (rect.right - 16 - k.get_width(), ry))
        ry += row_h


def _draw_highscores_column(
    screen: pygame.Surface,
    scores: HighScores,
    x: int,
    y: int,
    width: int,
    fonts: Fonts,
) -> None:
    entries = scores.entries[:5]
    row_h = 26
    height = 44 + row_h * max(len(entries), 1)
    rect = pygame.Rect(x, y, width, height)
    theme.panel(screen, rect, fill=theme.SURFACE, border=theme.BORDER, radius=8)

    hdr = fonts.label.render("HIGH SCORES", True, theme.TEXT_DIM)
    screen.blit(hdr, (rect.x + 16, rect.y + 14))

    if not entries:
        empty = fonts.small.render("— no runs yet —", True, theme.TEXT_DIM)
        screen.blit(empty, (rect.x + 16, rect.y + 44))
        return

    ry = rect.y + 44
    for i, entry in enumerate(entries, start=1):
        rank = fonts.small.render(f"{i:>2}.", True, theme.TEXT_DIM)
        score = fonts.value.render(f"{entry.score:>7}", True, theme.TEXT)
        # scale down the value font for row alignment
        score = pygame.transform.smoothscale(
            score, (score.get_width() * 2 // 3, score.get_height() * 2 // 3)
        )
        lvl = fonts.small.render(f"L{entry.level}", True, theme.TEXT_DIM)
        screen.blit(rank,  (rect.x + 16, ry))
        screen.blit(score, (rect.x + 48, ry - 2))
        screen.blit(lvl,   (rect.right - 16 - lvl.get_width(), ry))
        ry += row_h


# --------------------------------------------------------------------------
# Pause
# --------------------------------------------------------------------------

def draw_pause(screen: pygame.Surface, fonts: Fonts) -> None:
    w, h = screen.get_size()
    _dim(screen, 170)

    box = pygame.Rect(0, 0, 420, 200)
    box.center = (w // 2, h // 2)
    theme.panel(screen, box, fill=theme.SURFACE_HI, border=theme.BORDER_HI, radius=12)

    title = theme.render_neon(fonts.big, "PAUSED", theme.ACCENT, glow=theme.ACCENT)
    screen.blit(title, title.get_rect(center=(box.centerx, box.y + 60)))

    sub = fonts.small.render(
        "ESC  resume     R  restart", True, theme.TEXT_DIM
    )
    screen.blit(sub, sub.get_rect(center=(box.centerx, box.y + 130)))


# --------------------------------------------------------------------------
# Game over
# --------------------------------------------------------------------------

def draw_game_over(
    screen: pygame.Surface,
    score: int,
    lines: int,
    level: int,
    made_high_score: bool,
    fonts: Fonts,
) -> None:
    w, h = screen.get_size()
    _dim(screen, 190)

    box = pygame.Rect(0, 0, 520, 340)
    box.center = (w // 2, h // 2)
    theme.panel(screen, box, fill=theme.SURFACE_HI, border=theme.BORDER_HI, radius=12)

    title = theme.render_neon(fonts.big, "GAME OVER", theme.ACCENT, glow=theme.ACCENT)
    screen.blit(title, title.get_rect(center=(box.centerx, box.y + 60)))

    # Stat grid: 3 columns
    stats = [("SCORE", f"{score:,}"), ("LINES", str(lines)), ("LEVEL", str(level))]
    col_w = box.width // 3
    for i, (label, value) in enumerate(stats):
        cx = box.x + col_w * i + col_w // 2
        l = fonts.label.render(label, True, theme.TEXT_DIM)
        v = fonts.value.render(value, True, theme.TEXT)
        screen.blit(l, l.get_rect(center=(cx, box.y + 150)))
        screen.blit(v, v.get_rect(center=(cx, box.y + 190)))

    if made_high_score:
        hs = theme.render_neon(
            fonts.small, "★ NEW HIGH SCORE ★", theme.ACCENT, glow=theme.ACCENT
        )
        screen.blit(hs, hs.get_rect(center=(box.centerx, box.y + 250)))

    prompt = fonts.small.render(
        "ENTER  menu     R  play again     Q  quit", True, theme.TEXT_DIM
    )
    screen.blit(prompt, prompt.get_rect(center=(box.centerx, box.bottom - 40)))


# --------------------------------------------------------------------------
# Level-up flash
# --------------------------------------------------------------------------

def draw_level_up_flash(
    screen: pygame.Surface, level: int, progress: float, fonts: Fonts
) -> None:
    """`progress` goes from 1.0 down to 0.0 as the flash fades."""
    if progress <= 0:
        return
    alpha = int(255 * min(1.0, progress * 1.4))
    text = theme.render_neon(
        fonts.big, f"LEVEL {level}", theme.ACCENT, glow=theme.ACCENT
    )
    text = text.copy()
    text.set_alpha(alpha)

    cx = config.BOARD_X + (config.COLS * config.CELL_SIZE) // 2
    cy = config.BOARD_Y + 260
    screen.blit(text, text.get_rect(center=(cx, cy)))