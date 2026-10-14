"""Command-line interface for LumenRadar (analyze / probe)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .ingest import probe as probe_source
from .roi import ROI, manual_roi, stable_roi
from .signal import extract_series
from .verdict import build_verdict


def _parse_roi(text: str) -> ROI:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("ROI must be 'x,y,w,h'")
    try:
        x, y, w, h = (int(p) for p in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ROI values must be integers") from exc
    return manual_roi((x, y, w, h))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lumenradar",
        description="Detect covert optical signaling in camera footage (defensive tooling).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="Analyze a video file for covert optical signaling.")
    a.add_argument("video", help="Path to a video file")
    a.add_argument("--roi", type=_parse_roi, default=None, help="Manual ROI as x,y,w,h")
    a.add_argument("--max-fps", type=float, default=None, help="Subsample the source to this FPS")
    a.add_argument(
        "--json-out", type=Path, default=None, help="Also write the JSON report to this path"
    )

    pr = sub.add_parser("probe", help="Print video metadata as JSON.")
    pr.add_argument("video", help="Path to a video file")
    return p


def _resolve_roi(video: str, manual: ROI | None) -> tuple[ROI | None, str]:
    """ROI resolution order: manual override > stable auto-LED > full-frame."""
    if manual is not None:
        return manual, "manual"
    auto = stable_roi(video)
    if auto is not None:
        return auto, "auto"
    return None, "fullframe"


def _emit(report: dict, json_out: Path | None) -> None:
    text = json.dumps(report, indent=2)
    print(text)
    if json_out is not None:
        json_out.write_text(text, encoding="utf-8")


def cmd_analyze(args: argparse.Namespace) -> int:
    try:
        meta = probe_source(args.video)
    except FileNotFoundError as exc:
        _emit({"error": str(exc)}, None)
        return 2

    if args.roi is not None and (
        args.roi.x < 0
        or args.roi.y < 0
        or args.roi.x + args.roi.w > meta.width
        or args.roi.y + args.roi.h > meta.height
    ):
        _emit({"error": f"ROI exceeds frame {meta.width}x{meta.height}"}, None)
        return 2

    try:
        roi, mode = _resolve_roi(args.video, args.roi)
        series = extract_series(args.video, roi=roi, max_fps=args.max_fps)
        control = (
            extract_series(args.video, roi=None, exclude=roi, max_fps=args.max_fps)
            if roi
            else None
        )
    except (FileNotFoundError, ValueError) as exc:
        _emit({"error": str(exc)}, None)
        return 2

    resid = series.detrend()
    verdict = build_verdict(series, control)
    report = {
        "tool": "lumenradar",
        "version": __version__,
        "source": {
            "path": meta.source,
            "width": meta.width,
            "height": meta.height,
            "fps": round(meta.fps, 3),
            "frame_count": meta.frame_count,
        },
        "roi": {"mode": mode, **(roi.as_dict() if roi is not None else {})},
        "series": {
            "n": series.n,
            "duration_s": round(series.duration, 3),
            "effective_fps": round(series.effective_fps, 2),
        },
        "stats": {
            "residual_std": round(float(resid.std()), 4),
            "residual_min": round(float(resid.min()), 4),
            "residual_max": round(float(resid.max()), 4),
        },
        "detection": verdict.as_dict(),
    }
    _emit(report, args.json_out)
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    try:
        meta = probe_source(args.video)
    except FileNotFoundError as exc:
        _emit({"error": str(exc)}, None)
        return 2
    _emit(
        {
            "path": meta.source,
            "width": meta.width,
            "height": meta.height,
            "fps": round(meta.fps, 3),
            "frame_count": meta.frame_count,
        },
        None,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return cmd_analyze(args)
    if args.command == "probe":
        return cmd_probe(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
