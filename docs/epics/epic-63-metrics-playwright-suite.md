# Epic 63 — Metrics: Playwright Full-Stack Test Suite

**Status:** Proposed
**Priority:** P1 — High
**Estimated LoE:** ~3–4 days (1 developer)
**Dependencies:** Epic 58 (Playwright Test Infrastructure)

---

## Purpose & Intent

We are doing this so that the Metrics page (`/admin/ui/metrics`) is comprehensively validated by Playwright — verifying page intent, backing API endpoints, style guide compliance, interactive elements, WCAG 2.2 AA accessibility, and establishing a visual snapshot baseline.

## Goal

Deliver a complete Playwright test suite for the Metrics page that validates it delivers its intended purpose, its backing APIs return correct data, it conforms to the UI/UX style guide, all interactive elements function correctly, it meets accessibility standards, and a visual regression baseline is captured.

## Motivation

Metrics drive trust tier decisions and pipeline tuning. If success rates are wrong or gate status is missing, operators make bad decisions. This page must accurately display quality metrics including success rates, gate status, loopback breakdown, and reopen attribution with time window context.

## Acceptance Criteria

- [ ] Page intent validated: success rate shown with percentage, gate status shown (PASSING/FAILING/Insufficient), loopback breakdown visible, reopen rate with attribution visible, time window context (7d, 30d)
- [ ] All backing API endpoints return 200 with valid JSON
- [ ] Style guide compliance: colors, typography, spacing, components match `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
- [ ] All buttons, forms, and interactive elements function correctly
- [ ] WCAG 2.2 AA: focus indicators, keyboard navigation, ARIA roles, contrast ratios
- [ ] Visual snapshot baseline captured and committed
- [ ] Zero console errors during all test execution

## Stories

| # | Story | Points | File |
|---|-------|--------|------|
| 63.1 | [Page Intent & Semantic Content](stories/epic-63/63.1-page-intent.md) | 3 | `tests/playwright/test_metrics_intent.py` |
| 63.2 | [API Endpoint Verification](stories/epic-63/63.2-api-verification.md) | 3 | `tests/playwright/test_metrics_api.py` |
| 63.3 | [Style Guide Compliance](stories/epic-63/63.3-style-guide-compliance.md) | 5 | `tests/playwright/test_metrics_style.py` |
| 63.4 | [Interactive Elements](stories/epic-63/63.4-interactive-elements.md) | 3 | `tests/playwright/test_metrics_interactions.py` |
| 63.5 | [Accessibility (WCAG 2.2 AA)](stories/epic-63/63.5-accessibility.md) | 3 | `tests/playwright/test_metrics_a11y.py` |
| 63.6 | [Visual Snapshot Baseline](stories/epic-63/63.6-visual-snapshot.md) | 2 | `tests/playwright/test_metrics_snapshot.py` |

**Total:** 19 points
