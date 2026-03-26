# Story 76.5 -- Fix Kanban and View-Toggle Tests

<!-- docsmcp:start:user-story -->

> **As a** test engineer, **I want** workflow tests to work regardless of initial view state, **so that** kanban tests validate the board after toggling, not fail on missing elements

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that workflow page tests (style, interactions, API) handle the initial page state correctly. The workflows page defaults to list view, but kanban-related tests assume they start in board view. Tests also assume specific localStorage keys and API response field names that do not match the deployed system.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Fix workflow test files to explicitly click the view toggle before asserting kanban board elements, handle the default list-view state on page load, clear or set `localStorage` to ensure deterministic initial state, and update API response field assertions to match the actual JSON shape returned by the workflows endpoint.

See [Epic 76](../../epic-76-playwright-test-calibration.md) for project context and failure baseline.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `tests/playwright/test_workflows_style.py`
- `tests/playwright/test_workflows_interactions.py`
- `tests/playwright/test_workflows_api.py`
- `tests/playwright/test_workflows_intent.py`
- `src/admin/router.py` (read-only reference for actual endpoint response shape)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read `src/admin/router.py` to identify the actual workflows endpoint URL and response JSON shape (field names, nesting)
- [ ] Update `tests/playwright/test_workflows_api.py` to assert against the actual response field names and structure
- [ ] Update kanban-related tests in `tests/playwright/test_workflows_interactions.py` to click the view toggle button before asserting kanban column elements
- [ ] Add a test setup step that clears or sets `localStorage` to ensure the page loads in a known view state (list or board) (`tests/playwright/test_workflows_style.py`, `test_workflows_interactions.py`)
- [ ] Update `tests/playwright/test_workflows_style.py` to handle both view states (list and board) in style assertions
- [ ] Update `tests/playwright/test_workflows_intent.py` for any intent/toggle-related assertions
- [ ] Run all workflow test files and verify zero failures related to view state, missing kanban elements, or API field mismatches

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Kanban-related tests click the view toggle before asserting board columns or cards
- [ ] Tests work with clean `localStorage` (no leftover view-preference state)
- [ ] API response field assertions match the actual JSON keys returned by the workflows endpoint
- [ ] Zero workflow test failures caused by initial view state assumptions or API field mismatches

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 76](../../epic-76-playwright-test-calibration.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_kanban_tests_click_toggle_before_asserting` -- Kanban tests explicitly switch to board view before asserting column elements
2. `test_ac2_clean_localstorage_deterministic_state` -- Tests produce the same results with empty localStorage as with pre-set localStorage
3. `test_ac3_api_fields_match_actual_response` -- Workflow API assertions use the same field names that the endpoint returns
4. `test_ac4_zero_workflow_failures` -- All four workflow test files pass with no view-state or API-related failures

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use `page.evaluate(() => localStorage.clear())` before `page.goto()` to guarantee a clean initial state.
- The view toggle is likely a button with a data attribute or aria-label -- identify the actual selector from the deployed page before hardcoding it.
- The workflows endpoint may return paginated results -- tests should handle the pagination wrapper if present.

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 76.1 (token names should be correct before validating workflow page styles)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Isolated to the workflows page test files
- [x] **N**egotiable -- View toggle approach can be refined during implementation
- [x] **V**aluable -- Fixes workflow page test failures caused by state assumptions
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
