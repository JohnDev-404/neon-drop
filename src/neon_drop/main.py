"""Entry point: boot pygame, run the game loop."""

from __future__ import annotations

import pygame

from neon_drop import config
from neon_drop.core.game import Game, GameState
from neon_drop.input.handler import InputHandler
from neon_drop.ui import renderer, theme
from neon_drop.ui.hud import draw_hud


def main() -> None:
    pygame.init()
    pygame.display.set_caption(config.WINDOW_TITLE)
    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    game = Game()
    inputs = InputHandler()
    fonts = theme.Fonts()

    running = True
    while running:
        dt = clock.tick(config.FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                running = False
            else:
                inputs.handle_event(event, game)
                inputs.handle_keyup(event)

        inputs.tick(dt, game)
        game.tick(dt)

        _render(screen, game, fonts)
        pygame.display.flip()

    pygame.quit()


def _render(screen: pygame.Surface, game: Game, fonts: theme.Fonts) -> None:
    screen.fill(theme.BG)

    renderer.draw_playfield(screen, game.board)
    if game.current is not None and game.state != GameState.GAME_OVER:
        renderer.draw_ghost(screen, game.current, game.board)
        renderer.draw_piece(screen, game.current)

    draw_hud(screen, game, fonts)

    if game.state == GameState.PAUSED:
        _draw_banner(screen, "PAUSED", "ESC to resume", fonts)
    elif game.state == GameState.GAME_OVER:
        _draw_banner(screen, "GAME OVER", "R to restart · Q to quit", fonts)


def _draw_banner(screen: pygame.Surface, title: str, subtitle: str, fonts: theme.Fonts) -> None:
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    title_surf = theme.render_neon(fonts.title, title, theme.ACCENT, glow=theme.ACCENT)
    sub_surf = theme.render_neon(fonts.small, subtitle, theme.TEXT, glow=theme.BORDER)
    screen.blit(title_surf, (w // 2 - title_surf.get_width() // 2, h // 2 - 70))
    screen.blit(sub_surf, (w // 2 - sub_surf.get_width() // 2, h // 2 + 20))


if __name__ == "__main__":
    main()
