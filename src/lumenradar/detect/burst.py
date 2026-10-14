"""M2 — burst pulse-count symbol structure (the blink-code signature).

A blink-count covert code emits N short pulses per symbol (1=A, 2=B, ...),
repeated with machine-like timing. The detector segments pulses via threshold
crossing, splits intervals into intra/inter-symbol clusters at the largest
bimodal jump (NOT the median — when single-count symbols dominate, the
median lands on the inter-gap and a median-based split collapses), then
requires: repeating counts, low intra-gap variance AND low inter-gap variance
(random aperiodic activity — e.g. an HDD LED — fails the pacing test).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np

JUMP_MIN = 2.0
INTRA_CV_MAX = 0.6
INTER_CV_MAX = 0.35
GAP_CONTRAST = 2.0
MIN_PULSES = 4
MIN_SYMBOLS = 3
MIN_INTRA_INTERVALS = 2


@dataclass
class BurstResult:
    """Outcome of M2 burst-structure analysis."""

    pulses: int
    counts: list[int]
    symbol_repeats: bool
    timing_regular: bool
    detected: bool
    duty: float


def _split_threshold(intervals: np.ndarray) -> float | None:
    """Bimodal split at the largest ratio jump between sorted intervals."""
    s = np.sort(intervals)
    ratios = s[1:] / np.maximum(s[:-1], 1e-9)
    j = int(np.argmax(ratios))
    if ratios[j] < JUMP_MIN:
        return None
    # The low cluster must hold at least MIN_INTRA_INTERVALS intervals,
    # otherwise the "jump" is just a sparse tail, not a bimodal structure.
    low = int((s <= s[j]).sum())
    if low < MIN_INTRA_INTERVALS:
        return None
    return float((s[j] + s[j + 1]) / 2.0)


def _counts_from_intervals(intervals: np.ndarray, split: float | None) -> list[int]:
    """Group pulses into symbols; the trailing separator is NOT a symbol.

    The interval list is between consecutive pulses, so a trailing gap does
    not create a phantom extra symbol — but a final symbol that is cut off
    by the end of the clip (no separator after it) cannot be verified as
    complete and is excluded from the pattern when it would stand alone.
    """
    if split is None:
        return [len(intervals) + 1]
    counts: list[int] = []
    current = 1
    for iv in intervals:
        if iv > split:
            counts.append(current)
            current = 1
        else:
            current += 1
    counts.append(current)
    return counts


def _cv(vals: np.ndarray) -> float:
    return float(np.std(vals)) / max(float(np.mean(vals)), 1e-9)


def detect_bursts(
    x: np.ndarray,
    fps: float,
    rel_threshold: float = 0.5,
    min_pulses: int = MIN_PULSES,
    min_symbols: int = MIN_SYMBOLS,
) -> BurstResult:
    """Detect a repeating pulse-count pattern in the series."""
    del fps  # intervals are handled in frames; fps kept for API symmetry
    x = np.asarray(x, dtype=np.float32)
    empty = BurstResult(0, [], False, False, False, 0.0)
    if x.size < 15 or float(x.std()) < 1e-6 or float(x.max()) <= float(x.min()):
        return empty

    thr = float(x.min()) + rel_threshold * (float(x.max()) - float(x.min()))
    on = x > thr
    d = np.diff(on.astype(np.int8))
    rising = np.flatnonzero(d == 1) + 1
    if bool(on[0]):
        rising = np.concatenate(([0], rising))
    pulses = int(rising.size)
    duty = float(on.mean())
    if pulses < min_pulses:
        return BurstResult(pulses, [], False, False, False, duty)

    intervals = np.diff(rising).astype(np.float64)
    split = _split_threshold(intervals)
    counts = _counts_from_intervals(intervals, split)
    if len(counts) < min_symbols:
        return BurstResult(pulses, counts, False, False, False, round(duty, 3))

    repeats = max(Counter(counts).values()) >= 2

    regular = False
    if split is not None:
        intra = intervals[intervals <= split]
        inter = intervals[intervals > split]
        if intra.size >= MIN_INTRA_INTERVALS and inter.size >= 2:
            contrast = float(np.median(inter)) / max(float(np.median(intra)), 1e-9)
            regular = (
                _cv(intra) <= INTRA_CV_MAX
                and _cv(inter) <= INTER_CV_MAX
                and contrast >= GAP_CONTRAST
            )

    detected = bool(repeats and regular)
    return BurstResult(pulses, counts, repeats, regular, detected, round(duty, 3))
