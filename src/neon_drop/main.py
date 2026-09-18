"""Entry point: boot pygame, run the game loop, drive effects."""

from __future__ import annotations

import pygame

from neon_drop import config
from neon_drop.core.game import (
    CLEAR_ANIMATION_SECONDS,
    Game,
    GameState,
    HardDropEvent,
    LineClearEvent,
    LockEvent,
)
from neon_drop.input.handler import InputHandler
from neon_drop.ui import renderer, theme
from neon_drop.ui.effects import ParticleSystem, ScreenShake
from neon_drop.ui.hud import draw_hud


def _cell_center(cell: tuple[int, int]) -> tuple[float, float]:
    col, row = cell
    visible_row = row - config.HIDDEN_ROWS
    return (
        config.BOARD_X + col * config.CELL_SIZE + config.CELL_SIZE / 2,
        config.BOARD_Y + visible_row * config.CELL_SIZE + config.CELL_SIZE / 2,
    )


def main() -> None:
    pygame.init()
    pygame.display.set_caption(config.WINDOW_TITLE)
    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    game = Game()
    inputs = InputHandler()
    fonts = theme.Fonts()
    particles = ParticleSystem()
    shake = ScreenShake()

    running = True
    while running:
        # Cap dt to 1/30 s to avoid tunneling on slow frames.
        dt = min(clock.tick(config.FPS) / 1000.0, 1 / 30)

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
        _process_events(game, particles, shake)

        particles.update(dt)
        shake.update(dt)

        _render(screen, game, fonts, particles, shake)
        pygame.display.flip()

    pygame.quit()


def _process_events(game: Game, particles: ParticleSystem, shake: ScreenShake) -> None:
    for ev in game.drain_events():
        if isinstance(ev, HardDropEvent):
            shake.trigger(intensity=3 + ev.distance * 0.2, duration=0.14)
            for cell in ev.cells:
                x, y = _cell_center(cell)
                particles.burst(
                    x,
                    y,
                    theme.cell_color(ev.kind),
                    count=2,
                    speed=180,
                    size=3,
                    life=0.35,
                )
        elif isinstance(ev, LockEvent):
            for cell in ev.cells:
                x, y = _cell_center(cell)
                particles.burst(
                    x,
                    y,
                    theme.cell_color(ev.kind),
                    count=1,
                    speed=70,
                    size=3,
                    life=0.25,
                )
        elif isinstance(ev, LineClearEvent):
            shake.trigger(
                intensity=3 * ev.count + 2,
                duration=0.18 + 0.06 * ev.count,
            )
            for row in ev.rows:
                visible_row = row - config.HIDDEN_ROWS
                if visible_row < 0:
                    continue
                for col in range(config.COLS):
                    x = config.BOARD_X + col * config.CELL_SIZE + config.CELL_SIZE / 2
                    y = config.BOARD_Y + visible_row * config.CELL_SIZE + config.CELL_SIZE / 2
                    particles.burst(
                        x,
                        y,
                        (255, 255, 255),
                        count=2,
                        speed=260,
                        size=4,
                        life=0.5,
                    )


def _render(
    screen: pygame.Surface,
    game: Game,
    fonts: theme.Fonts,
    particles: ParticleSystem,
    shake: ScreenShake,
) -> None:
    screen.fill(theme.BG)

    offset = shake.offset()

    # Line clear phase: first half flash, second half hide.
    flash_amount = 0.0
    hide_clearing = False
    if game.clearing:
        t = game.clear_timer / CLEAR_ANIMATION_SECONDS  # 1.0 → 0.0
        if t > 0.5:
            flash_amount = (t - 0.5) * 2  # 1.0 → 0.0 over first half
        else:
            hide_clearing = True

    renderer.draw_playfield(
        screen,
        game.board,
        offset=offset,
        clearing_rows=game.clearing_rows,
        flash_amount=flash_amount,
        hide_clearing=hide_clearing,
    )

    if game.current is not None and game.state != GameState.GAME_OVER:
        renderer.draw_ghost(screen, game.current, game.board, offset=offset)
        renderer.draw_piece(screen, game.current, offset=offset)

    particles.draw(screen, offset=offset)

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
