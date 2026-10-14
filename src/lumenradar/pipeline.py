"""Single analysis entry shared by the CLI and the dataset evaluator.

``analyze_source`` resolves the ROI, extracts the signal and control series,
runs the verdict fusion, and returns the full JSON-compatible report. Keeping
one path guarantees that `lumenradar analyze` and batch evaluation behave
identically.
"""

from __future__ import annotations

from . import __version__
from .ingest import probe as probe_source
from .roi import ROI, stable_roi
from .signal import extract_series
from .verdict import build_verdict


def ring_box(width: int, height: int, keep: float = 0.8) -> ROI:
    """Central box to EXCLUDE so the remaining border ring is a spatial control.

    Whole-frame phenomena (auto-exposure hunting) modulate the ring together
    with the center; a localized light source does not. Used in fullframe
    mode, where no ROI exists to exclude.
    """
    mx, my = int(width * (1 - keep) / 2), int(height * (1 - keep) / 2)
    return ROI(mx, my, width - 2 * mx, height - 2 * my)


def resolve_roi(video: str, manual: ROI | None) -> tuple[ROI | None, str]:
    """ROI resolution order: manual override > stable auto-LED > full-frame."""
    if manual is not None:
        return manual, "manual"
    auto = stable_roi(video)
    if auto is not None:
        return auto, "auto"
    return None, "fullframe"


def analyze_source(
    source: str,
    manual_roi: ROI | tuple[int, int, int, int] | None = None,
    max_fps: float | None = None,
) -> dict:
    """Analyze one video file and return the full report dict.

    ``manual_roi`` accepts an (x, y, w, h) tuple or an ROI object. Raises
    FileNotFoundError / ValueError from the extraction layer — callers map
    those to their own error handling.
    """
    from .roi import manual_roi as make_roi

    if isinstance(manual_roi, tuple):
        manual_roi = make_roi(manual_roi)
    meta = probe_source(source)
    if manual_roi is not None and (
        manual_roi.x < 0
        or manual_roi.y < 0
        or manual_roi.x + manual_roi.w > meta.width
        or manual_roi.y + manual_roi.h > meta.height
    ):
        raise ValueError(f"ROI exceeds frame {meta.width}x{meta.height}")

    roi, mode = resolve_roi(source, manual_roi)
    series = extract_series(source, roi=roi, max_fps=max_fps)
    if roi:
        control = extract_series(source, roi=None, exclude=roi, max_fps=max_fps)
    else:
        # Fullframe mode: use the border ring as a spatial control channel.
        control = extract_series(
            source, roi=None, exclude=ring_box(meta.width, meta.height), max_fps=max_fps
        )

    resid = series.detrend()
    verdict = build_verdict(series, control)
    return {
        "tool": "lumenradar",
        "version": __version__,
        "source": {
            "path": meta.source,
            "width": meta.width,
            "height": meta.height,
            "fps": round(meta.fps, 3),
            "frame_count": meta.frame_count,
        },
        "roi": {"mode": mode, **(roi.as_dict() if roi is not None else {})},
        "series": {
            "n": series.n,
            "duration_s": round(series.duration, 3),
            "effective_fps": round(series.effective_fps, 2),
        },
        "stats": {
            "residual_std": round(float(resid.std()), 4),
            "residual_min": round(float(resid.min()), 4),
            "residual_max": round(float(resid.max()), 4),
        },
        "detection": verdict.as_dict(),
    }
