import numpy as np

from lumenradar.detect import classify, mains_alias_match, mains_aliases


def _sine(freq: float, fps: float, seconds: float = 6.0, amp: float = 1.0) -> np.ndarray:
    n = int(seconds * fps)
    return (amp * np.sin(2 * np.pi * freq * np.arange(n) / fps)).astype(np.float32)


def test_ae_lockstep_flagged():
    """Correlation AND magnitude both high -> exposure artifact."""
    roi = _sine(2.0, 30.0)
    control = 2.0 * _sine(2.0, 30.0) + 0.05
    r = classify(roi, control, 30.0, 2.0)
    assert r.artifact == "ae_hunting"
    assert r.correlation is not None and r.correlation > 0.95
    assert r.control_ratio is not None and r.control_ratio >= 0.25


def test_correlated_but_tiny_control_not_flagged():
    """Codec bleed: correlated with the ROI but orders of magnitude smaller."""
    roi = _sine(2.0, 30.0)
    control = 0.01 * _sine(2.0, 30.0)
    r = classify(roi, control, 30.0, 2.0)
    assert r.artifact is None


def test_localized_signal_not_flagged():
    roi = _sine(2.0, 30.0)
    rng = np.random.default_rng(1)
    control = rng.normal(0.0, 0.3, roi.size).astype(np.float32)
    r = classify(roi, control, 30.0, 2.0)
    assert r.artifact is None
    assert r.correlation is not None and abs(r.correlation) < 0.7


def test_control_none_disables_correlation():
    r = classify(_sine(2.0, 30.0), None, 30.0, 2.0)
    assert r.artifact is None
    assert r.correlation is None
    assert r.control_ratio is None


def test_mains_alias_math():
    assert mains_aliases(240.0) == [100.0, 120.0]
    assert mains_alias_match(100.0, 240.0)
    assert mains_alias_match(120.5, 240.0)
    # 30 fps cannot resolve a 100/120 Hz drive — never flag there.
    assert not mains_alias_match(10.0, 30.0)
    assert not mains_alias_match(None, 240.0)
    # Aliases fold into Nyquist: 100 Hz @ 70 fps -> 100 % 70 = 30 -> min(30, 40) = 30
    assert mains_aliases(70.0) == [30.0, 20.0]
