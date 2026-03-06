# 13 — Verification Gate

## Purpose

Enforce deterministic, fail-closed checks before publication.
Verification blocks unsafe or low-quality changes and emits structured signals for learning.

## Intent

The intent is to:
- stop low-quality changes early
- produce measurable signals that reduce future failures
- ensure evidence exists before QA and publication

## Plane Placement

Platform Plane: deterministic gate and signal emission

Agent Plane: Primary Agent responds to failures; cannot waive checks

## Responsibilities

- run required checks (format, lint, tests, security scans where required)
- record failure count and categories per task
- attach evidence to TaskPacket / PR evidence bundle
- emit verification events to signal stream
- trigger loopback to Primary Agent on failure

## Key Inputs

- working branch changes
- standards and guardrails (what must be enforced)
- CI status and logs where applicable

## Key Outputs

- verification_passed or verification_failed events
- failure categories and iteration counts
- evidence artifacts

## Failure Handling

- flaky CI: rerun policy, record as flake signal, avoid infinite loops
- missing dependencies: fail with clear error and remediation notes
- policy violations: stop and escalate if high-risk

## Signals

- verification_failed (category, iteration count, time-to-green)
- verification_passed
- verification_flake_detected

## Admin UI Integration

This component should expose status, key metrics, and safe control hooks to the Admin UI via the Admin API (RBAC + audit log).

## Repo Profile Dependencies

Verification is repo-specific. The Verification Gate must use the Repo Profile to determine:
- required checks and commands
- whether checks run locally, in CI, or both
- how to classify failures (lint, test, build, security, policy)
- which artifacts and logs must be attached as evidence

## Flake Policy

Verification must treat flaky checks as a first-class operational condition.

Definitions
- Flake: a check that fails and then passes on rerun without code changes.

Policy
- Max flake reruns per workflow step: 2
- If a check passes on rerun, mark the event as verification_flake_detected and continue.
- If flake repeats across tasks, classify as pipeline instability and escalate to platform owners.

Loop caps
- Verification loop cap is enforced separately from flake reruns.
- A task that hits verification loop cap must escalate to human review or be paused.

Evidence
- Record initial failure output and the rerun pass result in the evidence bundle.
- Emit flake_rate metric per repo (rolling window).

Admin UI
- show flake rate and top flaky checks per repo

## Evidence Bundle Requirements

Evidence bundle requirements make PR review and QA deterministic.

On verification pass, the evidence bundle must include:
- formatting and lint summary (tool version, counts, link to logs)
- test summary (tests run, pass/fail, duration, link to logs)
- security scan summary when applicable (secret scan, dependency audit)
- build or package summary when applicable

On verification failure, the evidence bundle must include:
- failure category (lint, test, build, security, policy)
- top error output snippet or log link
- attempt count and whether a rerun occurred
