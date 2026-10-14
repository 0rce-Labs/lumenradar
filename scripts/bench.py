"""Runtime benchmark — analyze_source wall time vs video duration (synthetic)."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from lumenradar.pipeline import analyze_source
from lumenradar.synth import burst_video, clean_video, write_video

FPS = 30.0
SECONDS = (6.0, 12.0, 30.0)
REPEATS = 3


def run(out_path: str) -> dict:
    tmp = tempfile.mkdtemp(prefix="lrbench_")
    rows = []
    for secs in SECONDS:
        for label, arr in (
            ("clean", clean_video(seconds=secs, fps=FPS)),
            ("burst", burst_video(seconds=secs, fps=FPS)),
        ):
            path = str(Path(tmp) / f"{label}_{int(secs)}.mp4")
            write_video(path, arr, FPS)
            times = []
            for _ in range(REPEATS):
                t0 = time.perf_counter()
                analyze_source(path)
                times.append(time.perf_counter() - t0)
            best = min(times)
            rows.append(
                {
                    "clip": label,
                    "duration_s": secs,
                    "wall_s": round(best, 3),
                    "realtime_factor": round(secs / best, 2),
                }
            )
            print(f"{label:6s} {int(secs):3d}s  wall={best:.2f}s  x{secs / best:.1f} realtime")

    report = {
        "benchmark": "runtime",
        "config": {"fps": FPS, "repeats": REPEATS, "stat": "min", "machine": "oracle-aarch64"},
        "rows": rows,
        "note": "synthetic clips; absolute numbers are machine-relative",
    }
    Path(out_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"written: {out_path}")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/paper/results/runtime.json")
    args = ap.parse_args()
    run(args.out)
