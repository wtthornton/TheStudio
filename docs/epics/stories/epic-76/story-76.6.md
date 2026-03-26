# Story 76.6 -- Fix Tools API Tests

<!-- docsmcp:start:user-story -->

> **As a** test engineer, **I want** tools API tests to validate actual endpoints, **so that** API failures indicate real changes, not wrong URLs

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the tools page API and intent tests assert against the correct endpoint URLs and response field names. Currently, the tests reference URLs and JSON keys that do not match the actual admin router, causing all tools API assertions to fail regardless of whether the endpoint is working correctly.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Read the actual endpoint definitions from `src/admin/router.py`, identify the correct URLs and response JSON shape for the tools page, and update `test_tools_api.py` and `test_tools_intent.py` to match. After this story, tools API tests validate the real endpoint behavior.

See [Epic 76](../../epic-76-playwright-test-calibration.md) for project context and failure baseline.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/router.py` (read-only reference for actual endpoint URLs and response shapes)
- `tests/playwright/test_tools_api.py`
- `tests/playwright/test_tools_intent.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read `src/admin/router.py` and identify all tools-related endpoint URLs (page route and any API/partial routes)
- [ ] Document the actual JSON response shape returned by the tools endpoint (field names, types, nesting)
- [ ] Update `tests/playwright/test_tools_api.py` to use the correct endpoint URLs and assert against actual response field names (`tests/playwright/test_tools_api.py`)
- [ ] Update `tests/playwright/test_tools_intent.py` to use the correct endpoint URLs and validate actual page behavior (`tests/playwright/test_tools_intent.py`)
- [ ] Run both tools test files and verify zero URL-mismatch or field-mismatch failures

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] All endpoint URLs in `test_tools_api.py` match routes defined in `src/admin/router.py`
- [ ] Response field assertions match the actual JSON keys returned by the tools endpoint
- [ ] Zero tools test failures caused by incorrect URLs or field names
- [ ] Tests correctly distinguish between "endpoint returned unexpected data" and "endpoint does not exist"

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 76](../../epic-76-playwright-test-calibration.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_urls_match_router_definitions` -- Every URL used in test_tools_api.py exists as a route in router.py
2. `test_ac2_response_fields_match_json_keys` -- Response field assertions use the same keys that the endpoint returns
3. `test_ac3_zero_tools_failures_url_or_field` -- Both tools test files pass with no URL or field mismatch errors
4. `test_ac4_endpoint_existence_vs_data_errors` -- Tests produce distinct error messages for 404 (bad URL) vs. assertion failure (wrong data)

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- The admin router uses FastAPI's `APIRouter` with path prefixes -- verify the full URL path including any `/admin/ui/` prefix.
- The tools page may use HTMX partial endpoints in addition to the main page route -- check for `hx-get` targets in the template.
- Response shapes may include pagination wrappers, metadata fields, or nested objects -- test assertions should account for the full shape.

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None (isolated to tools page, can proceed in parallel with other page-specific fixes)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Isolated to two test files and one reference source
- [x] **N**egotiable -- Assertion specificity can be refined during implementation
- [x] **V**aluable -- Fixes all tools API test failures
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within a single session
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
