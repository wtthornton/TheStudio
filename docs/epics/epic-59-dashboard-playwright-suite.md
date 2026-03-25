# Epic 59 — Fleet Dashboard: Playwright Full-Stack Test Suite

**Status:** Proposed
**Priority:** P1 — High
**Estimated LoE:** ~3–4 days (1 developer)
**Dependencies:** Epic 58 (Playwright Test Infrastructure)

---

## Purpose & Intent

We are doing this so that the Fleet Dashboard page (`/admin/ui/dashboard`) is comprehensively validated by Playwright — verifying page intent, backing API endpoints, style guide compliance, interactive elements, WCAG 2.2 AA accessibility, and establishing a visual snapshot baseline.

## Goal

Deliver a complete Playwright test suite for the Fleet Dashboard page that validates it delivers its intended purpose, its backing APIs return correct data, it conforms to the UI/UX style guide, all interactive elements function correctly, it meets accessibility standards, and a visual regression baseline is captured.

## Motivation

The Dashboard is the operator's first screen — the single most important page for situational awareness. It must always show accurate health, metrics, and activity. Any regression on this page — broken health indicators, stale metrics, or a non-functional repo table — directly undermines operator confidence and delays incident response.

## Acceptance Criteria

- [ ] Page intent validated: system health section shows Temporal and Postgres with status indicators and latency, workflow summary shows Running/Stuck/Failed/Queue metrics, repo activity table shows repos or empty state
- [ ] All backing API endpoints return 200 with valid JSON
- [ ] Style guide compliance: colors, typography, spacing, components match `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
- [ ] All buttons, forms, and interactive elements function correctly
- [ ] WCAG 2.2 AA: focus indicators, keyboard navigation, ARIA roles, contrast ratios
- [ ] Visual snapshot baseline captured and committed
- [ ] Zero console errors during all test execution

## Stories

| # | Story | Points | File |
|---|-------|--------|------|
| 59.1 | [Page Intent & Semantic Content](stories/epic-59/59.1-page-intent.md) | 3 | `tests/playwright/test_dashboard_intent.py` |
| 59.2 | [API Endpoint Verification](stories/epic-59/59.2-api-verification.md) | 3 | `tests/playwright/test_dashboard_api.py` |
| 59.3 | [Style Guide Compliance](stories/epic-59/59.3-style-guide-compliance.md) | 5 | `tests/playwright/test_dashboard_style.py` |
| 59.4 | [Interactive Elements](stories/epic-59/59.4-interactive-elements.md) | 3 | `tests/playwright/test_dashboard_interactions.py` |
| 59.5 | [Accessibility (WCAG 2.2 AA)](stories/epic-59/59.5-accessibility.md) | 3 | `tests/playwright/test_dashboard_a11y.py` |
| 59.6 | [Visual Snapshot Baseline](stories/epic-59/59.6-visual-snapshot.md) | 2 | `tests/playwright/test_dashboard_snapshot.py` |

**Total:** 19 points
