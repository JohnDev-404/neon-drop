"""Entry point. Boots pygame, opens a window, runs the main loop."""

from __future__ import annotations

import pygame

from neon_drop import config


def main() -> None:
    """Start the game."""
    pygame.init()
    pygame.display.set_caption(config.WINDOW_TITLE)

    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.fill(config.BG_COLOR)
        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
