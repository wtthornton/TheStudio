# Epic 15 Session Plan — Real Repo Observe-Tier Trial

**Date:** 2026-03-16
**Status:** Ready to execute (Meridian reviewed, 2 rounds passed)
**Prerequisite check:** Epics 17 (polling), 18 (E2E tests), 22 (Execute tier) complete

## Sprint Order

| Priority | Story | What | Size | Depends On |
|----------|-------|------|------|------------|
| 1 | 15.1 | Mock provider harness in tests/integration/ | M | — |
| 2 | 15.2 | Full pipeline smoke test (webhook → draft PR) | M | 15.1 |
| 3 | 15.3 | Loopback integration tests (verify + QA retry) | M | 15.1 |
| 4 | 15.4 | Evidence comment validation (all 7 sections) | S | 15.2 |
| 5 | 15.5 | Temporal workflow data-fidelity test | M | 15.1 |
| 6 | 15.6 | Pipeline latency baseline doc | S | 15.2 |
| 7 | 15.7 | Real repo onboarding guide | S | — |

## Pre-Sprint Verification

- [ ] All 9 pipeline modules importable without side effects
- [ ] `temporalio.testing.WorkflowEnvironment` available in test dependencies
- [ ] Existing 5 integration tests in `test_pipeline_workflow.py` still pass
- [ ] Evidence comment format unchanged since last review

## Key Decision: Start with Story 15.1

The mock provider harness unblocks Stories 15.2-15.5. Story 15.7 (onboarding guide)
is independent and can be written in parallel.

## Success Gate

- 9/9 pipeline stages exercised end-to-end with realistic mock data
- Evidence comment contains all 7 required sections (non-empty)
- Loopback paths tested (verify retry, QA retry, exhaustion)
- Total pipeline time < 5s with mocks
- Onboarding guide followable within 30 minutes
