"""Frequency-sweep robustness experiment (SYNTHETIC).

Verifies M1 detection across the full 0.5-15 Hz analysis band and M2 blink
timing across its supported pulse-rate range, plus interspersed clean-FP
probes. Output feeds docs/paper (synthetic-only).
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from lumenradar.pipeline import ring_box
from lumenradar.roi import ROI
from lumenradar.signal import extract_series
from lumenradar.synth import Scene, periodic_video, write_video
from lumenradar.verdict import build_verdict

FPS = 30.0
SECONDS = 6.0
SEEDS = (1, 2, 3)
POSITIVE_STATUSES = {"suspicious", "signal_detected"}
FREQS = (0.5, 0.8, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 12.0, 14.0, 15.0)
DEPTH = 0.6  # ~76 gray levels p-p — comfortably above the calibrated floor


def run(out_path: str) -> dict:
    tmp = tempfile.mkdtemp(prefix="lrfreq_")
    scene = Scene()
    ring = ring_box(scene.width, scene.height)
    x, y = scene.light_center
    w, h = scene.light_size
    roi = ROI(x, y, w, h)

    rows = []
    for freq in FREQS:
        hits, peaks = 0, []
        for seed in SEEDS:
            path = str(Path(tmp) / f"f{freq}_s{seed}.mp4")
            write_video(
                path,
                periodic_video(freq=freq, seconds=SECONDS, fps=FPS, depth=DEPTH, seed=seed),
                FPS,
            )
            series = extract_series(path, roi=roi)
            control = extract_series(path, roi=None, exclude=ring)
            v = build_verdict(series, control)
            if v.status in POSITIVE_STATUSES:
                hits += 1
            peaks.append(v.evidence["m1_periodicity"]["peak_freq_hz"])
        rows.append({"freq_hz": freq, "hits": hits, "n": len(SEEDS), "peaks": peaks})
        print(f"freq={freq:5.1f} Hz  TPR={hits}/{len(SEEDS)}  peaks={peaks}")

    # Clean-FP probes between sweep points (no signal at all).
    fp = 0
    clean_n = 12
    for seed in range(200, 200 + clean_n):
        path = str(Path(tmp) / f"clean_{seed}.mp4")
        write_video(
            path, periodic_video(freq=0.2, seconds=SECONDS, fps=FPS, depth=0.001, seed=seed), FPS
        )
        series = extract_series(path, roi=roi)
        control = extract_series(path, roi=None, exclude=ring)
        v = build_verdict(series, control)
        fp += int(v.status in POSITIVE_STATUSES)
    fpr = round(fp / clean_n, 3)
    print(f"sub-threshold clean FPR={fp}/{clean_n}")

    report = {
        "experiment": "frequency_sweep",
        "config": {"fps": FPS, "seconds": SECONDS, "depth": DEPTH, "codec": "mp4v"},
        "positive": rows,
        "sub_threshold_clean_fpr": fpr,
        "clean_n": clean_n,
        "note": "synthetic-only robustness calibration; real-hardware pending",
    }
    Path(out_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"written: {out_path}")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/paper/results/freq_sweep.json")
    args = ap.parse_args()
    run(args.out)
