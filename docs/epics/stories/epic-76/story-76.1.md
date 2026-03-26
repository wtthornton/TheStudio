# Story 76.1 -- Fix Design Token Assertions

<!-- docsmcp:start:user-story -->

> **As a** test engineer, **I want** style tests to assert CSS tokens that actually exist in the deployed app, **so that** token assertion failures indicate real regressions, not mismatched names

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the 16 per-page style test files assert against CSS custom property names that actually exist in the deployed admin UI's `:root` block. Currently, many assertions reference token names that were drafted in the style guide but never shipped in `base.html`, causing cascading false failures across every page suite.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Extract the authoritative set of CSS custom properties from `src/admin/templates/base.html` (the `:root` block), then update the token registry in `tests/playwright/lib/style_assertions.py` to match. Propagate corrected token names into all 16 `test_*_style.py` files. After this story, every token assertion references a property that exists in the deployed stylesheet.

See [Epic 76](../../epic-76-playwright-test-calibration.md) for project context and failure baseline.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/base.html` (read-only reference for `:root` tokens)
- `tests/playwright/lib/style_assertions.py`
- `tests/playwright/test_dashboard_style.py`
- `tests/playwright/test_repos_style.py`
- `tests/playwright/test_workflows_style.py`
- `tests/playwright/test_audit_style.py`
- `tests/playwright/test_metrics_style.py`
- `tests/playwright/test_experts_style.py`
- `tests/playwright/test_tools_style.py`
- `tests/playwright/test_models_style.py`
- `tests/playwright/test_compliance_style.py`
- `tests/playwright/test_quarantine_style.py`
- `tests/playwright/test_dead_letters_style.py`
- `tests/playwright/test_planes_style.py`
- `tests/playwright/test_settings_style.py`
- `tests/playwright/test_cost_dashboard_style.py`
- `tests/playwright/test_portfolio_health_style.py`
- `tests/playwright/test_detail_pages_style.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Extract the complete set of CSS custom properties from the `:root` block in `src/admin/templates/base.html` and document them as the authoritative token list
- [ ] Update the `_PRIMITIVES` dict and any token-name constants in `tests/playwright/lib/style_assertions.py` to match the actual `:root` properties (`tests/playwright/lib/style_assertions.py`)
- [ ] Update `tests/playwright/test_dashboard_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_repos_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_workflows_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_audit_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_metrics_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_experts_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_tools_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_models_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_compliance_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_quarantine_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_dead_letters_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_planes_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_settings_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_cost_dashboard_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_portfolio_health_style.py` to use corrected token names
- [ ] Update `tests/playwright/test_detail_pages_style.py` to use corrected token names
- [ ] Run all 16 style test files and verify zero "token not registered" or "property not found" failures

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Every token name referenced in `style_assertions.py` corresponds to a CSS custom property that exists in `base.html` `:root`
- [ ] All 16 `test_*_style.py` files reference only tokens registered in `style_assertions.py`
- [ ] Zero "token not registered" or "property not found" failures across all style tests
- [ ] All style test suites pass (excluding tests that fail for reasons unrelated to token naming)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 76](../../epic-76-playwright-test-calibration.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_all_token_names_match_root_properties` -- Every token name in style_assertions.py exists as a CSS custom property in base.html :root
2. `test_ac2_style_tests_reference_registered_tokens` -- All 16 test files reference only tokens that are registered in the assertion library
3. `test_ac3_zero_token_not_registered_failures` -- Running the full style test suite produces zero "token not registered" errors
4. `test_ac4_style_suites_pass_all_pages` -- Each of the 16 page style test suites passes

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- The authoritative token source is the `:root` block in `base.html`, not the style guide document. The style guide may define aspirational tokens not yet shipped.
- Use `page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--token-name'))` to verify tokens exist at runtime.
- Some tokens may use fallback values via `var(--token, fallback)` -- the assertion library should handle this pattern.

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None (can start immediately, first in the calibration sequence after 76.4 and 76.3)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed and delivered independently
- [x] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Unblocks ~100+ style test failures across 16 pages
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
