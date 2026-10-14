<div align="center">

# LumenRadar

**Detect covert optical signaling in camera footage — before it detects you.**

LED blink-count codes, backlight pulses, and screen-brightness flashes that are
invisible (or unremarkable) to a human observer but carry data to a receiver
camera. LumenRadar analyzes ordinary video and tells you whether one was used.

[![CI](https://github.com/0rce-Labs/lumenradar/actions/workflows/ci.yml/badge.svg)](https://github.com/0rce-Labs/lumenradar/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![GitHub release](https://img.shields.io/github/v/release/0rce-Labs/lumenradar)](https://github.com/0rce-Labs/lumenradar/releases)

*An open research project by [0rce-Labs](https://github.com/0rce-Labs)*

</div>

---

## Why

Commercial exam-evasion products now ship covert answer channels — menu-bar
icons, Caps-Lock LED blink counts, keyboard-backlight pulses, screen flashes —
marketed as undetectable in video proctoring. The *attack* side of this channel
family is well studied (LED-it-GO, BRIGHTNESS, VisiSploit), but the **detection**
side is not: prior work explicitly leaves camera-based monitoring unimplemented.

LumenRadar closes that gap. It is detection-only: no transmitter, no answer
path, no LLM — see [`docs/THREAT-MODEL.md`](docs/THREAT-MODEL.md).

## How it works

```
video ──▶ ingest ──▶ LED ROI localization ──▶ luminance time-series
                                                        │
                              ┌─────────────────────────┼──────────────────┐
                              ▼                         ▼                  ▼
                    M1 band periodicity        M2 burst pulse-count   M3 session baseline
                    (0.5-15 Hz, 3-gate)        (blink-code symbols)   (onset detection)
                              └──────────┬──────────────┴──────────────────┘
                                         ▼
                          artifact rejection (AE-hunting, mains, transients)
                                         ▼
                       fused verdict + full evidence (JSON) — explainable
```

Three independent detectors vote; the output is an explainable JSON verdict
with full per-detector evidence — never a bare score.

## Results

| Evaluation | Outcome |
|---|---|
| **Real hardware** (Retina 2880×1800 screen recording, VFR 24–52 fps, 6 clips) | **3/3 positives detected, 0 false positives** |
| Blink-count symbol recovery through mp4 codec | exact: `(1,1,2,1,2,…)` decoded after round-trip |
| Synthetic detection floor (30 fps, codec round-trip) | ~4 gray levels peak-to-peak |
| Synthetic frequency sweep | TPR 3/3 across 0.5–14 Hz |
| Clean-clip false positives (synthetic) | 0/10 |
| Runtime | 12–16× realtime on ARM (30 s clip in ≈2.2 s) |
| Tests / CI | 76 tests, CI green |

Full per-clip results: [`docs/paper/results/`](docs/paper/results/) ·
benchmark scripts: [`scripts/`](scripts/)

The dataset surfaced three real-world defects invisible to synthetic data
(beacon-square ROI beyond small-LED heuristics, low-duty blink lead-in, VFR
spectral leakage) — all fixed and documented in the working-paper draft
[`docs/paper/DRAFT.md`](docs/paper/DRAFT.md). The LaTeX source compiles to a
4-page A4 PDF: [`docs/paper/latex/`](docs/paper/latex/).

## Installation

```bash
pip install git+https://github.com/0rce-Labs/lumenradar.git
lumenradar --version
```

Requires Python ≥ 3.11. Works on Linux, macOS, and Windows. Video-file analysis
needs no camera.

## Usage

**Analyze a recording:**

```bash
$ lumenradar analyze proctor-recording.mp4
{
  "detection": {
    "status": "signal_detected",
    "confidence": 0.85,
    "signal_class": "blink_count",
    "evidence": {
      "m2_burst": {"pulses": 10, "symbol_counts": [1,1,2,1,2,1,2], "...": "..."}
    }
  }
}
```

Every verdict carries the full detector evidence — suitable as reviewable
material for human decision-makers, never an automated accusation.

Other analyze options: `--roi x,y,w,h` (manual LED box), `--max-fps 15`
(subsample high-fps sources), `--json-out report.json`, `--plot fig.pdf`
(publication-style figure).

**Build your own labeled dataset** (your hardware only):

```bash
lumenradar beacon --pattern blink --duration 30     # fixed calibration pattern
lumenradar manifest ./dataset --json-out manifest.json
lumenradar evaluate  ./dataset                      # confusion matrix
```

Recording and labeling protocol: [`docs/DATASET.md`](docs/DATASET.md).

## Scope & rules

- **Detection only.** No transmitter, no answer generation, no proctoring
  evasion. The calibration beacon is a fixed-pattern dataset-labeling utility,
  not connected to any capture or AI path.
- Pull requests adding message transmission via screen/LED channels are
  rejected without review.
- Do not upload third-party exam or proctoring recordings — issues containing
  them will be closed. Record your own calibration clips.

Full rationale: [`docs/THREAT-MODEL.md`](docs/THREAT-MODEL.md) ·
[`CONTRIBUTING.md`](CONTRIBUTING.md)

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q          # 76 tests, fully camera-less (synthetic video generator)
ruff check src tests scripts
```

CI runs on a self-hosted ARM64 runner with no `pull_request` trigger (public
repo + self-hosted machine security rule) — see
[`docs/SELF-HOSTED-CI.md`](docs/SELF-HOSTED-CI.md).

## Roadmap

Open items live in the
[issue tracker](https://github.com/0rce-Labs/lumenradar/issues):
scaled-up multi-device dataset + formal ROC (#1), >30 fps / codec matrix
(#2), optional explainable ML layer (#3), dataset license policy (#4).

## Contributing

Issues and PRs welcome — read [`CONTRIBUTING.md`](CONTRIBUTING.md) first.
Accuracy problems are best reported via the
**Detector FP/FN** issue template with the CLI JSON of the clip.

## Security

See [`SECURITY.md`](SECURITY.md). Report vulnerabilities privately — do not
open public issues for them.

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md).

## License

[MIT](LICENSE) © [0rce-Labs](https://github.com/0rce-Labs)
