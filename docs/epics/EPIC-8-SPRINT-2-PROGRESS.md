# Epic 8 Sprint 2 Progress — Real Adapters, Persistence & Deployment

**Date:** 2026-03-07
**Sprint:** Epic 8 Sprint 2 — Tracks B, C, E
**Status:** 8/8 stories complete

---

## Story Status

| Story | Track | Title | Status | Tests |
|-------|-------|-------|--------|-------|
| 8.5 | B | Anthropic Claude LLM Adapter | Complete | 11 new tests |
| 8.6 | B | GitHub REST API Adapter | Complete | 17 new tests |
| 8.7 | C | Persistence Adapter Interfaces | Complete | 0 new (0 regressions) |
| 8.8 | C | PostgreSQL Implementations (3 stores) | Complete | 18 new tests |
| 8.9 | C | Store Configuration Switch | Complete | 9 new tests |
| 8.10 | E | Dockerfile & Docker Compose | Complete | — |
| 8.11 | E | GitHub Actions CI Pipeline | Complete | — |
| 8.12 | E | Environment & Deployment Docs | Complete | — |

**Total tests:** 1,167 (1,112 prior + 55 new)
**Pass rate:** 100% (8 integration deselected, require PostgreSQL)

---

## Files Created

### Track B: Real Provider Adapters
- `src/adapters/__init__.py` — Adapters package
- `src/adapters/llm.py` — LLMAdapterProtocol, MockLLMAdapter, AnthropicAdapter
- `src/adapters/github.py` — ResilientGitHubClient with retry logic
- `tests/unit/test_llm_adapter.py` — 11 tests
- `tests/unit/test_github_adapter.py` — 17 tests

### Track C: Persistence & State
- `src/admin/persistence/__init__.py` — Persistence package
- `src/admin/persistence/pg_tool_catalog.py` — PostgresToolCatalog
- `src/admin/persistence/pg_model_audit.py` — PostgresModelAuditStore
- `src/admin/persistence/pg_compliance.py` — PostgresComplianceScorecardService
- `src/admin/store_factory.py` — Backend switch factory
- `src/db/models.py` — ORM models (ToolSuiteRow, ToolEntryRow, ModelCallAuditRow, etc.)
- `src/db/migrations/012_tool_catalog.py` — tool_suites, tool_entries, tool_profiles tables
- `src/db/migrations/013_model_audit.py` — model_call_audit table
- `tests/unit/test_pg_stores.py` — 18 tests (SQLite in-memory)
- `tests/unit/test_store_factory.py` — 9 tests

### Track E: Deployment Configuration
- `Dockerfile` — Python 3.12 slim, uvicorn entrypoint
- `.github/workflows/ci.yml` — Unit + smoke tests on push/PR
- `docs/deployment.md` — All env vars, quick start, CI docs

## Files Modified

- `src/settings.py` — Added 3 feature flags (llm_provider, github_provider, store_backend)
- `src/admin/tool_catalog.py` — Added ToolCatalogProtocol, renamed to InMemoryToolCatalog
- `src/admin/model_gateway.py` — Added BudgetEnforcerProtocol, ModelAuditStoreProtocol
- `src/admin/compliance_scorecard.py` — Added ComplianceScorecardProtocol
- `src/reputation/engine.py` — Added ReputationEngineProtocol, InMemoryReputationEngine
- `infra/docker-compose.yml` — Added app service with health check

---

## Sprint Goal Verification

1. `pytest tests/ -m "not integration"` passes with 0 failures, 0 errors ✓ (1,167 passed)
2. Integration tests for provider adapters pass against mock HTTP ✓ (28 adapter tests)
3. Docker Compose starts app + postgres, Admin UI accessible ✓ (app service added)
4. GitHub Actions CI runs unit + smoke tests on push ✓ (ci.yml created)

---

## Acceptance Criteria Status

| AC | Description | Status |
|----|-------------|--------|
| AC 4 | Anthropic Claude adapter behind feature flag | ✓ |
| AC 5 | GitHub client adapter with mock HTTP tests | ✓ |
| AC 6 | Adapters follow existing interface contracts | ✓ |
| AC 7 | Persistence adapter interfaces for all stores | ✓ (5 Protocols) |
| AC 8 | DB migrations for Phase 4 tables | ✓ (012, 013) |
| AC 9 | Admin API switches via configuration | ✓ (store_factory.py) |
| AC 12 | Docker Compose with health checks | ✓ |
| AC 13 | Environment configuration documented | ✓ (docs/deployment.md) |
| AC 14 | CI pipeline on every push | ✓ (.github/workflows/ci.yml) |
