# Governance

This document describes the governance model for LumenRadar.

## Overview

LumenRadar is an open-source defensive research project that welcomes
contributions from anyone. It operates with a small set of maintainers
responsible for direction, code review, and releases, and aims to grow that
set over time.

## Roles

### Users

Anyone using LumenRadar — proctoring services, security teams, researchers.
Users are encouraged to file issues (especially Detector FP/FN reports),
suggest features, and contribute recordings for the dataset.

### Contributors

Anyone submitting pull requests, reporting bugs, improving documentation, or
helping other users. All contributors are listed at
<https://github.com/0rce-Labs/lumenradar/graphs/contributors>.

### Maintainers

People with commit access and review responsibility, listed in
[`OWNERS.md`](OWNERS.md). Maintainers review PRs, triage issues, and
participate in governance discussions.

### Project lead

Holds final decision-making authority on project direction, releases, and
governance — with one absolute constraint: **the scope boundary
(`docs/THREAT-MODEL.md`) is not subject to governance.** No vote, proposal,
or maintainer decision can authorize features outside it (transmitters,
answer paths, input capture). Changes to the boundary itself require replacing
the project lead.

## Becoming a maintainer

Maintainers are added based on sustained, high-quality contributions. Considered
signals: accepted PRs over several months, thoughtful code review of others'
work, constructive issue participation, and follow-through. Any maintainer can
nominate; the project lead decides.

## Decision making

Day-to-day decisions (bug fixes, small features, docs) go through normal PR
review. Larger decisions (architecture, new detector models, dependency
additions) use lazy consensus: a proposal issue is opened for at least 7 days;
silence from maintainers counts as consent; objections trigger discussion until
(resolve or) escalation to the project lead.

## Scope-violation handling

PRs adding transmitters, answer generation, or input capture are rejected
without review and documented in the PR thread. Repeated attempts or
contributions aimed at circumventing `docs/THREAT-MODEL.md` in letter or
spirit lead indefinitely to contributor blocking; scope-violating forks may be
noted in `docs/THREAT-MODEL.md` alongside the reason.
