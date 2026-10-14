# Dataset Protocol

## Directory layout

```
dataset/
├── pos_blink_macbook_bright.mp4     # positive: beacon pattern on screen/LED
├── pos_sine2_macbook_bright.mp4
├── neg_clean_macbook_bright.mp4     # negative: same setup, beacon off
├── neg_lamp_macbook_night.mp4       # negative: known flicker sources
└── ...
```

Naming contract: `<pos|neg>_<what>_<device>_<condition>.mp4`. The leading
`pos_` / `neg_` prefix is the ground-truth label parsed by
`lumenradar manifest` / `lumenradar evaluate`. Files without a recognized
prefix are hashed and reported but excluded from the confusion matrix.

## Recording protocol (per device)

1. Fix the camera (webcam/phone) with the screen or LED in frame; lock
   exposure/focus if the camera app allows it.
2. **Negative pass:** record 30 s of normal use (typing, browsing) — `neg_*`.
3. **Positive pass:** run `lumenradar beacon --pattern blink --duration 30`
   on the recorded machine, record the screen/LED — `pos_*`.
4. Repeat under 2-3 lighting conditions (bright / dim / lamp-on).
5. Copy clips into one directory, run:

```bash
lumenradar manifest ./dataset --json-out manifest.json
lumenradar evaluate ./dataset --threshold suspicious --json-out eval.json
```

## Integrity

Every clip is SHA-256 hashed into the manifest (16-hex prefix). Keep
`manifest.json` with the dataset; re-run `manifest` and diff before any
re-evaluation to prove clips did not change.

## Academic honesty

Only real recordings count as dataset rows. Synthetic clips
(`lumenradar.synth`) are for unit tests and threshold calibration only and
are never reported as evaluation results.
