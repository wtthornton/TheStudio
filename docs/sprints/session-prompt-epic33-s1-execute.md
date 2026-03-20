# Session Prompt: Execute Epic 33 Sprint 1 — P0 Deployment Test Harness

## Context

**Phase 8 has begun** (2026-03-20). Phase 7 is complete. All 33 prior epics delivered.

**What was just done (2026-03-20):**
- Two critical deployment blockers fixed:
  - `publish_activity` wired to real `publish()` — creates real PRs when `github_provider=real` (10 new tests)
  - Migration auto-run added to app lifespan — DB schema created on startup when `store_backend=postgres`
- Epic 31 Meridian review: PASS (formal sign-off)
- Epic 33 Sprint 1 plan: Helm-created, Meridian-reviewed (CONDITIONAL PASS, must-fixes applied)
- Epic status tracker updated with Phase 8 section

**Test health:** 1,842+ unit tests, 9 E2E pipeline, ~244 integration. 84% coverage. Zero failures from our changes (2 pre-existing date-dependent failures in `test_model_spend.py` and `test_workflow_trigger.py`).

---

## Sprint 1 Goal

Deliver a unified health gate, runner script, and deployment-mode integration tests that exercise the deployed Docker stack through Caddy on HTTPS port 9443.

**Full sprint plan:** `docs/sprints/session-prompt-epic33-s1.md` (Meridian-approved)

---

## Story Execution Order

Execute stories in this exact order (dependencies flow downward):

### Story 33.1: Docker Stack Health Gate Module (5h)

Create `tests/p0/__init__.py`, `tests/p0/health.py`, `tests/p0/test_health_gate.py`.

**Probes:** App (HTTPS healthz), Caddy (HTTPS connect), Postgres (TCP 5434).

**Critical finding:** `/healthz` is trivial — returns `{"status": "ok"}` without checking Temporal/NATS/Postgres. Temporal and NATS ports are NOT exposed to host. Use `docker compose exec` to probe them:
- Temporal: `docker compose -f infra/docker-compose.prod.yml exec temporal tctl cluster health`
- NATS: `docker compose -f infra/docker-compose.prod.yml exec nats nats-server --signal health`

**Done when:**
- `check_all_services() -> HealthReport` returns per-service pass/fail
- Failed services named with remediation hints
- Total check time < 15 seconds
- 3+ tests: healthy path, failure message format, timeout enforcement

### Story 33.2: Runner Script (5h)

Create `scripts/run-p0-tests.sh`.

**Flow:**
```
set -euo pipefail
set -a; source infra/.env; set +a
# Validate credentials (reject empty/placeholder)
# Run health gate
# Run pytest tests/p0/ -v
# Report summary
```

**Credential guards:** `THESTUDIO_ANTHROPIC_API_KEY` (not empty, starts with `sk-ant-`), `POSTGRES_PASSWORD` (not `thestudio_dev`), `ADMIN_USER`, `ADMIN_PASSWORD` (plaintext, NOT hash), `THESTUDIO_WEBHOOK_SECRET`.

**Done when:** Empty/placeholder credentials abort before any test runs. Exit code nonzero on failure.

### Story 33.3: P0 Conftest (4h)

Create `tests/p0/conftest.py` with shared fixtures.

**Key fixtures:**
- `require_healthy_stack` — session autouse, skips if stack down
- `caddy_client` — httpx with `https://localhost:9443`, `verify=False`, Basic Auth from `ADMIN_USER`/`ADMIN_PASSWORD`
- `unauthenticated_client` — same base URL, no auth (for webhooks)
- `webhook_secret` — from `THESTUDIO_WEBHOOK_SECRET` env var
- `registered_test_repo` — registers via `POST /admin/repos`, tolerates 409
- Helpers: `compute_signature`, `build_webhook_headers`, `make_issue_payload` — import from `tests/docker/conftest.py`

**Meridian must-fix applied:** All calls to `compute_signature` MUST pass env-sourced `THESTUDIO_WEBHOOK_SECRET` explicitly. The docker helper defaults to `"test-webhook-secret"` which won't match prod.

**Meridian must-fix applied:** `ADMIN_PASSWORD` (plaintext) must be added to `infra/.env`. Story 33.2's guard validates it. This fixture reads it for Basic Auth.

**Done when:** `pytest tests/p0/ --collect-only` succeeds. Stopping app container causes all P0 tests to skip.

### Story 33.4: Deployment-Mode GitHub Integration Tests (5h)

Create `tests/p0/test_github_deployed.py` — 4 tests:

1. `test_webhook_accepted_with_valid_signature` — POST webhook, expect 200/202
2. `test_webhook_rejected_without_signature` — POST without HMAC, expect 401/400
3. `test_webhook_creates_workflow` — POST webhook, GET `/admin/workflows`, verify record exists
4. `test_webhook_through_caddy_not_bypassed` — port 9443 reachable, port 8000 NOT exposed

**All interaction through HTTP.** No Python imports of application code.

### Story 33.5: Deployment-Mode Postgres Integration Tests (3h)

Create `tests/p0/test_postgres_deployed.py` — 3 tests:

1. `test_workflow_persisted_after_webhook` — webhook -> query workflows -> exists
2. `test_workflow_has_expected_fields` — repo_name, status, current_step populated
3. `test_repo_registration_persists` — register, re-register -> 409 (data survived)

**Compressible:** If short on time, cut test 2. Tests 1 and 3 are minimum viable.

---

## Technical Reference

**Key files to read before starting:**
- `tests/docker/conftest.py` — existing deployment-test helpers (compute_signature, build_webhook_headers)
- `infra/docker-compose.prod.yml` — production Docker stack (services, ports, healthchecks)
- `infra/Caddyfile` — TLS config, port 9443, HTTP->HTTPS redirect on 9080
- `src/app.py:120-136` — `/healthz` endpoint (trivial liveness probe only)
- `src/ingress/webhook_handler.py` — webhook endpoint, HMAC validation
- `src/admin/router.py` — admin API routes (`/admin/repos`, `/admin/workflows`)

**Caddy TLS:** All tests MUST use `https://localhost:9443` with `verify=False`. Port 9080 redirects to HTTPS and will NOT work. This tests the actual production path.

**Exposed ports (prod compose):**
- 9080 (HTTP -> redirect to HTTPS)
- 9443 (HTTPS, self-signed cert)
- 5434 (pg-proxy to Postgres)
- Temporal (7233) and NATS (4222) are NOT exposed

---

## Risks to Watch

| # | Risk | Mitigation |
|---|------|------------|
| R1 | Caddy HTTPS `verify=False` may have httpx edge cases | httpx handles this well. If issues, test with `REQUESTS_CA_BUNDLE` |
| R2 | `ADMIN_PASSWORD` plaintext not in `.env` yet | Add it as first action in Story 33.2 |
| R3 | Temporal/NATS not reachable from host | Use `docker compose exec` commands |
| R4 | Webhook secret mismatch between host env and container | Runner sources same `.env` used by compose. Validate alignment. |
| R5 | Admin API auth differs in prod (Caddy Basic Auth) vs dev (auto-auth) | `caddy_client` fixture includes Basic Auth header |

---

## Constraints

- New files in `tests/p0/`, `scripts/run-p0-tests.sh`, and docs only
- NO modifications to `src/` production code
- NO modifications to `docker-compose.dev.yml`
- Eval test refactoring (AC 2) deferred to Sprint 2
- Results persistence (AC 6) deferred to Sprint 2

---

## Definition of Done (Sprint Level)

All 6 sprint tests pass (from sprint plan):

1. Health gate reports pass/fail for 5 services, completes < 15s
2. Stopping Caddy -> health gate names Caddy as failed service
3. `run-p0-tests.sh` rejects empty/placeholder credentials
4. GitHub deployed tests: webhook accepted, rejected, creates workflow, via Caddy
5. Postgres deployed tests: persistence round-trip through admin API
6. All existing tests still pass (`pytest tests/unit/ tests/integration/` green)

---

## After Sprint 1 Completes

**Sprint 2 scope (preview, not committed):**
- AC 2: Eval tests guarded by stack health (preflight check, not HTTP endpoint)
- AC 6: Results persistence (structured Markdown with cost tracking)
- False-pass validation (intentional service-down test)
- Documentation update

**Production deployment:** Once Sprint 1 passes on the deployed stack, attempt processing a real GitHub issue at Observe tier.
