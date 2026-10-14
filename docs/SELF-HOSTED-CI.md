# Self-Hosted CI (boringserver-arm64)

GitHub-hosted runners for the 0rce-Labs org are unusable: every job dies at
start with *"The job was not started because your account is locked due to a
billing issue."* Rather than wait on the billing fix, CI runs on the Oracle
ARM free-tier box.

## Setup (already done)

- Runner: `~/actions-runner-lum` (actions-runner-linux-arm64 2.338.0)
- Name: `boringserver-arm64`, labels `self-hosted, Linux, ARM64`
- Service: `actions.runner.0rce-Labs-lumenradar.boringserver-arm64.service`
  (systemd, enabled, auto-starts on boot)
- Manage: `sudo ./svc.sh start | stop | status` (from the runner dir)

## Security posture (IMPORTANT)

- The workflow has **no `pull_request` trigger**: this is a public repo; PR
  code from strangers must never execute on the self-hosted machine. CI runs
  only on `main` pushes and manual `workflow_dispatch`.
- Labels in the workflow pin `[self-hosted, linux, ARM64]` — the job cannot
  be hijacked onto a different org runner.
- If a task ever requires executing PR patches, run it in a disposable
  container, never on the runner host directly.

## Verify

```bash
gh run list --repo 0rce-Labs/lumenradar --limit 3
gh run view <run-id> --repo 0rce-Labs/lumenradar --json conclusion
```

First green run on the self-hosted runner: run 38589856831 (commit 8eab065),
conclusion `success`.

## When billing unlocks

You can migrate back to hosted runners by reverting workflow `runs-on` to
`ubuntu-latest` + the 3.11/3.12 matrix — or leave as-is; the self-hosted
runner costs nothing and finishes the suite in ~40 s.
