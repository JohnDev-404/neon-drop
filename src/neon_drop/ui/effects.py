"""Visual effects: particles and screen shake.

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


class ParticleSystem:
    """A pool of short-lived neon squares."""

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
        """Emit `count` particles from (x, y)."""
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
            p.vy += 900.0 * dt  # gravity
            p.vx *= 0.98  # drag
            alive.append(p)
        self.particles = alive

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        ox, oy = offset
        for p in self.particles:
            alpha = max(0.0, min(1.0, p.life / p.max_life))
            size = max(1, int(p.size * (0.4 + alpha * 0.6)))
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            surf.fill((*p.color, int(220 * alpha)))
            surface.blit(
                surf,
                (int(p.x + ox) - size // 2, int(p.y + oy) - size // 2),
                special_flags=pygame.BLEND_RGBA_ADD,
            )


class ScreenShake:
    """Time-decaying random jitter applied to the world layer."""

    def __init__(self) -> None:
        self.intensity: float = 0.0
        self.duration: float = 0.0
        self.max_duration: float = 1e-6

    def trigger(self, intensity: float, duration: float) -> None:
        """Start a shake. Larger intensities override smaller ones."""
        if intensity >= self.intensity or self.duration <= 0:
            self.intensity = intensity
            self.duration = duration
            self.max_duration = max(duration, 1e-6)

    def update(self, dt: float) -> None:
        if self.duration > 0:
            self.duration -= dt
            if self.duration <= 0:
                self.intensity = 0.0
                self.duration = 0.0

    def offset(self) -> tuple[int, int]:
        if self.duration <= 0:
            return 0, 0
        falloff = self.duration / self.max_duration
        mag = self.intensity * falloff
        return (
            int(random.uniform(-mag, mag)),
            int(random.uniform(-mag, mag)),
        )

    def reset(self) -> None:
        self.intensity = 0.0
        self.duration = 0.0

    def clear(self) -> None:
        self.particles = []
