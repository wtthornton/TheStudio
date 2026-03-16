# Production Test Rig Contract

TheStudio is a multi-repo system. **One dedicated repo** runs tests against a **deployed** production (or staging) instance. That test rig does not start Docker or build TheStudio; it assumes the system is already running and validates it over HTTP/HTTPS.

This document defines the contract between TheStudio and the dedicated test rig so both repos can evolve independently.

## Scope

- **TheStudio repo:** Application code, unit/integration tests, and **in-repo** Docker smoke tests that start the **dev** stack and run `tests/docker/`.
- **Test rig repo:** Standalone test suite that runs against a **live** deployment (production or staging). Configurable base URL, no dependency on TheStudio source.

## Test rig responsibilities

- Read base URL and secrets from environment (or `.env`).
- Assume the deployment is already up (no `docker compose up`).
- Use only public or documented APIs over HTTP(S).
- Be idempotent where possible (e.g. tolerate "repo already registered" 409).

## Contract: endpoints and behavior

### Base URL

- **Production (shared host):** `https://localhost:9443` (or your deployment URL).
- **Dev (reference):** `http://localhost:8000`.
- Set via `THESTUDIO_BASE_URL` (or `BASE_URL`) in the test rig. No trailing slash.
- Full URL reference (health, admin UI, API, webhook): **TheStudio docs/URLs.md**.

### TLS

- Production uses a self-signed cert by default. The test rig must either disable TLS verification for that host or trust the cert (e.g. `verify=False` in httpx, or `NODE_TLS_REJECT_UNAUTHORIZED=0` for Node).

### Health (unauthenticated)

| Endpoint     | Method | Expected | Purpose        |
|-------------|--------|----------|----------------|
| `/healthz`  | GET    | 200, `{"status":"ok"}` | Liveness       |
| `/readyz`   | GET    | 200, `{"status":"ready"}` | Readiness (DB) |

### Admin API (authenticated)

- **Dev / mock:** When `THESTUDIO_LLM_PROVIDER=mock`, the app auto-provisions `X-User-ID: dev-admin@localhost` as admin. Use that header for admin API calls in the test rig when testing mock deployments.
- **Production with real providers:** Admin may require real auth; the test rig may need a dedicated test user or token if you enable auth.
- **Endpoints used by the test rig:**

| Endpoint           | Method | Purpose                          |
|--------------------|--------|----------------------------------|
| `/admin/health`    | GET    | Fleet health (Temporal, NATS, DB) |
| `/admin/repos`     | POST   | Register repo (body: owner, repo, installation_id, default_branch) |
| `/admin/repos`     | GET    | List repos (for verification)    |
| `/docs`            | GET    | OpenAPI docs                     |

### Poll intake (Epic 17 — E2E tests, no webhook)

| Endpoint           | Method | Purpose                          |
|--------------------|--------|----------------------------------|
| `/admin/poll/run`  | POST   | Trigger one poll cycle (for testing) |

- Requires `THESTUDIO_INTAKE_POLL_ENABLED=true` and `THESTUDIO_INTAKE_POLL_TOKEN` on the deployment.
- Response: `{repos_polled, issues_created, rate_limit_hit}`.

### Webhook intake

| Endpoint | Method | Required Headers | Expected | Purpose |
|----------|--------|------------------|----------|---------|
| `/webhook/github` | POST | `X-GitHub-Delivery` (UUID), `X-Hub-Signature-256` (HMAC-SHA256), `X-GitHub-Event` | 200/201 (valid), 400 (missing delivery header), 401 (missing/invalid signature), 404 (unregistered repo) | GitHub webhook intake |

- Payload: GitHub `issues` event JSON (`action: "opened"`, `issue: {number, title, body}`, `repository: {full_name}`).
- Signature: HMAC-SHA256 of raw request body using `THESTUDIO_WEBHOOK_SECRET`. Header format: `sha256=<hex>`.
- Header validation order: delivery header checked before signature. Missing delivery returns 400 even with valid signature.
- Repo must be registered via `POST /admin/repos` before webhooks are accepted (unregistered repos return 404).

### Repo registration

- POST `/admin/repos` with JSON: `{"owner":"...","repo":"...","installation_id":12345,"default_branch":"main"}`.
- 201 = created; 409 = already registered (test rig may treat as success for idempotency).

### Repo profile (poll config)

- PATCH `/admin/repos/{id}/profile` with JSON: `{"poll_enabled": true, "poll_interval_minutes": 10}` (all fields optional).
- 200 = updated. Response includes `updated_fields`.
- GET `/admin/repos/{id}` returns full profile including `poll_enabled`, `poll_interval_minutes`.

## What the test rig should validate

1. **Health:** GET `/healthz` and `/readyz` return 200 with expected body.
2. **Fleet health:** GET `/admin/health` returns 200 and `overall_status` (e.g. OK).
3. **Webhook signature:** Valid HMAC-SHA256 accepted (200/201), missing signature rejected (401), invalid signature rejected (401/403), missing delivery header rejected (400).
4. **Admin API:** Repo registration (POST 201/409), listing (GET), detail (GET), profile update (PATCH).
5. **Poll config:** Register repo, PATCH profile with `poll_enabled`, GET repo to verify.
6. **Poll E2E:** Register real repo, enable poll, POST `/admin/poll/run`, verify `repos_polled` >= 0 and `rate_limit_hit` is false.
7. **Pipeline smoke:** Register repo, send valid webhook, verify 200/201 (proves intake path works end-to-end).

## CI and multi-repo

- The test rig repo’s CI job does **not** start TheStudio. It runs pytest (or equivalent) with `THESTUDIO_BASE_URL` and `WEBHOOK_SECRET` set (e.g. from CI secrets pointing at a staging or production URL).
- TheStudio’s CI continues to run in-repo Docker smoke tests against the **dev** stack it starts. The dedicated test rig runs separately against the deployment you configure.

## Test Coverage Mapping

Every contract endpoint is covered by at least one test in the production test rig.

| Contract Endpoint | Method | Test Module | Test Class/Function |
|-------------------|--------|-------------|---------------------|
| `/healthz` | GET | `test_health.py` | `TestHealth.test_healthz_returns_200` |
| `/readyz` | GET | `test_health.py` | `TestHealth.test_readyz_returns_200` |
| `/admin/health` | GET | `test_admin_api.py` | `TestAdminHealth.test_admin_health_returns_200` |
| `/docs` | GET | `test_admin_api.py` | `TestOpenAPI.test_docs_returns_200` |
| `/admin/repos` | POST | `test_admin_api.py` | `TestRepoRegistration.test_repo_registration_returns_201_or_409` |
| `/admin/repos` | GET | `test_admin_api.py` | `TestRepoRegistration.test_repo_list_returns_repos` |
| `/admin/repos/{id}` | GET | `test_admin_api.py` | `TestRepoRegistration.test_repo_detail_returns_profile` |
| `/admin/repos/{id}/profile` | PATCH | `test_admin_api.py` | `TestRepoRegistration.test_repo_profile_patch` |
| `/admin/poll/run` | POST | `test_poll_intake.py` | `TestPollE2E.test_poll_run_fetches_issues` |
| `/webhook/github` | POST | `test_webhook.py` | `TestWebhookSignature` (4 tests) |
| `/webhook/github` (pipeline) | POST | `test_pipeline_smoke.py` | `TestPipelineSmoke.test_webhook_triggers_taskpacket` |

## Reference

- In-repo Docker smoke tests: `TheStudio/tests/docker/` (dev stack, port 8000).
- Production deployment: `TheStudio/infra/docker-compose.prod.yml` (default HTTPS port 9443).
- This contract: `TheStudio/docs/production-test-rig-contract.md`.
- **Dedicated test rig scaffold:** `TheStudio/thestudio-production-test-rig/` — copy or extract that folder (including `.github/workflows/`) as the root of a separate repo to run tests against production. See that folder’s README for setup and CI (GitHub Actions with `THESTUDIO_BASE_URL` and `WEBHOOK_SECRET`).
