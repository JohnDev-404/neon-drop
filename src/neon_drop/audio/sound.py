"""Procedurally-synthesized sound effects.

Every sound is generated with numpy at startup. No .wav or .ogg files
are needed; the entire audio palette lives in this module.

The sounds use short envelopes (attack / decay / release) applied to
sine, square, and saw waves. Higher frequencies read as "brighter"
and lower ones as "heavier."
"""

from __future__ import annotations

import numpy as np
import pygame

SAMPLE_RATE = 44100


def _envelope(n: int, attack: float, decay: float) -> np.ndarray:
    """Return a length-n array: linear attack, exponential decay."""
    attack_n = max(1, int(attack * SAMPLE_RATE))
    decay_n = max(1, n - attack_n)
    a = np.linspace(0.0, 1.0, attack_n, endpoint=False)
    d = np.exp(-np.linspace(0, decay, decay_n))
    return np.concatenate([a, d])[:n]


def _sine(freq: float, duration: float) -> np.ndarray:
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    return np.sin(2 * np.pi * freq * t)


def _saw(freq: float, duration: float) -> np.ndarray:
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    return 2.0 * (t * freq - np.floor(0.5 + t * freq))


def _square(freq: float, duration: float) -> np.ndarray:
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    return np.sign(np.sin(2 * np.pi * freq * t))


def _to_sound(wave: np.ndarray, volume: float = 0.3) -> pygame.mixer.Sound:
    """Convert a float array in [-1, 1] to a pygame Sound."""
    clipped = np.clip(wave * volume, -1.0, 1.0)
    ints = (clipped * 32767).astype(np.int16)
    stereo = np.column_stack([ints, ints])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _sweep(
    f_start: float, f_end: float, duration: float, waveform: str = "sine"
) -> np.ndarray:
    """A frequency sweep from f_start to f_end over `duration`."""
    n = int(duration * SAMPLE_RATE)
    freqs = np.linspace(f_start, f_end, n)
    phase = 2 * np.pi * np.cumsum(freqs) / SAMPLE_RATE
    if waveform == "saw":
        return 2.0 * (phase / (2 * np.pi) - np.floor(0.5 + phase / (2 * np.pi)))
    if waveform == "square":
        return np.sign(np.sin(phase))
    return np.sin(phase)


class SoundBank:
    """The full SFX set, synthesized at construction.

    Construction takes ~50 ms. After that, play(name) is O(1).
    """

    def __init__(self) -> None:
        self.enabled = True
        self.available = pygame.mixer.get_init() is not None
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        if not self.available:
            # No audio device (e.g. WSL, containers, browsers without
            # WebAudio). Play calls become no-ops.
            self.enabled = False
            return
        try:
            self._build()
        except (pygame.error, ValueError) as exc:
            print(f"[audio] SoundBank synthesis failed: {exc}")
            self.available = False
            self.enabled = False
            self._sounds = {}

    def _build(self) -> None:
        # Move: short, dry, low volume.
        move = _square(220, 0.03) * _envelope(int(0.03 * SAMPLE_RATE), 0.001, 8.0)
        self._sounds["move"] = _to_sound(move, volume=0.35)

        # Rotate: brighter, crisper.
        rot = _square(440, 0.04) * _envelope(int(0.04 * SAMPLE_RATE), 0.001, 6.0)
        self._sounds["rotate"] = _to_sound(rot, volume=0.40)

        # Lock: low thud with a slight saw.
        lock = _saw(110, 0.10) * _envelope(int(0.10 * SAMPLE_RATE), 0.002, 12.0)
        self._sounds["lock"] = _to_sound(lock, volume=0.55)

        # Hard drop: short downward sweep.
        hd = _sweep(320, 80, 0.10, "saw") * _envelope(
            int(0.10 * SAMPLE_RATE), 0.001, 14.0
        )
        self._sounds["hard_drop"] = _to_sound(hd, volume=0.60)

        # Hold: brief two-tone chime.
        hold1 = _sine(660, 0.05) * _envelope(int(0.05 * SAMPLE_RATE), 0.002, 8.0)
        hold2 = _sine(880, 0.05) * _envelope(int(0.05 * SAMPLE_RATE), 0.002, 8.0)
        hold = np.concatenate([hold1, hold2])
        self._sounds["hold"] = _to_sound(hold, volume=0.45)

        # Clear: rising sweep.
        clr = _sweep(300, 900, 0.22, "saw") * _envelope(
            int(0.22 * SAMPLE_RATE), 0.003, 6.0
        )
        self._sounds["clear"] = _to_sound(clr, volume=0.65)

        # Tetris: bigger, deeper, longer.
        tet = _sweep(200, 1200, 0.40, "saw") * _envelope(
            int(0.40 * SAMPLE_RATE), 0.004, 4.0
        )
        self._sounds["tetris"] = _to_sound(tet, volume=0.70)

        # T-spin: sparkle — a brief upward arpeggio.
        notes = [523, 659, 784, 1047]  # C5, E5, G5, C6
        parts = []
        for f in notes:
            seg = _sine(f, 0.06) * _envelope(int(0.06 * SAMPLE_RATE), 0.003, 6.0)
            parts.append(seg)
        self._sounds["tspin"] = _to_sound(np.concatenate(parts), volume=0.55)

        # Level up: rising three-note fanfare.
        fanfare = [392, 523, 659]  # G4, C5, E5
        parts = []
        for f in fanfare:
            seg = _square(f, 0.10) * _envelope(int(0.10 * SAMPLE_RATE), 0.004, 5.0)
            parts.append(seg)
        self._sounds["level_up"] = _to_sound(np.concatenate(parts), volume=0.55)

        # Game over: descending minor arpeggio.
        over_notes = [523, 440, 349, 262]  # C5, A4, F4, C4
        parts = []
        for f in over_notes:
            seg = _saw(f, 0.14) * _envelope(int(0.14 * SAMPLE_RATE), 0.005, 3.0)
            parts.append(seg)
        self._sounds["game_over"] = _to_sound(np.concatenate(parts), volume=0.60)

        # Ambient pad: three harmonically-related sines. 8 s at 44100 Hz
        # = 352 800 samples = exactly 440 / 660 / 880 cycles for the
        # three frequencies, so the loop point is sample-perfect.
        ambient = (
            _sine(55.0, 8.0) * 0.5
            + _sine(82.5, 8.0) * 0.3
            + _sine(110.0, 8.0) * 0.2
        )
        self._sounds["ambient"] = _to_sound(ambient, volume=0.20)

    def play(self, name: str) -> None:
        if not self.enabled or not self.available:
            return
        snd = self._sounds.get(name)
        if snd is not None:
            snd.play()

    def start_ambient(self) -> None:
        """Begin the looping ambient pad. Safe to call once at boot."""
        if not self.available or not self.enabled:
            return
        snd = self._sounds.get("ambient")
        if snd is not None:
            snd.play(loops=-1)

    def toggle(self) -> None:
        if not self.available:
            return
        self.enabled = not self.enabled
        # Pause/resume the whole mixer so ambient and SFX silence together.
        if self.enabled:
            pygame.mixer.unpause()
        else:
            pygame.mixer.pause()