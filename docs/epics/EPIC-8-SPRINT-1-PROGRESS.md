# Epic 8 Sprint 1 Progress — Test Health & End-to-End Smoke Test

**Date:** 2026-03-07
**Sprint:** Epic 8 Sprint 1 — Test Health, Integration Markers, Smoke Test, Coverage
**Status:** 4/4 stories complete

---

## Story Status

| Story | Title | Status | Tests |
|-------|-------|--------|-------|
| 8.1 | Fix TemplateResponse Deprecation Warnings | Complete | 80 UI tests, 0 warnings |
| 8.2 | Fix Integration Test DB Dependency | Complete | 8 tests deselected by default |
| 8.3 | End-to-End Smoke Test | Complete | 11 new tests |
| 8.4 | Test Coverage Report | Complete | Baseline: 81% |

**Total tests:** 1,112 (1,101 unit + 11 e2e)
**Pass rate:** 100% (8 integration deselected, require PostgreSQL)

---

## Files Created

- `tests/e2e/__init__.py` — E2E test package
- `tests/e2e/test_smoke.py` — 11 smoke tests covering full intake-to-publish flow
- `docs/epics/epic-8-production-readiness.md` — Epic 8 definition (Saga)
- `docs/epics/epic-8-sprint-1-plan.md` — Sprint 1 plan (Helm)

## Files Modified

- `src/admin/ui_router.py` — 26 TemplateResponse calls updated to non-deprecated signature
- `pyproject.toml` — Added `addopts = "-m 'not integration'"` to exclude integration tests by default

---

## Coverage Baseline

| Metric | Value |
|--------|-------|
| Total statements | 7,603 |
| Covered | 6,191 |
| Missing | 1,412 |
| **Coverage** | **81%** |

### High coverage (>95%)
- `src/admin/` — tool_catalog, model_gateway, compliance_scorecard, operational_targets, platform_router
- `src/routing/router.py` — 100%
- `src/publisher/evidence_comment.py` — 100%
- `src/reputation/` — engine, models, tiers, drift all >93%

### Low coverage (<50%)
- `src/workflow/pipeline.py` — 47% (Temporal integration, not unit-testable)
- `src/verification/gate.py` — 39% (subprocess runners, mocked in unit tests)
- `src/publisher/github_client.py` — 39% (real HTTP client, deferred to Track B)
- `src/qa/signals.py` — 48% (JetStream integration)

---

## Sprint Goal Verification

1. All tests pass with zero failures, zero errors ✓ (1,112 passed, 8 deselected)
2. TemplateResponse deprecation warnings eliminated ✓ (0 warnings in UI tests)
3. E2E smoke test proves full flow ✓ (11 tests, intake→context→intent→agent→verify→publish)
4. Coverage baseline established ✓ (81%)
