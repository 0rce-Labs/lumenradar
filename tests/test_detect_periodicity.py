import numpy as np

from lumenradar.detect import band_periodicity


def _sine(freq: float, fps: float, seconds: float, amp: float = 1.0) -> np.ndarray:
    n = int(seconds * fps)
    return (amp * np.sin(2 * np.pi * freq * np.arange(n) / fps)).astype(np.float32)


def _square(freq: float, fps: float, seconds: float, duty: float = 0.5) -> np.ndarray:
    n = int(seconds * fps)
    period = fps / freq
    on = int(period * duty)
    phase = np.arange(n) % period
    return (phase < on).astype(np.float32)


def test_sine_detected_with_harmonics():
    r = band_periodicity(_sine(2.0, 30.0, 6.0), 30.0)
    assert r.detected
    assert r.strong
    assert r.harmonic_ok is True
    assert abs(r.peak_freq - 2.0) <= 0.05


def test_pulse_train_detected():
    r = band_periodicity(_square(5.0, 30.0, 6.0), 30.0)
    assert r.detected
    assert abs(r.peak_freq - 5.0) <= 0.1


def test_white_noise_not_detected():
    for seed in range(10):
        rng = np.random.default_rng(seed)
        x = rng.normal(0.0, 1.0, 180).astype(np.float32)
        assert not band_periodicity(x, 30.0).detected, f"FP on noise seed {seed}"


def test_flat_not_detected():
    assert not band_periodicity(np.zeros(180, dtype=np.float32), 30.0).detected


def test_below_band_not_detected():
    r = band_periodicity(_sine(0.2, 30.0, 8.0), 30.0)
    assert not r.detected  # 0.2 Hz sits under the 0.5 Hz band edge


def test_low_frequency_in_band():
    r = band_periodicity(_sine(0.8, 30.0, 10.0), 30.0)
    assert r.detected
    assert abs(r.peak_freq - 0.8) <= 0.05
