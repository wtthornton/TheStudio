# Story 76.2 -- Fix Typography Assertions

<!-- docsmcp:start:user-story -->

> **As a** test engineer, **I want** typography assertions calibrated to actual rendered values, **so that** typography failures indicate real regressions, not calibration drift

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that typography assertions (font-family, font-size, font-weight) match the actual computed CSS values rendered by the browser, rather than idealized values from the style guide. Currently, tests fail because expected font-size values are off by a few pixels, font-family strings do not account for system fallbacks, and font-weight comparisons are overly strict.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Capture the actual computed typography values from each admin page by running `getComputedStyle()` against heading, title, body, and label elements. Update the type scale definitions and tolerance ranges in `tests/playwright/lib/typography_assertions.py` to match reality. Propagate fixes into all 16 `test_*_style.py` files that call typography assertion helpers. After this story, font assertions use contains-match for font-family and plus-or-minus 2px tolerance for font-size.

See [Epic 76](../../epic-76-playwright-test-calibration.md) for project context and failure baseline.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `tests/playwright/lib/typography_assertions.py`
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

- [ ] Write a diagnostic script or test that captures actual computed font-family, font-size, font-weight, and line-height for h1, h2, h3, body, label, caption, and code elements on the dashboard page via `page.evaluate(() => getComputedStyle(el))`
- [ ] Update the type scale definitions (`_TYPE_SCALE` or equivalent) in `tests/playwright/lib/typography_assertions.py` to reflect actual computed values
- [ ] Change font-family assertions to use contains-match (e.g., assert `"Inter"` appears in the computed font-family string) rather than exact-match (`tests/playwright/lib/typography_assertions.py`)
- [ ] Change font-size assertions to use a plus-or-minus 2px tolerance band rather than exact pixel values (`tests/playwright/lib/typography_assertions.py`)
- [ ] Update all 16 `test_*_style.py` files to use the corrected typography assertion calls
- [ ] Run all 16 style test suites and verify zero heading/title/body/label font assertion failures

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Typography assertions in `typography_assertions.py` match actual computed styles from the deployed admin UI
- [ ] Font-family assertions use contains-match (substring check for primary font name)
- [ ] Font-size assertions use a +/-2px tolerance band
- [ ] Zero heading, title, body, or label typography failures across all 16 page style test suites
- [ ] Font-weight assertions accept both numeric (400/500/600/700) and keyword (normal/medium/semibold/bold) equivalents

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 76](../../epic-76-playwright-test-calibration.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_typography_assertions_match_computed_styles` -- Type scale values in typography_assertions.py match actual getComputedStyle output
2. `test_ac2_font_family_uses_contains_match` -- Font-family assertions pass when computed value includes fallback fonts
3. `test_ac3_font_size_uses_tolerance_band` -- Font-size assertions pass when computed value is within +/-2px of expected
4. `test_ac4_zero_typography_failures_all_pages` -- All 16 page style suites produce zero typography-related failures
5. `test_ac5_font_weight_accepts_numeric_and_keyword` -- Font-weight assertions accept both "700" and "bold" for the same weight

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- `getComputedStyle()` returns the resolved font-family as a comma-separated string with system fallbacks (e.g., `"Inter", ui-sans-serif, system-ui, sans-serif`). The assertion must check that the primary font appears in this string.
- Computed font-size is always in pixels (e.g., `"16px"`) regardless of the CSS unit used in the stylesheet.
- Browser rounding can cause 1-2px differences between the CSS declaration and the computed value -- hence the tolerance band.
- Line-height may be a unitless ratio or a pixel value depending on how it is declared; the assertion should normalize to pixels for comparison.

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 76.1 (token names must be correct before typography can be validated)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed and delivered independently (after 76.1)
- [x] **N**egotiable -- Tolerance values can be adjusted during implementation
- [x] **V**aluable -- Unblocks ~80+ typography-related test failures
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
