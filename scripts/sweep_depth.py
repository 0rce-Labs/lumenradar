"""Depth-sweep calibration experiment (SYNTHETIC data only).

Measures the minimum detectable peak-to-peak luminance amplitude of a 2 Hz
sinusoidal LED modulation at 30 fps / 6 s clips, through the FULL pipeline
including mp4 codec round-trip. Results feed docs/paper (labeled synthetic).
"""

from __future__ import annotations

import argparse
import json
import math
import tempfile
from pathlib import Path

import numpy as np

from lumenradar.pipeline import ring_box
from lumenradar.roi import ROI
from lumenradar.signal import extract_series
from lumenradar.synth import Scene, write_video
from lumenradar.verdict import build_verdict

FPS = 30.0
SECONDS = 6.0
SEEDS = (1, 2, 3, 4, 5)
AMPS_GRAY = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0)
FREQ = 2.0
POSITIVE_STATUSES = {"suspicious", "signal_detected"}


def render_clip(amp_gray: float, seed: int, freq: float = FREQ) -> np.ndarray:
    """Scene with the LED swinging amp_gray gray levels peak-to-peak at freq."""
    scene = Scene(seed=seed)
    n = int(SECONDS * FPS)
    half = amp_gray / 2.0
    levels = 0.5 + (half / 255.0) * np.sin(2 * math.pi * freq * np.arange(n) / FPS)
    return np.stack([scene.frame(float(b)) for b in levels])


def oracle_roi() -> ROI:
    x, y = Scene().light_center
    w, h = Scene().light_size
    return ROI(x, y, w, h)


def run(out_path: str) -> dict:
    tmp = tempfile.mkdtemp(prefix="lrsweep_")
    roi = oracle_roi()
    results: list[dict] = []
    scene = Scene()
    width, height = scene.width, scene.height
    ring = ring_box(width, height)

    for amp in AMPS_GRAY:
        hits, ratios, peaks = 0, [], []
        for seed in SEEDS:
            path = str(Path(tmp) / f"amp{amp}_seed{seed}.mp4")
            write_video(path, render_clip(amp, seed), FPS)
            series = extract_series(path, roi=roi)
            control = extract_series(path, roi=None, exclude=ring)
            v = build_verdict(series, control)
            if v.status in POSITIVE_STATUSES:
                hits += 1
            m1 = v.evidence["m1_periodicity"]
            ratios.append(m1["ratio"])
            peaks.append(m1["peak_freq_hz"])
        results.append(
            {
                "amp_gray": amp,
                "tpr": round(hits / len(SEEDS), 3),
                "hits": hits,
                "n": len(SEEDS),
                "peak_freqs": peaks,
            }
        )
        print(f"amp={amp:6.1f} gray  TPR={hits}/{len(SEEDS)}")

    # False-positive rate on clean clips (amp = 0), same procedure.
    fp = 0
    clean_n = 10
    for seed in range(100, 100 + clean_n):
        path = str(Path(tmp) / f"clean_{seed}.mp4")
        write_video(path, render_clip(0.0, seed), FPS)
        series = extract_series(path, roi=roi)
        control = extract_series(path, roi=None, exclude=ring)
        v = build_verdict(series, control)
        fp += int(v.status in POSITIVE_STATUSES)
    fpr = round(fp / clean_n, 3)
    print(f"clean FPR={fp}/{clean_n}")

    report = {
        "experiment": "depth_sweep",
        "config": {"fps": FPS, "seconds": SECONDS, "freq_hz": FREQ, "codec": "mp4v"},
        "positive": results,
        "clean_fpr": fpr,
        "clean_n": clean_n,
        "note": "synthetic-only calibration; real-hardware evaluation pending",
    }
    Path(out_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"written: {out_path}")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/paper/results/depth_sweep.json")
    args = ap.parse_args()
    run(args.out)
