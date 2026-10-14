"""Dataset tooling — manifest building and batch evaluation.

A dataset is a directory of clips named ``<label>_<device>_<condition>.mp4``
where the label prefix is ``pos_`` (contains a beacon pattern = positive
class) or ``neg_`` (no beacon = negative class). The manifest builder hashes
each file and parses the label; the evaluator runs the exact same analysis
pipeline as the CLI over every manifest row and reports a confusion matrix.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .pipeline import analyze_source

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}
LABELS = {"pos_": "signal", "neg_": "clean"}
# Verdict statuses considered a positive prediction, by evaluation threshold.
THRESHOLDS = {
    "suspicious": {"suspicious", "signal_detected"},
    "signal_detected": {"signal_detected"},
}


@dataclass
class ManifestRow:
    path: str
    label: str
    sha256_16: str
    bytes: int


def _iter_clips(root: Path) -> Iterator[Path]:
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS:
            yield p


def build_manifest(root: str | Path) -> list[ManifestRow]:
    """Hash every clip under ``root`` and parse its label from the filename."""
    root_path = Path(root)
    if not root_path.is_dir():
        raise FileNotFoundError(f"not a directory: {root_path}")
    rows: list[ManifestRow] = []
    for p in _iter_clips(root_path):
        label = "unknown"
        for prefix, lab in LABELS.items():
            if p.name.startswith(prefix):
                label = lab
                break
        h = hashlib.sha256()
        size = 0
        with p.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
                size += len(chunk)
        rows.append(ManifestRow(str(p), label, h.hexdigest()[:16], size))
    return rows


def evaluate(
    rows: list[ManifestRow], threshold: str = "suspicious", max_fps: float | None = None
) -> dict:
    """Run the analysis pipeline per clip and aggregate a confusion matrix.

    ``unknown``-label rows are analyzed and reported but excluded from the
    confusion matrix.
    """
    if threshold not in THRESHOLDS:
        raise ValueError(f"threshold must be one of {sorted(THRESHOLDS)}")
    positives = THRESHOLDS[threshold]
    tp = fp = tn = fn = 0
    per_file: list[dict] = []
    for row in rows:
        try:
            report = analyze_source(row.path, max_fps=max_fps)
            status = report["detection"]["status"]
            conf = report["detection"]["confidence"]
            error = None
        except (FileNotFoundError, ValueError) as exc:
            status, conf, error = "error", 0.0, str(exc)
        pred = status in positives
        scored = row.label in ("signal", "clean") and error is None
        if scored:
            if row.label == "signal":
                tp += int(pred)
                fn += int(not pred)
            else:
                tn += int(not pred)
                fp += int(pred)
        per_file.append(
            {
                "path": row.path,
                "label": row.label,
                "pred_positive": pred,
                "status": status,
                "confidence": conf,
                "error": error,
            }
        )
    total = tp + fp + tn + fn
    return {
        "threshold": threshold,
        "total": total,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "tpr": round(tp / (tp + fn), 4) if (tp + fn) else None,
        "fpr": round(fp / (fp + tn), 4) if (fp + tn) else None,
        "accuracy": round((tp + tn) / total, 4) if total else None,
        "per_file": per_file,
    }
