"""Luminance time-series extraction from an ROI."""

from __future__ import annotations

import cv2
import numpy as np

from .ingest import frames
from .roi import ROI


class LuminanceSeries:
    """Per-frame mean luminance of a fixed ROI, plus derived stats."""

    def __init__(self, times: np.ndarray, values: np.ndarray, source_fps: float) -> None:
        if times.shape != values.shape:
            raise ValueError("times and values must have the same shape")
        self.times = times.astype(np.float32)
        self.values = values.astype(np.float32)
        self.source_fps = float(source_fps)

    @property
    def n(self) -> int:
        return int(self.times.size)

    @property
    def duration(self) -> float:
        return float(self.times[-1]) if self.times.size else 0.0

    @property
    def effective_fps(self) -> float:
        if self.times.size < 2:
            return self.source_fps
        d = np.diff(self.times)
        med = float(np.median(d))
        return 1.0 / med if med > 0 else self.source_fps

    def detrend(self, window_s: float = 2.0) -> np.ndarray:
        """Remove slow drift with a centered moving median.

        A moving mean follows oscillation valleys and suppresses low-duty
        pulses; the median is robust there. Window ~2 s preserves the whole
        0.5-15 Hz band of interest while killing sub-0.5 Hz drift.
        """
        x = self.values
        n = x.size
        if n == 0:
            return x.copy()
        w = max(3, int(round(window_s * self.effective_fps)))
        if w % 2 == 0:
            w += 1
        pad = np.pad(x, (w // 2, w // 2), mode="edge")
        base = np.array([np.median(pad[i : i + w]) for i in range(n)], dtype=np.float32)
        return (x - base).astype(np.float32)


def extract_series(
    source: str | int, roi: ROI | None = None, max_fps: float | None = None
) -> LuminanceSeries:
    """Extract the ROI mean-luminance series from a video source.

    ``roi=None`` analyzes the whole frame — background drift dominates there,
    which is useful as a control channel for artifact rejection in Faz 2.
    """
    times: list[float] = []
    values: list[float] = []
    sl = roi.slice() if roi is not None else None
    for t, frame in frames(source, max_fps=max_fps):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        region = gray[sl] if sl is not None else gray
        times.append(float(t))
        values.append(float(region.mean()))
    if not values:
        raise ValueError(f"no frames decoded from source: {source!r}")
    arr_t = np.asarray(times, dtype=np.float32)
    arr_v = np.asarray(values, dtype=np.float32)
    src_fps = 30.0
    if arr_t.size >= 2:
        d = float(np.median(np.diff(arr_t)))
        if d > 0:
            src_fps = 1.0 / d
    return LuminanceSeries(arr_t, arr_v, src_fps)
