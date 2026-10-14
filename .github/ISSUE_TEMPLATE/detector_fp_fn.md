---
name: Detector false positive / false negative
about: Report a clean clip flagged as suspicious (FP) or a beacon clip missed (FN)
title: ''
labels: detector-accuracy
assignees: ''
---

> Please **never attach raw exam/proctoring footage** — record your own
> calibration clips per `docs/DATASET.md` instead. Reports containing
> third-party recordings will be closed.

**Clip properties**
- Source (webcam model / screen rec.), resolution, fps:
- Contents (what happens in the clip, lighting):
- Label: false positive on a clean clip / false negative on a beacon clip

**Evidence**
- Full JSON verdict:
- If possible, the rendered figure (`lumenradar analyze clip.mp4 --plot fig.png`)

**Environment**
- OS / Python:
- lumenradar version:
