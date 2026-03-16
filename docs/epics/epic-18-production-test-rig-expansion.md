# Epic 18 — Production E2E Test Suite Delivers Full Contract Coverage

**Author:** Saga
**Date:** 2026-03-12
**Status:** COMPLETE — All 5 slices delivered (2026-03-16)
**Target Sprint:** Sprint 22 (delivered)

---

## 1. Title

Production E2E Test Suite Delivers Full Contract Coverage — Split the monolithic production test rig into focused test modules covering health, webhook signature validation, admin API, poll intake, and pipeline smoke, closing the gap between what the contract promises and what the rig actually validates.

## 2. Narrative

The production test rig (`thestudio-production-test-rig/`) exists to answer one question: "Is this deployment healthy and behaving correctly?" Today it does not answer that question well enough.

The rig has a single test file (`tests/test_production_smoke.py`) with five test classes covering health, admin health, OpenAPI docs, poll config, and poll E2E. That is a good start, but there are visible gaps:

**The webhook endpoint is untested.** The README claims webhook signature validation is tested ("Valid signed POST to `/webhook/github` returns 200 or 201; missing signature returns 401") but no such test exists. The contract in `docs/production-test-rig-contract.md` does not list webhook validation either, but the README advertises it and the deployment exposes `/webhook/github` with HMAC-SHA256 signature validation via `src/ingress/signature.py`. A production test rig that cannot verify its own intake path is a rig that lies to you.

**The single-file structure does not scale.** As Epic 17 (poll intake) and future work add more endpoints, one file becomes a maintenance burden. Test isolation suffers — a conftest change intended for poll tests affects health tests. Pytest markers and selective runs become harder when everything lives in one module.

**The contract and the rig have drifted.** The contract lists repo registration and profile PATCH endpoints. The rig tests them inside `TestPollConfig` but not as standalone admin API validation. Repo list (`GET /admin/repos`) is used only as a helper, never asserted as a first-class endpoint. The contract says "what the test rig should validate" but the rig validates a subset.

This epic closes those gaps. It splits the monolith into focused modules, adds the missing webhook signature tests, adds standalone admin API tests, and ensures every endpoint listed in the contract has at least one dedicated test. The result: a rig that CI can run against any deployment and get an honest answer.

## 3. References

| Artifact | Location |
|----------|----------|
| Production test rig contract | `docs/production-test-rig-contract.md` |
| Current test rig source | `thestudio-production-test-rig/tests/test_production_smoke.py` |
| Current conftest | `thestudio-production-test-rig/tests/conftest.py` |
| Test rig README | `thestudio-production-test-rig/README.md` |
| Webhook handler | `src/ingress/webhook_handler.py` |
| Signature validation | `src/ingress/signature.py` |
| URL reference | `docs/URLs.md` |
| Epic 17 (poll intake) | `docs/epics/epic-17-poll-for-issues-backup.md` |
| Epic 15 (E2E integration) | `docs/epics/epic-15-e2e-integration-real-repo.md` |
| Prod compose | `infra/docker-compose.prod.yml` |

## 4. Acceptance Criteria

1. **Module split complete.** The test rig has separate test files: `test_health.py`, `test_webhook.py`, `test_admin_api.py`, `test_poll_intake.py`, and `test_pipeline_smoke.py`. Each is independently runnable via `pytest tests/test_health.py`.
2. **Webhook signature tests exist and pass.** At minimum: (a) POST to `/webhook/github` with a valid HMAC-SHA256 signature and well-formed issue payload returns 200 or 201; (b) POST without `X-Hub-Signature-256` returns 401; (c) POST with an invalid signature returns 401 or 403. Tests use `WEBHOOK_SECRET` from environment (already documented in README).
3. **Admin API has standalone tests.** `test_admin_api.py` covers: (a) `GET /admin/health` returns 200 with `overall_status`; (b) `POST /admin/repos` creates a repo (201) or reports conflict (409); (c) `GET /admin/repos` returns a list; (d) `GET /admin/repos/{id}` returns repo detail; (e) `PATCH /admin/repos/{id}/profile` updates fields. These are not entangled with poll-specific logic.
4. **Contract alignment verified.** Every endpoint listed in the "Contract: endpoints and behavior" section of `docs/production-test-rig-contract.md` has at least one test in the rig. A mapping table in the test rig README documents which test file covers which contract endpoint.
5. **Conftest remains shared.** The `conftest.py` provides `http_client`, `require_deployment`, `base_url`, and a new `webhook_secret` fixture. Module-specific fixtures live in their own files or test classes.
6. **CI workflow unchanged in structure.** `pytest -v` still runs all tests. Selective module runs are possible but not required by CI.
7. **README updated.** The test rig README reflects the new file structure, the webhook tests, and the contract-to-test mapping.
8. **No TheStudio application code changes.** This epic modifies only the `thestudio-production-test-rig/` directory and `docs/production-test-rig-contract.md`. No changes to `src/`, `tests/`, or `infra/`.

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Webhook secret not available in test environment | Medium | High — webhook tests fail or skip silently | Make `WEBHOOK_SECRET` required for webhook module; clear skip message if missing |
| Webhook endpoint expects real GitHub payload shape | Medium | Medium — tests pass with minimal payload but miss edge cases | Use realistic payload fixtures based on actual GitHub webhook examples |
| Poll tests depend on Epic 17 endpoints not yet deployed | Low | Medium — tests skip in environments without poll | Guard poll tests with a pytest marker and env check; skip cleanly |
| Splitting files introduces import errors | Low | Low — caught immediately by pytest collection | Run `pytest --collect-only` as validation step |

## 5. Constraints & Non-Goals

### Constraints

- All test rig code lives in `thestudio-production-test-rig/`. No changes to the main TheStudio `src/` or `tests/` directories.
- Tests must work with self-signed TLS (existing `THESTUDIO_INSECURE_TLS` support).
- Tests must be idempotent — re-running does not corrupt deployment state.
- Tests must skip cleanly (not fail) when the deployment is unreachable or a required env var is missing.
- Python 3.12+, httpx, pytest — no new runtime dependencies.

### Non-Goals

- **No Playwright or browser tests.** Admin UI testing is Epic 12's scope.
- **No load testing or performance benchmarking.** This is functional validation only.
- **No changes to the webhook handler itself.** If the handler has bugs, this epic surfaces them; it does not fix them.
- **No pipeline-end-to-end validation** (issue in, PR out). That is Epic 15's scope. The "pipeline smoke" module here checks only that a webhook or poll triggers TaskPacket creation (observable via admin API), not that the full pipeline completes.
- **No auth beyond dev-mode `X-User-ID`.** Production auth (OAuth, tokens) is out of scope until the auth system is implemented.
- **No contract changes for new endpoints.** If a new endpoint is needed, update the contract in a follow-up, not this epic.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Saga | Definition, scope, story map |
| Tech Lead | Implementation agent | Module split, fixture design, webhook test implementation |
| QA | Meridian (review) | Validate acceptance criteria coverage, flag gaps |
| External | GitHub API | Webhook payload format, signature algorithm (HMAC-SHA256) |

## 7. Success Metrics

| Metric | Target | How Measured |
|--------|--------|-------------|
| Contract endpoint coverage | 100% of endpoints in contract have >= 1 test | Manual audit: contract endpoints vs test files |
| Test count | >= 12 individual test functions (up from 5) | `pytest --collect-only \| grep "test session starts"` |
| Webhook test coverage | >= 3 webhook tests (valid sig, missing sig, bad sig) | `pytest tests/test_webhook.py --collect-only` |
| Clean skip behavior | All modules skip gracefully when deployment unreachable | Run with no deployment; verify 0 failures, all skipped |
| README-to-reality match | README "What is tested" section matches actual test files | Code review |
| CI pass rate | Green on first run against a healthy deployment | CI workflow result |

## 8. Context & Assumptions

### Assumptions

- The deployment under test has `THESTUDIO_WEBHOOK_SECRET` set and the webhook endpoint is functional. If the secret is unavailable, webhook tests skip.
- The `X-User-ID: dev-admin@localhost` auto-provision works for admin API calls in mock/dev deployments (confirmed in `conftest.py`).
- Poll endpoints (`/admin/poll/run`) may not be deployed yet if Epic 17 is incomplete. Poll tests use a pytest marker and skip if the endpoint returns 404.
- GitHub webhook payload format follows the standard `issues` event schema: `{"action": "opened", "issue": {...}, "repository": {"full_name": "owner/repo"}, ...}`.
- The existing CI workflow (`.github/workflows/production-smoke.yml`) runs `pytest -v` and does not need structural changes; new test files are auto-discovered.

### Dependencies

| Dependency | Status | Impact if Missing |
|-----------|--------|-------------------|
| Deployed TheStudio instance | Required | All tests skip |
| `WEBHOOK_SECRET` env var | Required for webhook module | Webhook tests skip, others run |
| `THESTUDIO_POLL_TEST_REPO` env var | Required for poll E2E | Poll E2E tests skip, others run |
| Epic 17 poll endpoints | Optional | Poll tests skip if 404 |

### Systems Affected

- `thestudio-production-test-rig/tests/` — primary work area
- `thestudio-production-test-rig/README.md` — documentation update
- `docs/production-test-rig-contract.md` — contract-to-test mapping (addendum only, no endpoint changes)

---

## Story Map

### Slice 1 — Foundation: Module Split and Conftest Hardening (Risk Reduction)

> Split the monolith first so every subsequent slice lands in the right file.

**Story 1.1: Split test_production_smoke.py into focused modules**
- Extract `TestHealth` into `tests/test_health.py`
- Extract `TestAdminHealth` and `TestOpenAPI` into `tests/test_admin_api.py`
- Extract `TestPollConfig` and `TestPollE2E` into `tests/test_poll_intake.py`
- Create empty `tests/test_webhook.py` and `tests/test_pipeline_smoke.py` with class stubs
- Verify: `pytest --collect-only` discovers all existing tests in new locations; zero failures
- **Files to modify/create:**
  - `thestudio-production-test-rig/tests/test_health.py` (create)
  - `thestudio-production-test-rig/tests/test_admin_api.py` (create)
  - `thestudio-production-test-rig/tests/test_poll_intake.py` (create)
  - `thestudio-production-test-rig/tests/test_webhook.py` (create, stubs)
  - `thestudio-production-test-rig/tests/test_pipeline_smoke.py` (create, stubs)
  - `thestudio-production-test-rig/tests/test_production_smoke.py` (delete or keep as re-export for backwards compat)

**Story 1.2: Harden conftest with webhook_secret fixture and skip helpers**
- Add `webhook_secret` fixture that reads `WEBHOOK_SECRET` from env; returns `pytest.skip` if missing
- Add `poll_enabled` fixture that probes `/admin/poll/run` for 404 and skips if unavailable
- Keep `http_client` and `require_deployment` unchanged
- Verify: running with no env vars gives clean skips, no errors
- **Files to modify/create:**
  - `thestudio-production-test-rig/tests/conftest.py` (modify)

### Slice 2 — Webhook Signature Tests (Highest-Value Gap)

> This is the biggest lie in the current README. Fix it.

**Story 2.1: Add webhook test with valid signature**
- Construct a minimal but realistic GitHub `issues` event payload (action: opened, issue object, repository with full_name)
- Compute HMAC-SHA256 using `WEBHOOK_SECRET`
- POST to `/webhook/github` with `X-Hub-Signature-256`, `X-GitHub-Delivery` (UUID), `X-GitHub-Event: issues` headers
- Assert 200 or 201 (handler may create TaskPacket or skip if repo not registered; both are valid)
- **Files to modify/create:**
  - `thestudio-production-test-rig/tests/test_webhook.py` (implement)

**Story 2.2: Add webhook test for missing signature (401)**
- POST to `/webhook/github` without `X-Hub-Signature-256` header
- Assert 401
- **Files to modify/create:**
  - `thestudio-production-test-rig/tests/test_webhook.py` (add test)

**Story 2.3: Add webhook test for invalid signature (401/403)**
- POST to `/webhook/github` with a deliberately wrong `X-Hub-Signature-256`
- Assert 401 or 403
- **Files to modify/create:**
  - `thestudio-production-test-rig/tests/test_webhook.py` (add test)

**Story 2.4: Add webhook test for missing delivery header (400)**
- POST with valid signature but no `X-GitHub-Delivery` header
- Assert 400
- **Files to modify/create:**
  - `thestudio-production-test-rig/tests/test_webhook.py` (add test)

### Slice 3 — Standalone Admin API Tests

> Decouple admin API validation from poll-specific logic.

**Story 3.1: Add repo registration and listing tests**
- `POST /admin/repos` with test payload, assert 201 or 409
- `GET /admin/repos`, assert 200 and response contains `repos` list
- `GET /admin/repos/{id}` for the registered repo, assert 200 and body includes `owner`, `repo`
- **Files to modify/create:**
  - `thestudio-production-test-rig/tests/test_admin_api.py` (implement)

**Story 3.2: Add repo profile PATCH test (standalone)**
- PATCH `/admin/repos/{id}/profile` with `{"poll_enabled": false}`, assert 200
- Verify `updated_fields` in response
- GET repo detail, verify field updated
- Clean up: restore original value
- **Files to modify/create:**
  - `thestudio-production-test-rig/tests/test_admin_api.py` (add test)

### Slice 4 — Pipeline Smoke (Webhook-Triggered TaskPacket)

> Prove that a webhook actually enters the pipeline, not just returns 200.

**Story 4.1: Add pipeline smoke test via webhook**
- Register a test repo via admin API
- Send a valid signed webhook for that repo
- Query admin API to verify a TaskPacket was created (or that the repo shows activity)
- This is a thin smoke test, not full pipeline validation (that is Epic 15)
- Skip if `WEBHOOK_SECRET` is not set
- **Files to modify/create:**
  - `thestudio-production-test-rig/tests/test_pipeline_smoke.py` (implement)

### Slice 5 — Contract Alignment and Documentation

> Make the README honest and the contract traceable.

**Story 5.1: Add contract-to-test mapping to README**
- Create a table in the README mapping every contract endpoint to the test file and test class that covers it
- Verify no contract endpoint is unmapped
- **Files to modify/create:**
  - `thestudio-production-test-rig/README.md` (update)

**Story 5.2: Update contract with test rig cross-reference**
- Add a "Test Coverage" section to `docs/production-test-rig-contract.md` listing which test modules cover which contract sections
- No new endpoints; documentation only
- **Files to modify/create:**
  - `docs/production-test-rig-contract.md` (append section)

**Story 5.3: Clean up old monolith file**
- Delete `tests/test_production_smoke.py` (all tests now live in focused modules)
- Run full `pytest -v` to confirm zero regressions
- **Files to modify/create:**
  - `thestudio-production-test-rig/tests/test_production_smoke.py` (delete)

---

## Meridian Review Status

### Round 1: CONDITIONAL PASS — 3 must-fix items

**Date:** 2026-03-16
**Verdict:** CONDITIONAL PASS → all 3 must-fix items resolved in implementation

| # | Question | Status | Notes |
|---|----------|--------|-------|
| 1 | Goal testable? | PASS | Concrete and falsifiable |
| 2 | Acceptance criteria testable? | GAP → Fixed | MF-1: Header validation order (tests include all required headers); MF-3: Story 2.1 self-contained (tests specify full payload + register repo first) |
| 3 | Non-goals explicit? | PASS | Six clear non-goals with cross-references |
| 4 | Dependencies identified? | GAP → Fixed | MF-2: Webhook endpoint added to contract |
| 5 | Metrics measurable? | PASS | All 6 metrics verifiable with existing tooling |
| 6 | AI-implementable? | GAP → Fixed | Story 2.1 specifies payload shape, headers, and repo registration prerequisite |
| 7 | Narrative compelling? | PASS | README lie identified, structural concerns escalated |

### Must-Fix Resolutions

| MF | Issue | Resolution |
|----|-------|------------|
| MF-1 | AC 2(b)/(c) header validation order | Tests include `X-GitHub-Delivery` when testing missing/invalid signatures. Missing delivery tested separately (Story 2.4). |
| MF-2 | Webhook endpoint missing from contract | Added webhook section to `docs/production-test-rig-contract.md` with headers, responses, and validation order. |
| MF-3 | Story 2.1 not self-contained | Implementation registers repo via admin API, specifies `action: "opened"` payload with all required headers and realistic GitHub payload shape. |

### Round 2: COMMITTABLE

All 3 must-fix items resolved. Advisory items noted (A-2: OpenAPI placement is organizational preference, kept in admin_api for now).
