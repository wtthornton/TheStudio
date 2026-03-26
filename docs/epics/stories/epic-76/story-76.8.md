# Story 76.8 -- Validation Run

<!-- docsmcp:start:user-story -->

> **As a** test engineer, **I want** the full Playwright suite at >= 95% pass rate, **so that** the test suite is a reliable quality gate for all future UI changes

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the calibration work from stories 76.1--76.7 is validated end-to-end with a full suite run. The validation confirms that the pass rate target is met, documents any remaining genuine failures, and updates the baseline in the Playwright guide. This is the final gate before declaring Epic 76 complete.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Run the full Playwright test suite against the deployed admin UI. Triage any remaining failures to determine whether they are genuine app bugs (document them), remaining test calibration issues (fix them), or environment-specific flakes (mark them). Update the baseline statistics in `docs/testing/playwright-guide.md`. The target is >= 95% pass rate with zero `TypeError` or `AttributeError` exceptions in the test output.

See [Epic 76](../../epic-76-playwright-test-calibration.md) for project context and failure baseline.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `tests/playwright/` (full test suite -- all test files)
- `docs/testing/playwright-guide.md` (update baseline statistics)
- `docs/epics/epic-76-playwright-test-calibration.md` (update baseline table with final results)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Run the full Playwright test suite: `pytest tests/playwright/ --tb=short -q` and capture the output
- [ ] Calculate the pass rate: passed / (passed + failed) -- skips excluded from the denominator
- [ ] Triage each remaining failure into one of three categories: genuine app bug, remaining calibration issue, or environment flake
- [ ] Fix any remaining calibration issues discovered during triage (if fewer than 5 tests)
- [ ] Document genuine app bugs as follow-up items (not in scope to fix in this epic unless trivial)
- [ ] Update the baseline statistics table in `docs/testing/playwright-guide.md` with the post-calibration numbers
- [ ] Update the baseline table in `docs/epics/epic-76-playwright-test-calibration.md` with final results
- [ ] Commit all changes from Epic 76 and push

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Full suite pass rate is >= 95% (skips excluded from denominator)
- [ ] Zero `TypeError` or `AttributeError` exceptions in the test output
- [ ] Any remaining failures are documented with their category (app bug, calibration, flake)
- [ ] `docs/testing/playwright-guide.md` baseline statistics are updated to reflect the post-calibration state
- [ ] Epic 76 baseline table is updated with final pass/fail/skip counts

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 76](../../epic-76-playwright-test-calibration.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_pass_rate_above_95_percent` -- Full suite run produces >= 95% pass rate (skips excluded)
2. `test_ac2_zero_type_error_attribute_error` -- grep of test output shows zero TypeError and zero AttributeError
3. `test_ac3_remaining_failures_documented` -- Every remaining failure has a documented triage category
4. `test_ac4_playwright_guide_baseline_updated` -- playwright-guide.md contains updated pass/fail/skip numbers matching the latest run
5. `test_ac5_epic_baseline_table_updated` -- Epic 76 markdown contains a final results row in the baseline table

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Run tests with `--tb=short` for compact failure output and `-q` for summary counts.
- The 549 skipped tests from the baseline are expected -- they skip on empty data conditions and should remain stable.
- If the pass rate is between 90-95%, evaluate whether the remaining failures are worth an additional calibration pass or should be deferred.
- Environment flakes (network timeouts, CDN failures for axe-core) should be marked with `@pytest.mark.flaky` if they recur.
- The validation run is the epic's final gate -- do not mark Epic 76 as complete until this story passes.

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Stories 76.1 through 76.7 (all calibration work must be complete before the validation run)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Validates the aggregate result of all prior stories
- [x] **N**egotiable -- Triage thresholds can be adjusted during implementation
- [x] **V**aluable -- Proves the test suite is reliable and establishes the new baseline
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within a single session
- [x] **T**estable -- Has a clear numeric pass/fail gate (>= 95%)

<!-- docsmcp:end:invest -->
