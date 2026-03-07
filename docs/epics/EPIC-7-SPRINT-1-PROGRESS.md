# Epic 7 Sprint 1 Progress — Platform Maturity Foundations

**Date:** 2026-03-07
**Sprint:** Epic 7 Sprint 1 — Tool Hub, Model Gateway, Compliance Scorecard, Operational Targets
**Status:** 9/9 stories complete

---

## Story Status

| Story | Title | Status | Tests |
|-------|-------|--------|-------|
| 7.1 | Tool Catalog Schema & Registry | Complete | 12 |
| 7.2 | Tool Profile & Policy Engine | Complete | 11 |
| 7.3 | Tool Hub API & Audit | Complete | 6 |
| 7.4 | Model Class & Routing Rules | Complete | 15 |
| 7.5 | Fallback Chains & Budget Enforcement | Complete | 9 |
| 7.6 | Model Gateway API & Audit | Complete | 5 |
| 7.7 | Compliance Scorecard Service | Complete | 11 |
| 7.8 | Compliance Scorecard API & Promotion Gate | Complete | 3 |
| 7.9 | Lead Time, Cycle Time & Reopen Target | Complete | 14 + 3 API |

**Total new tests:** 110 (93 service + 17 API)
**Pass rate:** 100%

---

## Files Created

### Tool Hub (`src/admin/`)
- `tool_catalog.py` — ToolSuite, ToolEntry, ToolCatalog, ToolProfile, ToolPolicyEngine, 3 standard suites

### Model Gateway (`src/admin/`)
- `model_gateway.py` — ModelClass, ProviderConfig, RoutingRule, ModelRouter, BudgetEnforcer, ModelAuditStore

### Compliance Scorecard (`src/admin/`)
- `compliance_scorecard.py` — ScorecardCheck, ComplianceScorecard, ComplianceScorecardService (7 checks)

### Operational Targets (`src/admin/`)
- `operational_targets.py` — LeadTimeMetrics, CycleTimeMetrics, ReopenTargetMetrics, OperationalTargetsService

### Platform API (`src/admin/`)
- `platform_router.py` — All Phase 4 API endpoints (Tool Hub, Model Gateway, Compliance, Targets)

### Tests
- `tests/unit/test_tool_catalog.py` — 23 tests for catalog, policy engine
- `tests/unit/test_model_gateway.py` — 30 tests for router, budget, audit
- `tests/unit/test_compliance_scorecard.py` — 13 tests for scorecard service
- `tests/unit/test_operational_targets.py` — 14 tests for lead/cycle time, reopen target
- `tests/unit/test_platform_api.py` — 17 tests for all API endpoints (RBAC-bypassed)

### Files Modified
- `src/app.py` — Added platform_router import and registration

---

## API Endpoints Added

### Tool Hub
- `GET /admin/tools/catalog` — List all tool suites
- `GET /admin/tools/catalog/{suite_name}` — Suite detail
- `POST /admin/tools/catalog/{suite_name}/promote` — Promote approval status
- `GET /admin/tools/profiles` — List tool profiles
- `POST /admin/tools/check-access` — Check tool access policy

### Model Gateway
- `POST /admin/models/route` — Simulate routing decision
- `GET /admin/models/providers` — List provider configs
- `PATCH /admin/models/providers/{id}` — Enable/disable provider
- `GET /admin/models/audit` — Query model call audit
- `POST /admin/models/budget/{repo_id}` — Set repo budget

### Compliance
- `GET /admin/repos/{id}/compliance` — Run compliance scorecard
- `POST /admin/repos/{id}/compliance/evaluate` — Evaluate with explicit data

### Operational Targets
- `GET /admin/metrics/lead-time` — Lead time percentiles
- `GET /admin/metrics/cycle-time` — Cycle time percentiles
- `GET /admin/metrics/reopen-target` — Reopen rate vs <5% target

---

## Sprint Goal Verification

1. `GET /admin/tools/catalog` returns 3+ tool suites (code-quality, context-retrieval, documentation) ✓
2. `POST /admin/models/route` returns model selection for step/role/tier ✓
3. `GET /admin/repos/{id}/compliance` returns scorecard with 7 checks ✓
4. All 110 tests pass ✓
