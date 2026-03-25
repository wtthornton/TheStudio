# Epic 70 — Execution Planes: Playwright Full-Stack Test Suite

**Status:** Draft
**Total Points:** 19
**Path:** `/admin/ui/planes`
**Slug:** `planes`

## Purpose

Show distributed worker clusters, their health, repo assignments, allow registration of new planes, and pause/resume for maintenance.

## Motivation

Execution planes are the compute layer. Operators need to register, monitor, pause, and resume planes — broken controls mean uncontrolled capacity.

## APIs Under Test

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/ui/partials/planes` | Planes list partial |
| POST | `/admin/ui/partials/planes/register` | Register new plane |
| POST | `/admin/ui/partials/planes/{id}/pause` | Pause plane |
| POST | `/admin/ui/partials/planes/{id}/resume` | Resume plane |

## Components

- Summary cards (total / active counts)
- Data table (plane list)
- Status badges (active / paused / draining)
- Registration form
- Action buttons (Pause / Resume)
- Empty state

## Stories

| Story | Title | Points |
|-------|-------|--------|
| 70.1 | Page Intent & Semantic Content | 3 |
| 70.2 | API Endpoint Verification | 3 |
| 70.3 | Style Guide Compliance | 5 |
| 70.4 | Interactive Elements | 3 |
| 70.5 | Accessibility WCAG 2.2 AA | 3 |
| 70.6 | Visual Snapshot Baseline | 2 |

## Intent Checks

- Summary counts visible (total, active, planes, repos)
- Register plane form / capability available (form, input, button)
- Status indicators visible (active, paused, draining, health)
- Region information shown or accepted (region, default)

## Accessibility Specifics

- Registration form inputs have labels
- Status badges use text + color (not color alone)
- Action buttons have clear labels

## Definition of Done

- [ ] All 6 stories complete and merged
- [ ] Playwright tests pass in CI
- [ ] No accessibility violations (axe-core clean)
- [ ] Visual snapshots committed as baselines
