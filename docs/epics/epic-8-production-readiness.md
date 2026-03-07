# Epic 8 — Production Readiness & Integration

**Author:** Saga
**Date:** 2026-03-07
**Status:** Draft — awaiting Meridian review

---

## 1. Title

Production Readiness & Integration — Close the gap between platform services and real-world deployment.

## 2. Narrative

Phases 0–4 built the entire platform as testable services: intake, context, intent, experts, routing, reputation, compliance, tool hub, model gateway, admin UI, and operational targets. All 1,101 tests pass. But every external integration is mocked: GitHub API, LLM providers, Temporal workflows, JetStream signals, PostgreSQL persistence at runtime.

This epic closes the integration gap. The goal is not to deploy to production yet — it's to make every service capable of running against real backends, with integration tests proving it, so the first real deployment is a configuration exercise, not a code exercise.

## 3. References

- Architecture overview: `thestudioarc/00-overview.md`
- System runtime flow: `thestudioarc/15-system-runtime-flow.md`
- Tool Hub: `thestudioarc/25-tool-hub-mcp-toolkit.md`
- Model Gateway: `thestudioarc/26-model-runtime-and-routing.md`
- Admin UI: `thestudioarc/23-admin-control-ui.md`
- Aggressive roadmap: `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md`

## 4. Acceptance Criteria

### Track A: Test Health & Technical Debt
- **AC 1:** All unit tests pass with zero failures and zero errors (currently 1,101 pass, 0 fail).
- **AC 2:** TemplateResponse deprecation warnings eliminated across all UI routes.
- **AC 3:** Integration test fixtures use testcontainers or equivalent for PostgreSQL, so integration tests run without an external DB.

### Track B: Real Provider Adapters
- **AC 4:** Model Gateway has at least one real LLM provider adapter (Anthropic Claude) behind a feature flag, with integration test using a mock HTTP server (not a real API key).
- **AC 5:** GitHub client adapter supports real GitHub API calls (create PR, post comment, manage labels) behind a feature flag, with integration test using a mock HTTP server.
- **AC 6:** Provider adapters follow the existing interface contracts (ProviderConfig, GitHubClient) — no service layer changes required.

### Track C: Persistence & State
- **AC 7:** All in-memory stores (ToolCatalog, ModelAuditStore, BudgetEnforcer, ComplianceScorecardService, ReputationEngine) have a persistence adapter interface, with at least one in-memory and one PostgreSQL implementation.
- **AC 8:** Database migrations cover all new Phase 4 tables (tool_suites, model_audit, compliance_results, operational_metrics).
- **AC 9:** Admin API endpoints can switch between in-memory and DB-backed stores via configuration.

### Track D: End-to-End Smoke Test
- **AC 10:** A single end-to-end test exercises the full flow: mock webhook → intake → context → intent → primary agent (stub) → verification (stub) → publisher (mock) → evidence comment. This test uses in-memory stores and no external services.
- **AC 11:** The smoke test asserts: TaskPacket created, intent built, verification ran, PR draft created with evidence comment, lifecycle labels applied.

### Track E: Deployment Configuration
- **AC 12:** Docker Compose file defines all services (FastAPI app, PostgreSQL, optional Redis) with health checks.
- **AC 13:** Environment configuration documented: required env vars, optional feature flags, secrets management guidance.
- **AC 14:** CI pipeline configuration (GitHub Actions) runs all unit tests and the smoke test on every push.

## 4b. Top Risks

1. **Persistence adapter scope creep** — Adding DB adapters for every in-memory store could balloon. Mitigation: start with the 3 most critical stores (ToolCatalog, ModelAuditStore, ComplianceScorecard); others stay in-memory until needed.
2. **Integration test flakiness** — Tests against testcontainers or mock HTTP servers can be flaky on CI. Mitigation: keep integration tests in a separate test marker; unit tests remain the primary gate.
3. **Docker Compose complexity** — Too many services in Compose can make local dev slow. Mitigation: keep it minimal (app + postgres); Redis and workers are optional.

## 5. Constraints & Non-Goals

### Non-goals
- **No real LLM API calls in CI** — provider adapters use mock HTTP servers in tests.
- **No real GitHub App registration** — GitHub adapter tests use mock HTTP, not a live repo.
- **No Temporal or JetStream deployment** — workflow orchestration stays as direct function calls for now.
- **No multi-repo deployment** — single-repo, single-instance is sufficient for this epic.
- **No OpenClaw integration** — remains deferred per roadmap.
- **No Kubernetes manifests** — Docker Compose is the deployment target for now.

### Constraints
- All new code must maintain the existing test pass rate (zero regressions).
- Feature flags must default to off (in-memory/mock mode) so existing tests are unaffected.
- No breaking changes to existing API contracts.

## 6. Stakeholders

- **Engineering:** Builds adapters and deployment config.
- **Leadership:** Decides when to provision real API keys and GitHub App.
- **Meridian:** Reviews epic and plan quality.

## 7. Success Metrics

- **Primary:** End-to-end smoke test passes in CI on every push.
- **Secondary:** All 5 tracks have passing tests; zero regressions from Phases 0–4.
- **Tertiary:** Docker Compose `docker compose up` starts the full stack and serves the Admin UI on localhost.

## 8. Context & Assumptions

- PostgreSQL is the target database (already used for TaskPacket, RepoProfile, IntentSpec, ExpertLibrary).
- The Anthropic Python SDK (`anthropic`) is the first real LLM provider.
- GitHub REST API v3 is used for PR/issue/label operations (not GraphQL for now).
- Feature flags are simple environment variables, not a feature flag service.
- The platform already has 90+ source files and 1,101 tests — this epic adds integration plumbing, not new business logic.
