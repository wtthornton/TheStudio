# Epic 76: Playwright Test Calibration — Fix 390 Failures Against Deployed System

<!-- docsmcp:start:metadata -->
**Status:** Proposed
**Priority:** P1 - High
**Estimated LOE:** ~1-2 weeks (1 developer)
**Dependencies:** Epics 58-74 (test infrastructure and per-page suites)

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that the Playwright test suite (Epics 59-74) produces reliable, actionable results against the deployed system. Currently 392 tests fail due to test calibration issues — assertions that don't match actual CSS token names, API response shapes, or shared helper function signatures. These are not app bugs; they are test bugs that mask real regressions and erode trust in the test suite.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Bring the Playwright test suite from 77% pass rate (1,291 passed / 392 failed / 549 skipped) to 95%+ pass rate by fixing test calibration across 6 failure categories. Remaining failures should be genuine app bugs, not test code defects.

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

A test suite that fails 392 out of 2,200 tests is noise, not signal. Developers and Ralph cannot trust it to catch real regressions. The failures are concentrated in a few systematic categories (design token names, typography values, axe-core API misuse, helper signatures) that can be fixed in bulk. Once calibrated, the suite becomes a reliable quality gate for every future UI change.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Design token assertions use actual CSS custom property names from base.html :root
- [ ] Typography assertions match actual computed font values from the deployed pages
- [ ] axe-core integration returns parseable results with .violations attribute
- [ ] assert_focus_visible() function signature matches accessibility_helpers.py definition
- [ ] Kanban and view-toggle tests handle initial page state correctly
- [ ] Tools API tests match actual endpoint response schema
- [ ] Full suite pass rate >= 95% (skips excluded from denominator)
- [ ] Zero test-code TypeErrors or AttributeErrors in the failure output

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### [76.1 — Fix Design Token Assertions](stories/epic-76/story-76.1.md)

**Points:** 5 | Align CSS custom property names in all 16 page style test files with actual :root tokens.

### [76.2 — Fix Typography Assertions](stories/epic-76/story-76.2.md)

**Points:** 5 | Calibrate font-size, font-weight, font-family assertions to actual computed browser values.

### [76.3 — Fix axe-core Integration](stories/epic-76/story-76.3.md)

**Points:** 3 | Fix run_axe_audit() return type and update all a11y test files to parse results correctly.

### [76.4 — Fix assert_focus_visible() Signature](stories/epic-76/story-76.4.md)

**Points:** 2 | Align function signature with all callers across 16 a11y test files.

### [76.5 — Fix Kanban and View-Toggle Tests](stories/epic-76/story-76.5.md)

**Points:** 3 | Handle initial page state (list view default) in workflow kanban/toggle tests.

### [76.6 — Fix Tools API Tests](stories/epic-76/story-76.6.md)

**Points:** 2 | Match endpoint URLs and response schema to actual admin API.

### [76.7 — Fix Real Accessibility Bugs](stories/epic-76/story-76.7.md)

**Points:** 3 | Fix genuine a11y issues in templates (missing table captions, ARIA labels).

### [76.8 — Validation Run](stories/epic-76/story-76.8.md)

**Points:** 2 | Full suite run targeting >= 95% pass rate, document remaining genuine failures.

<!-- docsmcp:end:stories -->

**Total:** 25 points

<!-- docsmcp:start:implementation-order -->
## Implementation Order

1. 76.4 Fix assert_focus_visible() — quickest fix, unblocks a11y tests
2. 76.3 Fix axe-core integration — unblocks a11y tests
3. 76.1 Fix design token assertions — highest failure count
4. 76.2 Fix typography assertions — second highest failure count
5. 76.6 Fix tools API tests — isolated to one page
6. 76.5 Fix kanban/toggle tests — isolated to workflows page
7. 76.7 Fix real a11y bugs — template changes
8. 76.8 Validation run — final gate

<!-- docsmcp:end:implementation-order -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- All fixes are in test code (tests/playwright/) or shared libs (tests/playwright/lib/) unless a genuine a11y bug is found in templates
- Token names must be read from the actual deployed :root CSS not from the style guide document
- Typography values must be captured from computed styles via page.evaluate(getComputedStyle) not assumed from Tailwind classes
- axe-core returns an array of violation objects with id/impact/nodes — not a single object with .passed
- The 549 skipped tests are expected — they skip on empty data conditions and are not failures
- See `docs/testing/playwright-guide.md` for how to run tests

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope

- Fixing visual snapshot baseline differences (platform-dependent)
- Adding new test coverage beyond what Epics 59-74 defined
- Refactoring the shared test libraries beyond fixing the API mismatches
- Addressing the 549 skipped tests (they correctly skip when data is absent)

<!-- docsmcp:end:non-goals -->

## Baseline (2026-03-26)

| Metric | Value |
|--------|-------|
| Passed | 1,291 |
| Failed | 392 |
| Skipped | 549 |
| Pass rate (non-skipped) | 77% |
| Target pass rate | >= 95% |

## References

- `docs/testing/playwright-guide.md` — How to run Playwright tests
- `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` — Canonical style guide
- `tests/playwright/lib/` — Shared assertion libraries (Epic 58)
