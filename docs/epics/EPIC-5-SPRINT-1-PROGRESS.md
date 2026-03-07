# Epic 5 Sprint 1 Progress — Eval Suite & Metrics APIs

**Date:** 2026-03-06
**Sprint:** Epic 5 Sprint 1 — Observability & Quality Measurement
**Status:** 8/8 stories complete

---

## Story Status

| Story | Title | Status | Tests |
|-------|-------|--------|-------|
| 5.1 | Eval Framework & Intent Correctness Eval | Complete | 21 |
| 5.2 | Routing Correctness & Verification Friction Evals | Complete | 13 |
| 5.3 | QA Defect Mapping Eval & Eval Runner | Complete | 12 |
| 5.4 | Metrics APIs — Single-Pass & Loopbacks | Complete | 11 |
| 5.5 | Metrics APIs — Reopen Rate & Attribution | Complete | 5 |
| 5.6 | Expert Performance API | Complete | 12 |
| 5.7 | Admin UI — Metrics Dashboard | Complete | 7 |
| 5.8 | Admin UI — Expert Performance Console | Complete | 9 |

**Total tests:** 90
**Pass rate:** 100%

---

## Files Created

### Eval Suite (`src/evals/`)
- `__init__.py` — module init
- `__main__.py` — CLI entry point
- `framework.py` — EvalCase, EvalResult, EvalSuite base types
- `intent_correctness.py` — keyword/structure matching eval
- `routing_correctness.py` — set comparison eval for expert coverage
- `verification_friction.py` — friction scoring normalized by complexity
- `qa_defect_mapping.py` — defect-to-criteria mapping with intent_gap classification
- `runner.py` — loads fixtures, runs all suites, produces aggregate JSON report
- `fixtures/intent_correctness.json` — 3 fixtures
- `fixtures/routing_correctness.json` — 3 fixtures
- `fixtures/verification_friction.json` — 3 fixtures
- `fixtures/qa_defect_mapping.json` — 4 fixtures (13 total)

### Metrics & Expert APIs (`src/admin/`)
- `metrics.py` — MetricsService: single-pass, loopbacks, reopen rate
- `experts.py` — ExpertPerformanceService: list, detail, drift

### Admin UI Templates
- `templates/metrics.html` — metrics page with repo filter
- `templates/partials/metrics_content.html` — single-pass card, loopback table, reopen card
- `templates/experts.html` — expert list with repo/tier filters
- `templates/partials/experts_list.html` — expert table with tier badges, drift indicators
- `templates/expert_detail.html` — expert detail page
- `templates/partials/expert_detail_content.html` — expert summary + per-repo breakdown

### Files Modified
- `src/admin/router.py` — added 6 API endpoints (3 metrics, 3 experts)
- `src/admin/ui_router.py` — added 6 UI routes (metrics page + partial, experts page + partial + detail + detail partial)
- `src/admin/templates/base.html` — added Metrics and Experts to sidebar navigation

### Tests
- `tests/unit/test_eval_framework.py` — 21 tests
- `tests/unit/test_eval_routing_verification.py` — 13 tests
- `tests/unit/test_eval_qa_runner.py` — 12 tests
- `tests/unit/test_metrics_api.py` — 16 tests
- `tests/unit/test_expert_performance.py` — 12 tests
- `tests/unit/test_admin_ui_metrics_experts.py` — 16 tests

---

## Sprint Goal Verification

1. `python -m src.evals.runner` — runs 13 cases across 4 eval types, all pass
2. `GET /admin/metrics/single-pass` — returns 7d and 30d rates with per-repo breakdown
3. `GET /admin/metrics/loopbacks` — returns loopback counts by category (lint/test/security/other)
4. `GET /admin/metrics/reopen` — returns reopen rate with attribution breakdown (or note if empty)
5. `/admin/ui/metrics` — renders metrics dashboard with all cards and repo filter
6. `/admin/ui/experts` — renders expert table with tier badges, drift indicators, and filters
