# Epic 60 — Repo Management: Playwright Full-Stack Test Suite

**Status:** Proposed
**Priority:** P1 — High
**Estimated LoE:** ~3–4 days (1 developer)
**Dependencies:** Epic 58 (Playwright Test Infrastructure)

---

## Purpose & Intent

We are doing this so that the Repo Management page (`/admin/ui/repos`) is comprehensively validated by Playwright — verifying page intent, backing API endpoints, style guide compliance, interactive elements, WCAG 2.2 AA accessibility, and establishing a visual snapshot baseline.

## Goal

Deliver a complete Playwright test suite for the Repo Management page that validates it delivers its intended purpose, its backing APIs return correct data, it conforms to the UI/UX style guide, all interactive elements function correctly, it meets accessibility standards, and a visual regression baseline is captured.

## Motivation

Repos are the fundamental unit of work in TheStudio. Registration errors or broken controls block the entire pipeline. If an operator cannot register a repo, view its tier status, or pause/resume processing, the platform is effectively non-functional. This page must be rock-solid.

## Acceptance Criteria

- [ ] Page intent validated: "Register Repo" button or form is accessible, repo list table shows repos or empty state with guidance, tier badges (shadow/probation/trusted) displayed with correct colors, status indicators (active/paused) visible
- [ ] All backing API endpoints return 200 with valid JSON
- [ ] Style guide compliance: colors, typography, spacing, components match `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
- [ ] All buttons, forms, and interactive elements function correctly
- [ ] WCAG 2.2 AA: focus indicators, keyboard navigation, ARIA roles, contrast ratios
- [ ] Visual snapshot baseline captured and committed
- [ ] Zero console errors during all test execution

## Stories

| # | Story | Points | File |
|---|-------|--------|------|
| 60.1 | [Page Intent & Semantic Content](stories/epic-60/60.1-page-intent.md) | 3 | `tests/playwright/test_repos_intent.py` |
| 60.2 | [API Endpoint Verification](stories/epic-60/60.2-api-verification.md) | 3 | `tests/playwright/test_repos_api.py` |
| 60.3 | [Style Guide Compliance](stories/epic-60/60.3-style-guide-compliance.md) | 5 | `tests/playwright/test_repos_style.py` |
| 60.4 | [Interactive Elements](stories/epic-60/60.4-interactive-elements.md) | 3 | `tests/playwright/test_repos_interactions.py` |
| 60.5 | [Accessibility (WCAG 2.2 AA)](stories/epic-60/60.5-accessibility.md) | 3 | `tests/playwright/test_repos_a11y.py` |
| 60.6 | [Visual Snapshot Baseline](stories/epic-60/60.6-visual-snapshot.md) | 2 | `tests/playwright/test_repos_snapshot.py` |

**Total:** 19 points
