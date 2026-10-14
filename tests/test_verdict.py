import json

import numpy as np

from lumenradar.cli import main
from lumenradar.roi import ROI
from lumenradar.signal import extract_series
from lumenradar.synth import (
    Scene,
    burst_video,
    clean_video,
    global_osc_video,
    noisy_video,
    periodic_video,
    write_video,
)
from lumenradar.verdict import build_verdict


def _write(arr, fps, tmp_path, name="clip.mp4"):
    path = str(tmp_path / name)
    write_video(path, arr, fps)
    return path


def _light_roi() -> ROI:
    x, y = Scene().light_center
    w, h = Scene().light_size
    return ROI(x, y, w, h)


def test_clean_clip_is_clean(tmp_path):
    path = _write(clean_video(seconds=6.0, fps=30.0), 30.0, tmp_path, "c.mp4")
    v = build_verdict(extract_series(path, roi=_light_roi()), extract_series(path))
    assert v.status == "clean"
    assert v.signal_class is None
    assert set(v.evidence) == {"m1_periodicity", "m2_burst", "m3_baseline", "artifacts"}


def test_noisy_clip_is_clean(tmp_path):
    path = _write(noisy_video(seconds=6.0, fps=30.0, sigma=4.0), 30.0, tmp_path, "n.mp4")
    v = build_verdict(extract_series(path, roi=_light_roi()), extract_series(path))
    assert v.status == "clean"


def test_periodic_clip_flagged(tmp_path):
    path = _write(
        periodic_video(freq=2.0, seconds=6.0, fps=30.0, depth=0.8), 30.0, tmp_path, "p.mp4"
    )
    v = build_verdict(extract_series(path, roi=_light_roi()), extract_series(path))
    assert v.status in ("suspicious", "signal_detected")
    assert v.signal_class == "periodic"
    assert v.peak_freq is not None and abs(v.peak_freq - 2.0) <= 0.1


def test_burst_clip_signal_detected(tmp_path):
    pattern = (1, 1, 2, 1, 2, 1, 2)
    path = _write(burst_video(pattern=pattern, seconds=8.0, fps=30.0), 30.0, tmp_path, "b.mp4")
    v = build_verdict(extract_series(path, roi=_light_roi()), extract_series(path))
    assert v.status == "signal_detected"
    assert v.signal_class == "blink_count"
    assert v.evidence["m2_burst"]["symbol_counts"] == list(pattern)


def test_onset_burst_trips_m3(tmp_path):
    """Signal starting mid-session must fire the baseline detector too."""
    fps = 30.0
    arr = burst_video(seconds=6.0, fps=fps)
    pad = clean_video(seconds=2.0, fps=fps)
    path = _write(np.concatenate([pad, arr]), fps, tmp_path, "o.mp4")
    v = build_verdict(extract_series(path, roi=_light_roi()), extract_series(path))
    assert v.status == "signal_detected"
    assert v.evidence["m3_baseline"]["detected"] is True


def test_global_oscillation_is_camera_artifact(tmp_path):
    path = _write(global_osc_video(freq=2.0, seconds=6.0, fps=30.0), 30.0, tmp_path, "ae.mp4")
    v = build_verdict(extract_series(path, roi=_light_roi()), extract_series(path))
    assert v.status == "camera_artifact"
    assert v.evidence["artifacts"]["type"] == "ae_hunting"


def test_cli_end_to_end_burst(tmp_path, capsys):
    path = _write(burst_video(seconds=8.0, fps=30.0), 30.0, tmp_path, "cli_b.mp4")
    assert main(["analyze", path]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["detection"]["status"] == "signal_detected"
    assert report["detection"]["signal_class"] == "blink_count"


def test_cli_end_to_end_clean(tmp_path, capsys):
    path = _write(clean_video(seconds=6.0, fps=30.0), 30.0, tmp_path, "cli_c.mp4")
    assert main(["analyze", path]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["detection"]["status"] == "clean"
    assert report["detection"]["confidence"] >= 0.7


def test_cli_end_to_end_ae_with_manual_roi(tmp_path, capsys):
    x, y = Scene().light_center
    w, h = Scene().light_size
    path = _write(global_osc_video(freq=2.0, seconds=6.0, fps=30.0), 30.0, tmp_path, "cli_ae.mp4")
    assert main(["analyze", path, "--roi", f"{x},{y},{w},{h}"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["detection"]["status"] == "camera_artifact"
