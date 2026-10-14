# Detecting Covert Optical Signaling in Camera Footage: A DSP Pipeline for Blink-Count and Brightness Channels

**Working draft (v0.1) — 0rce-Labs.** Status: method + synthetic calibration complete;
real-hardware dataset evaluation pending (docs/DATASET.md). All numbers in §6 are
synthetic-only and labeled as such.

## 1. Introduction

Consumer screen- and LED-control software can modulate a light source so that a
nearby camera receives data that a human supervisor misses: answer codes encoded
as Caps-Lock/keyboard-backlight blink counts, screen-brightness pulses, or
sub-perceptual luminance oscillation. Commercial products in the exam-proctoring
evasion space now ship exactly these channels (e.g., Rubric's menu-bar/LED/
backlight/screen-flash modes). The attack side is well studied — optical covert
channels from air-gapped machines (LED-it-GO, BRIGHTNESS, VisiSploit) — but the
**detection** side is not: Guri et al. explicitly leave camera-based monitoring
"nontrivial and impractical at wide scale" unimplemented, and the 2023 receiver
literature solves *decoding* (the attacker's problem), not *detection* (the
defender's).

We present LumenRadar, an open-source, camera-less-developable detector that
analyzes ordinary video (proctor webcam, phone recording) and reports whether a
localized light source carries covert modulation. Contributions:

1. A three-detector DSP pipeline (narrow-band periodicity, burst pulse-count
   structure, session-baseline comparison) fused with artifact rejection
   (auto-exposure hunting, mains-flicker aliases) into an explainable verdict.
2. The first open-source detector targeting **blink-count symbol modulation**
   (1-4 pulses = choice A-D) in the proctoring context.
3. A synthetic calibration quantifying the perceptible-detection floor
   (~2-4 gray levels peak-to-peak at 30 fps through an mp4v round-trip)
   and a dataset protocol + tooling for real-hardware evaluation.

Scope statement: LumenRadar is detection-only. The repository contains no
transmitter and no answer path; the calibration beacon exists solely to label
positive-class samples on the defender's own hardware.

## 2. Related Work

| Work | Channel | Direction | Gap we fill |
|---|---|---|---|
| LED-it-GO (Guri et al., 2017, arXiv:1702.06715) | HDD LED OOK, 4000 bit/s | attack | suggests tape/jamming only |
| BRIGHTNESS (Guri et al., 2020, arXiv:2002.01078) | screen brightness, ~10 bit/s | attack | camera-based detection left "nontrivial" |
| VisiSploit (Guri et al., 2016, arXiv:1607.03946) | sub-perceptual images | attack | — |
| HiLight (Wang et al., MobiCom'16) | pixel translucency FSK 20/30 Hz | attack (decode) | DSP methods we adapt defensively |
| Sensors 23-00665 (2023) | brightness 2-PAM, k-means seg. | attack (decode) | decoding ≠ detecting |
| Proctoring-integrity literature | screen capture, gaze | defense | no optical-channel detector |

## 3. Threat Model

**Attacker:** app/malware controlling an LED or screen region on the supervised
device + receiver camera with line of sight. **Defender:** has only the camera
stream (the proctor's webcam); no access to the supervised device. **Signals:**
(1) blink-count symbols, (2) periodic brightness pulses, (3) sub-perceptual
oscillation. **Non-goals:** keystroke/EM/acoustic channels; high-rate PWM
bandwidths beyond camera Nyquist.

## 4. Method

Pipeline per clip: ingest → LED ROI localization (small saturated stable blob;
manual override; full-frame fallback) → luminance series (ROI mean, control =
frame mean with ROI/ring excluded) → three detectors → artifact classification →
fused verdict with full evidence JSON.

- **M1 band periodicity (0.5-15 Hz).** Hann PSD; three gates: absolute
  amplitude A = 4·sqrt(P)/N ≥ 0.5 gray (perceptibility; also kills out-of-band
  leakage skirts), peak/median-local-floor ratio ≥ 8, and peak above the
  Gumbel noise-max expectation 2·(ln n + γ). Harmonic check against the global
  floor.
- **M2 burst pulse-count.** Threshold segmentation → intervals → bimodal split
  at the largest jump (median splits collapse when single-count symbols
  dominate) → symbol counts; detected iff counts repeat AND intra-gap CV ≤ 0.6
  AND inter-gap CV ≤ 0.35 AND gap contrast ≥ 2 (aperiodic HDD-LED-like activity
  fails pacing).
- **M3 session baseline.** First 2 s as beacon-free profile; candidate windows
  compared by smoothed PSD ratio; z ≥ 5 (log-ratio σ = sqrt(2·ψ′(5))) AND
  amplitude ≥ 0.5 gray (near-zero-energy baselines make ratios explode).
- **Artifacts.** AE-hunting: ROI/control lockstep (r ≥ 0.85) with comparable
  magnitude (control/ROI std ≥ 0.25) — correlation alone is fooled by mp4v
  codec bleed (measured r = 0.86-0.98 with ~0 control amplitude). Mains
  2f aliases only when Nyquist covers 100/120 Hz. Full-frame mode gains a
  spatial control from the border ring.

## 5. Dataset Protocol

`docs/DATASET.md`: pos_/neg_ naming contract, SHA-256 manifest, per-device
protocol (2-3 lighting conditions, 30 s clips, beacon for positives on the
defender's own hardware). Synthetic clips are unit-test/calibration only and
never count as evaluation rows.

**Real-hardware results (Mac dataset, 14 Oct 2026):** 6 clips (3 pos, 3 neg),
Retina 2880×1800 screen recording, 24-52 fps variable frame rate.
**3/3 positives detected, 0 false positives** (at the `suspicious`
threshold: 2× `signal_detected`/`blink_count` with symbol timing recovered,
1× `suspicious`/`periodic` at the true 1.8 Hz). The dataset surfaced three
genuine defects synthetic data could not:

1. The calibration beacon renders as a **~300 px solid bright square** —
   beyond the small-LED ROI heuristic (which instead anchored on 2×2 sensor
   specks). Fixed: class-aware beacon-square scan (`allow_large_beacon`)
   prioritized over the speck path.
2. **Low-duty blink lead-in:** the first ON frame arrives at #39 (0.65 s);
   a 15-frame probe window found nothing. Fixed: beacon scan widened to
   180 frames.
3. **VFR spectral leakage:** uneven frame pacing (16.7-133 ms dt) spreads a
   69-gray 2 Hz tone's energy across thousands of bins, collapsing the
   local-floor ratio to 2.43. Fixed: strong-amplitude (≥ 8 gray) +
   harmonic-confirmed bypass.
4. (Post-dataset addition) **Sustained-power gate:** a one-off UI element
   vanishing at 10 s produced a step-edge transient that fired M3 (z=21.9);
   sustained-power fraction separates it from real beacons (0.05 vs 1.00).

Full per-clip results: `docs/paper/results/mac_redetect.json`.

## 6. Synthetic Calibration (preliminary)

Config: 640×480 scene with structured background, LED ROI 16×16, 30 fps,
6 s, mp4v round-trip, 5 seeds per amplitude, 10 clean seeds.

- Detection floor (2 Hz sine, TPR 5/5 from): **4 gray levels peak-to-peak**;
  partial detection at 2; amp-gate correctly rejects ≤ 1.
- Clean FPR: **0/10** at the `suspicious` threshold.
- Frequency sweep (~76 gray p-p, 3 seeds/freq): TPR 3/3 at every frequency
  0.5–14 Hz, peaks recovered at the true frequency; at 15 Hz the mp4 codec
  itself destroys the signal (≈0.1 gray after round-trip) — the practical
  band edge is codec-bound, not detector-bound.
- End-to-end classes: clean/noisy → clean; 2 Hz → periodic; (1,1,2,1,2,…)
  blink pattern → signal_detected, blink_count, symbol counts recovered
  exactly after codec; whole-frame oscillation → camera_artifact (AE).
- Runtime: ~12–16× realtime on an ARM aarch64 core (30 s clip in 2.2 s).
- Limits: codec I-frame breathing is the dominant artifact class; the 15 Hz
  Nyquist edge is codec-bound; PWM-adjacent channels are best-effort.

*These numbers are synthetic; real-camera datasets (rolling shutter, real AE,
sensor noise) are expected to shift the floor — that measurement is the
immediate next step.*

## 7. Countermeasures (guidance output)

For flagged sessions: physical LED covering policy, brightness-locked displays,
proctor-cam exposure lock, and session-baseline comparison as continuous
monitoring. Detector output is evidence (JSON), never an automated accusation.

## 8. Threats to Validity

Synthetic scenes lack realistic texture/illumination dynamics; the beacon
pattern is machine-timed while human-driven blink codes may jitter (M2 CV
thresholds may need loosening); adaptive adversaries can randomize duty
cycles to defeat M2 pacing; low-cost webcams may compress away sub-0.5-gray
signals (which also *raises* the attacker's perceptibility requirement —
favoring the defender).

## 9. Roadmap

Real-hardware dataset + ROC (TPR@FPR≤5%) → arXiv preprint → SIU / IEEE Access
submission. Repo: github.com/0rce-Labs/lumenradar (MIT).
