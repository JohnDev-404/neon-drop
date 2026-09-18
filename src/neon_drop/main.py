"""Entry point: boot pygame, run the game loop, drive screens and effects."""

from __future__ import annotations

import asyncio
from enum import Enum, auto

import pygame

from neon_drop import config
from neon_drop.audio.sound import SoundBank
from neon_drop.core.game import (
    CLEAR_ANIMATION_SECONDS,
    Game,
    GameState,
    HardDropEvent,
    LineClearEvent,
    LockEvent,
)
from neon_drop.core.high_scores import HighScores
from neon_drop.core.scoring import ClearType
from neon_drop.input.handler import InputHandler
from neon_drop.ui import renderer, screens, theme
from neon_drop.ui.effects import ParticleSystem, ScreenShake
from neon_drop.ui.hud import draw_hud

LEVEL_FLASH_SECONDS = 1.2


class AppScreen(Enum):
    MENU = auto()
    PLAYING = auto()
    GAME_OVER = auto()


def _cell_center(cell: tuple[int, int]) -> tuple[float, float]:
    col, row = cell
    visible_row = row - config.HIDDEN_ROWS
    return (
        config.BOARD_X + col * config.CELL_SIZE + config.CELL_SIZE / 2,
        config.BOARD_Y + visible_row * config.CELL_SIZE + config.CELL_SIZE / 2,
    )


async def _main_async() -> None:
    pygame.init()

    # Audio is optional — WSL and some browsers have no device. If the
    # mixer can't initialize, SoundBank runs in disabled mode and the
    # game continues silently.
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
    except pygame.error:
        pass

    pygame.display.set_caption(config.WINDOW_TITLE)
    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    game = Game()
    inputs = InputHandler()
    fonts = theme.Fonts()
    particles = ParticleSystem()
    shake = ScreenShake()
    sound = SoundBank()
    scores = HighScores()

    app_screen = AppScreen.MENU
    made_high_score = False

    # Level-up flash state.
    level_flash_timer = 0.0
    last_seen_level = game.level

    running = True
    while running:
        dt = min(clock.tick(config.FPS) / 1000.0, 1 / 30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                running = False
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                sound.toggle()
                continue

            if app_screen is AppScreen.MENU:
                if event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_RETURN,
                    pygame.K_KP_ENTER,
                    pygame.K_SPACE,
                ):
                    game.reset()
                    particles.particles.clear()
                    shake.intensity = 0
                    shake.duration = 0
                    last_seen_level = game.level
                    made_high_score = False
                    app_screen = AppScreen.PLAYING
                continue

            if app_screen is AppScreen.GAME_OVER:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    game.reset()
                    particles.particles.clear()
                    shake.intensity = 0
                    shake.duration = 0
                    last_seen_level = game.level
                    made_high_score = False
                    app_screen = AppScreen.PLAYING
                elif event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_RETURN,
                    pygame.K_KP_ENTER,
                ):
                    app_screen = AppScreen.MENU
                continue

            # app_screen is PLAYING
            inputs.handle_event(event, game)
            inputs.handle_keyup(event)

            # Play a sound on rotate/hold via the handler side-effects.
            # (Handled implicitly by event-type checks here — simpler
            #  than threading sound into the handler.)
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_UP,
                pygame.K_x,
                pygame.K_z,
                pygame.K_LCTRL,
                pygame.K_RCTRL,
            ):
                sound.play("rotate")
            elif event.type == pygame.KEYDOWN and event.key in (
                pygame.K_c,
                pygame.K_LSHIFT,
                pygame.K_RSHIFT,
            ):
                sound.play("hold")

        if app_screen is AppScreen.PLAYING:
            inputs.tick(dt, game)
            game.tick(dt)
            _process_events(game, particles, shake, sound)

            # Detect level change for the flash and sound.
            if game.level > last_seen_level:
                level_flash_timer = LEVEL_FLASH_SECONDS
                sound.play("level_up")
                last_seen_level = game.level

            # Detect game over.
            if game.state == GameState.GAME_OVER:
                made_high_score = scores.submit(game.score, game.lines, game.level)
                sound.play("game_over")
                app_screen = AppScreen.GAME_OVER

        particles.update(dt)
        shake.update(dt)
        if level_flash_timer > 0:
            level_flash_timer = max(0.0, level_flash_timer - dt)

        _render(
            screen,
            game,
            fonts,
            particles,
            shake,
            app_screen,
            scores,
            level_flash_timer,
            made_high_score,
        )
        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


def _process_events(
    game: Game,
    particles: ParticleSystem,
    shake: ScreenShake,
    sound: SoundBank,
) -> None:
    for ev in game.drain_events():
        if isinstance(ev, HardDropEvent):
            shake.trigger(intensity=3 + ev.distance * 0.2, duration=0.14)
            sound.play("hard_drop")
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
            sound.play("lock")
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
            if ev.clear_type in (
                ClearType.T_SPIN,
                ClearType.T_SPIN_SINGLE,
                ClearType.T_SPIN_DOUBLE,
                ClearType.T_SPIN_TRIPLE,
                ClearType.T_SPIN_MINI,
                ClearType.T_SPIN_MINI_SINGLE,
                ClearType.T_SPIN_MINI_DOUBLE,
            ):
                sound.play("tspin")
            elif ev.count >= 4:
                sound.play("tetris")
            else:
                sound.play("clear")

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
    app_screen: AppScreen,
    scores: HighScores,
    level_flash_timer: float,
    made_high_score: bool,
) -> None:
    screen.fill(theme.BG)

    if app_screen is AppScreen.MENU:
        screens.draw_menu(screen, scores, fonts)
        return

    offset = shake.offset()

    flash_amount = 0.0
    hide_clearing = False
    if game.clearing:
        t = game.clear_timer / CLEAR_ANIMATION_SECONDS
        if t > 0.5:
            flash_amount = (t - 0.5) * 2
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

    # Level-up flash: fades from 1.0 to 0.0.
    if level_flash_timer > 0:
        progress = level_flash_timer / LEVEL_FLASH_SECONDS
        screens.draw_level_up_flash(screen, game.level, progress, fonts)

    if game.state == GameState.PAUSED:
        screens.draw_pause(screen, fonts)
    elif app_screen is AppScreen.GAME_OVER:
        screens.draw_game_over(
            screen,
            game.score,
            game.lines,
            game.level,
            made_high_score,
            fonts,
        )


def main() -> None:
    """Synchronous entry point for the console script."""
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
