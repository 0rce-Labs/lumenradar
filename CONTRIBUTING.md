# Contributing to LumenRadar

Thanks for your interest. LumenRadar is defensive tooling: it detects covert
optical signaling in camera footage. Before contributing, read
`docs/THREAT-MODEL.md` — it defines the hard scope boundary of this project.

## Non-negotiables

1. **Detection only.** No transmitter, no answer path, no screen/input capture,
   no LLM. PRs adding message transmission via screen/LED channels are
   rejected without review. The beacon must remain a fixed-pattern, unidirectional
   dataset-labeling utility.
2. **Akademik dürüstlük / academic honesty.** Benchmark claims must come from
   real recordings; synthetic results are always labeled synthetic. Never
   present synthetic data as hardware data.
3. **Test coverage.** Every bug fix needs a regression test; every new
   detector threshold change needs the calibration suites re-run
   (`scripts/sweep_depth.py`, `scripts/sweep_freq.py`) and the results diff'd.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest            # 76 tests, fully camera-less
ruff check src tests scripts
```

CI runs on a self-hosted ARM64 runner (`docs/SELF-HOSTED-CI.md`); it has **no
`pull_request` trigger by design** (public repo, self-hosted machine). Your
contribution is smoke-tested locally by you; a maintainer will verify it on
the runner after merging/rebasing to a branch they control.

## Conventions

- Code and comments in English; docs may be English or Turkish.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `ci:`, `test:`), one purpose
  per commit.
- Detector threshold changes must update `docs/paper/DRAFT.md` numbers or be
  flagged as a calibration TODO in the PR discussion.

## Reporting accuracy issues

Use the **"Detector false positive / false negative"** issue template. For
legal/ethical reasons, do **not** upload third-party exam or proctoring
recordings — record your own beacon-calibration clips instead.

## License

By contributing you agree your work is released under the repository's MIT
license.
