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


def _center_blit(screen: pygame.Surface, surf: pygame.Surface, y: int) -> None:
    w = screen.get_width()
    screen.blit(surf, (w // 2 - surf.get_width() // 2, y))


def draw_menu(screen: pygame.Surface, scores: HighScores, fonts: Fonts) -> None:
    _dim(screen, 200)

    title = theme.render_neon(
        fonts.title, "NEON DROP", theme.ACCENT, glow=theme.ACCENT, glow_alpha=140
    )
    _center_blit(screen, title, 100)

    tagline = theme.render_neon(
        fonts.small,
        "a modern falling-block puzzler",
        theme.TEXT,
        glow=theme.BORDER,
        glow_alpha=70,
    )
    _center_blit(screen, tagline, 190)

    # Big play prompt.
    prompt = theme.render_neon(fonts.value, "PRESS ENTER TO PLAY", theme.BORDER, glow=theme.BORDER)
    _center_blit(screen, prompt, 300)

    # Controls.
    controls = [
        "MOVE          ← →  /  A D",
        "ROTATE        ↑ X  /  Z",
        "SOFT DROP     ↓",
        "HARD DROP     SPACE",
        "HOLD          C  /  SHIFT",
        "PAUSE         ESC",
        "MUTE          M",
    ]
    y = 420
    for line in controls:
        surf = theme.render_neon(fonts.small, line, theme.TEXT, glow=theme.BORDER, glow_alpha=40)
        _center_blit(screen, surf, y)
        y += 28

    # High scores.
    if scores.entries:
        header = theme.render_neon(fonts.label, "HIGH SCORES", theme.ACCENT, glow=theme.ACCENT)
        _center_blit(screen, header, 640)
        y = 675
        for i, entry in enumerate(scores.entries[:5], start=1):
            line = f"{i}.  {entry.score:>7}   L{entry.level}"
            surf = theme.render_neon(
                fonts.small, line, theme.TEXT, glow=theme.BORDER, glow_alpha=40
            )
            _center_blit(screen, surf, y)
            y += 26

    footer = theme.render_neon(
        fonts.small, "Q to quit", theme.TEXT, glow=theme.BORDER, glow_alpha=40
    )
    _center_blit(screen, footer, config.WINDOW_HEIGHT - 40)


def draw_pause(screen: pygame.Surface, fonts: Fonts) -> None:
    _dim(screen, 170)
    title = theme.render_neon(fonts.title, "PAUSED", theme.ACCENT, glow=theme.ACCENT)
    sub = theme.render_neon(
        fonts.small, "ESC to resume   ·   R to restart", theme.TEXT, glow=theme.BORDER
    )
    _center_blit(screen, title, config.WINDOW_HEIGHT // 2 - 80)
    _center_blit(screen, sub, config.WINDOW_HEIGHT // 2 + 20)


def draw_game_over(
    screen: pygame.Surface,
    score: int,
    lines: int,
    level: int,
    made_high_score: bool,
    fonts: Fonts,
) -> None:
    _dim(screen, 190)
    title = theme.render_neon(fonts.title, "GAME OVER", theme.ACCENT, glow=theme.ACCENT)
    _center_blit(screen, title, 180)

    stats = [
        f"SCORE   {score}",
        f"LINES   {lines}",
        f"LEVEL   {level}",
    ]
    y = 320
    for line in stats:
        surf = theme.render_neon(fonts.value, line, theme.TEXT, glow=theme.BORDER)
        _center_blit(screen, surf, y)
        y += 60

    if made_high_score:
        hs = theme.render_neon(fonts.label, "★ NEW HIGH SCORE ★", theme.ACCENT, glow=theme.ACCENT)
        _center_blit(screen, hs, 540)

    prompt = theme.render_neon(
        fonts.small,
        "ENTER to menu   ·   R to play again   ·   Q to quit",
        theme.BORDER,
        glow=theme.BORDER,
    )
    _center_blit(screen, prompt, config.WINDOW_HEIGHT - 120)


def draw_level_up_flash(screen: pygame.Surface, level: int, progress: float, fonts: Fonts) -> None:
    """`progress` goes from 1.0 down to 0.0 as the flash fades."""
    if progress <= 0:
        return
    alpha = int(255 * min(1.0, progress))
    text = theme.render_neon(fonts.value, f"LEVEL {level}", theme.ACCENT, glow=theme.ACCENT)
    text.set_alpha(alpha)
    _center_blit(screen, text, config.WINDOW_HEIGHT // 2 - 300)
