# Story 76.4 -- Fix assert_focus_visible() Signature

<!-- docsmcp:start:user-story -->

> **As a** test engineer, **I want** `assert_focus_visible()` to work when called from any test file, **so that** focus tests detect missing focus rings instead of crashing with TypeError

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the `assert_focus_visible()` function signature in `accessibility_helpers.py` matches how it is called across all 16+ a11y test files. Currently, callers pass arguments that do not match the function definition, causing `TypeError` exceptions that mask real focus-ring accessibility issues.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Read the actual `assert_focus_visible()` definition in `tests/playwright/lib/accessibility_helpers.py`, compare it against every call site in the `test_*_a11y.py` files, and align them. Either update the function signature to accept the arguments callers provide, or update all callers to match the existing signature -- whichever requires fewer changes and produces a cleaner API. After this story, zero `TypeError` exceptions occur in focus-visibility tests.

See [Epic 76](../../epic-76-playwright-test-calibration.md) for project context and failure baseline.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `tests/playwright/lib/accessibility_helpers.py`
- `tests/playwright/test_dashboard_a11y.py`
- `tests/playwright/test_repos_a11y.py`
- `tests/playwright/test_workflows_a11y.py`
- `tests/playwright/test_audit_a11y.py`
- `tests/playwright/test_metrics_a11y.py`
- `tests/playwright/test_experts_a11y.py`
- `tests/playwright/test_tools_a11y.py`
- `tests/playwright/test_models_a11y.py`
- `tests/playwright/test_compliance_a11y.py`
- `tests/playwright/test_quarantine_a11y.py`
- `tests/playwright/test_dead_letters_a11y.py`
- `tests/playwright/test_planes_a11y.py`
- `tests/playwright/test_settings_a11y.py`
- `tests/playwright/test_cost_dashboard_a11y.py`
- `tests/playwright/test_portfolio_health_a11y.py`
- `tests/playwright/test_detail_pages_a11y.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read the `assert_focus_visible()` definition in `tests/playwright/lib/accessibility_helpers.py` and document its current parameter list
- [ ] Grep all `test_*_a11y.py` files for calls to `assert_focus_visible` and document every distinct call signature used
- [ ] Decide whether to update the function definition or the callers (prefer whichever minimizes changes)
- [ ] Apply the fix -- update the function signature and/or all call sites to be consistent (`tests/playwright/lib/accessibility_helpers.py`, `tests/playwright/test_*_a11y.py`)
- [ ] Run all a11y test files and verify zero `TypeError` exceptions in focus-visibility tests

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] `assert_focus_visible()` has a single, consistent signature in `accessibility_helpers.py`
- [ ] Every call to `assert_focus_visible()` across all `test_*_a11y.py` files matches the function signature
- [ ] Zero `TypeError` exceptions when running focus-visibility tests
- [ ] Focus tests verify that interactive elements display a visible focus ring (2px solid outline or equivalent CSS)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 76](../../epic-76-playwright-test-calibration.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_assert_focus_visible_consistent_signature` -- assert_focus_visible() accepts the same parameters from every caller
2. `test_ac2_zero_type_errors_in_focus_tests` -- Running all a11y tests produces zero TypeError on assert_focus_visible calls
3. `test_ac3_focus_ring_css_verified` -- Focus tests confirm a visible focus ring (outline-style, outline-width, or box-shadow) on interactive elements

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- The function should accept a Playwright `Page` object and optionally a CSS selector to scope the check. If callers pass additional arguments (e.g., expected ring color, ring width), make them optional keyword arguments with sensible defaults.
- Focus ring detection should check for `outline`, `outline-offset`, or `box-shadow` properties on `:focus-visible` pseudo-class elements.
- This is the quickest fix in the epic and unblocks a11y test triage for stories 76.3 and 76.7.

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None (first story to implement per the epic's implementation order)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed and delivered independently
- [x] **N**egotiable -- Signature design can be refined during implementation
- [x] **V**aluable -- Unblocks focus-visibility assertions across 16+ test files
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within a single session
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
