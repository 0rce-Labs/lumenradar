import json
import subprocess
import sys

from lumenradar.cli import main
from lumenradar.synth import burst_video, clean_video, periodic_video, write_video


def _write(arr, fps, tmp_path, name="clip.mp4"):
    path = str(tmp_path / name)
    write_video(path, arr, fps)
    return path


def test_analyze_clean_fullframe(tmp_path):
    path = _write(clean_video(seconds=2.0, fps=30.0), 30.0, tmp_path, "clean.mp4")
    out = tmp_path / "r.json"
    rc = main(["analyze", path, "--json-out", str(out)])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["tool"] == "lumenradar"
    assert report["source"]["frame_count"] == 60
    assert report["roi"]["mode"] == "fullframe"  # no LED visible -> control channel
    assert report["detection"]["status"] == "clean"
    assert report["stats"]["residual_std"] < 2.0


def test_analyze_periodic_auto_roi(tmp_path, capsys):
    path = _write(
        periodic_video(freq=2.0, seconds=6.0, fps=30.0, depth=0.8), 30.0, tmp_path, "p.mp4"
    )
    assert main(["analyze", path]) == 0
    report = json.loads(capsys.readouterr().out)
    # The beacon-square scan may claim the synthetic LED (its 16x16 blinking
    # block passes the beacon filter at low resolution clips); either auto
    # path is valid as long as the signal lands in ROI.
    assert report["roi"]["mode"] in ("auto", "auto_beacon")
    assert report["stats"]["residual_std"] > 10.0


def test_analyze_burst_auto_roi(tmp_path, capsys):
    path = _write(burst_video(seconds=8.0, fps=30.0), 30.0, tmp_path, "b.mp4")
    assert main(["analyze", path]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["roi"]["mode"] in ("auto", "auto_beacon")
    assert report["stats"]["residual_std"] > 10.0


def test_analyze_manual_roi(tmp_path, capsys):
    from lumenradar.synth import Scene

    x, y = Scene().light_center
    w, h = Scene().light_size
    path = _write(
        periodic_video(freq=2.0, seconds=4.0, fps=30.0, depth=0.8), 30.0, tmp_path, "m.mp4"
    )
    assert main(["analyze", path, "--roi", f"{x},{y},{w},{h}"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["roi"]["mode"] == "manual"
    assert report["stats"]["residual_std"] > 10.0


def test_analyze_roi_out_of_bounds(tmp_path, capsys):
    path = _write(clean_video(seconds=1.0, fps=30.0), 30.0, tmp_path)
    assert main(["analyze", path, "--roi", "700,500,20,20"]) == 2
    assert "error" in json.loads(capsys.readouterr().out)


def test_analyze_missing_file(tmp_path, capsys):
    assert main(["analyze", str(tmp_path / "nope.mp4")]) == 2
    assert "error" in json.loads(capsys.readouterr().out)


def test_probe(tmp_path, capsys):
    path = _write(clean_video(seconds=1.0, fps=30.0), 30.0, tmp_path)
    assert main(["probe", path]) == 0
    meta = json.loads(capsys.readouterr().out)
    assert meta["width"] == 640 and meta["frame_count"] == 30


def test_console_entrypoint(tmp_path):
    path = _write(clean_video(seconds=1.0, fps=30.0), 30.0, tmp_path)
    r = subprocess.run(
        [sys.executable, "-m", "lumenradar.cli", "analyze", path],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert json.loads(r.stdout)["tool"] == "lumenradar"
