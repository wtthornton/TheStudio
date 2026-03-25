# Epic 72 — Cost Dashboard: Playwright Full-Stack Test Suite

**Status:** Draft
**Total Points:** 19
**Path:** `/admin/ui/cost-dashboard`
**Slug:** `cost-dashboard`

## Purpose

Model spend visualization, budget utilization tracking, cost breakdown by provider/model/stage.

## Motivation

LLM costs are the largest variable expense. Without cost visibility, budgets blow out silently. This page is currently NOT in the Playwright test rig — zero coverage.

## APIs Under Test

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/ui/partials/cost-dashboard` | Cost dashboard content |
| GET | `/admin/ui/partials/model-spend` | Model spend data |
| GET | `/admin/ui/partials/budget-utilization` | Budget utilization |
| GET | `/admin/models/providers` | Provider list with cost info |
| GET | `/admin/models/audit` | Model usage audit trail |

## Components

- KPI cards (total spend, budget remaining, utilization percentage)
- Charts/bars (budget utilization visualization)
- Provider breakdown table (Anthropic, OpenAI, etc.)
- Model usage table (per-model cost and call counts)
- Time range selector
- Provider filter
- Empty state

## Stories

| Story | Title | Points |
|-------|-------|--------|
| 72.1 | Page Intent & Semantic Content | 3 |
| 72.2 | API Endpoint Verification | 3 |
| 72.3 | Style Guide Compliance | 5 |
| 72.4 | Interactive Elements | 3 |
| 72.5 | Accessibility WCAG 2.2 AA | 3 |
| 72.6 | Visual Snapshot Baseline | 2 |

## Intent Checks

- Cost/spend data visible ($ amounts or cost metrics)
- Budget utilization shown (percentage or bar)
- Provider breakdown visible (Anthropic, OpenAI, etc.)
- Model usage breakdown visible

## Accessibility Specifics

- Currency values formatted with `font-mono` for readability
- Charts have text alternatives (aria-label or visible legend)
- Progress bars have `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- Tables have `scope` attributes on headers

## Definition of Done

- [ ] All 6 stories complete and merged
- [ ] Playwright tests pass in CI
- [ ] No accessibility violations (axe-core clean)
- [ ] Visual snapshots committed as baselines
