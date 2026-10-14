# Changelog

All notable changes to LumenRadar are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/); versioning follows SemVer.

## [0.2.0] — 2026-10-14

### Added
- Detection engine: M1 narrow-band periodicity (0.5–15 Hz, three-gate rule:
  amplitude ≥ 0.5 gray, local-floor ratio ≥ 8, Gumbel noise-max check),
  M2 burst pulse-count symbol detection (bimodal gap split + pacing
  regularity: intra CV ≤ 0.6, inter CV ≤ 0.35, contrast ≥ 2), M3
  session-baseline spectral comparison (z ≥ 5 + amplitude gate), fused with
  artifact rejection (AE-hunting correlation+magnitude pair; mains 2f alias
  check) into an explainable JSON verdict (`verdict.py`).
- Spatial ring control channel for full-frame mode — auto-exposure artifacts
  are separable even without an ROI (`pipeline.ring_box`).
- Calibration beacon (`lumenradar beacon`): fixed-pattern dataset labeling
  utility (blink 1-2-3-4 / sine2 / square5). Detection-only scope; see
  docs/THREAT-MODEL.md.
- Dataset tooling: SHA-256 manifest builder and batch evaluator
  (`lumenradar manifest`, `lumenradar evaluate`) sharing the CLI analysis
  path one-to-one.
- Synthetic video generator (`lumenradar.synth`) with oracle light-region
  means — all development and testing is camera-less.
- CLI `--plot` flag: publication-style two-panel figures (series + Welch PSD).
- Calibration experiments (synthetic, mp4 round-trip):
  depth sweep (detection floor ≈ 4 gray levels p-p; clean FPR 0/10),
  frequency sweep (TPR 3/3 across 0.5–14 Hz; 15 Hz is codec-bound),
  runtime (≈ 12–16× realtime on ARM aarch64).
- Paper skeleton (`docs/paper/`): markdown working draft + LaTeX source
  compiling to a 4-page A4 PDF with verified citations.

### Fixed
- Absolute amplitude gate for M3: near-zero-energy baselines made spectral
  ratios explode on codec/quantization noise (clean FP).
- mp4v container FPS (e.g. 30.000029) no longer trips integer session-length
  gates via float comparison.
- Harmonic check compares against the global spectral floor (Hann leakage
  decays with distance, local floors were unfairly strict for pure sines).
- ROI auto-localization no longer shifts blobs by ±1 px (removed unnecessary
  morphology).
- `Intended Audience :: Security Industry` is not a valid PyPI classifier
  (packaging fix).

### Security
- Self-hosted CI hardening: workflow targets org runner labels explicitly;
  `pull_request` trigger deliberately absent for the public repo (PR code
  must never execute on the self-hosted machine). See docs/SELF-HOSTED-CI.md.

## [0.1.0] — 2026-10-14

### Added
- Project scaffold: pyproject (MIT), CI, threat model document.
- Core signal chain: video ingest (file + camera, FPS-safe subsampling),
  auto LED ROI localization (small saturated stable blobs, manual override,
  full-frame fallback), luminance series extraction with robust moving-median
  detrending, `analyze`/`probe` CLI JSON reports.
- 29 tests covering ingest/ROI/signal/CLI/synth.
