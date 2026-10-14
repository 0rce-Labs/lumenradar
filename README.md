# LumenRadar

Detection of covert optical signaling in camera footage — LED blink-count codes,
backlight pulses, and screen-brightness flashes that are invisible (or unremarkable)
to a human observer but carry data to a receiver camera.

**Defensive tooling.** LumenRadar analyzes video (file or live camera) for periodic
luminance oscillation and pulse-symbol structure that indicate a covert optical
channel, and reports a verdict with evidence.

## Scope & rules

- This repository contains **detection only**. There is no transmitter, no answer
  generation, and no exam-proctoring evasion of any kind.
- The calibration beacon (`lumenradar beacon`, Faz 3) exists solely to produce
  labeled positive samples on **your own hardware** for dataset construction. It
  emits a fixed, documented test pattern and is not connected to any capture or
  LLM path.
- Pull requests adding transmission/encoding of messages via screen/LED channels
  will be rejected. See `docs/THREAT-MODEL.md`.

## Install

```bash
pipx install lumenradar          # or: pip install lumenradar
```

From source:

```bash
pip install -e .
```

Works on Linux, macOS, and Windows (Python >= 3.11). Video-file analysis needs no
camera; live analysis uses any OpenCV-compatible webcam.

## Usage

```bash
lumenradar analyze recording.mp4              # JSON report to stdout
lumenradar analyze clip.mp4 --roi 100,40,24,18
lumenradar analyze clip.mp4 --max-fps 15      # subsample high-fps sources
```

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

Development and testing are fully camera-less: synthetic test videos are generated
in-process (`lumenradar.synth`).

## Status

Faz 1 (alpha): video ingestion, LED ROI localization, luminance time-series, CLI.
Faz 2 next: detection engine (periodicity / burst-symbol / session-baseline) +
artifact rejection (auto-exposure, mains flicker).

## License

MIT — see `LICENSE`. A 0rce-Labs project.
