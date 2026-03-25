# Epic 58 — Playwright Test Infrastructure & Visual Snapshot Framework

**Status:** **COMPLETE** (2026-03-25) — All 7 stories (58.1–58.7) delivered
**Priority:** P0 — Critical
**Estimated LoE:** ~1 week (1 developer)
**Dependencies:** Epic 12 (original Playwright test rig)
**Blocks:** Epics 59–74 (all per-page test suites)

---

## Purpose & Intent

We are doing this so that all subsequent per-page Playwright test epics (59–74) share a common, battle-tested foundation for style-guide compliance checks, API endpoint verification, interactive element testing, accessibility auditing, and Playwright visual snapshot baselines — eliminating duplication and ensuring consistent quality gates across every Admin UI page.

## Goal

Build shared Playwright test infrastructure: reusable fixtures for style-guide color/typography/spacing assertions, API response verification helpers, interactive element test utilities, WCAG 2.2 AA accessibility checks, and a visual snapshot baseline framework that captures and compares page screenshots.

## Motivation

The existing Playwright test rig validates page intent and rendering quality but lacks style-guide compliance checks, API verification, interactive element testing, accessibility auditing, and visual regression baselines. Every page epic (59–74) will depend on these shared utilities.

## Acceptance Criteria

- [x] Style-guide color assertion helper validates semantic token colors (status success/warning/error/info/neutral) against `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` Section 5
- [x] Typography assertion helper validates font family (Inter / JetBrains Mono) and size scale per Section 6
- [x] Spacing assertion helper validates 4px base-unit grid per Section 7
- [x] Component recipe validators for cards, tables, badges, buttons, forms per Section 9
- [x] API endpoint verification helper: call endpoint, assert status + JSON schema
- [x] Interactive element tester: click buttons, verify response / state change / HTMX swap
- [x] WCAG 2.2 AA accessibility checker: contrast ratios, focus indicators, ARIA roles, keyboard navigation
- [x] Visual snapshot framework: capture full-page screenshot, compare against baseline with configurable threshold
- [x] Snapshot storage in `tests/playwright/snapshots/` with platform-aware naming
- [x] All helpers importable from `tests/playwright/lib/` and documented with docstrings
- [x] CI-compatible: snapshots auto-update on first run, fail on diff above threshold

## Stories

| # | Story | Points | File |
|---|-------|--------|------|
| 58.1 | [Style Guide Color & Token Assertion Library](stories/epic-58/58.1-style-guide-color-assertions.md) | 5 | `tests/playwright/lib/style_assertions.py` |
| 58.2 | [Typography & Spacing Assertion Library](stories/epic-58/58.2-typography-spacing-assertions.md) | 3 | `tests/playwright/lib/typography_assertions.py` |
| 58.3 | [Component Recipe Validators](stories/epic-58/58.3-component-recipe-validators.md) | 5 | `tests/playwright/lib/component_validators.py` |
| 58.4 | [API Endpoint Verification Helper](stories/epic-58/58.4-api-endpoint-verification.md) | 3 | `tests/playwright/lib/api_helpers.py` |
| 58.5 | [Interactive Element Test Utilities](stories/epic-58/58.5-interactive-element-utilities.md) | 3 | `tests/playwright/lib/interaction_helpers.py` |
| 58.6 | [WCAG 2.2 AA Accessibility Checker](stories/epic-58/58.6-accessibility-checker.md) | 5 | `tests/playwright/lib/accessibility_helpers.py` |
| 58.7 | [Visual Snapshot Baseline Framework](stories/epic-58/58.7-visual-snapshot-framework.md) | 5 | `tests/playwright/lib/snapshot_helpers.py` |

**Total:** 29 points

## Technical Notes

- All helpers must work with pytest-playwright (not @playwright/test)
- Style guide reference: `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
- Color extraction uses `page.evaluate()` to get `getComputedStyle()` values
- axe-core integration via inline script injection for accessibility checks
- Snapshots use Playwright `expect(page).to_have_screenshot()` with `maxDiffPixelRatio`
- Visual snapshots require consistent viewport (1280×720) and font rendering
- All helpers importable from `tests/playwright/lib/__init__.py`

## Non-Goals

- Testing React SPA Dashboard (separate epic scope)
- Implementing fixes for style guide violations (test-only epic)
- Dark theme testing beyond token validation
- Performance / load testing
- Mobile responsive testing beyond basic viewport checks

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Snapshot flakiness across platforms | High | Platform-aware naming, configurable threshold |
| axe-core version drift | Medium | Pin version, document update procedure |
| Style guide changes invalidate assertions | Medium | Assertion helpers read from style guide tokens, not hardcoded values |
