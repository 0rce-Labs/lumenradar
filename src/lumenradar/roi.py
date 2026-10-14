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
    allow_large_beacon: bool = False,
    beacon_side_px: tuple[int, int] = (60, 400),
    beacon_solidity: float = 0.55,
) -> list[ROI]:
    """Rank small bright blobs that look like indicator LEDs.

    Returns candidates sorted by score (most LED-like first). Empty list when
    nothing stands out — callers fall back to manual ROI or full-frame.

    ``allow_large_beacon`` additionally accepts LARGE solid bright squares
    (the calibration beacon window rendered on screen — 300x300 Retina px in
    real captures). Without it, a screen-rendered beacon is invisible to the
    detector: it is not a "small indicator LED", so auto-ROI skips it and
    analysis degrades to the full-frame path where the beacon itself pollutes
    the control channel (measured correlation 0.997 → false AE veto).
    """
    if frame.ndim == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame
    h, w = gray.shape
    max_area = max(min_area, int(max_area_ratio * h * w))

    thr = int(np.percentile(gray, brightness_percentile))
    mask = (gray >= max(thr, 200)).astype(np.uint8)

    candidates: list[ROI] = []
    n_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    for i in range(1, n_labels):
        x, y, bw, bh, area = (int(v) for v in stats[i])
        if area < min_area or area > max_area:
            if not (allow_large_beacon
                    and beacon_side_px[0] <= bw <= beacon_side_px[1]
                    and beacon_side_px[0] <= bh <= beacon_side_px[1]
                    and area / float(bw * bh) >= beacon_solidity):
                continue
        fill = area / float(bw * bh)
        aspect = max(bw, bh) / max(1.0, float(min(bw, bh)))
        mean_v = float(gray[y : y + bh, x : x + bw].mean())
        # LED-like: bright blob; beacon-like: large solid square. Both are
        # compact bright regions worth tracking — the score rewards solidity.
        score = mean_v * fill / aspect
        candidates.append(ROI(x, y, bw, bh, score))
    candidates.sort(key=lambda r: r.score, reverse=True)
    return candidates


def stable_roi(
    source: str | int,
    probe_frames: int = 15,
    tolerance: float = 8.0,
    allow_large_beacon: bool = False,
) -> ROI | None:
    """Most consistently detected bright blob across the first frames.

    A real indicator LED is visible (on or idle) in most frames; scanning a
    window avoids anchoring on a frame where the light is momentarily off.
    With ``allow_large_beacon`` the scan also accepts the calibration beacon's
    large solid square — and the scan window widens, because a low-duty blink
    pattern (e.g. 1-2-3-4 counts) leaves the square OFF for most early
    frames; real captures showed the first ON frame as late as #39. Returns
    None when nothing recurs — callers fall back to the full-frame path.
    """
    if allow_large_beacon:
        # ~3 s at 60 Hz: spread the scan over lead-in + several blink symbols.
        probe_frames = max(probe_frames, 180)
    centers: list[tuple[float, float]] = []
    boxes: list[ROI] = []
    for i, (_, frame) in enumerate(frames(source)):
        if i >= probe_frames:
            break
        cands = auto_led_roi(frame, allow_large_beacon=allow_large_beacon)
        if cands:
            centers.append(cands[0].center())
            boxes.append(cands[0])
    if not centers:
        return None
    # Class-aware grouping: small-LED blobs and the large beacon square have
    # wildly different scales; clustering across classes would anchor on the
    # most frequent class and swallow the other (real captures: ~1400 noise
    # blobs at 2x2 px vs a 318x318 beacon square visible in only ~20% of
    # frames — a single greedy bucket returns the 2x2 centroid).
    if allow_large_beacon:
        large = [b for b in boxes if max(b.w, b.h) >= 60]
        if len(large) >= 2:
            return ROI(
                x=int(np.median([b.x for b in large])),
                y=int(np.median([b.y for b in large])),
                w=int(np.median([b.w for b in large])),
                h=int(np.median([b.h for b in large])),
                score=float(len(large)) / probe_frames,
            )
        # No consistently recurring large square: in beacon-scan mode return
        # None — falling through to the small-blob result would mislabel a
        # 2x2 sensor speck as an "auto_beacon" hit and hijack the ROI choice
        # (real-hardware regression: all three negative clips analyzed a
        # speck as the beacon carrier).
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
