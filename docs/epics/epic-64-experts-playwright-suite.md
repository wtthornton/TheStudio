# Epic 64 — Expert Performance: Playwright Full-Stack Test Suite

**Status:** Proposed
**Priority:** P1 — High
**Estimated LoE:** ~3–4 days (1 developer)
**Dependencies:** Epic 58 (Playwright Test Infrastructure)

---

## Purpose & Intent

We are doing this so that the Expert Performance page (`/admin/ui/experts`) is comprehensively validated by Playwright — verifying page intent, backing API endpoints, style guide compliance, interactive elements, WCAG 2.2 AA accessibility, and establishing a visual snapshot baseline.

## Goal

Deliver a complete Playwright test suite for the Expert Performance page that validates it delivers its intended purpose, its backing APIs return correct data, it conforms to the UI/UX style guide, all interactive elements function correctly, it meets accessibility standards, and a visual regression baseline is captured.

## Motivation

Expert selection directly controls code quality. If trust tiers or drift signals are wrong, bad experts get promoted and good ones get suppressed. This page must accurately display the AI expert roster with trust tiers, confidence scores, and drift signals for tuning expert selection.

## Acceptance Criteria

- [ ] Page intent validated: trust tier labels visible (shadow, probation, trusted), performance metric columns shown (confidence, weight, drift, score), expert filtering available, expert list table or empty state shown
- [ ] All backing API endpoints return 200 with valid JSON
- [ ] Style guide compliance: colors, typography, spacing, components match `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
- [ ] All buttons, forms, and interactive elements function correctly
- [ ] WCAG 2.2 AA: focus indicators, keyboard navigation, ARIA roles, contrast ratios
- [ ] Visual snapshot baseline captured and committed
- [ ] Zero console errors during all test execution

## Stories

| # | Story | Points | File |
|---|-------|--------|------|
| 64.1 | [Page Intent & Semantic Content](stories/epic-64/64.1-page-intent.md) | 3 | `tests/playwright/test_experts_intent.py` |
| 64.2 | [API Endpoint Verification](stories/epic-64/64.2-api-verification.md) | 3 | `tests/playwright/test_experts_api.py` |
| 64.3 | [Style Guide Compliance](stories/epic-64/64.3-style-guide-compliance.md) | 5 | `tests/playwright/test_experts_style.py` |
| 64.4 | [Interactive Elements](stories/epic-64/64.4-interactive-elements.md) | 3 | `tests/playwright/test_experts_interactions.py` |
| 64.5 | [Accessibility (WCAG 2.2 AA)](stories/epic-64/64.5-accessibility.md) | 3 | `tests/playwright/test_experts_a11y.py` |
| 64.6 | [Visual Snapshot Baseline](stories/epic-64/64.6-visual-snapshot.md) | 2 | `tests/playwright/test_experts_snapshot.py` |

**Total:** 19 points
