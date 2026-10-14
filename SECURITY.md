# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| latest (main) | ✅ |
| < 0.2.0 | ❌ |

## Reporting a vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

Report privately via
[GitHub Security Advisory ("Report a vulnerability")](https://github.com/0rce-Labs/lumenradar/security/advisories/new)
or email the maintainers listed in the repository owner profile.

Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive an acknowledgment within 7 days and a status update within 30
days. We will credit reporters in release notes unless anonymity is requested.

## Scope

**In scope:**

- The analysis pipeline (`src/lumenradar/`): parsing/corruption crashes,
  path traversal in CLI file arguments, JSON output injection
- The beacon, manifest, and evaluate commands
- Supply-chain issues in declared dependencies

**Out of scope:**

- Statistics/accuracy limitations of the detector (use the
  [Detector FP/FN template](.github/ISSUE_TEMPLATE/detector_fp_fn.md) instead)
- Denial-of-service on极其 large inputs beyond documented memory behavior
- Issues in third-party dependencies (report upstream; notify us for
  coordinated disclosure)
- Anything requiring physical access to the recording machine

## Project-specific security notes

This is a **defensive analysis tool** with no network-facing surface: it reads
local media files and writes local JSON/figures. There is no server, no
telemetry, and no network code path. The highest-value review targets are
therefore media parsers (OpenCV usage in `ingest.py`) and the CLI argument
surface.

If you find a way to make the tool **transmit** information through a
screen/LED channel, that is not a vulnerability — it is a scope violation,
and the report will be handled under the project's scope rules
(`docs/THREAT-MODEL.md`), not the security process.
