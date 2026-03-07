# Epic 5 Sprint 1 Retro

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Sprint:** Eval Suite & Metrics APIs (Stories 5.1-5.8)
**Result:** 8/8 stories complete, 90 tests passing, all quality gates green

---

## What Worked

### 1. Two independent tracks enabled fast progress
The eval suite (5.1-5.3) and metrics/expert APIs (5.4-5.6) had no dependencies on each other. Sequential execution with no blocking.

### 2. Eval framework dataclass pattern was clean
`EvalCase` -> `EvalSuite.run()` -> `EvalResult` with `to_dict()` — simple, testable, extensible. Adding new eval types was just subclassing and registering.

### 3. Existing in-memory stores provided data for metrics
`get_signals()`, `get_reopen_outcomes()`, `get_all_weights()` — all data sources existed. MetricsService and ExpertPerformanceService were pure aggregation layers.

### 4. HTMX partial pattern continued to scale
Stories 5.7-5.8 followed the exact pattern from Epic 4 Sprint 2. No new patterns needed.

---

## What to Improve

### 1. Fixture calibration required iteration
Intent correctness fixtures initially failed because keyword matching is sensitive to term extraction (3-char minimum, stop word list). Two rounds of fixture tuning were needed.

**Action item:** Consider adding a `debug_match` mode to eval suites for easier fixture calibration.

### 2. TemplateResponse deprecation warnings persist
16 warnings from Starlette about `TemplateResponse(name, context)` vs `TemplateResponse(request, name)` — carryover from Epic 4 Sprint 2.

**Action item:** Batch-update all `TemplateResponse` calls in `ui_router.py` to new signature.

### 3. Confidence growth is very slow
CONFIDENCE_SAMPLE_WEIGHT of 0.05 means 10 samples only reach 0.22 confidence (tier promotion requires 0.3). May be too conservative.

**Action item:** Review confidence parameters with domain expert before Phase 3 completion.

---

## Metrics

| Metric | Value |
|--------|-------|
| Stories planned | 8 |
| Stories completed | 8 |
| Completion rate | 100% |
| Total tests | 90 |
| Eval fixtures | 13 |
| API endpoints added | 6 |
| UI pages added | 4 |
| Files created | 24 |
| Files modified | 3 |

---

## Phase 3 Progress Assessment

| Phase 3 Deliverable | Status |
|---------------------|--------|
| First eval suite (intent, routing, verification, QA) | Complete |
| Metrics and Trends dashboard | Complete |
| Expert Performance Console | Complete |
| Reopen rate tracking and attribution | Complete |
| Single-pass success target (>=60%) | Measurement in place, enforcement deferred |
| Service Context Packs (2+ in production) | Not started |
| Expert classes expansion (5+ classes) | Not started (2 seeded) |

**4 of 7 Phase 3 deliverables complete.**

---

## Recommendation for Next Work

Phase 3 remaining deliverables:
1. Service Context Packs — at least 2 packs for production repos
2. Expert classes expansion — seed 3+ more classes beyond security and qa_validation
3. Single-pass success target enforcement — gate at >=60% with alerting

**Helm recommends:** Epic 6 focused on closing out Phase 3 — Service Context Packs, expert expansion, and success target enforcement. These are the final deliverables before Phase 4 (Autonomy).

---

*Retro by Helm. Ready for Epic 6 creation (Saga) and planning.*
