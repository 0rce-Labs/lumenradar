"""M3 — session-baseline spectral comparison (transmission-onset detector).

The first ``baseline_s`` seconds of a session are treated as a beacon-free
baseline profile. A spectral power ratio is computed between the candidate
window(s) and the baseline over the 0.5-15 Hz band. Because per-bin PSDs of
white noise are exponentially distributed (log-ratio sigma ~1.81 per bin),
both spectra are smoothed (L-bin moving average) so the log-ratio becomes
approximately Gaussian with known sigma = sqrt(2 * psi'(L)); the z-score is
thresholded at 5. This fires only when a signal starts mid-session — a clip
that oscillates from frame zero has the same content in both windows.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import polygamma

from .periodicity import MIN_AMP_GRAY

BASELINE_S = 2.0
Z_MIN = 5.0
SMOOTH_L = 5
MIN_BASE_FRAMES_FACTOR = 2.0  # baseline must span >= 2 s
MIN_CAND_S = 4.0  # candidate must span >= 4 s


@dataclass
class BaselineResult:
    """Outcome of M3 baseline comparison."""

    baseline_s: float
    candidate_s: float
    z: float
    peak_freq: float | None
    amplitude: float
    detected: bool
    sufficient: bool


def _smooth(p: np.ndarray, bins: int = SMOOTH_L) -> np.ndarray:
    kernel = np.ones(bins) / bins
    return np.convolve(p, kernel, mode="same")


def baseline_compare(
    x: np.ndarray,
    fps: float,
    baseline_s: float = BASELINE_S,
    fmin: float = 0.5,
    fmax: float = 15.0,
    z_min: float = Z_MIN,
) -> BaselineResult:
    """Compare the candidate part of the series against the session baseline."""
    x = np.asarray(x, dtype=np.float32)
    fps = float(fps)
    n_base = int(round(baseline_s * fps))
    cand_n = x.size - n_base
    insufficient = BaselineResult(0.0, 0.0, 0.0, None, 0.0, False, False)
    # Integer-based minimums: container FPS values like 30.000029 must not
    # turn "exactly 2 s of baseline" into an insufficiency via float compare.
    if n_base < int(round(MIN_BASE_FRAMES_FACTOR * fps)) or cand_n < int(round(MIN_CAND_S * fps)):
        return insufficient

    m = cand_n // n_base  # number of equal-length candidate windows
    if m < 2:
        return insufficient

    base = x[:n_base].astype(np.float32)
    _, base_psd = _win_psd(base, fps)

    band = (_freqs(n_base, fps) >= fmin) & (_freqs(n_base, fps) <= min(fmax, fps / 2 - 1e-6))
    if not band.any():
        return insufficient

    cand_psds = []
    for i in range(m):
        seg = x[n_base + i * n_base : n_base + (i + 1) * n_base]
        _, psd = _win_psd(seg, fps)
        cand_psds.append(psd)
    cand_psd = np.mean(cand_psds, axis=0)

    base_s = _smooth(base_psd)
    cand_s = _smooth(cand_psd)
    floor = max(float(base_s.max()), 1e-12) * 1e-9
    ratios = cand_s[band] / np.maximum(base_s[band], floor)
    k = int(np.argmax(ratios))
    freqs_band = _freqs(n_base, fps)[band]
    peak_freq = round(float(freqs_band[k]), 3)
    ratio = float(ratios[k])
    sigma = float(np.sqrt(2.0 * float(polygamma(1, SMOOTH_L))))
    z = float(np.log(max(ratio, 1e-12)) / sigma)
    # Amplitude gate (same principle as M1): with a near-zero-energy baseline
    # the PSD ratio can explode on pure codec/quantization noise. A real
    # onset must also be PERCEPTIBLE — >= MIN_AMP_GRAY gray levels.
    amp = 4.0 * float(np.sqrt(max(float(cand_psd[band][k]), 0.0))) / n_base
    detected = bool(ratio > 1.0 and z >= z_min and amp >= MIN_AMP_GRAY)
    return BaselineResult(
        baseline_s=round(n_base / fps, 3),
        candidate_s=round(cand_n / fps, 3),
        z=round(z, 2),
        peak_freq=peak_freq,
        amplitude=round(amp, 4),
        detected=detected,
        sufficient=True,
    )


def _freqs(n: int, fps: float) -> np.ndarray:
    return np.fft.rfftfreq(n, d=1.0 / fps)


def _win_psd(x: np.ndarray, fps: float) -> tuple[np.ndarray, np.ndarray]:
    """Hann-windowed one-sided PSD of a window (mean-removed)."""
    x = np.asarray(x, dtype=np.float64)
    w = np.hanning(x.size)
    spec = np.abs(np.fft.rfft((x - x.mean()) * w)) ** 2
    return _freqs(x.size, fps), spec
