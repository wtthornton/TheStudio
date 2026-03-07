# Epic 8 Sprint 2 — Real Adapters, Persistence & Deployment

**Date:** 2026-03-07
**Sprint:** Epic 8 Sprint 2
**Tracks:** B (Real Provider Adapters) + C (Persistence & State) + E (Deployment Configuration)
**Status:** Planned — awaiting Meridian review

---

## Sprint Goal

**Objective:** Every platform service can run against real backends (Anthropic API, GitHub API, PostgreSQL) behind feature flags, with a Docker Compose stack that starts the full app and a CI pipeline that gates every push.

**Verification:** (1) `pytest tests/ -m "not integration"` passes with 0 failures (no regressions). (2) New integration tests for provider adapters pass against mock HTTP servers. (3) `docker compose up` starts app + postgres, Admin UI serves on localhost. (4) GitHub Actions CI runs unit + smoke tests on push.

**Constraint:** Feature flags default to off. Existing tests remain unaffected. No real API keys required in CI. No breaking changes to existing API contracts.

---

## What's Out This Sprint

- Real LLM API calls in CI — adapters use mock HTTP servers in tests
- Real GitHub App registration — GitHub adapter tests use mock HTTP
- Temporal or JetStream deployment — stays as direct function calls
- BudgetEnforcer and ReputationEngine PostgreSQL implementations — interfaces only; DB impl deferred (per risk mitigation: start with 3 most critical stores)
- Kubernetes manifests — Docker Compose is the deployment target
- OpenClaw integration — remains deferred

---

## Stories

### Story 8.5: Anthropic Claude LLM Adapter
**Track:** B | **Size:** M | **AC:** 3

Implement a real LLM adapter that calls the Anthropic API using the `anthropic` Python SDK. The adapter implements the same call contract used by `ModelRouter.select_model()` — given a `ProviderConfig`, it makes a real API call and returns a response. Behind `THESTUDIO_LLM_PROVIDER=anthropic` feature flag (default: `mock`).

- AC 1: `AnthropicAdapter` class accepts a `ProviderConfig` and makes async chat completion calls via the Anthropic SDK.
- AC 2: Feature flag `THESTUDIO_LLM_PROVIDER` switches between mock (default) and real adapter. Existing tests unaffected.
- AC 3: Integration test using `respx` or `httpx` mock transport proves the adapter sends correct request shape and parses the response, without a real API key.

**Dependencies:** None. Uses existing `ProviderConfig` and `ModelCallAudit` from `model_gateway.py`.

---

### Story 8.6: GitHub REST API Adapter
**Track:** B | **Size:** M | **AC:** 3

Wrap the existing `GitHubClient` with a feature-flagged adapter that supports real GitHub API calls (create PR, post comment, manage labels). The existing `GitHubClient` already has the right interface — this story adds a feature flag, retry/error handling for real HTTP, and integration tests with a mock HTTP server.

- AC 1: Feature flag `THESTUDIO_GITHUB_PROVIDER` switches between mock (default) and real GitHub client. Existing publisher tests unaffected.
- AC 2: Real adapter adds retry logic (3 retries with exponential backoff) and proper error classification (rate limit, auth, not found).
- AC 3: Integration test using `respx` or `httpx` mock transport exercises create_pull_request, add_comment, add_labels against mock GitHub API responses.

**Dependencies:** None. Builds on existing `GitHubClient` in `src/publisher/github_client.py`.

---

### Story 8.7: Persistence Adapter Interfaces
**Track:** C | **Size:** M | **AC:** 3

Define abstract base classes (Protocol or ABC) for the 5 in-memory stores: `ToolCatalog`, `ModelAuditStore`, `BudgetEnforcer`, `ComplianceScorecardService`, `ReputationEngine`. Refactor existing implementations to be the "in-memory" concrete class implementing each interface.

- AC 1: Each store has a `Protocol` or ABC defining its public methods (register/get/list/clear for catalogs, record/query for audit, etc.).
- AC 2: Existing in-memory implementations renamed to `InMemory*` classes (e.g., `InMemoryToolCatalog`) implementing the interface.
- AC 3: Global singleton getters (`get_tool_catalog()`, etc.) continue to return in-memory implementations by default. No existing test changes required.

**Dependencies:** None. This is a refactor — all existing tests must pass unchanged.

---

### Story 8.8: PostgreSQL Implementations — 3 Critical Stores
**Track:** C | **Size:** L | **AC:** 4

Implement PostgreSQL-backed versions of the 3 most critical stores: `ToolCatalog`, `ModelAuditStore`, `ComplianceScorecardService`. Add database migrations for the new tables.

- AC 1: `PostgresToolCatalog` implements `ToolCatalogProtocol` using SQLAlchemy async sessions. Tables: `tool_suites`, `tool_entries`, `tool_profiles`.
- AC 2: `PostgresModelAuditStore` implements `ModelAuditStoreProtocol`. Table: `model_call_audit`.
- AC 3: `PostgresComplianceScorecardService` implements `ComplianceScorecardProtocol`. Uses existing `compliance_results` table (migration 009).
- AC 4: Database migrations (012–014) create `tool_suites`, `tool_entries`, `tool_profiles`, `model_call_audit` tables. Follow existing migration pattern.

**Dependencies:** Story 8.7 (interfaces must exist first).

---

### Story 8.9: Store Configuration Switch
**Track:** C | **Size:** S | **AC:** 2

Add a `THESTUDIO_STORE_BACKEND` environment variable that switches singleton getters between in-memory (default) and PostgreSQL implementations.

- AC 1: `THESTUDIO_STORE_BACKEND=postgres` causes `get_tool_catalog()`, `get_model_audit_store()`, and `get_scorecard_service()` to return PostgreSQL implementations.
- AC 2: Default remains `memory` — all existing tests pass without changes. Admin API endpoints work with either backend.

**Dependencies:** Story 8.8 (PostgreSQL implementations must exist).

---

### Story 8.10: Dockerfile & Docker Compose Update
**Track:** E | **Size:** M | **AC:** 3

Create a Dockerfile for the FastAPI app and update the existing `infra/docker-compose.yml` to include the app service with health checks.

- AC 1: `Dockerfile` builds the FastAPI app (Python 3.12 slim, pip install, uvicorn entrypoint).
- AC 2: `infra/docker-compose.yml` adds `app` service depending on `postgres` (healthy). App binds to port 8000.
- AC 3: `docker compose up` starts postgres + app, Admin UI accessible at `http://localhost:8000/admin/`.

**Dependencies:** Story 8.9 (app needs store config to know which backend to use).

---

### Story 8.11: GitHub Actions CI Pipeline
**Track:** E | **Size:** M | **AC:** 3

Create a GitHub Actions workflow that runs unit tests and smoke tests on every push and PR.

- AC 1: `.github/workflows/ci.yml` triggers on push to `master` and all PRs.
- AC 2: Pipeline installs Python 3.12, project dependencies, runs `pytest tests/ -m "not integration"` with coverage.
- AC 3: Pipeline fails if any test fails or coverage drops below 75%.

**Dependencies:** None. Can be built in parallel with other stories.

---

### Story 8.12: Environment & Deployment Documentation
**Track:** E | **Size:** S | **AC:** 2

Document all environment variables, feature flags, secrets management, and local development setup.

- AC 1: `docs/deployment.md` lists all `THESTUDIO_*` env vars with descriptions, defaults, and whether they're required.
- AC 2: Quick-start section covers: clone → install → docker compose up → run tests → access Admin UI.

**Dependencies:** Stories 8.5, 8.6, 8.9, 8.10 (needs all feature flags and config to be finalized).

---

## Order of Work

```
Phase 1 (parallel, no dependencies):
  8.5  Anthropic adapter ──────────────┐
  8.6  GitHub adapter ─────────────────┤
  8.7  Persistence interfaces ─────────┤── can all start immediately
  8.11 GitHub Actions CI ──────────────┘

Phase 2 (after 8.7):
  8.8  PostgreSQL implementations ─────── depends on 8.7

Phase 3 (after 8.8):
  8.9  Store configuration switch ─────── depends on 8.8

Phase 4 (after 8.9):
  8.10 Dockerfile & Docker Compose ────── depends on 8.9

Phase 5 (after all):
  8.12 Env & deployment docs ──────────── depends on 8.5, 8.6, 8.9, 8.10
```

**Critical path:** 8.7 → 8.8 → 8.9 → 8.10 → 8.12

**Mid-sprint check:** After Phase 2 (Story 8.8 complete). Assess: are migrations clean? Do PostgreSQL implementations pass against testcontainers? Replan Phase 3–5 if Track C took longer than expected.

---

## Capacity & Buffer

8 stories. 80% commitment — Stories 8.5–8.11 are committed; Story 8.12 (docs) is the buffer and can slip if Track C is harder than expected.

| Size | Count | Relative effort |
|------|-------|-----------------|
| S    | 2     | ~10%            |
| M    | 5     | ~65%            |
| L    | 1     | ~25%            |

Story 8.8 (PostgreSQL implementations + migrations) is the riskiest — 3 store implementations, 3 migrations, ORM mapping. If it runs long, consider cutting to 2 stores (defer ComplianceScorecard since migration 009 already exists).

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| PostgreSQL adapter scope creep (8.8) | Medium | High | Start with 3 stores, not 5. BudgetEnforcer and ReputationEngine stay in-memory. |
| Mock HTTP test flakiness (8.5, 8.6) | Low | Medium | Use `respx` for deterministic HTTP mocking, no real network calls. |
| Docker Compose port conflicts | Low | Low | Use non-standard ports (5434 for postgres already set). |
| CI coverage threshold too aggressive | Low | Medium | Set floor at 75%, not 81%. Coverage may dip slightly as new adapter code has lower unit coverage. |

---

## Retro Actions from Sprint 1

| Action | How addressed |
|--------|---------------|
| Integration tests missing (Epic 4 retro) | Stories 8.5, 8.6 add integration tests with mock HTTP. Story 8.8 adds DB integration tests. |
| Identify cross-cutting concerns early (Epic 4 retro) | Feature flag pattern (8.5, 8.6, 8.9) is the cross-cutting concern — defined in Settings before individual stories. |
| Keep mid-sprint checks (Epic 4 retro) | Mid-sprint check after Phase 2 (Story 8.8). |

---

## Dependencies

- `anthropic` Python SDK — already referenced in `pyproject.toml` via `claude-agent-sdk`; may need direct `anthropic` dependency.
- `respx` — new dev dependency for HTTP mocking in integration tests.
- Existing `infra/docker-compose.yml` — will be modified, not replaced.
- Existing migrations 001–011 — new migrations 012–014 build on them.

---

*Plan by Helm. Awaiting Meridian review before execution.*
