import numpy as np

from lumenradar.detect import baseline_compare


def _session(fps: float = 30.0, base_s: float = 2.0, osc_s: float = 6.0, freq: float = 3.0):
    n = int((base_s + osc_s) * fps)
    x = np.zeros(n, dtype=np.float32)
    start = int(base_s * fps)
    t = np.arange(n - start) / fps
    x[start:] = np.sin(2 * np.pi * freq * t).astype(np.float32)
    return x


def test_onset_detected():
    r = baseline_compare(_session(), 30.0)
    assert r.sufficient
    assert r.detected
    assert r.z >= 5.0
    assert r.peak_freq is not None and abs(r.peak_freq - 3.0) <= 0.1


def test_whole_clip_oscillation_not_detected():
    """A clip that oscillates from frame zero has no onset — M3 must stay quiet."""
    fps = 30.0
    n = int(8 * fps)
    x = np.sin(2 * np.pi * 2.0 * np.arange(n) / fps).astype(np.float32)
    r = baseline_compare(x, fps)
    assert r.sufficient
    assert not r.detected


def test_clean_session_not_detected():
    r = baseline_compare(np.zeros(int(8 * 30), dtype=np.float32), 30.0)
    assert r.sufficient
    assert not r.detected


def test_insufficient_session():
    r = baseline_compare(np.zeros(int(3 * 30), dtype=np.float32), 30.0)
    assert not r.sufficient
    assert not r.detected


def test_tiny_noise_onset_not_detected():
    """Near-zero-energy onset: huge z on codec noise must NOT fire (amp gate)."""
    fps = 30.0
    n = int(8 * fps)
    rng = np.random.default_rng(2)
    x = (0.02 * rng.standard_normal(n)).astype(np.float32)
    x[int(2 * fps) :] += 0.04 * np.sin(2 * np.pi * 1.0 * np.arange(n - int(2 * fps)) / fps)
    r = baseline_compare(x, fps)
    assert r.sufficient
    assert r.z >= 5.0  # spectral test alone would fire
    assert r.amplitude < 0.5
    assert not r.detected  # amplitude gate rejects it
