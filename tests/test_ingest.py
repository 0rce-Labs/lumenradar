import numpy as np
import pytest

from lumenradar.ingest import frames, probe
from lumenradar.synth import clean_video, write_video

SMALL = dict(width=64, height=48, light_center=(52, 6), light_size=(6, 6))


def _write(arr, fps, tmp_path, name="clip.mp4"):
    path = str(tmp_path / name)
    write_video(path, arr, fps)
    return path


def test_write_and_read_roundtrip(tmp_path):
    arr = clean_video(seconds=1.0, fps=30.0)
    path = _write(arr, 30.0, tmp_path)
    meta = probe(path)
    assert meta.width == 640 and meta.height == 480
    assert meta.frame_count == 30


def test_frames_yields_all_with_uniform_time(tmp_path):
    arr = clean_video(seconds=1.0, fps=30.0)
    path = _write(arr, 30.0, tmp_path)
    out = list(frames(path))
    assert len(out) == 30
    ts = np.array([t for t, _ in out])
    assert ts[0] == 0.0
    assert np.allclose(np.diff(ts), 1 / 30.0, atol=1e-3)
    assert out[0][1].shape == (480, 640, 3)
    assert out[0][1].dtype == np.uint8


def test_frames_missing_source_raises():
    with pytest.raises(FileNotFoundError):
        next(frames("/nonexistent/nope.mp4"))


def test_max_fps_subsamples(tmp_path):
    arr = clean_video(seconds=2.0, fps=30.0, **SMALL)
    path = _write(arr, 30.0, tmp_path)
    out = list(frames(path, max_fps=15.0))
    assert len(out) == 30  # every 2nd frame of 60


def test_timestamps_follow_container_fps(tmp_path):
    """Writer caps FPS at the container limit; timestamps must follow stored FPS."""
    arr = clean_video(seconds=1.0, fps=2000.0, **SMALL)
    path = _write(arr, 2000.0, tmp_path)
    stored = probe(path).fps
    assert stored <= 1000.0  # mp4v cap applied by the writer guard
    out = list(frames(path))
    assert len(out) == 2000
    ts = np.array([t for t, _ in out])
    assert np.allclose(np.diff(ts), 1 / stored, atol=1e-4)
