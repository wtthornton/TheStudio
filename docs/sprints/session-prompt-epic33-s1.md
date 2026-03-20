# Sprint Plan: Epic 33 Sprint 1 -- P0 Deployment Test Harness (Foundation + Deployment-Mode Integration)

**Planned by:** Helm
**Date:** 2026-03-20
**Status:** APPROVED -- Meridian reviewed 2026-03-20 (CONDITIONAL PASS, must-fixes applied)
**Epic:** `docs/epics/epic-33-p0-deployment-test-harness.md`
**Sprint Duration:** 1 week (5 working days, 2026-03-24 to 2026-03-28)
**Capacity:** Single developer, 30 hours total (5 days x 6 productive hours), 77% allocation = 23 hours, 7 hours buffer

---

## Sprint Goal (Testable Format)

**Objective:** Deliver a unified health gate that verifies all 5 Docker services before any P0 test runs, a runner script that handles env loading and credential validation, and deployment-mode integration tests for GitHub webhook intake and Postgres persistence -- all exercising the deployed stack through Caddy on port 9443 (HTTPS, self-signed).

**Test:** After all stories (33.1 through 33.5) are complete:

1. `python -m tests.p0.health` (or `pytest tests/p0/test_health_gate.py`) reports pass/fail for all 5 services (app, Caddy, Postgres, Temporal, NATS) and completes in under 15 seconds.
2. Stopping the Caddy container, then running the health gate, produces a clear abort message naming Caddy as the failed service.
3. `scripts/run-p0-tests.sh` sources `infra/.env`, runs the health gate, validates credentials (rejects empty/placeholder API keys), and returns nonzero when any check fails.
4. `pytest tests/p0/test_github_deployed.py -v` registers a test repo via `/admin/repos` through Caddy with Basic Auth, sends an HMAC-signed webhook to `/webhook/github`, and verifies the app returns 200/202.
5. `pytest tests/p0/test_postgres_deployed.py -v` sends a webhook, then queries `/admin/workflows` through Caddy with Basic Auth and verifies a workflow record exists in Postgres.
6. All existing tests continue to pass (`pytest tests/` green, excluding P0 tests that require the Docker stack).

**Constraint:** 5 working days. New files confined to `tests/p0/`, `scripts/run-p0-tests.sh`, and documentation updates. No modifications to production source code (`src/`). No modifications to `docker-compose.dev.yml`. Eval test refactoring (AC 2) is explicitly deferred to Sprint 2 -- this sprint focuses on the health gate, runner, and integration test deployment modes.

---

## What's In / What's Out

**In this sprint (5 stories, ~22 estimated hours):**
- Story 33.1: Docker Stack Health Gate Module (AC 1)
- Story 33.2: Runner Script with Env Loading and Credential Guard (AC 5, 7, 8 partial)
- Story 33.3: P0 Test Conftest -- Shared Deployment-Mode Fixtures (AC 3, 4 foundation)
- Story 33.4: Deployment-Mode GitHub Integration Tests (AC 3)
- Story 33.5: Deployment-Mode Postgres Integration Tests (AC 4 partial -- webhook-through-API path)

**Deferred to Sprint 2:**
- AC 2: Eval tests guarded by stack health (requires design decision on how to validate container config without an eval HTTP endpoint)
- AC 6: Results persistence (structured output with cost tracking)
- Story 33.8: False-pass validation (manual Caddy-down verification)
- Story 33.9: Documentation update

**Out of scope (entire epic):**
- CI integration for deployment-mode tests
- New eval HTTP endpoints
- Modifications to `docker-compose.dev.yml`

---

## Dependency Review (30-Minute Pre-Planning)

### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| Docker stack running (`infra/docker-compose.prod.yml`) | Must be `up` before tests | All deployment-mode tests skip | Health gate aborts with clear message; no silent pass |
| Real credentials in `infra/.env` | Required for all P0 tests | Tests cannot authenticate | Credential guard (Story 33.2) rejects placeholders before any test runs |
| Caddy HTTPS on port 9443 | Required for all through-Caddy tests | Tests cannot reach the app | See Risk R1 below -- HTTP redirect means tests MUST use HTTPS |
| `ADMIN_USER` / `ADMIN_PASSWORD_HASH` in `.env` | Required for admin API calls | Cannot register repos or query workflows | Conftest reads credentials from env; guard validates they exist |
| `THESTUDIO_WEBHOOK_SECRET` in container | Required for HMAC signature verification | Webhook rejects all payloads | Runner script validates secret is set and matches test config |
| `httpx` with HTTPS support | Already in dependencies | Cannot make HTTPS requests | `httpx` supports `verify=False` for self-signed certs |

### Internal Dependencies (Story Order)

```
33.1 (Health Gate) ──> 33.2 (Runner Script) ──> 33.3 (Conftest)
                                                    │
                                                    ├──> 33.4 (GitHub Deployed)
                                                    └──> 33.5 (Postgres Deployed)
```

**33.1 must come first** -- the health gate is a prerequisite for the runner script and all deployment-mode tests.
**33.3 must precede 33.4 and 33.5** -- shared fixtures (Caddy client, Basic Auth, webhook signing) are consumed by both test files.
**33.4 and 33.5 are independent** -- can be implemented in either order.

### Critical Technical Finding: Caddy TLS Redirect

The Caddyfile configures:
- Port 9443 (mapped from 443 inside Caddy): `localhost { tls internal }` -- serves HTTPS with self-signed cert
- Port 9080 (mapped from 80 inside Caddy): `:80 { redir https://{host}{uri} permanent }` -- redirects all HTTP to HTTPS

**Impact:** Tests hitting `http://localhost:9080` will receive a 301 redirect to `https://localhost/...` (which won't resolve). All deployment-mode tests MUST hit `https://localhost:9443` with `verify=False` (self-signed cert). The epic text says "port 9080" in AC 3 and AC 4 -- this is incorrect. The conftest (Story 33.3) must use `https://localhost:9443` as the base URL.

**Alternative:** Add a non-redirecting HTTP listener to the Caddyfile. However, the Constraints section says this epic targets the production stack as-is. Decision: tests use HTTPS on 9443 with `verify=False`. This is the correct approach because it tests the actual production path.

---

## Ordered Backlog

### Story 33.1: Docker Stack Health Gate Module
**Points:** 5 (medium) | **Estimated hours:** 5 | **AC:** 1

**What:** Create `tests/p0/__init__.py` and `tests/p0/health.py` with functions that probe all 5 Docker services and return a structured health report. Create `tests/p0/test_health_gate.py` that exercises the health gate and validates the 15-second ceiling.

**Service probes:**
| Service | Probe Method | Endpoint/Target |
|---------|-------------|-----------------|
| App | HTTP GET | `https://localhost:9443/healthz` (verify=False) |
| Caddy | TCP connect + HTTP response | `https://localhost:9443` (any 2xx/3xx) |
| Postgres | TCP connect on pg-proxy | `localhost:5434` |
| Temporal | HTTP GET | Temporal API health (or TCP to exposed port if available) |
| NATS | TCP connect | `localhost:4222` (NATS client port -- check if exposed) |

**Risk: Temporal and NATS ports not exposed.** The prod compose does NOT expose Temporal (7233) or NATS (4222) to the host. Only Caddy (9080/9443) and pg-proxy (5434) are exposed.

**Mitigation options (decide during implementation):**
1. **Indirect probe via app healthz:** If `/healthz` checks Temporal and NATS internally, a single healthz call covers 3 services (app + Temporal + NATS). Verify what `/healthz` actually checks.
2. **Add port mappings to prod compose for test access.** This modifies prod compose -- acceptable per epic constraints (only dev compose is off-limits).
3. **Probe via `docker compose exec`** commands to check service health from inside the Docker network.

Recommended: Option 1 first (check what `/healthz` covers), fall back to Option 3 if needed.

**Done criteria:**
- `tests/p0/health.py` exists with `check_all_services() -> HealthReport` function
- `HealthReport` is a dataclass/TypedDict with per-service pass/fail and overall status
- Failed service names and remediation hints appear in the output
- Total check time < 15 seconds (enforced by timeout, not hope)
- `tests/p0/test_health_gate.py` has at least 3 tests: all-healthy path, individual service failure message format, timeout enforcement

**Resolved unknowns (Meridian review):**
- **`/healthz` is a trivial liveness probe** (`src/app.py:133-136`): returns `{"status": "ok"}` without checking Temporal, NATS, or Postgres. Option 1 (indirect via healthz) will NOT work. Use Option 3 (`docker compose exec`) or add port mappings.
- Temporal/NATS are NOT reachable from host. Recommended: `docker compose exec temporal tctl cluster health` (mirrors the container's own healthcheck at line 178 of compose file).

---

### Story 33.2: Runner Script with Env Loading and Credential Guard
**Points:** 5 (medium) | **Estimated hours:** 5 | **AC:** 5, 7, 8

**What:** Create `scripts/run-p0-tests.sh` that orchestrates the full P0 test ceremony: source env, validate credentials, run health gate, run test suites.

**Script flow:**
```
1. set -euo pipefail
2. set -a; source infra/.env; set +a
3. Validate: THESTUDIO_ANTHROPIC_API_KEY not empty, starts with "sk-ant-"
4. Validate: POSTGRES_PASSWORD not empty, not "thestudio_dev" (placeholder)
5. Validate: ADMIN_USER and ADMIN_PASSWORD_HASH are set
6. Validate: THESTUDIO_WEBHOOK_SECRET is set
7. Run health gate: python -m tests.p0.health (exit on failure)
8. Run deployment-mode integration tests: pytest tests/p0/ -v
9. (Sprint 2: run eval tests with stack-health guard)
10. Report summary and exit code
```

**Done criteria:**
- `scripts/run-p0-tests.sh` is executable (`chmod +x`)
- Running with empty `THESTUDIO_ANTHROPIC_API_KEY` exits with error message before any test runs
- Running with `THESTUDIO_ANTHROPIC_API_KEY=placeholder` exits with error (does not start with `sk-ant-`)
- Running with `POSTGRES_PASSWORD=thestudio_dev` exits with error (placeholder detected)
- Env is loaded via `source`, not `grep|cut`
- Script works on bash (Linux/macOS/WSL)
- Exit code is nonzero if any suite fails

**Compressible:** If time is short, the eval suite integration (step 9) is already deferred. The credential validation can be simplified to "not empty" checks only, deferring the format validation (sk-ant- prefix) as a nice-to-have.

---

### Story 33.3: P0 Test Conftest -- Shared Deployment-Mode Fixtures
**Points:** 3 (small) | **Estimated hours:** 4 | **AC:** 3, 4 foundation

**What:** Create `tests/p0/conftest.py` with shared fixtures that deployment-mode tests consume. This is the bridge between the existing `tests/docker/conftest.py` patterns and the new P0 tests.

**Fixtures to provide:**

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `require_healthy_stack` | session, autouse | Runs health gate; skips all P0 tests if stack is down |
| `caddy_client` | session | `httpx.Client` with `base_url="https://localhost:9443"`, `verify=False`, Basic Auth header for admin routes |
| `unauthenticated_client` | session | `httpx.Client` with `base_url="https://localhost:9443"`, `verify=False`, no auth (for webhook endpoint) |
| `webhook_secret` | session | Reads `THESTUDIO_WEBHOOK_SECRET` from env |
| `registered_test_repo` | session | Registers a test repo via `POST /admin/repos` with Basic Auth; returns repo data. Tolerates 409 (already registered). |
| `compute_signature(body, secret)` | function (helper) | HMAC-SHA256 signature for webhook payloads -- reuse from `tests/docker/conftest.py`. **Meridian MF-2:** All P0 calls MUST pass the env-sourced `THESTUDIO_WEBHOOK_SECRET` explicitly (the docker helper defaults to `"test-webhook-secret"` which won't match prod). |
| `build_webhook_headers(body, event, delivery_id)` | function (helper) | Full GitHub webhook header set -- reuse from `tests/docker/conftest.py`. Must pass env-sourced secret. |
| `make_issue_payload(owner, repo, ...)` | function (helper) | Minimal valid GitHub issues webhook payload -- reuse from `tests/docker/conftest.py` |

**Key decisions:**
- **Reuse, don't duplicate** helpers from `tests/docker/conftest.py`. Import `compute_signature`, `build_webhook_headers`, `make_issue_payload` directly. If imports create coupling issues, extract to a shared `tests/helpers/` module.
- **Basic Auth credentials** come from `ADMIN_USER` (default: `admin`) and `ADMIN_PASSWORD` (plaintext, NOT the hash). The hash is for Caddy config. Tests need the plaintext password. **Decision (Meridian MF-1):** Add `ADMIN_PASSWORD=<plaintext>` to `infra/.env`. Story 33.2's credential guard validates it exists. Story 33.3's `caddy_client` fixture reads it for Basic Auth.
- **Self-signed TLS:** All httpx clients use `verify=False`.

**Done criteria:**
- `tests/p0/conftest.py` exists with all fixtures listed above
- `pytest tests/p0/ --collect-only` succeeds (fixtures resolve without error)
- Health gate auto-skip works: stopping the app container causes all P0 tests to show as "skipped"

---

### Story 33.4: Deployment-Mode GitHub Integration Tests
**Points:** 5 (medium) | **Estimated hours:** 5 | **AC:** 3

**What:** Create `tests/p0/test_github_deployed.py` that exercises the deployed app's webhook intake through Caddy. These tests prove that a GitHub webhook sent to the production stack is accepted, HMAC-verified, and creates a TaskPacket.

**Test cases:**

| # | Test | What it proves |
|---|------|---------------|
| 1 | `test_webhook_accepted_with_valid_signature` | POST to `/webhook/github` with HMAC-signed payload returns 200 or 202. Proves: Caddy reverse proxy works, app receives the webhook, HMAC verification passes. |
| 2 | `test_webhook_rejected_without_signature` | POST without `X-Hub-Signature-256` returns 401 or 400. Proves: webhook security is enforced in the deployed stack, not just in unit tests. |
| 3 | `test_webhook_creates_workflow` | POST a valid webhook for a registered repo, then GET `/admin/workflows` and verify a workflow record exists with the expected repo. Proves: webhook -> intake -> TaskPacket -> Postgres persistence is working end-to-end in the deployed stack. |
| 4 | `test_webhook_through_caddy_not_bypassed` | Confirm that the webhook endpoint is reachable on port 9443 (through Caddy) and NOT on port 8000 (which should not be exposed). Proves: tests exercise the production network path. |

**Requires from conftest (Story 33.3):**
- `unauthenticated_client` for webhook POST (webhooks are not behind Basic Auth per Caddyfile)
- `caddy_client` for admin API queries (GET `/admin/workflows`)
- `registered_test_repo` for repo registration
- `webhook_secret` for HMAC signing
- `compute_signature`, `build_webhook_headers`, `make_issue_payload` helpers

**Done criteria:**
- All 4 tests pass when the Docker stack is running with valid credentials
- Tests skip cleanly when the Docker stack is not running (health gate)
- Tests use HTTPS on port 9443, not HTTP on 8000
- No test uses direct Python imports of application code (all interaction through HTTP)

---

### Story 33.5: Deployment-Mode Postgres Integration Tests
**Points:** 3 (small) | **Estimated hours:** 3 | **AC:** 4 (partial -- webhook-through-API path)

**What:** Create `tests/p0/test_postgres_deployed.py` that proves the deployed app's Postgres persistence works by exercising it through the API. Unlike the existing `tests/integration/test_postgres_backend.py` (which creates its own SQLAlchemy engine), these tests prove the *deployed container's* database connection, migrations, and persistence layer.

**Test cases:**

| # | Test | What it proves |
|---|------|---------------|
| 1 | `test_workflow_persisted_after_webhook` | Send a webhook, query `/admin/workflows`, verify a workflow exists. Proves: app container -> Postgres connection pool -> write -> read round-trip works in the deployed stack. |
| 2 | `test_workflow_has_expected_fields` | Query `/admin/workflows/{id}` for a known workflow and verify it has `repo_name`, `status`, `current_step`, `started_at` populated. Proves: ORM mapping and schema migrations ran correctly in the production container. |
| 3 | `test_repo_registration_persists` | Register a repo via `POST /admin/repos`, restart the query (new HTTP session), query `/admin/repos` or re-register (expect 409). Proves: Postgres persistence survives across requests (not just in-memory store). |

**Overlap with 33.4:** Test 1 here overlaps with test 3 in Story 33.4. This is intentional -- Story 33.4 proves the webhook path; Story 33.5 proves the persistence path. The webhook is the mechanism, but the assertion focus is different (HTTP response vs. database state).

**Done criteria:**
- All 3 tests pass when the Docker stack is running with `THESTUDIO_STORE_BACKEND=postgres`
- Tests skip cleanly when the Docker stack is not running
- No test creates its own SQLAlchemy engine or connects directly to Postgres
- All database verification goes through the admin API

**Compressible:** If time is short, test 2 (field verification) can be deferred. Tests 1 and 3 are the minimum viable proof.

---

## Estimation Summary

| Story | Points | Hours | Risk | Notes |
|-------|--------|-------|------|-------|
| 33.1 Health Gate | 5 | 5 | Medium | Temporal/NATS port exposure unknown |
| 33.2 Runner Script | 5 | 5 | Low | Shell scripting, well-defined |
| 33.3 P0 Conftest | 3 | 4 | Medium | Caddy TLS + Basic Auth credentials gap |
| 33.4 GitHub Deployed | 5 | 5 | Medium | Depends on webhook secret alignment |
| 33.5 Postgres Deployed | 3 | 3 | Low | Uses established admin API endpoints |
| **Total** | **21** | **22** | | 73% of 30h capacity |

**Buffer:** 8 hours (27%) reserved for:
- Resolving the Caddy HTTPS redirect issue if `verify=False` is not sufficient
- Debugging credential alignment between host env and container env
- Temporal/NATS probe strategy (if indirect via healthz is insufficient)

---

## Risk Register

| # | Risk | Severity | Mitigation | Story Affected |
|---|------|----------|------------|----------------|
| R1 | **Caddy HTTPS redirect:** Port 9080 redirects to HTTPS. Tests MUST use `https://localhost:9443` with `verify=False` for self-signed cert. The epic text says "port 9080" -- this is incorrect. | High | Conftest uses 9443. Document the correction. If httpx has issues with self-signed certs, add `REQUESTS_CA_BUNDLE` or modify Caddyfile to add a plain HTTP test listener. | 33.3, 33.4, 33.5 |
| R2 | **Basic Auth plaintext password not in `.env`:** The `.env` has `ADMIN_PASSWORD_HASH` (bcrypt hash for Caddy). Tests need the *plaintext* password for Basic Auth. No `ADMIN_PASSWORD` variable exists. | Medium | Add `ADMIN_PASSWORD` to `infra/.env` and `.env.example`. Runner script validates it exists. | 33.2, 33.3 |
| R3 | **Temporal and NATS ports not exposed to host:** Prod compose only exposes 9080, 9443, and 5434. Health gate cannot directly probe Temporal (7233) or NATS (4222) from the host. | Medium | Check if `/healthz` probes these services internally. If not, use `docker compose exec` to run health checks inside the network, or add port mappings to prod compose. | 33.1 |
| R4 | **Webhook secret alignment:** The test must sign payloads with the same secret the container expects (`THESTUDIO_WEBHOOK_SECRET`). If the runner sources the same `.env`, this should align. But if the container has a different value (e.g., from a previous deploy), signatures will fail. | Low | Runner script validates `THESTUDIO_WEBHOOK_SECRET` is set and non-empty. Tests read the same env var. | 33.4 |
| R5 | **Admin API auth mode in prod vs. dev:** The existing `tests/docker/conftest.py` says "dev-mode auto-auth, no headers needed." Prod compose goes through Caddy which enforces Basic Auth on `/admin/*`. Tests must include auth headers. | Low | Conftest provides `caddy_client` with Basic Auth built in. All admin calls use this client. | 33.3, 33.4, 33.5 |

---

## Compressible Stories (What Gets Cut If Time Runs Short)

1. **Story 33.5 (Postgres Deployed)** can be reduced to a single test (test 1 only) -- saves ~1.5 hours.
2. **Story 33.2 (Runner Script)** credential format validation (sk-ant- prefix check) can be deferred -- saves ~0.5 hours. Keep the "not empty" check.

If both compressions activate, the sprint still delivers: health gate, basic runner script, conftest, and GitHub deployment-mode tests. That is the minimum viable proof that the deployed stack's webhook intake works end-to-end.

---

## Sprint 2 Preview (Not Committed)

Sprint 2 will cover:
- **AC 2:** Eval tests guarded by stack health -- the runner validates container config (LLM provider, API key) before running existing eval tests in-process. No new HTTP endpoints needed (Meridian review RF-1 resolved: eval tests stay in-process per AC 2, the guard is a preflight check, not an HTTP eval endpoint).
- **AC 6:** Results persistence -- structured Markdown output from the runner script.
- **Story 33.8:** False-pass validation (intentional Caddy-down test).
- **Story 33.9:** Documentation update.

---

## Meridian Review Checklist

This plan requires Meridian review before commit. Key questions for review:

1. **Caddy HTTPS decision:** Is `https://localhost:9443` with `verify=False` the right approach, or should we add a plain HTTP test listener to the Caddyfile?
2. **ADMIN_PASSWORD in .env:** Adding a plaintext password variable -- is this acceptable from a security perspective, or should we use a different auth mechanism for tests?
3. **Temporal/NATS probe strategy:** If `/healthz` does not check these services, is adding port mappings to prod compose acceptable?
4. **AC 2 deferred:** Is it acceptable to defer eval-test guarding to Sprint 2, given that eval tests remain in-process and the guard is a preflight check?
5. **Story count:** 5 stories at 73% allocation with 27% buffer -- is this appropriate given the infrastructure unknowns?

---

## Meridian Review: CONDITIONAL PASS (2026-03-20)

### 7-Question Checklist

| # | Question | Verdict |
|---|----------|---------|
| 1 | Is the order of work justified? | **Pass** |
| 2 | Are sprint goals testable? | **Pass** |
| 3 | Are dependencies visible and tracked? | **Pass (gap fixed)** — MF-2 applied: webhook secret handling added to Story 33.3/33.4 |
| 4 | Is estimation reasoning recorded? | **Pass** |
| 5 | Are unknowns surfaced and buffered for? | **Pass** |
| 6 | Does the plan reflect learning from previous retros? | **Pass** |
| 7 | Can the team execute async without daily clarification? | **Pass (gap fixed)** — MF-1 applied: `ADMIN_PASSWORD` decision committed |

### Must-Fix Items (Both Resolved)

**MF-1 (Q7):** `ADMIN_PASSWORD` was a placeholder ("resolve during implementation"). Fixed: committed decision to add `ADMIN_PASSWORD=<plaintext>` to `infra/.env`, validated in Story 33.2, consumed in Story 33.3.

**MF-2 (Q3):** Webhook secret mismatch risk. Fixed: all P0 calls to `compute_signature` must pass env-sourced `THESTUDIO_WEBHOOK_SECRET` explicitly. Docker conftest default `"test-webhook-secret"` does not match prod.

### Key Technical Findings Applied

- `/healthz` is trivial liveness probe (returns `{"status": "ok"}`). Option 1 won't work. Applied to Story 33.1.
- Caddy HTTPS on 9443 with `verify=False` approved — tests the actual production path.
- Temporal/NATS probe via `docker compose exec temporal tctl cluster health` recommended.

### No Auto-Reject Red Flags

Goals have measurable targets, dependencies tracked, AC machine-verifiable, non-goals explicit, 73% allocation (not 100%).

**Verdict:** CONDITIONAL PASS — must-fixes applied inline. Plan is ready for execution.
