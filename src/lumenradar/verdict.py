"""Verdict fusion — combine M1/M2/M3 detectors and artifact classification
into a single, explainable report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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
from .signal import LuminanceSeries


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

    evidence = {
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
