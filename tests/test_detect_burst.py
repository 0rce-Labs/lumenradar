import numpy as np

from lumenradar.detect import detect_bursts


def _levels(
    pattern: tuple[int, ...],
    fps: float = 30.0,
    on: int = 2,
    off: int = 3,
    gap_s: float = 0.6,
    lead_s: float = 0.2,
    tail_s: float = 1.0,
) -> np.ndarray:
    pattern_s = sum(c * (on + off) for c in pattern) / fps + gap_s * len(pattern)
    total = int((lead_s + pattern_s + tail_s) * fps)
    levels = np.zeros(total, dtype=np.float32)
    t = int(lead_s * fps)
    for count in pattern:
        for _ in range(count):
            for k in range(on):
                if t + k < total:
                    levels[t + k] = 1.0
            t += on + off
        t += int(gap_s * fps)
    return levels


def test_blink_pattern_detected_counts_match():
    pattern = (1, 1, 2, 1, 2, 1, 2)
    r = detect_bursts(_levels(pattern), 30.0)
    assert r.pulses == sum(pattern)
    assert r.counts == list(pattern)
    assert r.symbol_repeats
    assert r.timing_regular
    assert r.detected


def test_low_duty_blink_survives():
    pattern = (1, 2, 1, 2, 1, 2)
    r = detect_bursts(_levels(pattern, on=1, off=14, gap_s=1.5), 30.0)
    assert r.detected
    assert r.counts == list(pattern)


def test_single_count_pattern_is_periodic_pulse():
    pattern = (2, 2, 2, 2, 2, 2)
    r = detect_bursts(_levels(pattern), 30.0)
    assert r.detected
    assert all(c == 2 for c in r.counts)


def test_aperiodic_activity_not_detected():
    """HDD-LED-like irregular blinking must not trip the symbol detector."""
    rng = np.random.default_rng(4)
    intervals = rng.integers(3, 26, size=40)
    rising = np.cumsum(intervals)
    x = np.zeros(int(rising[-1]) + 5, dtype=np.float32)
    x[rising] = 1.0
    x[rising + 1] = 1.0
    r = detect_bursts(x, 30.0)
    assert not r.detected


def test_too_few_pulses():
    r = detect_bursts(_levels((1,), tail_s=2.0), 30.0)
    assert not r.detected
    assert r.pulses == 1


def test_noise_no_pulses():
    rng = np.random.default_rng(9)
    x = rng.normal(0.0, 0.5, 240).astype(np.float32)
    r = detect_bursts(x, 30.0)
    assert not r.detected


def test_constant_empty():
    r = detect_bursts(np.ones(120, dtype=np.float32), 30.0)
    assert not r.detected
    assert r.pulses == 0
