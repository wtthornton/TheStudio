# Epic 61 — Workflow Console: Playwright Full-Stack Test Suite

**Status:** Proposed
**Priority:** P1 — High
**Estimated LoE:** ~3–4 days (1 developer)
**Dependencies:** Epic 58 (Playwright Test Infrastructure)

---

## Purpose & Intent

We are doing this so that the Workflow Console page (`/admin/ui/workflows`) is comprehensively validated by Playwright — verifying page intent, backing API endpoints, style guide compliance, interactive elements, WCAG 2.2 AA accessibility, and establishing a visual snapshot baseline.

## Goal

Deliver a complete Playwright test suite for the Workflow Console page that validates it delivers its intended purpose, its backing APIs return correct data, it conforms to the UI/UX style guide, all interactive elements function correctly, it meets accessibility standards, and a visual regression baseline is captured.

## Motivation

Operators need real-time visibility into pipeline execution to detect stuck or failed workflows and take action. A broken workflow console means blind spots in production — operators cannot see what the system is doing, cannot identify stuck jobs, and cannot intervene before SLA breaches.

## Acceptance Criteria

- [ ] Page intent validated: status filter is present and functional, status labels (running, completed, failed, stuck) are referenced, workflow list table or empty state is shown, workflow entries show pipeline stage and duration
- [ ] All backing API endpoints return 200 with valid JSON
- [ ] Style guide compliance: colors, typography, spacing, components match `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
- [ ] All buttons, forms, and interactive elements function correctly
- [ ] WCAG 2.2 AA: focus indicators, keyboard navigation, ARIA roles, contrast ratios
- [ ] Visual snapshot baseline captured and committed
- [ ] Zero console errors during all test execution

## Stories

| # | Story | Points | File |
|---|-------|--------|------|
| 61.1 | [Page Intent & Semantic Content](stories/epic-61/61.1-page-intent.md) | 3 | `tests/playwright/test_workflows_intent.py` |
| 61.2 | [API Endpoint Verification](stories/epic-61/61.2-api-verification.md) | 3 | `tests/playwright/test_workflows_api.py` |
| 61.3 | [Style Guide Compliance](stories/epic-61/61.3-style-guide-compliance.md) | 5 | `tests/playwright/test_workflows_style.py` |
| 61.4 | [Interactive Elements](stories/epic-61/61.4-interactive-elements.md) | 3 | `tests/playwright/test_workflows_interactions.py` |
| 61.5 | [Accessibility (WCAG 2.2 AA)](stories/epic-61/61.5-accessibility.md) | 3 | `tests/playwright/test_workflows_a11y.py` |
| 61.6 | [Visual Snapshot Baseline](stories/epic-61/61.6-visual-snapshot.md) | 2 | `tests/playwright/test_workflows_snapshot.py` |

**Total:** 19 points
