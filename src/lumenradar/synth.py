"""Synthetic video generation for camera-less development and testing.

Every detector path is exercised through synthetic clips: a clean scene
(negative class), periodic brightness oscillation (M1 positive), and
burst/blink-count patterns (M2 positive). The calibration beacon (Faz 3)
reproduces the same physical patterns on real hardware.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def _safe_fps(fps: float, container: str) -> float:
    """Clamp FPS into a range the container actually supports.

    MP4V caps the timebase at 1000 FPS; a higher value silently truncates
    and desyncs timestamps, so the writer clamps instead of trusting input.
    """
    limit = 1000.0 if container in ("mp4", "mov", "m4v") else 10000.0
    if fps <= 0 or math.isnan(fps):
        return 30.0
    return min(fps, limit)


def _resolve_fps(fps: float, path: str) -> float:
    suffix = Path(path).suffix.lstrip(".").lower()
    return _safe_fps(fps, suffix)


@dataclass
class Scene:
    """A synthetic scene: structured background + a controllable light source.

    The background is deliberately non-flat (gradient + blocks) so that a
    detector shortcut keyed on "flat average" cannot pass trivially.
    ``light`` adds a bright rectangle whose extra brightness follows the
    modulation value in [0..1].
    """

    width: int = 640
    height: int = 480
    background: np.ndarray | None = None
    light_center: tuple[int, int] = (520, 60)
    light_size: tuple[int, int] = (16, 16)
    light_gain: float = 255.0  # max extra brightness of the light region
    seed: int = 42
    _rng: np.random.Generator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.background is None:
            x = np.linspace(0, 1, self.width, dtype=np.float32)
            y = np.linspace(0, 1, self.height, dtype=np.float32)
            grad = np.add.outer(y * 40, x * 40)
            base = np.full((self.height, self.width, 3), 60, dtype=np.float32)
            base[:, :, 0] += grad
            base[:, 64:192, 1] += 25
            base[360:440, :, 2] += 20
            self.background = np.clip(base, 0, 255).astype(np.uint8)
        self._rng = np.random.default_rng(self.seed)

    def frame(self, brightness: float) -> np.ndarray:
        """Render one frame; ``brightness`` in [0..1] scales the light source."""
        img = self.background.copy()
        cx, cy = self.light_center
        w, h = self.light_size
        add = float(np.clip(self.light_gain * brightness, 0, 255))
        roi = img[cy : cy + h, cx : cx + w].astype(np.float32)
        img[cy : cy + h, cx : cx + w] = np.clip(roi + add, 0, 255).astype(np.uint8)
        noise = self._rng.normal(0.0, 1.2, img.shape).astype(np.float32)
        return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    def light_means(self, frames_arr: np.ndarray) -> np.ndarray:
        """Per-frame mean intensity inside the light region (test oracle)."""
        cx, cy = self.light_center
        w, h = self.light_size
        region = frames_arr[:, cy : cy + h, cx : cx + w, :]
        return region.astype(np.float32).mean(axis=(1, 2, 3))


def write_video(path: str, frames_arr: np.ndarray, fps: float, codec: str = "mp4v") -> Path:
    """Write an (n, h, w, 3) uint8 array to a video file. Returns the path."""
    if frames_arr.ndim != 4 or frames_arr.dtype != np.uint8:
        raise ValueError("frames must be an (n, h, w, 3) uint8 array")
    if frames_arr.shape[0] == 0:
        raise ValueError("cannot write an empty frame array")
    n, _, _, _ = frames_arr.shape
    h, w = frames_arr.shape[1], frames_arr.shape[2]
    fourcc = cv2.VideoWriter_fourcc(*codec)
    out = cv2.VideoWriter(str(path), fourcc, _resolve_fps(fps, path), (w, h))
    if not out.isOpened():
        raise RuntimeError(f"VideoWriter failed to open {path!r} (codec={codec})")
    try:
        for i in range(n):
            out.write(frames_arr[i])
    finally:
        out.release()
    return Path(path)


def _render(scene: Scene, levels: np.ndarray) -> np.ndarray:
    return np.stack([scene.frame(float(b)) for b in levels])


def clean_video(
    seconds: float = 4.0, fps: float = 30.0, seed: int = 42, path: str | None = None, **kw: Any
) -> np.ndarray:
    """Static scene, light off — the negative class."""
    scene = Scene(seed=seed, **kw)
    arr = _render(scene, np.zeros(int(seconds * fps), dtype=np.float32))
    if path:
        write_video(path, arr, fps)
    return arr


def periodic_video(
    freq: float = 2.0,
    seconds: float = 6.0,
    fps: float = 30.0,
    depth: float = 0.5,
    seed: int = 7,
    path: str | None = None,
    **kw: Any,
) -> np.ndarray:
    """Sinusoidal luminance oscillation of the light source (M1 positive)."""
    scene = Scene(seed=seed, **kw)
    n = int(seconds * fps)
    levels = 0.5 + depth / 2 * np.sin(2 * math.pi * freq * np.arange(n) / fps)
    arr = _render(scene, levels.astype(np.float32))
    if path:
        write_video(path, arr, fps)
    return arr


def burst_video(
    pattern: Sequence[int] = (1, 1, 2, 1, 2, 1, 2),
    seconds: float = 8.0,
    fps: float = 30.0,
    seed: int = 3,
    path: str | None = None,
    **kw: Any,
) -> np.ndarray:
    """Burst/blink-count symbol pattern (M2 positive).

    Each symbol emits ``count`` short pulses (2 frames on, 3 frames off),
    then a 0.6 s gap before the next symbol — the temporal signature of a
    blink-count covert code (1 pulse = A, 2 = B, ...).
    """
    scene = Scene(seed=seed, **kw)
    total = int(seconds * fps)
    levels = np.zeros(total, dtype=np.float32)
    t = int(0.2 * fps)  # lead-in with the light off
    on, off = 2, 3
    for count in pattern:
        for _ in range(count):
            for k in range(on):
                if t + k < total:
                    levels[t + k] = 1.0
            t += on + off
        t += int(0.6 * fps)
    arr = _render(scene, levels)
    if path:
        write_video(path, arr, fps)
    return arr
