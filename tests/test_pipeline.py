import json

from lumenradar.cli import main
from lumenradar.pipeline import analyze_source
from lumenradar.synth import burst_video, clean_video, write_video


def _write(arr, fps, tmp_path, name="clip.mp4"):
    path = str(tmp_path / name)
    write_video(path, arr, fps)
    return path


def test_analyze_source_clean(tmp_path):
    path = _write(clean_video(seconds=6.0, fps=30.0), 30.0, tmp_path, "c.mp4")
    report = analyze_source(path)
    assert report["tool"] == "lumenradar"
    assert report["detection"]["status"] == "clean"
    assert report["roi"]["mode"] == "fullframe"


def test_analyze_source_matches_cli(tmp_path, capsys):
    path = _write(burst_video(seconds=8.0, fps=30.0), 30.0, tmp_path, "b.mp4")
    direct = analyze_source(path)
    assert main(["analyze", path]) == 0
    via_cli = json.loads(capsys.readouterr().out)
    assert via_cli["detection"] == direct["detection"]
    assert via_cli["roi"] == direct["roi"]


def test_analyze_source_roi_bounds(tmp_path):
    path = _write(clean_video(seconds=1.0, fps=30.0), 30.0, tmp_path)
    try:
        analyze_source(path, manual_roi=(700, 500, 20, 20))
        raised = False
    except ValueError:
        raised = True
    assert raised
