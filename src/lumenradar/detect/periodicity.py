"""M1 — narrow-band periodicity detection in the luminance series.

Detects a sinusoid-like or pulse-train oscillation in the 0.5-15 Hz band.
Three gates, each closing a distinct false-positive path:

1. **Amplitude gate** — the peak bin must correspond to a real luminance
   swing (>= MIN_AMP gray levels via the Hann amplitude estimate
   amp = 4*sqrt(P)/N). Sensor noise and detrend residue live far below this;
   it also rejects tones *outside* the band whose leakage skirts reach in.
2. **Local-floor ratio** — peak vs the median of neighboring bins (the
   residual noise after detrending is red-ish, so a global median floor
   over-estimates the ratio at low frequencies).
3. **Noise-max expectation** — per-bin PSDs of white noise are exponential,
   so the expected max over n bins is ln(n)+gamma (Gumbel); a plain ratio
   threshold alone cannot survive peak-picking over the whole band.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

BAND_MIN_HZ = 0.5
BAND_MAX_HZ = 15.0
RATIO_MIN = 8.0
RATIO_STRONG = 20.0
HARMONIC_FACTOR = 3.0
MIN_AMP_GRAY = 0.5
LOCAL_FLOOR_SPAN = 3  # +- this many bins around the peak


@dataclass
class PeriodicityResult:
    """Outcome of M1 band-periodicity analysis."""

    peak_freq: float | None
    ratio: float
    amplitude: float
    harmonic_ok: bool | None
    strong: bool
    detected: bool


def band_spectrum(x: np.ndarray, fps: float) -> tuple[np.ndarray, np.ndarray]:
    """One-sided power spectrum of a (mean-removed, Hann-windowed) series."""
    x = np.asarray(x, dtype=np.float64)
    w = np.hanning(x.size)
    spec = np.abs(np.fft.rfft((x - x.mean()) * w)) ** 2
    freqs = np.fft.rfftfreq(x.size, d=1.0 / fps)
    return freqs, spec


def band_periodicity(
    x: np.ndarray,
    fps: float,
    fmin: float = BAND_MIN_HZ,
    fmax: float = BAND_MAX_HZ,
) -> PeriodicityResult:
    """Detect a narrow-band oscillation in [fmin, fmax]."""
    x = np.asarray(x, dtype=np.float32)
    none = PeriodicityResult(None, 0.0, 0.0, None, False, False)
    if x.size < 30 or float(x.std()) < 1e-6:
        return none
    freqs, spec = band_spectrum(x, fps)
    band = (freqs >= fmin) & (freqs <= min(fmax, fps / 2 - 1e-6))
    if not band.any():
        return none
    bp = spec[band].astype(np.float64)
    bf = freqs[band]
    k = int(np.argmax(bp))
    peak_freq = float(bf[k])
    peak_power = float(bp[k])

    # Amplitude estimate (Hann-corrected sine peak): A = 4*sqrt(P)/N.
    amp = 4.0 * float(np.sqrt(peak_power)) / x.size
    if amp < MIN_AMP_GRAY:
        return PeriodicityResult(round(peak_freq, 3), 0.0, round(amp, 4), None, False, False)

    # Local floor: median of bins within +-LOCAL_FLOOR_SPAN of the peak,
    # excluding the peak's own +-1 bins (main lobe).
    df = float(bf[1] - bf[0]) if bf.size > 1 else 1.0
    near = (np.abs(bf - peak_freq) <= LOCAL_FLOOR_SPAN * df) & (
        np.abs(bf - peak_freq) > 1.5 * df
    )
    floor_vals = bp[near]
    floor = float(np.median(floor_vals)) if floor_vals.size else float(np.median(bp))
    if floor <= 0:
        floor = 1e-12
    ratio = peak_power / floor

    harmonic_ok: bool | None = None
    if 2 * peak_freq <= fmax:
        global_floor = max(float(np.median(bp)), 1e-12)
        h2 = float(spec[int(np.argmin(np.abs(freqs - 2 * peak_freq)))])
        h3: float | None = None
        if 3 * peak_freq <= fmax:
            h3 = float(spec[int(np.argmin(np.abs(freqs - 3 * peak_freq)))])
        best = h2 if h3 is None else max(h2, h3)
        # Compare against the GLOBAL floor: a pure sine has no harmonics, only
        # window leakage, and the Hann skirt decays with distance from the
        # peak — near-peak local floors would wrongly fail it.
        harmonic_ok = bool(best >= HARMONIC_FACTOR * global_floor)

    n_bins = int(band.sum())
    expected_max = float(np.log(n_bins) + 0.5772)  # E[max of n unit exponentials]
    detected = (ratio >= RATIO_MIN and harmonic_ok is True) or ratio >= 2.0 * expected_max
    strong = ratio >= RATIO_STRONG
    return PeriodicityResult(
        round(peak_freq, 3), round(ratio, 2), round(amp, 4), harmonic_ok, strong, detected
    )
