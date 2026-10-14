import numpy as np
import pytest

from lumenradar.roi import ROI, auto_led_roi, manual_roi, stable_roi
from lumenradar.synth import Scene, burst_video, write_video


def _frame_with_led(width=320, height=240, center=(280, 30), size=(10, 8), value=250, bg=60):
    img = np.full((height, width, 3), bg, dtype=np.uint8)
    x, y = center
    w, h = size
    img[y : y + h, x : x + w] = value
    return img


def test_auto_led_roi_finds_saturated_blob():
    cands = auto_led_roi(_frame_with_led())
    assert cands, "expected at least one candidate"
    top = cands[0]
    assert (top.x, top.y, top.w, top.h) == (280, 30, 10, 8)


def test_auto_led_roi_rejects_flat_frame():
    assert auto_led_roi(np.full((240, 320, 3), 60, dtype=np.uint8)) == []


def test_auto_led_roi_ignores_large_bright_regions():
    frame = np.full((240, 320, 3), 60, dtype=np.uint8)
    frame[40:200, 40:280] = 250  # a window, not an LED
    assert auto_led_roi(frame) == []


def test_manual_roi_validation():
    assert manual_roi((5, 6, 7, 8)) == ROI(5, 6, 7, 8)
    with pytest.raises(ValueError):
        manual_roi((-1, 0, 5, 5))
    with pytest.raises(ValueError):
        manual_roi((0, 0, 0, 5))


def test_stable_roi_finds_recurring_led(tmp_path):
    arr = burst_video(seconds=8.0, fps=30.0)
    path = str(tmp_path / "b.mp4")
    write_video(path, arr, 30.0)
    roi = stable_roi(path)
    assert roi is not None
    scene = Scene()
    x, y = scene.light_center
    w, h = scene.light_size
    assert abs(roi.x - x) <= 2 and abs(roi.y - y) <= 2
    assert abs(roi.w - w) <= 3 and abs(roi.h - h) <= 3


def test_stable_roi_none_on_clean_scene(tmp_path):
    from lumenradar.synth import clean_video

    path = str(tmp_path / "c.mp4")
    write_video(path, clean_video(seconds=2.0, fps=30.0), 30.0)
    assert stable_roi(path) is None
