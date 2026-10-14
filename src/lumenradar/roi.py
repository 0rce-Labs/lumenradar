"""Region-of-interest localization for small bright light sources.

``auto_led_roi`` finds small, bright, saturated blobs that stand out from the
scene — the shape of an indicator LED captured by a webcam. ``stable_roi``
picks the blob that persists across the first frames, so analysis does not
anchor on a lead-in frame where the light happens to be off.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .ingest import frames


@dataclass
class ROI:
    """Axis-aligned box in pixel coordinates."""

    x: int
    y: int
    w: int
    h: int
    score: float = 0.0

    def center(self) -> tuple[float, float]:
        return (self.x + self.w / 2, self.y + self.h / 2)

    def slice(self) -> tuple[slice, slice]:
        return (slice(self.y, self.y + self.h), slice(self.x, self.x + self.w))

    def as_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


def manual_roi(box: tuple[int, int, int, int]) -> ROI:
    """Build a ROI from an (x, y, w, h) tuple with shape validation.

    Frame-bounds validation happens at the call site where frame size is
    known (CLI checks against source metadata before extraction).
    """
    x, y, w, h = box
    if x < 0 or y < 0:
        raise ValueError(f"ROI origin must be non-negative, got {box!r}")
    if w <= 0 or h <= 0:
        raise ValueError(f"ROI size must be positive, got {box!r}")
    return ROI(x, y, w, h)


def auto_led_roi(
    frame: np.ndarray,
    min_area: int = 4,
    max_area_ratio: float = 0.01,
    brightness_percentile: float = 97.0,
) -> list[ROI]:
    """Rank small bright blobs that look like indicator LEDs.

    Returns candidates sorted by score (most LED-like first). Empty list when
    nothing stands out — callers fall back to manual ROI or full-frame.
    """
    if frame.ndim == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame
    h, w = gray.shape
    max_area = max(min_area, int(max_area_ratio * h * w))

    thr = int(np.percentile(gray, brightness_percentile))
    mask = (gray >= max(thr, 200)).astype(np.uint8)

    n_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    candidates: list[ROI] = []
    for i in range(1, n_labels):
        x, y, bw, bh, area = (int(v) for v in stats[i])
        if area < min_area or area > max_area:
            continue
        fill = area / float(bw * bh)
        aspect = max(bw, bh) / max(1.0, float(min(bw, bh)))
        mean_v = float(gray[y : y + bh, x : x + bw].mean())
        # LED-like: compact, roughly square, very bright.
        score = mean_v * fill / aspect
        candidates.append(ROI(x, y, bw, bh, score))
    candidates.sort(key=lambda r: r.score, reverse=True)
    return candidates


def stable_roi(source: str | int, probe_frames: int = 15, tolerance: float = 8.0) -> ROI | None:
    """Most consistently detected bright blob across the first frames.

    A real indicator LED is visible (on or idle) in most frames; scanning a
    window avoids anchoring on a frame where the light is momentarily off.
    Returns None when no blob recurs — callers fall back to full-frame.
    """
    centers: list[tuple[float, float]] = []
    boxes: list[ROI] = []
    for i, (_, frame) in enumerate(frames(source)):
        if i >= probe_frames:
            break
        cands = auto_led_roi(frame)
        if cands:
            centers.append(cands[0].center())
            boxes.append(cands[0])
    if not centers:
        return None
    # Greedy clustering around the first seen center (Faz 2 adds tracking).
    sx, sy = centers[0]
    group = [
        b
        for b, (cx, cy) in zip(boxes, centers, strict=False)
        if abs(cx - sx) <= tolerance and abs(cy - sy) <= tolerance
    ]
    if len(group) < 2:
        return None
    return ROI(
        x=int(np.median([b.x for b in group])),
        y=int(np.median([b.y for b in group])),
        w=int(np.median([b.w for b in group])),
        h=int(np.median([b.h for b in group])),
        score=float(len(group)) / probe_frames,
    )
