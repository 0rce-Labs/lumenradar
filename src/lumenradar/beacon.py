"""Calibration beacon — DATASET-LABELING UTILITY ONLY.

Produces a FIXED, DOCUMENTED test pattern (blink-count sequence, sine or
square brightness modulation) on screen, so positive-class samples can be
recorded on your own hardware for detector calibration.

Hard scope boundary (see docs/THREAT-MODEL.md):
- no input capture of any kind (no screen reading, no keylogging),
- no network access, no LLM, no answer generation,
- no integration point other than "play a fixed pattern for N seconds",
- PRs adding input capture or message encoding will be rejected.
"""

from __future__ import annotations

import numpy as np

PATTERNS = ("blink", "sine2", "square5")

_PULSE_ON_S = 0.05
_PULSE_OFF_S = 0.07
_SYMBOL_GAP_S = 0.7
_BLINK_CYCLE = (1, 2, 3, 4)


def waveform(pattern: str, seconds: float, fps: float) -> np.ndarray:
    """Light-source level in [0..1] per frame for the chosen fixed pattern."""
    if pattern not in PATTERNS:
        raise ValueError(f"unknown pattern {pattern!r}; choose from {PATTERNS}")
    n = int(seconds * fps)
    t = np.arange(n) / fps
    if pattern == "sine2":
        return (0.5 + 0.45 * np.sin(2 * np.pi * 2.0 * t)).astype(np.float32)
    if pattern == "square5":
        return np.where((t * 5.0) % 1.0 < 0.5, 0.95, 0.05).astype(np.float32)

    # blink: repeating 1..4 pulse-count symbols with machine-like timing.
    levels = np.zeros(n, dtype=np.float32)
    t_cursor = 0.0
    while t_cursor < seconds:
        for count in _BLINK_CYCLE:
            for _ in range(count):
                on_start = t_cursor
                on_end = t_cursor + _PULSE_ON_S
                idx = (t >= on_start) & (t < on_end)
                levels[idx] = 1.0
                t_cursor = on_end + _PULSE_OFF_S
            t_cursor += _SYMBOL_GAP_S
            if t_cursor >= seconds:
                break
    return levels


def play_screen(levels: np.ndarray, fps: float, size: int = 320) -> None:
    """Display the pattern in an OpenCV window (requires a display server).

    A centered white square whose brightness follows ``levels``. Quit early
    with the 'q' key. This is the entire beacon output path — no capture,
    no side channels.
    """
    import cv2  # deferred: analysis-only installs never need a GUI

    side = size
    margin = side // 4
    frame = np.zeros((side, side, 3), dtype=np.uint8)
    window = "lumenradar-beacon (q = quit)"
    delay = max(1, int(round(1000.0 / fps)))
    cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE)
    try:
        for level in levels:
            img = frame.copy()
            v = int(round(255.0 * float(np.clip(level, 0.0, 1.0))))
            img[margin : side - margin, margin : side - margin] = v
            cv2.imshow(window, img)
            if cv2.waitKey(delay) & 0xFF == ord("q"):
                break
    finally:
        cv2.destroyWindow(window)
