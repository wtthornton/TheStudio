# Epic 69 — Dead-Letter Inspector: Playwright Full-Stack Test Suite

**Status:** Draft
**Total Points:** 19
**Path:** `/admin/ui/dead-letters`
**Slug:** `dead-letters`

## Purpose

View events that failed after all retries — unrecoverable failures. Forensics and troubleshooting for systemic failures.

## Motivation

Dead-lettered events indicate systemic pipeline problems. Visibility into failure reasons and attempt counts is essential for root cause analysis.

## APIs Under Test

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/ui/partials/dead-letters` | Dead-letters list partial |
| GET | `/admin/ui/partials/dead-letter/{id}` | Dead-letter detail partial |
| DELETE | `/admin/ui/partials/dead-letter/{id}` | Delete dead-letter |

## Components

- Data table (event list)
- Failure reason badges / text
- Attempt count column
- Action buttons (Delete)
- Detail panel
- Empty state ("No dead-letter events")

## Stories

| Story | Title | Points |
|-------|-------|--------|
| 69.1 | Page Intent & Semantic Content | 3 |
| 69.2 | API Endpoint Verification | 3 |
| 69.3 | Style Guide Compliance | 5 |
| 69.4 | Interactive Elements | 3 |
| 69.5 | Accessibility WCAG 2.2 AA | 3 |
| 69.6 | Visual Snapshot Baseline | 2 |

## Intent Checks

- Event list table or "No dead-letter events" empty state
- Failure reason displayed for each event (reason, failure, error)
- Attempt count or retry info visible (attempt, retry, retries, count, tries)

## Accessibility Specifics

- Delete button is destructive variant
- Table has `scope` attributes
- Error content uses semantic markup

## Definition of Done

- [ ] All 6 stories complete and merged
- [ ] Playwright tests pass in CI
- [ ] No accessibility violations (axe-core clean)
- [ ] Visual snapshots committed as baselines
