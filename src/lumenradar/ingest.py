"""Frame ingestion from video files and cameras.

Provides a uniform (time, frame) iterator so the rest of the pipeline is
source-agnostic. Timestamps always follow the FPS the container actually
stores, not the FPS the caller requested at write time.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class VideoSource:
    """Metadata for an opened video source."""

    width: int
    height: int
    fps: float
    frame_count: int
    source: str


def frames(
    source: str | int, max_fps: float | None = None
) -> Iterator[tuple[float, np.ndarray]]:
    """Yield (timestamp_seconds, frame_bgr) from a video file or camera.

    ``max_fps`` subsamples the stream (e.g. a 240 fps capture analyzed at
    15 fps). Timestamps advance by the source's own frame period regardless
    of subsampling.
    """
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise FileNotFoundError(f"cannot open video source: {source!r}")
    src_fps = cap.get(cv2.CAP_PROP_FPS)
    if src_fps <= 0 or math.isnan(src_fps):
        src_fps = 30.0
    step = 1
    if max_fps is not None and max_fps > 0 and src_fps > max_fps:
        step = max(1, int(round(src_fps / max_fps)))
    t = 0.0
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % step == 0:
                yield t, frame
            t += 1.0 / src_fps
            idx += 1
    finally:
        cap.release()


def probe(source: str) -> VideoSource:
    """Return source metadata without decoding all frames."""
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise FileNotFoundError(f"cannot open video source: {source!r}")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or math.isnan(fps):
            fps = 30.0
        return VideoSource(
            width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=fps,
            frame_count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            source=str(source),
        )
    finally:
        cap.release()
