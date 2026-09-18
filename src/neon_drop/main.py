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
from neon_drop.ui.effects import DropAnimation, ParticleSystem, ScreenShake
from neon_drop.ui.hud import draw_hud

LEVEL_FLASH_SECONDS = 1.2
HITSTOP_SECONDS = 0.05
BANNER_SECONDS = 1.1

# Gameplay runs at a fixed rate independent of render rate. Keeps gravity,
# DAS, and lock delay consistent even when the OS hitches a frame.
FIXED_DT = 1 / 120.0


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
    # CRITICAL ORDER: pre_init must run before pygame.init(), otherwise
    # the mixer is already initialized with pygame's defaults and your
    # buffer size / sample rate requests are silently ignored.
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()

    try:
        pygame.mixer.init()
    except pygame.error as exc:
        print(f"[audio] mixer.init() failed: {exc}")

    if pygame.mixer.get_init() is None:
        print("[audio] mixer UNAVAILABLE — game will run silent.")
        print("        Ubuntu troubleshooting:")
        print("          - check `pactl info` shows a server")
        print("          - try: SDL_AUDIODRIVER=pulseaudio python -m neon_drop")
        print("          - or:  SDL_AUDIODRIVER=pipewire   python -m neon_drop")
    else:
        print(f"[audio] mixer ready: {pygame.mixer.get_init()}")

    pygame.display.set_caption(config.WINDOW_TITLE)
    screen = pygame.display.set_mode(
        (config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
        pygame.SCALED,
        vsync=1,
    )
    clock = pygame.time.Clock()

    game = Game()
    inputs = InputHandler()
    fonts = theme.Fonts()
    particles = ParticleSystem()
    shake = ScreenShake()
    sound = SoundBank()
    scores = HighScores()

    # Kick off the ambient pad if audio came up. No-op otherwise.
    sound.start_ambient()

    app_screen = AppScreen.MENU
    made_high_score = False

    level_flash_timer = 0.0
    last_seen_level = game.level
    hitstop_timer = 0.0
    banner_timer = 0.0
    drop_anims: list[DropAnimation] = []
    accumulator = 0.0

    def start_run() -> None:
        nonlocal app_screen, made_high_score, last_seen_level
        nonlocal hitstop_timer, banner_timer, level_flash_timer, accumulator
        game.reset()
        particles.particles.clear()
        shake.reset()
        drop_anims.clear()
        hitstop_timer = 0.0
        banner_timer = 0.0
        level_flash_timer = 0.0
        accumulator = 0.0
        last_seen_level = game.level
        made_high_score = False
        app_screen = AppScreen.PLAYING

    running = True
    while running:
        frame_dt = min(clock.tick(config.FPS) / 1000.0, 1 / 30)

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
                    start_run()
                continue

            if app_screen is AppScreen.GAME_OVER:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    start_run()
                elif event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_RETURN,
                    pygame.K_KP_ENTER,
                ):
                    app_screen = AppScreen.MENU
                continue

            # ---- PLAYING ----
            inputs.handle_event(event, game)
            inputs.handle_keyup(event)

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

        # ---------- Fixed-timestep gameplay ----------
        accumulator += frame_dt
        # Clamp to avoid a spiral-of-death after a long hitch.
        if accumulator > 0.25:
            accumulator = 0.25

        while accumulator >= FIXED_DT:
            if app_screen is AppScreen.PLAYING:
                if hitstop_timer > 0:
                    hitstop_timer = max(0.0, hitstop_timer - FIXED_DT)
                else:
                    prev_x = game.current.x if game.current is not None else None
                    inputs.tick(FIXED_DT, game)
                    game.tick(FIXED_DT)

                    # Dry tick on horizontal move. Comparing positions
                    # catches DAS auto-repeat too, unlike KEYDOWN events.
                    if (
                        prev_x is not None
                        and game.current is not None
                        and prev_x != game.current.x
                    ):
                        sound.play("move")

                    stop, banner = _process_events(
                        game, particles, shake, sound, drop_anims
                    )
                    if stop > 0:
                        hitstop_timer = stop
                    if banner > 0:
                        banner_timer = banner

                    if game.level > last_seen_level:
                        level_flash_timer = LEVEL_FLASH_SECONDS
                        sound.play("level_up")
                        last_seen_level = game.level

                    if game.state == GameState.GAME_OVER:
                        made_high_score = scores.submit(
                            game.score, game.lines, game.level
                        )
                        sound.play("game_over")
                        app_screen = AppScreen.GAME_OVER

            accumulator -= FIXED_DT

        # ---------- Visual updates at true frame rate ----------
        for a in drop_anims:
            a.t += frame_dt
        drop_anims[:] = [a for a in drop_anims if not a.done]

        particles.update(frame_dt)
        shake.update(frame_dt)
        if level_flash_timer > 0:
            level_flash_timer = max(0.0, level_flash_timer - frame_dt)
        if banner_timer > 0:
            banner_timer = max(0.0, banner_timer - frame_dt)

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
            drop_anims,
            hitstop_timer,
            banner_timer,
        )
        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


def _process_events(
    game: Game,
    particles: ParticleSystem,
    shake: ScreenShake,
    sound: SoundBank,
    drop_anims: list[DropAnimation],
) -> tuple[float, float]:
    """Drain Game events → visual/audio feedback.

    Returns (hitstop_seconds, banner_seconds) so the caller can schedule
    a freeze-frame and a status-banner fade.
    """
    hitstop = 0.0
    banner = 0.0

    for ev in game.drain_events():
        if isinstance(ev, HardDropEvent):
            shake.trigger(intensity=3 + ev.distance * 0.2, duration=0.14)
            sound.play("hard_drop")
            for cell in ev.cells:
                end_x, end_y = _cell_center(cell)
                col, row = cell
                start_x, start_y = _cell_center((col, row - ev.distance))
                drop_anims.append(
                    DropAnimation(ev.kind, start_x, start_y, end_x, end_y)
                )
                particles.burst(
                    end_x,
                    end_y,
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

            hitstop = HITSTOP_SECONDS
            banner = BANNER_SECONDS

            for row in ev.rows:
                visible_row = row - config.HIDDEN_ROWS
                if visible_row < 0:
                    continue
                for col in range(config.COLS):
                    x = config.BOARD_X + col * config.CELL_SIZE + config.CELL_SIZE / 2
                    y = (
                        config.BOARD_Y
                        + visible_row * config.CELL_SIZE
                        + config.CELL_SIZE / 2
                    )
                    particles.burst(
                        x,
                        y,
                        (255, 255, 255),
                        count=2,
                        speed=260,
                        size=4,
                        life=0.5,
                    )

    return hitstop, banner


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
    drop_anims: list[DropAnimation],
    hitstop_timer: float,
    banner_timer: float,
) -> None:
    screen.blit(theme.background(*screen.get_size()), (0, 0))

    if app_screen is AppScreen.MENU:
        screens.draw_menu(screen, scores, fonts)
        return

    offset = shake.offset()

    flash_amount = 0.0
    hide_clearing = False
    if game.clearing and hitstop_timer <= 0:
        t = game.clear_timer / CLEAR_ANIMATION_SECONDS
        if t < 0.35:
            flash_amount = (t / 0.35) ** 0.7
        elif t < 0.5:
            flash_amount = 1.0
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

    if drop_anims:
        renderer.draw_drop_animations(screen, drop_anims, offset=offset)

    particles.draw(screen, offset=offset)

    draw_hud(
        screen,
        game,
        fonts,
        banner_progress=banner_timer / BANNER_SECONDS if banner_timer > 0 else 0.0,
    )

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