# Epic 66 — Model Gateway: Playwright Full-Stack Test Suite

## Overview

**Page:** `/admin/ui/models`
**Heading:** "Model Gateway"
**Total Points:** 19

Full-stack Playwright test suite for the Model Gateway admin page, verifying that model providers, model classes, routing rules, and cost information render correctly and function as intended.

## Motivation

Model routing controls cost and quality. Wrong routing rules mean the pipeline uses expensive models for trivial tasks or weak models for complex ones. This suite ensures the Model Gateway page is correct, accessible, and visually stable.

## Purpose

Show model providers (Anthropic, OpenAI), model classes (fast/balanced/strong), routing rules mapping pipeline stages to model classes, and cost information.

## APIs Under Test

| Endpoint | Method | Description |
|---|---|---|
| `/admin/models/providers` | GET | List model providers |
| `/admin/models/audit` | GET | Model audit trail |
| `/admin/ui/partials/models` | GET | Models list partial |
| `/admin/ui/partials/model-spend` | GET | Model spend data |

## Key Components

- Provider table/cards
- Model class badges
- Routing rules table
- Cost display
- Spend chart

## Stories

| Story | Title | Points |
|---|---|---|
| 66.1 | Page Intent & Semantic Content | 3 |
| 66.2 | API Endpoint Verification | 3 |
| 66.3 | Style Guide Compliance | 5 |
| 66.4 | Interactive Elements | 3 |
| 66.5 | Accessibility WCAG 2.2 AA | 3 |
| 66.6 | Visual Snapshot Baseline | 2 |

## Acceptance Criteria

- [ ] All 6 stories pass
- [ ] No regressions in existing admin test suites
- [ ] Visual snapshots committed to baseline

## Definition of Done

- All stories complete and merged
- Playwright tests green in CI
- Visual baselines approved and committed
