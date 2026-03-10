# Epic 9 — Docker Deployed Stack Test Rig

**Author:** Saga
**Date:** 2026-03-10
**Status:** Updated -- Meridian Round 3 fixes applied

---

## 1. Title

Confidence in the Deployed Stack -- Automated test rig proves the Docker Compose services start, connect, and handle real HTTP traffic.

## 2. Narrative

TheStudio has 2,000+ unit tests, 9 integration test files, and a healthz integration test that hits FastAPI's TestClient -- but not a single test that starts the actual Docker Compose stack and verifies it works. The closest thing to deployed validation is a human running `curl http://localhost:8000/healthz` and eyeballing the result.

This matters now because Epic 8 delivered Docker Compose definitions, real provider adapters, and deployment configuration. The platform is approaching production. But between "all unit tests pass" and "the deployed system works" is a canyon of untested assumptions: Docker image builds successfully, containers start in the right order, health checks pass, the app connects to PostgreSQL and NATS and Temporal at the network addresses specified in `docker-compose.dev.yml`, and a webhook POST through the real HTTP layer actually creates a TaskPacket.

Every deployment failure that unit tests cannot catch lives in this gap. This epic fills it with a repeatable, automated test rig that builds the Docker image, starts the full stack, verifies infrastructure health, runs API smoke tests against the live containers, and tears everything down -- locally and in CI.

The scope is narrow on purpose. This epic does not rewrite existing tests or add new application features. It tests the deployment artifact, not the application logic.

## 3. References

- Docker Compose dev stack: `docker-compose.dev.yml`
- CI workflow (current): `.github/workflows/ci.yml`
- Existing healthz test (TestClient, not deployed): `tests/integration/test_healthz.py`
- Architecture overview: `thestudioarc/00-overview.md`
- System runtime flow: `thestudioarc/15-system-runtime-flow.md`
- Epic 8 (Production Readiness): `docs/epics/epic-8-production-readiness.md`
- Aggressive roadmap: `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md`
- Pipeline stage mapping: `.claude/rules/pipeline-stages.md`

## 4. Acceptance Criteria

**AC-1: Infrastructure readiness is verified programmatically.**
A single script or test module confirms all four Docker Compose services (PostgreSQL, Temporal, NATS, app) are healthy and accepting connections. The script exits 0 on success, non-zero with diagnostic output on failure. Timeout is configurable with a default of 120 seconds.

**AC-2: API smoke tests pass against the running stack.**
A test suite issues real HTTP requests to the deployed app container (port 8000) and verifies: `/healthz` returns 200 with `{"status": "ok"}`, at least one admin endpoint responds with a valid status code, and a POST to the webhook intake endpoint with a well-formed payload returns 200 or 201 (not a connection error or 500).

**AC-3: Full pipeline smoke proves end-to-end data flow.**
A test sends a webhook payload (with valid HMAC signature) through the deployed HTTP layer and then verifies -- via admin API query -- that a TaskPacket was created. (The dev stack uses `THESTUDIO_STORE_BACKEND=memory`, so verification is via API, not direct database query.) This proves the intake path works through the real network, not just in-process TestClient wiring.

**AC-4: Docker build and startup are validated before merge.**
A CI job (GitHub Actions) builds the Docker image from the Dockerfile, starts the full Compose stack, runs the smoke tests from AC-1 and AC-2, and tears down. This job runs on every PR and on pushes to master. Failure blocks merge.

**AC-5: Container lifecycle resilience is tested.**
Tests verify: (a) the app container shuts down gracefully on SIGTERM without data corruption, (b) the app recovers and passes health checks after a restart, and (c) the app behaves predictably (returns appropriate error responses or retries) when a dependency container (Temporal) is temporarily stopped and restarted. Note: the dev stack uses `THESTUDIO_STORE_BACKEND=memory`, so PostgreSQL is not exercised by most app endpoints — Temporal is the more meaningful dependency to test for resilience.

**AC-6: All stack tests are isolated from unit/integration test runs.**
Stack tests are marked (e.g., `@pytest.mark.docker`) or placed in a separate directory (e.g., `tests/docker/`) so that `pytest` without markers continues to run only unit and integration tests. The Docker test rig is opt-in locally, mandatory in CI.

## 4b. Top Risks

1. **CI runner resource limits.** Docker Compose with 4 services may exceed GitHub Actions runner memory or hit timeout limits. Mitigation: use `ubuntu-latest` with services started via `docker compose`, set aggressive health check timeouts, and cap the CI job at 15 minutes.
2. **Port conflicts.** Hardcoded ports (5434, 7233, 4222, 8000) may conflict with other CI services or parallel jobs. Mitigation: use a mandatory dedicated Compose project name (`thestudio-smoke`) for CI to avoid collisions with the existing integration job (which also uses port 5434). The CI jobs must not run in parallel — use GitHub Actions `concurrency` groups or sequential job ordering.
3. **Temporal startup latency.** The `temporalio/auto-setup` image takes 30-60 seconds to initialize. Mitigation: the readiness script must wait for Temporal health before proceeding, with the 120-second configurable timeout.
4. **Flaky network tests.** HTTP requests to containers can race against readiness. Mitigation: readiness gate (AC-1) must pass before any API tests (AC-2/AC-3) execute.

## 5. Constraints & Non-Goals

### Constraints
- All stack tests use the mock providers already configured in `docker-compose.dev.yml` (`THESTUDIO_LLM_PROVIDER=mock`, `THESTUDIO_GITHUB_PROVIDER=mock`). No real API keys in tests.
- Stack tests must not modify or duplicate existing unit/integration tests. They test the deployment, not the logic.
- The Docker image must build from the existing Dockerfile without modifications beyond what is needed for health checks.
- CI job must complete within 15 minutes including build, startup, test, and teardown.
- No new Python dependencies unless required for HTTP requests to the live stack (e.g., `httpx` is already in the project).

### Non-Goals
- **No Kubernetes manifests or Helm charts.** Docker Compose is the deployment target.
- **No load testing or performance benchmarking.** This is functional smoke, not stress testing.
- **No testing of real LLM or GitHub provider integrations.** Mock providers only.
- **No changes to application code or API contracts.** The test rig tests what exists.
- **No multi-node or multi-replica deployment testing.** Single-instance Compose stack only.
- **No Windows or macOS Docker testing in CI.** Linux runners only.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| **Epic Owner** | Engineering Lead | Scope decisions, priority calls |
| **Tech Lead** | Backend Engineer | Script design, CI integration, test architecture |
| **QA** | Meridian (review) | Acceptance criteria validation, flakiness review |
| **DevOps** | Backend Engineer | Docker Compose tuning, CI runner configuration |
| **Reviewer** | Meridian | Epic and plan review before commit |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Stack smoke pass rate in CI** | 100% on green builds (no flakes in 20 consecutive runs) | CI job history |
| **Time from PR open to stack test result** | Under 10 minutes (build + startup + test + teardown) | CI job duration |
| **Smoke test coverage** | All 4 services health-checked, 3+ API paths tested, 1 end-to-end pipeline path proven | Test file inspection |
| **Docker-related bug escapes** | Zero Docker build/startup regressions reaching manual testing after rig is in place | Issue tracker labels (`docker`, `deployment`) — team must label Docker-related issues consistently |
| **CI reliability** | Stack test job flake rate below 5% over rolling 4-week window | GitHub Actions job re-run history (manual review monthly) or `gh run list --workflow` script |

## 8. Context & Assumptions

### Assumptions
- The existing `docker-compose.dev.yml` is the canonical definition of the deployed dev stack. Tests target this file, not a separate test-specific Compose file.
- The Dockerfile at the repo root builds a working image. If it does not, fixing the Dockerfile is in scope for Story 9.4.
- The app exposes `/healthz` as an unauthenticated liveness endpoint (confirmed in existing code).
- The webhook intake endpoint requires valid `X-GitHub-Delivery` and `X-Hub-Signature-256` headers, plus a registered repo profile with a stored webhook secret. Tests must seed a repo profile with a known webhook secret and compute valid HMAC-SHA256 signatures for test payloads. This is a setup step, not a code change — the existing `src/ingress/signature.py` validation stays as-is.
- **Admin API authentication in dev mode:** When `THESTUDIO_LLM_PROVIDER=mock` (set in `docker-compose.dev.yml`), the RBAC middleware (`src/admin/rbac.py`) auto-authenticates requests without an `X-User-ID` header as `dev-admin@localhost` with ADMIN role. This means bare `httpx` calls to admin endpoints (e.g., `POST /admin/repos`, `GET /admin/workflows`) work without any auth setup. Tests should NOT send `X-User-ID` headers — rely on the dev-mode auto-auth.
- **Webhook secret is pinned in `docker-compose.dev.yml`.** The `THESTUDIO_WEBHOOK_SECRET=test-webhook-secret` env var must be added to the app service environment in `docker-compose.dev.yml` (not in a separate override file). All tests compute HMAC signatures using this known value.
- GitHub Actions `ubuntu-latest` runners have Docker and Docker Compose available.
- `httpx` is available as a main dependency for making HTTP requests from test code.

### Dependencies
- **Epic 8 deliverables (Status: Sprint 2 complete, all stories delivered):** Docker Compose file, Dockerfile, health checks are functional. Owner: Backend Engineer. No blockers.
- **Existing CI workflow:** `.github/workflows/ci.yml` -- the new job will be added to this file or as a separate workflow file. Owner: Backend Engineer.
- **Mock providers:** `THESTUDIO_LLM_PROVIDER=mock` and `THESTUDIO_GITHUB_PROVIDER=mock` must produce deterministic behavior for smoke tests. Owner: N/A (already implemented).
- **Webhook signature validation:** Tests require a seeded repo profile with a known webhook secret for HMAC computation. The `src/repo/repo_profile_crud.py` and `src/ingress/signature.py` modules must be stable. Owner: Backend Engineer.

### Systems Affected
- `.github/workflows/` -- new or modified CI workflow
- `tests/docker/` -- new test directory for stack tests
- `scripts/` -- infrastructure readiness script
- `docker-compose.dev.yml` -- may need minor adjustments (e.g., health check tuning)
- `pyproject.toml` -- new pytest marker registration

---

## Story Map

Stories are ordered as vertical slices. Each story delivers testable value independently. Stories 9.1-9.2 are the walking skeleton; 9.3 proves data flow; 9.4 makes it mandatory in CI; 9.5 adds resilience coverage; 9.6 ties the bow.

### Story 9.1: Infrastructure Readiness Script

**As a** developer or CI pipeline,
**I want** a script that waits for all Docker Compose services to be healthy,
**so that** I have a reliable gate before running any tests against the stack.

**Details:**
- Create `scripts/wait-for-stack.sh` (or Python equivalent) that polls health endpoints for PostgreSQL (pg_isready on port 5434), NATS (TCP connection check on port 4222 — note: the HTTP monitoring port 8222 is not exposed to the host in `docker-compose.dev.yml`), Temporal (tctl cluster health on port 7233), and the app (`/healthz` on port 8000).
- Configurable timeout via `--timeout` flag (default 120s).
- Exit 0 when all four services report healthy. Exit 1 with diagnostic output (which services failed, last error) on timeout.
- Also create `tests/docker/conftest.py` with a session-scoped fixture that calls this script and skips all docker-marked tests if the stack is not running.

**Acceptance Criteria:**
- Script exits 0 when all 4 services are healthy.
- Script exits 1 with per-service status when any service fails to become healthy within the timeout.
- Script completes in under 90 seconds on a healthy stack.
- Pytest fixture skips docker tests gracefully when the stack is not running.

### Story 9.2: API Smoke Test Suite

**As a** developer,
**I want** automated tests that hit the deployed app's HTTP endpoints,
**so that** I know the app is serving requests correctly through the real network stack.

**Details:**
- Create `tests/docker/test_api_smoke.py` marked with `@pytest.mark.docker`.
- Tests use `httpx` to issue real HTTP requests to `http://localhost:8000`.
- Test cases:
  - `GET /healthz` returns 200 with `{"status": "ok"}`.
  - `GET /admin/health` returns 200 (or appropriate admin endpoint).
  - `POST /webhook/github` with a valid payload, `X-GitHub-Delivery` header, and valid `X-Hub-Signature-256` (computed with a known test webhook secret from a seeded repo profile) returns 200 or 201 (not 500, not connection refused). See Story 9.3 for full webhook setup details.
  - `GET /docs` (OpenAPI) returns 200.
- All tests depend on the readiness fixture from Story 9.1.

**Acceptance Criteria:**
- All 4 endpoint tests pass against a running Docker Compose stack.
- Tests fail with clear error messages (not connection timeouts) when the stack is down.
- Tests complete in under 30 seconds.

### Story 9.3: Full Pipeline Smoke Through Docker

**As a** platform engineer,
**I want** a test that proves a webhook payload flows through the deployed stack and creates a TaskPacket,
**so that** I know the intake pipeline works end-to-end through real HTTP and real service connections.

**Details:**
- Create `tests/docker/test_pipeline_smoke.py` marked with `@pytest.mark.docker`.
- Create a `tests/docker/conftest.py` fixture that registers a test repo via `POST /admin/repos` (no auth headers needed — dev-mode auto-auth grants ADMIN when `THESTUDIO_LLM_PROVIDER=mock`; see Assumptions). The app container has `THESTUDIO_WEBHOOK_SECRET=test-webhook-secret` set in `docker-compose.dev.yml`. Registered repos inherit this secret. Provide a helper that computes valid `X-Hub-Signature-256` headers using `hmac.new(secret, body, sha256)`.
- Send a well-formed GitHub webhook payload via `httpx.post()` to the deployed app, including required headers (`X-GitHub-Delivery`, `X-GitHub-Event`, `X-Hub-Signature-256`).
- After the POST, verify the TaskPacket was created by querying the admin API endpoint (`GET /admin/workflows` — confirmed at `src/admin/router.py`; no auth headers needed in dev mode). Note: `docker-compose.dev.yml` sets `THESTUDIO_STORE_BACKEND=memory`, so TaskPackets are stored in-memory, not PostgreSQL. Do NOT attempt direct database queries for verification — use only HTTP API responses.
- Assert: TaskPacket exists in the API response, has expected repo/issue fields, status is not "error".

**Acceptance Criteria:**
- Test proves a webhook POST creates a TaskPacket in the deployed stack.
- Test does not depend on any in-process imports (pure HTTP via admin API only).
- Test includes cleanup or is idempotent (can run multiple times without accumulating state).

### Story 9.4: Docker Build & Startup Validation for CI

**As a** CI pipeline,
**I want** a job that builds the Docker image, starts the Compose stack, and runs the smoke tests,
**so that** broken Docker builds or startup failures are caught before merge.

**Details:**
- Create or extend `.github/workflows/ci.yml` with a new job `docker-smoke`.
- Job steps: checkout, `docker compose -f docker-compose.dev.yml build`, `docker compose -f docker-compose.dev.yml up -d`, run readiness script (9.1), run pytest with `docker` marker, `docker compose down -v`.
- Job timeout: 15 minutes.
- Job runs on `push` to master and on `pull_request`.
- Job failure blocks merge (required status check).
- Add `docker` marker to `pyproject.toml` under `[tool.pytest.ini_options]`.

**Acceptance Criteria:**
- CI job builds the image, starts the stack, runs smoke tests, and tears down cleanly.
- Job completes in under 12 minutes on a standard GitHub Actions runner.
- Job failure produces actionable logs (which service failed, which test failed, container logs).
- `docker compose down -v` runs in a `post` step or `always()` block so resources are cleaned up even on failure.

### Story 9.5: Container Lifecycle Tests

**As a** platform engineer,
**I want** tests that verify the stack handles shutdown, restart, and dependency failure gracefully,
**so that** I have confidence in operational resilience before production deployment.

**Details:**
- Create `tests/docker/test_lifecycle.py` marked with `@pytest.mark.docker`.
- Test cases:
  - **Graceful shutdown:** Send SIGTERM to the app container, verify it exits with code 0 within 10 seconds.
  - **Restart recovery:** Restart the app container (`docker compose restart app`), wait for health check, verify `/healthz` returns 200.
  - **Dependency failure:** Stop the Temporal container, send a webhook payload that would trigger a workflow, verify the app returns an error response or logs the failure (not a crash/hang), then restart Temporal and verify the app recovers and passes health checks. Note: Temporal is the correct dependency to test here because `THESTUDIO_STORE_BACKEND=memory` means most endpoints do not use PostgreSQL.
- Tests use `subprocess` or `docker` Python SDK to control containers.

**Acceptance Criteria:**
- Graceful shutdown test confirms exit code 0 after SIGTERM.
- Restart recovery test confirms healthy status within 60 seconds of restart.
- Dependency failure test confirms the app does not crash when Temporal is unavailable.
- All lifecycle tests are idempotent and leave the stack in a running state for subsequent tests.

### Story 9.6: CI Integration & Documentation

**As a** contributor,
**I want** clear documentation on how to run the Docker test rig locally and understand what CI validates,
**so that** I can troubleshoot failures and extend the rig as the platform grows.

**Details:**
- Add a `tests/docker/README.md` explaining: how to start the stack, how to run tests locally (`pytest -m docker`), how to read CI failures, how to add new smoke tests.
- Ensure the CI job output includes container logs on failure (e.g., `docker compose logs` in the failure handler).
- Add a CI badge or status reference in the project README if one exists.
- Register the `docker` pytest marker in `pyproject.toml` with a description.

**Acceptance Criteria:**
- A new contributor can run the Docker test rig locally by following the README instructions.
- CI failure output includes container logs for all 4 services.
- `pytest --markers` shows the `docker` marker with a description.

---

## Meridian Review Status

### Round 1: FAIL -- Fixable (5 must-fix items)

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Wrong webhook path (`/webhooks/github`) | Fixed to `/webhook/github` (matches `src/ingress/webhook_handler.py:29`) |
| 2 | Webhook auth has no mock bypass | Added explicit HMAC signature setup: seed repo profile + compute signatures in test fixtures |
| 3 | `STORE_BACKEND=memory` contradicts DB verification | Removed DB queries from AC-3 and Story 9.3; verification via admin API only |
| 4 | NATS port 8222 not exposed to host | Changed to TCP check on port 4222 in Story 9.1 |
| 5 | Dependencies have no owners or status | Added owners and Epic 8 completion status |

Also addressed should-fix items: replaced "developer confidence" metric, made Compose project name mandatory for CI, reconciled webhook auth with no-app-code-changes non-goal (solution: test fixture setup, not app changes).

### Round 2: PASS

All 7 questions passed. Two should-fix items addressed inline:
- Pinned webhook secret seeding to `THESTUDIO_WEBHOOK_SECRET` env var + `POST /admin/repos`
- Removed stale "optional DB query" reference from Story 9.3
- Pinned endpoint name to `GET /admin/workflows` (confirmed in source)

### Round 3: FAIL -- Fixable (3 must-fix, 4 should-fix)

| # | Type | Issue | Resolution |
|---|------|-------|------------|
| 1 | Must-fix | AC-2 said "200/202" but webhook handler returns 200/201, never 202 | Fixed to "200 or 201" (matches `src/ingress/webhook_handler.py`) |
| 2 | Must-fix | Admin API auth not addressed — `POST /admin/repos` and `GET /admin/workflows` require RBAC | Documented dev-mode auto-auth: when `THESTUDIO_LLM_PROVIDER=mock`, RBAC auto-authenticates bare requests as `dev-admin@localhost` with ADMIN role (`src/admin/rbac.py:412`). No auth headers needed in tests. Added to Assumptions and Story 9.3 details. |
| 3 | Must-fix | AC-5 dependency failure test untestable with `THESTUDIO_STORE_BACKEND=memory` — stopping PostgreSQL has no observable effect | Changed dependency-failure target from PostgreSQL to Temporal (the meaningful runtime dependency under memory store) in AC-5 and Story 9.5 |
| 4 | Should-fix | `THESTUDIO_WEBHOOK_SECRET` location left ambiguous ("docker-compose.dev.yml or test override") | Pinned to `docker-compose.dev.yml` only — no override file |
| 5 | Should-fix | "At least 1 real issue caught in 30 days" is a hope, not a controllable metric | Replaced with "All 4 services health-checked, 3+ API paths tested, 1 end-to-end pipeline path proven" |
| 6 | Should-fix | Flake rate metric needs instrumentation plan | Added measurement method: `gh run list --workflow` script or manual monthly review of re-run history |
| 7 | Should-fix | AC-3 used `STORE_BACKEND=memory` (no prefix) inconsistently with actual env var | Standardized to `THESTUDIO_STORE_BACKEND` throughout |
