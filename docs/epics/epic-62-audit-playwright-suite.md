# Epic 62 — Audit Log: Playwright Full-Stack Test Suite

**Status:** Proposed
**Priority:** P1 — High
**Estimated LoE:** ~3–4 days (1 developer)
**Dependencies:** Epic 58 (Playwright Test Infrastructure)

---

## Purpose & Intent

We are doing this so that the Audit Log page (`/admin/ui/audit`) is comprehensively validated by Playwright — verifying page intent, backing API endpoints, style guide compliance, interactive elements, WCAG 2.2 AA accessibility, and establishing a visual snapshot baseline.

## Goal

Deliver a complete Playwright test suite for the Audit Log page that validates it delivers its intended purpose, its backing APIs return correct data, it conforms to the UI/UX style guide, all interactive elements function correctly, it meets accessibility standards, and a visual regression baseline is captured.

## Motivation

Audit logs are the legal record of admin actions. If filtering is broken or events are missing, compliance audits fail and forensic investigations are blind. This page must reliably display governance events with correct time-range filtering, event type display, and actor/target columns.

## Acceptance Criteria

- [ ] Page intent validated: events table or empty state shown, event type references visible (registered, updated, changed, paused, resumed), time-range filtering available (1h, 6h, 24h, 7d), actor and target columns visible
- [ ] All backing API endpoints return 200 with valid JSON
- [ ] Style guide compliance: colors, typography, spacing, components match `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
- [ ] All buttons, forms, and interactive elements function correctly
- [ ] WCAG 2.2 AA: focus indicators, keyboard navigation, ARIA roles, contrast ratios
- [ ] Visual snapshot baseline captured and committed
- [ ] Zero console errors during all test execution

## Stories

| # | Story | Points | File |
|---|-------|--------|------|
| 62.1 | [Page Intent & Semantic Content](stories/epic-62/62.1-page-intent.md) | 3 | `tests/playwright/test_audit_intent.py` |
| 62.2 | [API Endpoint Verification](stories/epic-62/62.2-api-verification.md) | 3 | `tests/playwright/test_audit_api.py` |
| 62.3 | [Style Guide Compliance](stories/epic-62/62.3-style-guide-compliance.md) | 5 | `tests/playwright/test_audit_style.py` |
| 62.4 | [Interactive Elements](stories/epic-62/62.4-interactive-elements.md) | 3 | `tests/playwright/test_audit_interactions.py` |
| 62.5 | [Accessibility (WCAG 2.2 AA)](stories/epic-62/62.5-accessibility.md) | 3 | `tests/playwright/test_audit_a11y.py` |
| 62.6 | [Visual Snapshot Baseline](stories/epic-62/62.6-visual-snapshot.md) | 2 | `tests/playwright/test_audit_snapshot.py` |

**Total:** 19 points
