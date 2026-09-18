"""Visual effects: particles, screen shake, hard-drop animation.

Neither class touches game logic; they're pure cosmetic state.
main.py emits and ticks them based on Game events.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: tuple[int, int, int]
    size: float


# Spark sprites are cached per (color, size, alpha-bucket) so the draw
# loop never allocates. Size is quantized to even pixels and alpha to
# 32-step buckets to keep the cache tiny.
_SPARK_CACHE: dict[tuple, pygame.Surface] = {}


def _get_spark(
    color: tuple[int, int, int], size: int, alpha: int
) -> pygame.Surface:
    size = max(2, size & ~1)              # force even
    alpha_bucket = (alpha // 32) * 32     # 0, 32, 64, ..., 224
    key = (color, size, alpha_bucket)
    surf = _SPARK_CACHE.get(key)
    if surf is None:
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((color[0], color[1], color[2], alpha_bucket))
        _SPARK_CACHE[key] = surf
    return surf


class ParticleSystem:
    """A pool of short-lived neon sparks."""

    def __init__(self) -> None:
        self.particles: list[Particle] = []

    def burst(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        *,
        count: int = 12,
        speed: float = 220.0,
        size: float = 4.0,
        life: float = 0.6,
        spread: float = math.tau,
        direction: float = 0.0,
    ) -> None:
        for _ in range(count):
            angle = direction + (random.random() - 0.5) * spread
            mag = speed * (0.4 + random.random() * 0.6)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * mag,
                    vy=math.sin(angle) * mag,
                    life=life * (0.6 + random.random() * 0.6),
                    max_life=life,
                    color=color,
                    size=size * (0.6 + random.random() * 0.8),
                )
            )

    def update(self, dt: float) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 900.0 * dt       # gravity
            p.vx *= 0.98             # drag
            p.vy *= 0.98
            alive.append(p)
        self.particles = alive

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        ox, oy = offset
        for p in self.particles:
            alpha_f = max(0.0, min(1.0, p.life / p.max_life))
            size = max(2, int(p.size * (0.4 + alpha_f * 0.6)))
            alpha = int(220 * alpha_f)
            sprite = _get_spark(p.color, size, alpha)
            w = sprite.get_width()
            surface.blit(
                sprite,
                (int(p.x + ox) - w // 2, int(p.y + oy) - w // 2),
                special_flags=pygame.BLEND_RGBA_ADD,
            )


class ScreenShake:
    """Smooth damped-sine shake. Much better feel than pure random jitter."""

    def __init__(self) -> None:
        self.intensity: float = 0.0
        self.duration: float = 0.0
        self.max_duration: float = 1e-6
        self._phase: float = 0.0

    def trigger(self, intensity: float, duration: float) -> None:
        """Larger intensities override smaller ones."""
        if intensity >= self.intensity or self.duration <= 0:
            self.intensity = intensity
            self.duration = duration
            self.max_duration = max(duration, 1e-6)
            self._phase = 0.0

    def update(self, dt: float) -> None:
        if self.duration > 0:
            self.duration -= dt
            self._phase += dt
            if self.duration <= 0:
                self.intensity = 0.0
                self.duration = 0.0

    def offset(self) -> tuple[int, int]:
        if self.duration <= 0:
            return 0, 0
        falloff = self.duration / self.max_duration
        falloff = falloff * falloff * (3 - 2 * falloff)
        mag = self.intensity * falloff
        t = self._phase * 45.0
        return (
            int(math.sin(t * 1.7) * mag),
            int(math.cos(t * 2.3) * mag),
        )

    def reset(self) -> None:
        self.intensity = 0.0
        self.duration = 0.0
        self.max_duration = 1e-6
        self._phase = 0.0

    def clear(self) -> None:
        self.reset()


@dataclass
class DropAnimation:
    """Cosmetic interpolation for a hard drop. Purely visual."""

    kind: str
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    duration: float = 0.075
    t: float = 0.0

    @property
    def progress(self) -> float:
        if self.duration <= 0:
            return 1.0
        return min(1.0, self.t / self.duration)

    @property
    def done(self) -> bool:
        return self.t >= self.duration