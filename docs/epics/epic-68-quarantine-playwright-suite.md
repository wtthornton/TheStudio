# Epic 68 — Quarantine: Playwright Full-Stack Test Suite

**Status:** Draft
**Total Points:** 19
**Path:** `/admin/ui/quarantine`
**Slug:** `quarantine`

## Purpose

View quarantined events that failed gates, examine failure reason, replay or delete. Critical for post-mortem and recovery.

## Motivation

Quarantined events represent pipeline failures. If operators can't see, filter, or replay them, failures accumulate silently and recovery is impossible.

## APIs Under Test

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/ui/partials/quarantine` | Quarantine list partial |
| GET | `/admin/ui/partials/quarantine/{id}` | Quarantine detail partial |
| POST | `/admin/ui/partials/quarantine/{id}/replay` | Replay action |
| DELETE | `/admin/ui/partials/quarantine/{id}` | Delete action |

## Components

- Data table (event list)
- Status badges (pending / replayed / corrected)
- Filter controls (failure reason)
- Action buttons (Replay, Delete)
- Empty state ("No quarantined events")

## Stories

| Story | Title | Points |
|-------|-------|--------|
| 68.1 | Page Intent & Semantic Content | 3 |
| 68.2 | API Endpoint Verification | 3 |
| 68.3 | Style Guide Compliance | 5 |
| 68.4 | Interactive Elements | 3 |
| 68.5 | Accessibility WCAG 2.2 AA | 3 |
| 68.6 | Visual Snapshot Baseline | 2 |

## Intent Checks

- Failure reason filtering available (select or text filter)
- Event list table or "No quarantined events" empty state
- Status vocabulary: pending, replayed, corrected, reason, quarantine, status

## Accessibility Specifics

- Destructive Delete button is red (destructive variant)
- Action buttons have clear labels
- Table has `scope` attributes
- Filter has associated label

## Definition of Done

- [ ] All 6 stories complete and merged
- [ ] Playwright tests pass in CI
- [ ] No accessibility violations (axe-core clean)
- [ ] Visual snapshots committed as baselines
