# Epic 74 — Detail Pages (Repo/Workflow/Expert): Playwright Full-Stack Test Suite

**Status:** Draft
**Total Points:** 19
**Paths:**
- `/admin/ui/repos/{repo_id}` — Repo Detail
- `/admin/ui/workflows/{workflow_id}` — Workflow Detail
- `/admin/ui/experts/{expert_id}` — Expert Detail
**Slug:** `detail-pages`

## Purpose

Individual entity detail views showing full configuration, history, actions, and related data for a specific repo, workflow, or expert.

## Motivation

Detail pages are where operators take action — changing tier, rerunning verification, viewing drift. If detail pages are broken, operators lose control of individual entities.

## APIs Under Test

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/repos/{id}` | Repo detail |
| PATCH | `/admin/repos/{id}/profile` | Update profile |
| PATCH | `/admin/repos/{id}/tier` | Change tier |
| POST | `/admin/repos/{id}/pause` | Pause repo |
| POST | `/admin/repos/{id}/resume` | Resume repo |
| GET | `/admin/workflows/{id}` | Workflow detail |
| POST | `/admin/workflows/{id}/rerun-verification` | Rerun verification |
| POST | `/admin/workflows/{id}/escalate` | Escalate |
| GET | `/admin/experts/{id}` | Expert detail |
| GET | `/admin/experts/{id}/drift` | Drift analysis |
| GET | `/admin/ui/partials/repo/{id}` | Repo detail partial |
| GET | `/admin/ui/partials/workflow/{id}` | Workflow detail partial |
| GET | `/admin/ui/partials/expert/{id}` | Expert detail partial |
| GET | `/admin/ui/partials/merge-mode/{id}` | Merge mode controls |
| POST | `/admin/ui/partials/merge-mode/{id}` | Update merge mode |
| GET | `/admin/ui/partials/promotion-history/{id}` | Promotion history |

## Components

- Detail cards (entity summary, metadata)
- Config forms (tier change, merge mode, profile edit)
- Action buttons (Pause, Resume, Rerun, Escalate, Send-to-Agent)
- History tables (promotion history, workflow steps)
- Drift charts (expert drift analysis)
- Status badges (tier, health, pipeline stage)
- Empty state

## Stories

| Story | Title | Points |
|-------|-------|--------|
| 74.1 | Page Intent & Semantic Content | 3 |
| 74.2 | API Endpoint Verification | 3 |
| 74.3 | Style Guide Compliance | 5 |
| 74.4 | Interactive Elements | 3 |
| 74.5 | Accessibility WCAG 2.2 AA | 3 |
| 74.6 | Visual Snapshot Baseline | 2 |

## Intent Checks

- Repo detail: shows tier, status, config, merge mode, promotion history
- Workflow detail: shows pipeline stage, status, duration, action buttons (Rerun/Escalate/Send-to-Agent)
- Expert detail: shows trust tier, confidence, weight, drift analysis

## Accessibility Specifics

- All action buttons have descriptive labels
- Form inputs have associated labels
- Status badges are accessible (text + color, not color alone)
- Tables have `scope` attributes on headers

## Special Notes

Detail pages require seed data. Tests must either create entities first or use existing test fixtures. Test setup should handle the case where no entity exists by seeding a test entity before asserting detail page content.

## Definition of Done

- [ ] All 6 stories complete and merged
- [ ] Playwright tests pass in CI
- [ ] No accessibility violations (axe-core clean)
- [ ] Visual snapshots committed as baselines
