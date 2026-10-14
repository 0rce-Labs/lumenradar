"""Publication-style figures for analysis reports (optional matplotlib).

Academic format: grayscale-friendly (solid black ROI series, dashed dark-gray
control), serif font, vector output supported (pass a .pdf path for the
paper). PSD panels use Welch averaging (nperseg=256, 50% overlap, Hann) —
a raw periodogram is too noisy for publication.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.signal import welch

from .detect.periodicity import band_periodicity
from .signal import LuminanceSeries

_WELCH_NPERSEG = 256


def _welch_psd(x: np.ndarray, fps: float) -> tuple[np.ndarray, np.ndarray]:
    nper = min(_WELCH_NPERSEG, x.size)
    f, p = welch(x.astype(np.float64), fs=fps, window="hann", nperseg=nper, noverlap=nper // 2)
    return f, p


def render_plot(
    series: LuminanceSeries,
    control: LuminanceSeries | None,
    out_path: str | Path,
    title: str = "",
) -> Path:
    """Render a two-panel figure: luminance series + Welch PSD with the peak."""
    import matplotlib

    matplotlib.use("Agg")  # headless-safe
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 9,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "figure.dpi": 150,
        }
    )

    fps = series.effective_fps
    x = series.detrend()
    m1 = band_periodicity(x, fps)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.4, 4.2), constrained_layout=True)

    ax1.plot(series.times, x, color="black", lw=0.9, label="ROI luminance (detrended)")
    if control is not None and float(control.values.std()) > 0:
        yc = control.detrend()
        ax1.plot(
            control.times,
            (yc - yc.mean()) / float(yc.std()) * max(float(x.std()), 1e-9),
            color="0.35",
            lw=0.8,
            ls="--",
            label="control (scaled)",
        )
    ax1.set_xlabel("time [s]")
    ax1.set_ylabel("gray levels")
    ax1.legend(frameon=False, fontsize=8, loc="upper right")
    if title:
        ax1.set_title(title, fontsize=10)

    from .detect.burst import detect_bursts

    f, p = _welch_psd(x, fps)
    ax2.semilogy(f, p, color="black", lw=0.9)
    if control is not None and float(control.values.std()) > 0:
        fc, pc = _welch_psd(control.detrend(), fps)
        ax2.semilogy(fc, pc, color="0.35", lw=0.8, ls="--")
    # Shade the REJECTED parts of the axis (outside the 0.5-15 Hz gate).
    f_hi = min(30.0, fps / 2)
    ax2.axvspan(0.0, 0.5, color="0.85", alpha=0.6)
    if f_hi > 15.0:
        ax2.axvspan(15.0, f_hi, color="0.85", alpha=0.6)

    # Annotate what the verdict ACTUALLY used. A low-duty pulse train has an
    # inherently broadband spectrum — highlighting a narrowband M1 peak there
    # would overstate the evidence; the pulse structure itself (M2) is the
    # detector for that class, so the figure annotates it instead.
    burst = detect_bursts(x, fps)
    if burst.detected:
        ax2.text(
            0.5,
            0.97,
            f"M2: {burst.pulses} pulses, symbol counts {burst.counts}",
            transform=ax2.transAxes,
            ha="center",
            va="top",
            fontsize=8,
            bbox=dict(boxstyle="round", fc="white", ec="0.6", alpha=0.9),
        )
    elif m1.peak_freq is not None and m1.detected:
        ax2.axvline(m1.peak_freq, color="0.2", lw=1.0, ls=":", label=f"peak {m1.peak_freq:g} Hz")

    ax2.set_xlim(0, f_hi)
    ax2.set_xlabel("frequency [Hz]")
    ax2.set_ylabel(r"PSD [(gray level)$^2$/Hz]")
    # No legend, no inline notes in the PSD panel: the shading and line styles
    # are explained in the figure caption (paper convention), leaving the M2
    # annotation as the only text — collisions are impossible.

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    return out
