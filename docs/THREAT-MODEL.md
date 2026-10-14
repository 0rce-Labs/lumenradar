# Threat Model

## What LumenRadar detects

Covert optical signaling toward a camera receiver, in the proctoring/monitoring
context: an on-screen or on-device light source (status LED, keyboard backlight,
screen region) modulated to carry a multi-symbol message that a nearby camera can
read while a human supervisor cannot (or would not) notice.

Concrete signal classes:

1. **Blink-count symbols** — N short pulses (1..4) encoding choice A..D, repeated.
2. **Backlight / brightness pulses** — periodic screen-luminance modulation.
3. **Sub-perceptual oscillation** — narrow-band luminance oscillation below human
   perception thresholds (cf. BRIGHTNESS, Guri et al. 2020).

## Detector model

- Input: video file or live camera (the *supervisor's* camera, e.g. proctor webcam).
- Offline analysis; no network access; no third-party calls.
- Band: 0.5–15 Hz for >=30 fps sources (Nyquist-limited); PWM-adjacent classes are
  best-effort.

## What LumenRadar does NOT do

- **No transmitter:** nothing in this repo modulates a screen/LED to carry a message.
- **No capture-and-answer loop:** no screen-question capture, no LLM, no answer path.
- **Beacon boundary:** the beacon is a fixed-pattern calibration signal for dataset
  labeling on your own hardware only, explicitly not connected to any application
  or AI path.
- PRs adding message transmission will be rejected.

## Attacker model

Malware/app on the supervised device that can control an LED or a screen region,
plus a receiver camera with line of sight (proctor webcam, phone). The detector
assumes no access to the supervised device.

## Limitations

- Camera fps bounds detectable frequency (Nyquist); rolling shutter and
  auto-exposure artifacts create false positives — mitigated in the
  artifact-rejection layer (AE-hunting, mains flicker, aperiodic activity) and
  documented per verdict.
- A determined adversary can randomize duty cycles or hide within benign flicker;
  the tool reports confidence, never certainty.
