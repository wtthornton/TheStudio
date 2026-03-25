# Epic 67 — Compliance Scorecard: Playwright Full-Stack Test Suite

## Overview

**Page:** `/admin/ui/compliance`
**Heading:** "Compliance Scorecard"
**Total Points:** 19

Full-stack Playwright test suite for the Compliance Scorecard admin page, verifying that per-repo compliance status, individual check results, and repo selection render correctly and function as intended.

## Motivation

Compliance gates control tier promotion. If the scorecard is wrong, repos get promoted (or blocked) incorrectly, undermining trust in the system. This suite ensures the Compliance Scorecard page is correct, accessible, and visually stable.

## Purpose

Per-repo compliance scorecard showing overall PASS/FAIL status and individual check results (coverage, security, test requirements) with repo selector.

## APIs Under Test

| Endpoint | Method | Description |
|---|---|---|
| `/admin/repos/{repo_id}/compliance` | GET | Get compliance status |
| `/admin/repos/{repo_id}/compliance/evaluate` | POST | Evaluate compliance |
| `/admin/ui/partials/compliance` | GET | Compliance partial |
| `/admin/ui/partials/targets` | GET | Operational targets |

## Key Components

- Scorecard card with pass/fail badge
- Individual check rows with pass/fail indicators
- Repo selector dropdown
- Evaluate button

## Stories

| Story | Title | Points |
|---|---|---|
| 67.1 | Page Intent & Semantic Content | 3 |
| 67.2 | API Endpoint Verification | 3 |
| 67.3 | Style Guide Compliance | 5 |
| 67.4 | Interactive Elements | 3 |
| 67.5 | Accessibility WCAG 2.2 AA | 3 |
| 67.6 | Visual Snapshot Baseline | 2 |

## Acceptance Criteria

- [ ] All 6 stories pass
- [ ] No regressions in existing admin test suites
- [ ] Visual snapshots committed to baseline

## Definition of Done

- All stories complete and merged
- Playwright tests green in CI
- Visual baselines approved and committed
