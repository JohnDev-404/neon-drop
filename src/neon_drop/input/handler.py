"""Keyboard input with DAS/ARR auto-repeat."""

from __future__ import annotations

import pygame

from neon_drop.core.game import Game, GameState
from neon_drop.core.srs import CCW, CW

# Delayed Auto Shift: how long to hold a direction before it starts
# repeating. 133 ms matches modern guideline defaults.
DAS_SECONDS: float = 0.133

# Auto Repeat Rate: interval between repeats once DAS has elapsed.
ARR_SECONDS: float = 0.033

# Soft drop repeat interval when holding Down.
SOFT_DROP_INTERVAL: float = 0.025


class InputHandler:
    """Tracks key state and drives the Game in response to held keys."""

    def __init__(self) -> None:
        self._left_held = False
        self._right_held = False
        self._soft_held = False
        self._left_timer = 0.0
        self._right_timer = 0.0
        self._soft_timer = 0.0

    # --- one-shot events -------------------------------------------------

    def handle_event(self, event: pygame.event.Event, game: Game) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            game.toggle_pause()
            return

        if event.key == pygame.K_r:
            game.reset()
            return

        if game.state != GameState.PLAYING:
            return
        elif event.key in (pygame.K_c, pygame.K_LSHIFT, pygame.K_RSHIFT):
            game.hold()

        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._left_held = True
            self._left_timer = 0.0
            game.move(-1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._right_held = True
            self._right_timer = 0.0
            game.move(+1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._soft_held = True
            self._soft_timer = 0.0
            game.soft_drop()
        elif event.key in (pygame.K_UP, pygame.K_x):
            game.rotate(CW)
        elif event.key in (pygame.K_z, pygame.K_LCTRL, pygame.K_RCTRL):
            game.rotate(CCW)
        elif event.key == pygame.K_SPACE:
            game.hard_drop()

    def handle_keyup(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYUP:
            return
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._left_held = False
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._right_held = False
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._soft_held = False

    # --- per-frame update -----------------------------------------------

    def tick(self, dt: float, game: Game) -> None:
        if game.state != GameState.PLAYING:
            return

        self._tick_horizontal(dt, game)

        if self._soft_held:
            self._soft_timer += dt
            while self._soft_timer >= SOFT_DROP_INTERVAL:
                self._soft_timer -= SOFT_DROP_INTERVAL
                game.soft_drop()

    def _tick_horizontal(self, dt: float, game: Game) -> None:
        for held, timer_attr, direction in (
            (self._left_held, "_left_timer", -1),
            (self._right_held, "_right_timer", +1),
        ):
            if not held:
                continue
            timer = getattr(self, timer_attr) + dt
            if timer >= DAS_SECONDS:
                while timer >= DAS_SECONDS:
                    timer -= ARR_SECONDS
                    game.move(direction)
            setattr(self, timer_attr, timer)
