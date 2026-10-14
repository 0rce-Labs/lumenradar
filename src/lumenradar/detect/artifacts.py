"""Artifact rejection — auto-exposure hunting and mains-flicker aliases.

Auto-exposure ('AE-hunting') artifacts modulate the whole frame together with
the scene. Two independent markers distinguish them from a localized LED
signal, and BOTH are required (codec block-coupling can imitate the
correlation marker alone):

1. **Correlation** — ROI and the ROI-excluded control channel move in
   lockstep (r >= AE_CORR_THRESHOLD).
2. **Magnitude** — the control-channel swing is the same order as the ROI
   swing (>= AE_RATIO_THRESHOLD): a real exposure change moves every pixel,
   while codec bleed into the control channel stays orders of magnitude
   smaller than the LED itself.

Mains flicker (2x mains drive at 100/120 Hz) can only be identified
unambiguously when the camera Nyquist covers the drive frequency; at typical
30 fps the aliases (10 Hz / 0 Hz) are indistinguishable from real
low-frequency signals and are therefore NOT flagged (documented limitation).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..signal import moving_median

AE_CORR_THRESHOLD = 0.85
AE_RATIO_THRESHOLD = 0.25
MAINS_DRIVES_HZ = (100.0, 120.0)  # 2x mains for 50/60 Hz power grids
MAINS_MIN_FPS = 200.0  # Nyquist must cover the drive frequency
MAINS_TOL_HZ = 1.5


@dataclass
class ArtifactResult:
    """Outcome of artifact classification."""

    artifact: str | None
    correlation: float | None
    control_ratio: float | None


def mains_aliases(fps: float) -> list[float]:
    """Aliases of the 2x-mains drive frequencies folded into [0, fps/2]."""
    out = []
    for f in MAINS_DRIVES_HZ:
        a = float(f) % fps
        alias = min(a, fps - a)
        if alias > 0.5:
            out.append(round(alias, 2))
    return out


def mains_alias_match(freq: float | None, fps: float, tol: float = MAINS_TOL_HZ) -> bool:
    """True when ``freq`` matches a mains alias AND fps resolves the drive."""
    if freq is None or fps < MAINS_MIN_FPS:
        return False
    return any(abs(freq - a) <= tol for a in mains_aliases(fps))


def classify(
    x_roi: np.ndarray,
    x_control: np.ndarray | None,
    fps: float,
    peak_freq: float | None,
) -> ArtifactResult:
    """Classify the oscillation source: covert signal vs camera artifact.

    ``x_control=None`` (full-frame analysis mode) disables both tests —
    there is no independent control channel in that mode.
    """
    if x_control is None:
        artifact = "mains_flicker" if mains_alias_match(peak_freq, fps) else None
        return ArtifactResult(artifact, None, None)

    a = moving_median(np.asarray(x_roi, dtype=np.float32), 1.0, fps)
    b = moving_median(np.asarray(x_control, dtype=np.float32), 1.0, fps)
    corr: float | None = None
    ratio: float | None = None
    if float(a.std()) >= 1e-9 and float(b.std()) >= 1e-9:
        corr = float(np.corrcoef(a, b)[0, 1])
        ratio = float(b.std()) / float(a.std())
    if (
        corr is not None
        and corr >= AE_CORR_THRESHOLD
        and ratio is not None
        and ratio >= AE_RATIO_THRESHOLD
    ):
        return ArtifactResult("ae_hunting", round(corr, 3), round(ratio, 3))
    if mains_alias_match(peak_freq, fps):
        return ArtifactResult(
            "mains_flicker",
            None if corr is None else round(corr, 3),
            None if ratio is None else round(ratio, 3),
        )
    return ArtifactResult(
        None,
        None if corr is None else round(corr, 3),
        None if ratio is None else round(ratio, 3),
    )
