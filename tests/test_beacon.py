import numpy as np
import pytest

from lumenradar.beacon import PATTERNS, waveform


def _rising_groups(levels: np.ndarray) -> list[int]:
    """Count pulses per symbol from a beacon level sequence."""
    on = levels > 0.5
    d = np.diff(on.astype(np.int8))
    rising = np.flatnonzero(d == 1)
    if on[0]:
        rising = np.concatenate(([0], rising))
    if rising.size == 0:
        return []
    intervals = np.diff(rising)
    med = float(np.median(intervals))
    split = 0.3 / 0.12 * med  # symbol gap (0.7 s) vs pulse spacing (0.12 s)
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


def test_blink_waveform_repeats_1234():
    lv = waveform("blink", 8.5, 30.0)
    counts = _rising_groups(lv)
    assert counts[:8] == [1, 2, 3, 4, 1, 2, 3, 4]


def test_blink_duty_is_low():
    lv = waveform("blink", 8.0, 30.0)
    assert float((lv > 0.5).mean()) < 0.2  # mostly off — LED-like


def test_sine2_oscillates_at_2hz():
    lv = waveform("sine2", 6.0, 30.0)
    x = lv - lv.mean()
    spec = np.abs(np.fft.rfft(x * np.hanning(x.size)))
    freqs = np.fft.rfftfreq(x.size, d=1 / 30.0)
    peak = freqs[int(np.argmax(spec[1:])) + 1]
    assert abs(peak - 2.0) < 0.05


def test_square5_alternates():
    lv = waveform("square5", 2.0, 30.0)
    on = lv > 0.5
    d = np.diff(on.astype(np.int8))
    rises = int((d == 1).sum()) + int(on[0])  # np.diff misses the start-on edge
    assert rises == 10  # 5 Hz * 2 s


def test_levels_within_unit_range():
    for p in PATTERNS:
        lv = waveform(p, 2.0, 30.0)
        assert lv.min() >= 0.0 and lv.max() <= 1.0


def test_unknown_pattern_raises():
    with pytest.raises(ValueError):
        waveform("evil_pattern", 2.0, 30.0)
