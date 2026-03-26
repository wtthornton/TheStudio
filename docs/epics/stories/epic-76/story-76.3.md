# Story 76.3 -- Fix axe-core Integration

<!-- docsmcp:start:user-story -->

> **As a** test engineer, **I want** axe-core audit tests to parse results correctly, **so that** accessibility failures indicate real WCAG violations, not API errors

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the `run_axe_audit()` helper returns a structured result that callers can reliably inspect. Currently, tests crash with `AttributeError` because the return type does not match what the 16+ a11y test files expect (e.g., attempting to access `.violations` on a list, or `.passed` on a dict).

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Fix the `run_axe_audit()` function in `tests/playwright/lib/accessibility_helpers.py` so its return type is an object with `.violations`, `.passes`, and `.incomplete` attributes (or equivalent). Update all `test_*_a11y.py` files that call `run_axe_audit()` to use the corrected return shape. After this story, zero `AttributeError` exceptions occur in axe-core related tests.

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

- [ ] Read the current `run_axe_audit()` implementation in `tests/playwright/lib/accessibility_helpers.py` and identify the actual return type vs. what callers expect
- [ ] Fix `run_axe_audit()` to return a structured object (dataclass or named container) with `.violations`, `.passes`, and `.incomplete` attributes (`tests/playwright/lib/accessibility_helpers.py`)
- [ ] Update all `test_*_a11y.py` files to use the corrected return type (access `.violations` list, check `len(result.violations) == 0`, etc.)
- [ ] Run all 17 a11y test files and verify zero `AttributeError` exceptions in axe-core tests

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] `run_axe_audit()` returns an object with `.violations`, `.passes`, and `.incomplete` attributes
- [ ] Each attribute contains a list of axe-core result objects (dicts with `id`, `impact`, `nodes` keys)
- [ ] Zero `AttributeError` exceptions in any `test_*_a11y.py` file when calling `run_axe_audit()`
- [ ] Tests that previously crashed now either pass (no violations) or fail with a meaningful assertion message listing the actual violations

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 76](../../epic-76-playwright-test-calibration.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_run_axe_audit_returns_structured_object` -- run_axe_audit() return value has .violations, .passes, .incomplete attributes
2. `test_ac2_violations_contain_axe_result_objects` -- Each violation in .violations has id, impact, and nodes keys
3. `test_ac3_zero_attribute_errors_in_a11y_tests` -- Running all a11y test files produces zero AttributeError exceptions
4. `test_ac4_meaningful_failure_messages` -- A genuine axe violation produces an assertion message that includes the violation id and impact

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- axe-core's `axe.run()` returns a result object with shape `{ violations: [...], passes: [...], incomplete: [...], inapplicable: [...] }`. Each entry has `id`, `impact` (minor/moderate/serious/critical), `description`, `help`, `helpUrl`, `tags`, and `nodes` (array of affected DOM elements).
- The `AccessibilityResult` dataclass already exists in the helpers module -- consider extending it or creating a parallel `AxeAuditResult` dataclass.
- CDN injection of axe-core may fail if the page has a Content-Security-Policy -- add a fallback or document the CSP requirement.

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None (can start immediately, independent of token/typography fixes)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed and delivered independently
- [x] **N**egotiable -- Return type shape can be refined during implementation
- [x] **V**aluable -- Unblocks axe-core assertions across 17 a11y test files
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
