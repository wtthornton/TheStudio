# Epic 73 — Portfolio Health: Playwright Full-Stack Test Suite

**Status:** Draft
**Total Points:** 19
**Path:** `/admin/ui/portfolio-health`
**Slug:** `portfolio-health`

## Purpose

Cross-repo health overview showing aggregate health status, risk distribution, and per-repo health indicators across the portfolio.

## Motivation

Portfolio Health provides the big-picture view across all repos. Without it, operators must click through individual repos to find problems. This page is currently NOT in the Playwright test rig — zero coverage.

## APIs Under Test

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/ui/partials/portfolio-health` | Portfolio health content |
| GET | `/admin/repos` | Repo list |
| GET | `/admin/repos/health` | Repo health status |

## Components

- Summary cards (healthy/degraded/unhealthy counts)
- Repo health table (per-repo rows with status indicators)
- Risk distribution chart/badges (by tier or severity)
- Status indicators (healthy, degraded, unhealthy)
- Repo filter
- Health status filter
- Empty state

## Stories

| Story | Title | Points |
|-------|-------|--------|
| 73.1 | Page Intent & Semantic Content | 3 |
| 73.2 | API Endpoint Verification | 3 |
| 73.3 | Style Guide Compliance | 5 |
| 73.4 | Interactive Elements | 3 |
| 73.5 | Accessibility WCAG 2.2 AA | 3 |
| 73.6 | Visual Snapshot Baseline | 2 |

## Intent Checks

- Aggregate health status visible (healthy/degraded/unhealthy counts)
- Per-repo health indicators shown
- Risk distribution visible (by tier or severity)

## Accessibility Specifics

- Health status badges use text + color (not color alone)
- Summary numbers have descriptive labels
- Table has `scope` attributes on column headers
- Status indicators convey meaning without relying solely on color

## Definition of Done

- [ ] All 6 stories complete and merged
- [ ] Playwright tests pass in CI
- [ ] No accessibility violations (axe-core clean)
- [ ] Visual snapshots committed as baselines
