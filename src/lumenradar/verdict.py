"""Verdict fusion — combine M1/M2/M3 detectors and artifact classification
into a single, explainable report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .detect import (
    ArtifactResult,
    BaselineResult,
    BurstResult,
    PeriodicityResult,
    band_periodicity,
    baseline_compare,
    classify,
    detect_bursts,
)
from .detect.periodicity import BAND_MAX_HZ, BAND_MIN_HZ
from .signal import LuminanceSeries

SUSTAINED_MIN = 0.5  # fraction of windows carrying band power for M3 to stand


@dataclass
class Verdict:
    """Final fused verdict with full evidence for explainability."""

    status: str  # clean | suspicious | signal_detected | camera_artifact
    confidence: float
    signal_class: str | None  # blink_count | periodic_pulse | periodic | None
    peak_freq: float | None
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "confidence": round(self.confidence, 2),
            "signal_class": self.signal_class,
            "peak_freq_hz": self.peak_freq,
            "evidence": self.evidence,
        }


def sustained_power_fraction(x: np.ndarray, fps: float, rel: float = 0.05) -> float:
    """Fraction of analysis windows whose in-band power reaches ``rel`` of the
    strongest window.

    Discriminates a SUSTAINED oscillation (beacon present across the clip:
    every window carries band power) from a TRANSIENT step-edge artifact
    (a one-off UI object appearing/disappearing: first ~10 s of the
    real-hardware neg_clean clip had a static bright UI element that then
    vanished; the moving-median detrend turns that step into a wiggle whose
    power lives entirely in 1-2 windows — measured sustained_fraction 0.05
    vs 1.0 on all three true-positive clips).
    """
    x = np.asarray(x, dtype=np.float64)
    win = max(30, int(round(2.0 * fps)))
    if x.size <= win:
        return 1.0
    w = np.hanning(win)
    fr = np.fft.rfftfreq(win, d=1.0 / fps)
    band = (fr >= BAND_MIN_HZ) & (fr <= min(BAND_MAX_HZ, fps / 2 - 1e-6))
    if not band.any():
        return 1.0
    powers = []
    for i in range(x.size - win + 1):
        seg = x[i : i + win]
        spec = np.abs(np.fft.rfft((seg - seg.mean()) * w)) ** 2
        powers.append(float(spec[band].sum()))
    p = np.asarray(powers)
    peak = float(p.max())
    if peak <= 1e-12:
        return 1.0
    return float((p >= rel * peak).mean())


def build_verdict(series: LuminanceSeries, control: LuminanceSeries | None) -> Verdict:
    """Run all detectors over the ROI series (and its control channel) and fuse."""
    fps = series.effective_fps
    x = series.detrend()
    m1: PeriodicityResult = band_periodicity(x, fps)
    m2: BurstResult = detect_bursts(x, fps)
    m3: BaselineResult = baseline_compare(x, fps)
    art: ArtifactResult = classify(
        x, control.detrend() if control is not None else None, fps, m1.peak_freq
    )

    evidence: dict = {
        "m1_periodicity": {
            "peak_freq_hz": m1.peak_freq,
            "ratio": m1.ratio,
            "harmonic_ok": m1.harmonic_ok,
            "detected": m1.detected,
        },
        "m2_burst": {
            "pulses": m2.pulses,
            "symbol_counts": m2.counts,
            "symbol_repeats": m2.symbol_repeats,
            "timing_regular": m2.timing_regular,
            "detected": m2.detected,
        },
        "m3_baseline": {
            "available": m3.sufficient,
            "z": m3.z,
            "peak_freq_hz": m3.peak_freq,
            "amplitude": m3.amplitude,
            "detected": m3.detected,
        },
        "artifacts": {
            "type": art.artifact,
            "roi_control_correlation": art.correlation,
            "control_ratio": art.control_ratio,
        },
    }

    if art.artifact == "ae_hunting":
        # Whole-frame lockstep with comparable magnitude in the control
        # channel: exposure artifact. A real signal can ride on top of it,
        # but the ROI detector cannot separate them in this clip — report
        # the artifact, not a signal.
        return Verdict("camera_artifact", 0.6, None, None, evidence)

    if art.artifact == "mains_flicker":
        return Verdict("camera_artifact", 0.6, None, m1.peak_freq, evidence)

    m1_active = m1.detected
    m2_active = m2.detected
    m3_active = m3.sufficient and m3.detected
    # Sustained-power gate on M3: baseline z can fire on a one-off step
    # (UI object appearing/disappearing mid-session); a real beacon carries
    # band power in essentially every analysis window. Measured on the
    # real-hardware dataset: FP transient 0.05 vs true positives 1.00.
    sustained = sustained_power_fraction(x, fps)
    evidence["sustained_power_fraction"] = round(sustained, 3)
    if m3_active and sustained < SUSTAINED_MIN:
        m3_active = False
        evidence["m3_baseline"]["rejected_transient"] = True

    votes = int(m1_active) + int(m2_active) + int(m3_active)
    if votes == 0:
        return Verdict("clean", _clean_confidence(m1, m2, m3), None, None, evidence)

    if m2_active and m2.symbol_repeats and m2.timing_regular:
        # Repeating counts (1,1,2,...) = blink-count code even without a
        # narrow spectral line; irregular counts = unmodulated burst activity.
        signal_class = "blink_count" if len(set(m2.counts)) > 1 else "periodic_pulse"
        status = "signal_detected"
    elif m1_active:
        signal_class = "periodic"
        status = "suspicious" if votes == 1 else "signal_detected"
    else:
        signal_class = None
        status = "suspicious"

    base = 0.55 + 0.15 * votes
    if m1_active and m1.strong:
        base += 0.1
    if m3_active:
        base += 0.05
    return Verdict(status, min(0.99, base), signal_class, m1.peak_freq, evidence)


def _clean_confidence(m1: PeriodicityResult, m2: BurstResult, m3: BaselineResult) -> float:
    """Confidence that the clip is clean, scaled by how much was actually checked."""
    c = 0.7
    if m1.ratio < 3.0:
        c += 0.1
    if m3.sufficient and m3.z < 2.0:
        c += 0.1
    if m2.pulses == 0:
        c += 0.05
    return min(0.95, c)


__all__ = ["Verdict", "build_verdict"]
