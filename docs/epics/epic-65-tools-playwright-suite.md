# Epic 65 — Tool Hub: Playwright Full-Stack Test Suite

## Overview

**Page:** `/admin/ui/tools`
**Heading:** "Tool Hub"
**Total Points:** 19

Full-stack Playwright test suite for the Tool Hub admin page, verifying that the tool catalog, approval status badges, and access profiles render correctly and function as intended.

## Motivation

Tools are the verification backbone — ruff for lint, pytest for tests, security for CVEs. If the tool catalog is broken or approval status is wrong, the pipeline runs unverified code. This suite ensures the Tool Hub page is correct, accessible, and visually stable.

## Purpose

Show available tool suites (ruff, pytest, security scan), their approval status (observe/suggest/execute), and access profiles for role/tier combinations.

## APIs Under Test

| Endpoint | Method | Description |
|---|---|---|
| `/admin/tools/catalog` | GET | List tool suites |
| `/admin/tools/profiles` | GET | List tool profiles |
| `/admin/tools/check-access` | POST | Check tool access for role/tier |
| `/admin/ui/partials/tools` | GET | Tools list partial |

## Key Components

- Tool catalog list/cards
- Approval status badges (observe=gray, suggest=blue, execute=purple)
- Access check form
- Profile table

## Stories

| Story | Title | Points |
|---|---|---|
| 65.1 | Page Intent & Semantic Content | 3 |
| 65.2 | API Endpoint Verification | 3 |
| 65.3 | Style Guide Compliance | 5 |
| 65.4 | Interactive Elements | 3 |
| 65.5 | Accessibility WCAG 2.2 AA | 3 |
| 65.6 | Visual Snapshot Baseline | 2 |

## Acceptance Criteria

- [ ] All 6 stories pass
- [ ] No regressions in existing admin test suites
- [ ] Visual snapshots committed to baseline

## Definition of Done

- All stories complete and merged
- Playwright tests green in CI
- Visual baselines approved and committed
