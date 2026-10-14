# Dataset redistribution policy (DECIDED)

**Decision:** manifest + generation scripts are released; clips are available
on request. (Set by the project lead, 14 Oct 2026.)

## What is published

- `manifest.json` per evaluation round — SHA-256 hash of every clip, byte
  counts, labels, capture conditions encoded in filenames
  (see `docs/DATASET.md`)
- All clip-generation and analysis scripts (`scripts/`) plus the synthetic
  generator (`lumenradar.synth`) — anyone can rebuild the synthetic part
  verbatim
- Full numeric results per clip (`docs/paper/results/`)

## What is on request

- The real-hardware clips themselves. They are personal recordings made on
  the maintainer's own equipment; bulk release would publish device-specific
  data for no research gain. Request by opening an issue describing your use
  case, or e-mail the maintainer (`OWNERS.md`). Granted for reproducibility
  review at the maintainer's discretion.

## Why not CC-BY clips (considered and rejected)

- Full reproducibility of a *technique* does not require the exact pixels:
  synthetic regeneration + manifest-verified real results cover the claims.
- Personal-hardware footage is low-risk but not zero-risk; the project's
  privacy posture (no third-party recordings accepted) should extend to its
  own files.
- Venue precedent: papers shipping "dataset by request" are common in the
  security-measurement space and accepted at arXiv/IEEE venues.

## For the paper text

> Real-hardware recordings are not redistributed; a SHA-256 manifest and all
> generation/analysis scripts are provided for independent verification, and
> clips are available from the author on reasonable request.
