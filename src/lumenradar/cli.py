"""Command-line interface for LumenRadar (analyze / beacon / manifest / evaluate / probe)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .pipeline import analyze_source


def _parse_roi(text: str) -> tuple[int, int, int, int]:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("ROI must be 'x,y,w,h'")
    try:
        x, y, w, h = (int(p) for p in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ROI values must be integers") from exc
    if x < 0 or y < 0:
        raise argparse.ArgumentTypeError("ROI origin must be non-negative")
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError("ROI size must be positive")
    return (x, y, w, h)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lumenradar",
        description="Detect covert optical signaling in camera footage (defensive tooling).",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="Analyze a video file for covert optical signaling.")
    a.add_argument("video", help="Path to a video file")
    a.add_argument("--roi", type=_parse_roi, default=None, help="Manual ROI as x,y,w,h")
    a.add_argument("--max-fps", type=float, default=None, help="Subsample the source to this FPS")
    a.add_argument(
        "--json-out", type=Path, default=None, help="Also write the JSON report to this path"
    )

    b = sub.add_parser(
        "beacon",
        help="Play a fixed calibration pattern on screen (dataset labeling ONLY).",
        description=(
            "Display a fixed, documented test pattern for recording positive-class "
            "samples on your own hardware. No input capture, no network, no LLM — "
            "see docs/THREAT-MODEL.md."
        ),
    )
    b.add_argument(
        "--pattern", choices=("blink", "sine2", "square5"), default="blink", help="Fixed pattern"
    )
    b.add_argument("--duration", type=float, default=30.0, help="Seconds to play (default 30)")
    b.add_argument("--fps", type=float, default=30.0, help="Pattern frame rate (default 30)")
    b.add_argument("--size", type=int, default=320, help="Window size in px (default 320)")

    m = sub.add_parser("manifest", help="Build a SHA-256 manifest for a clip directory.")
    m.add_argument("directory", help="Directory containing pos_/neg_ prefixed clips")
    m.add_argument("--json-out", type=Path, default=None, help="Write manifest JSON to this path")

    e = sub.add_parser(
        "evaluate", help="Analyze every manifest clip and report a confusion matrix."
    )
    e.add_argument("directory", help="Directory containing pos_/neg_ prefixed clips")
    e.add_argument(
        "--threshold",
        choices=("suspicious", "signal_detected"),
        default="suspicious",
        help="Verdict level counted as a positive prediction (default: suspicious)",
    )
    e.add_argument("--max-fps", type=float, default=None, help="Subsample sources to this FPS")
    e.add_argument("--json-out", type=Path, default=None, help="Write evaluation JSON to this path")

    pr = sub.add_parser("probe", help="Print video metadata as JSON.")
    pr.add_argument("video", help="Path to a video file")
    return p


def _emit(report: dict, json_out: Path | None) -> None:
    text = json.dumps(report, indent=2)
    print(text)
    if json_out is not None:
        json_out.write_text(text, encoding="utf-8")


def cmd_analyze(args: argparse.Namespace) -> int:
    try:
        from .roi import manual_roi

        roi = manual_roi(args.roi) if args.roi is not None else None
        report = analyze_source(args.video, manual_roi=roi, max_fps=args.max_fps)
    except (FileNotFoundError, ValueError) as exc:
        _emit({"error": str(exc)}, None)
        return 2
    _emit(report, args.json_out)
    return 0


def cmd_beacon(args: argparse.Namespace) -> int:
    from .beacon import PATTERNS, play_screen, waveform

    levels = waveform(args.pattern, args.duration, args.fps)
    try:
        play_screen(levels, args.fps, size=args.size)
    except Exception as exc:  # noqa: BLE001 - cv2 raises assorted GUI errors
        _emit(
            {
                "error": f"cannot open beacon window (needs a display server): {exc}",
                "hint": "run this on the machine whose screen the camera records",
                "patterns": list(PATTERNS),
            },
            None,
        )
        return 2
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    from .dataset import build_manifest

    try:
        rows = build_manifest(args.directory)
    except FileNotFoundError as exc:
        _emit({"error": str(exc)}, None)
        return 2
    _emit(
        {
            "directory": str(args.directory),
            "count": len(rows),
            "rows": [
                {"path": r.path, "label": r.label, "sha256_16": r.sha256_16, "bytes": r.bytes}
                for r in rows
            ],
        },
        args.json_out,
    )
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    from .dataset import build_manifest, evaluate

    try:
        rows = build_manifest(args.directory)
        result = evaluate(rows, threshold=args.threshold, max_fps=args.max_fps)
    except (FileNotFoundError, ValueError) as exc:
        _emit({"error": str(exc)}, None)
        return 2
    _emit(result, args.json_out)
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    from .ingest import probe as probe_source

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
    handlers = {
        "analyze": cmd_analyze,
        "beacon": cmd_beacon,
        "manifest": cmd_manifest,
        "evaluate": cmd_evaluate,
        "probe": cmd_probe,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
