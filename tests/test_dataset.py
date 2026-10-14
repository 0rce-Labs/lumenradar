import json

from lumenradar.cli import main
from lumenradar.dataset import build_manifest, evaluate
from lumenradar.synth import burst_video, clean_video, write_video


def _make_dataset(tmp_path):
    root = tmp_path / "ds"
    root.mkdir()
    write_video(str(root / "pos_blink_cam1_bright.mp4"), burst_video(seconds=8.0, fps=30.0), 30.0)
    write_video(str(root / "neg_clean_cam1_bright.mp4"), clean_video(seconds=6.0, fps=30.0), 30.0)
    write_video(
        str(root / "neg_lamp_cam2_dim.mp4"), clean_video(seconds=6.0, fps=30.0, seed=9), 30.0
    )
    return root


def test_manifest_labels_and_hashes(tmp_path):
    root = _make_dataset(tmp_path)
    rows = build_manifest(root)
    assert len(rows) == 3
    by_label = {r.label for r in rows}
    assert by_label == {"signal", "clean"}
    hashes = {r.sha256_16 for r in rows}
    assert len(hashes) == 3  # distinct files -> distinct hashes


def test_manifest_missing_dir(tmp_path):
    try:
        build_manifest(tmp_path / "nope")
        raised = False
    except FileNotFoundError:
        raised = True
    assert raised


def test_evaluate_perfect_on_synthetic(tmp_path):
    root = _make_dataset(tmp_path)
    rows = build_manifest(root)
    result = evaluate(rows, threshold="suspicious")
    assert result["confusion"] == {"tp": 1, "fp": 0, "tn": 2, "fn": 0}
    assert result["accuracy"] == 1.0
    assert result["fpr"] == 0.0
    assert result["tpr"] == 1.0


def test_evaluate_threshold_signal_detected(tmp_path):
    root = _make_dataset(tmp_path)
    rows = build_manifest(root)
    result = evaluate(rows, threshold="signal_detected")
    # clean clips stay clean; the burst clip reaches signal_detected
    assert result["confusion"]["fp"] == 0
    assert result["confusion"]["tp"] == 1


def test_cli_manifest_and_evaluate(tmp_path, capsys):
    root = _make_dataset(tmp_path)
    out = tmp_path / "manifest.json"
    assert main(["manifest", str(root), "--json-out", str(out)]) == 0
    capsys.readouterr()
    manifest = json.loads(out.read_text())
    assert manifest["count"] == 3

    assert main(["evaluate", str(root)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["accuracy"] == 1.0


def test_cli_evaluate_bad_threshold(tmp_path, capsys):
    import pytest

    root = _make_dataset(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["evaluate", str(root), "--threshold", "bogus"])
    assert exc.value.code == 2
