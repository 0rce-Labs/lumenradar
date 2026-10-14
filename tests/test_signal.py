import numpy as np
import pytest

from lumenradar.roi import ROI
from lumenradar.signal import LuminanceSeries, extract_series
from lumenradar.synth import Scene, burst_video, clean_video, periodic_video, write_video


def _write(arr, fps, tmp_path, name="clip.mp4"):
    path = str(tmp_path / name)
    write_video(path, arr, fps)
    return path


def _light_roi() -> ROI:
    x, y = Scene().light_center
    w, h = Scene().light_size
    return ROI(x, y, w, h)


def test_extract_series_flat(tmp_path):
    path = _write(clean_video(seconds=2.0, fps=30.0), 30.0, tmp_path, "c.mp4")
    s = extract_series(path)
    assert s.n == 60
    assert abs(s.effective_fps - 30.0) < 0.5
    assert float(s.values.std()) < 2.0


def test_extract_series_with_roi_tracks_light(tmp_path):
    path = _write(
        periodic_video(freq=2.0, seconds=3.0, fps=30.0, depth=0.8), 30.0, tmp_path, "p.mp4"
    )
    s = extract_series(path, roi=_light_roi())
    resid = s.detrend()
    assert float(resid.std()) > 20.0
    spec = np.abs(np.fft.rfft(resid * np.hanning(resid.size)))
    freqs = np.fft.rfftfreq(resid.size, d=1 / 30.0)
    peak = freqs[int(np.argmax(spec[1:])) + 1]
    assert abs(peak - 2.0) < 0.15


def test_detrend_removes_drift():
    t = np.arange(300, dtype=np.float32) / 30.0
    vals = (40 + 0.05 * t).astype(np.float32)  # slow ramp
    s = LuminanceSeries(t, vals, 30.0)
    resid = s.detrend(window_s=2.0)
    assert float(np.abs(resid).max()) < 1.0


def test_extract_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_series(str(tmp_path / "nope.mp4"))


def test_burst_series_pulses_survive_codec(tmp_path):
    path = _write(burst_video(seconds=8.0, fps=30.0), 30.0, tmp_path, "b.mp4")
    s = extract_series(path, roi=_light_roi())
    on = s.values > s.values.min() + 0.5 * (s.values.max() - s.values.min())
    rising = int(np.diff(on.astype(int)).clip(min=0).sum())
    assert rising == 10
