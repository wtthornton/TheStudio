# Epic 33: P0 Deployment Test Harness

> **Status:** Planned
> **Epic Owner:** Primary Developer
> **Duration:** 2-3 sprints (~4-6 weeks)
> **Created:** 2026-03-18
> **Meridian Review:** Round 1: Pending

---

## 1. Title

**Every P0 Test Proves the Deployed Stack Works, Not Just the Source Code**

---

## 2. Narrative

TheStudio has 35 P0 tests across three suites: eval (25 tests, real Anthropic API), GitHub integration (4 tests), and Postgres integration (6 tests). All 35 passed during Epic 30 validation. The problem is *how* they passed.

The eval tests call `_enable_real_llm(monkeypatch)` to patch the in-process settings object, then invoke agent code directly via Python imports. They never touch the deployed FastAPI app running in Docker. If the Dockerfile missed a dependency, if an environment variable was misspelled in `docker-compose.prod.yml`, if Caddy was down for 32 hours (it was) -- these tests would still pass.

The GitHub integration tests instantiate `ResilientGitHubClient` directly in the test process. They prove the adapter works in isolation. They do not prove the deployed app can receive a webhook, route it through intake, and use that same adapter to create a PR.

The Postgres integration tests create their own SQLAlchemy engine from `settings.database_url`. They prove the ORM works. They do not prove the deployed app's database connection pool is healthy or that migrations ran correctly in the production container.

Meanwhile, the `tests/docker/` suite already demonstrates the correct pattern: a conftest that hits `localhost:8000/healthz`, session-scoped HTTP clients, and tests that exercise the deployed stack through its public API surface. But the P0 suites were never integrated into this pattern.

The operational ceremony compounds the problem. Running P0 tests today requires: manually exporting env vars (using a `grep|cut` command that breaks on comments in `.env`), manually starting a pg-proxy container, running three separate pytest commands, and remembering to clean up. There is no single script, no health pre-check, no results persistence.

This epic creates a unified P0 test harness that: (1) verifies all Docker services are healthy before any test runs, (2) refactors eval and integration tests to exercise the deployed app through HTTP endpoints rather than in-process imports, (3) provides a single `scripts/run-p0-tests.sh` that handles the full ceremony, and (4) saves structured results to `docs/eval-results/` for traceability.

**Why now:** The Caddy-down-for-32-hours incident is the proof point. The P0 tests passed while a critical service was offline. Every epic from here forward builds on the assumption that the deployed stack works. That assumption must be tested, not implied.

---

## 3. References

| Artifact | Location |
|----------|----------|
| Existing Docker test conftest (correct pattern) | `tests/docker/conftest.py` |
| Docker smoke tests (API, pipeline, lifecycle) | `tests/docker/test_api_smoke.py`, `test_pipeline_smoke.py`, `test_lifecycle.py` |
| Eval suite (monkeypatch-based) | `tests/eval/test_intent_eval.py`, `test_primary_eval.py`, `test_qa_eval.py`, `test_routing_eval.py` |
| GitHub integration tests (direct import) | `tests/integration/test_real_github.py` |
| Postgres integration tests (own engine) | `tests/integration/test_postgres_backend.py` |
| P0 test results (Epic 30) | `docs/eval-results/p0-integration-tests.md` |
| Production Docker Compose | `infra/docker-compose.prod.yml` |
| CI workflow (current) | `.github/workflows/ci.yml` |
| Epic 30 (Real Provider Integration) | `docs/epics/epic-30-real-provider-integration.md` |
| Settings (feature flags, env vars) | `src/settings.py` |
| Eval harness framework | `src/eval/` |

---

## 4. Acceptance Criteria

### AC 1: Unified Health Gate

A health check module exists that verifies all required Docker services (app, Caddy, Postgres, Temporal, NATS) are healthy before any P0 test begins. If any service is unreachable, the entire P0 run aborts with a clear diagnostic message naming the failed service(s) and suggesting remediation. The health gate runs in under 15 seconds.

### AC 2: Eval Tests Guarded by Stack Health

Eval tests remain in-process (no HTTP eval endpoint exists and building one is out of scope). However, the runner script validates that: (a) the Docker stack is healthy (all 5 services), (b) the container's `THESTUDIO_LLM_PROVIDER` is `anthropic` (not `mock`), and (c) the API key in the container matches the key used for tests. This ensures eval tests cannot pass while the deployed stack is misconfigured. The existing `tests/eval/` tests run unchanged via the runner.

### AC 3: Deployment-Mode GitHub Integration Tests

GitHub integration tests have deployment-mode variants that exercise the deployed app's webhook endpoint (`POST /webhook/github`) through Caddy on port 9080 with HTTP Basic Auth. Tests register a repo via `/admin/repos`, send HMAC-signed webhook payloads using helpers from `tests/docker/conftest.py` (`compute_signature`, `build_webhook_headers`), and verify the app accepts the webhook and creates a TaskPacket queryable via `/admin/workflows`.

### AC 4: Deployment-Mode Postgres Integration Tests

Postgres integration tests have deployment-mode variants that exercise the deployed app's persistence through its API: (1) send a webhook to create a TaskPacket, (2) query `/admin/workflows` to verify the TaskPacket was persisted in Postgres, (3) verify enrichment data is stored. Tests go through Caddy on port 9080 with Basic Auth. The admin endpoint for workflow listing (`GET /admin/workflows?repo_id=...`) is used for verification.

### AC 5: Single Runner Script

`scripts/run-p0-tests.sh` exists and handles: sourcing `infra/.env` correctly (using `source` or `set -a`, not `grep|cut`), verifying Docker stack health (AC 1), injecting required credentials, running all three P0 suites in sequence, collecting results, saving structured output to `docs/eval-results/`, and returning a nonzero exit code if any suite fails. The script works on both Linux and macOS (WSL for Windows).

### AC 6: Results Persistence

Each P0 run produces a timestamped results file in `docs/eval-results/` with: date, suite-by-suite pass/fail counts, total duration, total API cost, and any failures with enough context to diagnose without re-running. The latest results file is also symlinked or referenced from a `docs/eval-results/latest.md`.

### AC 7: Env File Parsing Fixed

The `infra/.env` file is either cleaned up to remove inline comments that break naive parsing, or the runner script and documentation exclusively use `source`-based loading that handles comments correctly. The broken `grep|cut` pattern documented in `docs/eval-results/p0-integration-tests.md` is replaced.

### AC 8: Placeholder Credential Guard

The runner script validates that critical environment variables (`THESTUDIO_ANTHROPIC_API_KEY`, `THESTUDIO_GITHUB_TOKEN`, `POSTGRES_PASSWORD`) contain real values, not placeholders or empty strings, before starting any test. Eval tests additionally verify the API key starts with `sk-ant-`.

---

## 4b. Top Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R1 | Eval tests currently invoke agent code synchronously; converting to HTTP may require new API endpoints | High — scope creep if many endpoints needed | Audit existing API surface first; reuse `/admin/eval/run` if it exists, or add a single thin endpoint |
| R2 | Eval tests cost ~$5/run; deployment-mode tests may double cost if they duplicate runs | Medium — budget pressure | Share eval runs between modes; deployment tests use the same 3-case subsets, not full 10-case sets |
| R3 | Caddy TLS termination may complicate localhost test access | Medium — tests may need HTTP bypass | Tests hit app:8000 directly through Docker network or via Caddy HTTP (port 9080), not HTTPS |
| R4 | GitHub webhook tests need a real webhook secret matching the container | Low — config alignment | Runner script reads the same `.env` the container uses |

---

## 5. Constraints & Non-Goals

### Constraints

- **No modifications to `docker-compose.dev.yml`**: The dev compose is for local development; this epic targets the production stack (`docker-compose.prod.yml`).
- **No test code shipped in the Docker image**: The Dockerfile correctly excludes `tests/` and dev deps. All test execution happens on the host, hitting Docker services over the network.
- **Budget ceiling**: A single P0 run must stay under $6 total API cost. If deployment-mode tests would exceed this, they must share results with in-process tests rather than duplicate calls.
- **Backward compatibility**: Existing in-process eval and integration tests continue to work unchanged. Deployment-mode tests are additive, not replacements.

### Non-Goals

- **CI integration for deployment-mode tests**: Adding the Docker prod stack to GitHub Actions is a follow-on epic. This epic creates the harness for local/staging use.
- **Performance benchmarking**: This epic validates correctness, not latency SLAs.
- **Fixing QA eval scoring**: The QA defect detection rate issue (0/7) is a scoring tuning problem, not a deployment problem. Out of scope.
- **TLS/certificate setup for Caddy**: Caddy TLS configuration is an infra hardening concern (Epic 11 territory).
- **Multi-environment support**: The runner targets a single local Docker stack. Supporting remote staging/production environments is future work.

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Primary Developer | Implementation, test refactoring, script authoring |
| Reviewer | Meridian | Epic review, story completeness, risk assessment |
| Planner | Helm | Sprint sequencing, dependency ordering |
| QA | Automated (pytest + runner script) | Test execution and results validation |
| External | Anthropic API | Eval test dependency; rate limits and cost |
| External | GitHub API | Integration test dependency; test repo access |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Service-down detection rate** | 100% of Docker service failures caught before test execution | Health gate blocks test run when any service is down |
| **Deployment coverage** | All 35 P0 tests have deployment-mode equivalents OR are explicitly documented as in-process-only with justification | Audit log in results file |
| **Runner ceremony time** | < 2 minutes from `./scripts/run-p0-tests.sh` to first test execution | Timed in script output |
| **False-pass elimination** | Zero P0 tests pass when Caddy or app container is stopped | Validated by intentionally stopping Caddy and running the harness |
| **Single-command execution** | Operator runs one script, gets pass/fail for all 3 suites | Script exit code and results file |
| **Results traceability** | Every P0 run has a timestamped results file in `docs/eval-results/` | File existence check |

---

## 8. Context & Assumptions

### Business Rules

- P0 tests are the minimum bar for deployment confidence. If P0 tests pass against the deployed stack, the stack is considered ready for real issue processing.
- Eval tests require a valid Anthropic API key. The runner must never expose this key in logs or results files.
- GitHub integration tests use the `wtthornton/thestudio-production-test-rig` repository. This repo must exist and the token must have push access.

### Dependencies

- **Docker stack running**: `infra/docker-compose.prod.yml` must be `up` with all services healthy before the runner starts.
- **Real credentials in `infra/.env`**: The runner sources this file; it must contain real values for `THESTUDIO_ANTHROPIC_API_KEY`, `POSTGRES_PASSWORD`, and the app must be configured with `THESTUDIO_LLM_PROVIDER=anthropic`.
- **pg-proxy service**: The production compose already includes a `pg-proxy` on port 5434. No manual socat container needed.
- **Network access**: Host must reach `localhost:9080` (Caddy), `localhost:8000` (if app port is exposed), and `localhost:5434` (pg-proxy).

### Systems Affected

| System | Impact |
|--------|--------|
| `tests/eval/` | New deployment-mode test files added alongside existing tests |
| `tests/integration/` | New deployment-mode test files for GitHub and Postgres suites |
| `tests/docker/conftest.py` | May be extended with shared fixtures for P0 tests |
| `scripts/run-p0-tests.sh` | New file |
| `docs/eval-results/` | New timestamped results files per run |
| `infra/.env` | Comments cleaned up or documented as requiring `source`-based loading |
| `docs/eval-results/p0-integration-tests.md` | "How to Re-Run" section updated to reference new script |

### Assumptions

- The app container exposes sufficient API endpoints to exercise eval, GitHub, and Postgres paths through HTTP. If not, minimal new endpoints will be added (scoped to what is testable, not building a full eval API).
- The existing `tests/docker/conftest.py` pattern (session-scoped health check, httpx client) is the correct foundation and will be extended, not replaced.
- The production compose does NOT expose port 8000 to the host directly (Caddy fronts it). Tests either go through Caddy on 9080 or the compose is temporarily modified to expose 8000. The preferred approach is through Caddy on 9080 to test the full production path.

---

## Story Map

### Slice 1: Foundation (Health Gate + Runner Script)

**Goal:** Single script that checks all services and fails fast if anything is down.

**Story 33.1: Docker Stack Health Gate Module**
Create `tests/p0/health.py` with functions to check each Docker service (app via `/healthz`, Caddy via HTTP probe on 9080, Postgres via pg-proxy connection test, Temporal via `tctl cluster health` or API probe, NATS via connection probe). Returns structured health report. Fails with clear diagnostics.
- Files to create: `tests/p0/__init__.py`, `tests/p0/health.py`
- Files to modify: none
- AC: AC 1

**Story 33.2: Runner Script (scripts/run-p0-tests.sh)**
Create the orchestrator script. Sources `infra/.env` using `set -a; source infra/.env; set +a`. Runs health gate. Validates credentials (not empty, not placeholder). Runs all P0 suites via pytest. Captures exit codes. Saves results summary. Returns nonzero if any suite fails.
- Files to create: `scripts/run-p0-tests.sh`
- Files to modify: none
- AC: AC 5, AC 7, AC 8

**Story 33.3: Fix .env Parsing and Credential Documentation**
Audit `infra/.env` for inline comments that break `key=value` parsing. Either clean the file or document that `source` is the only supported loading method. Update `docs/eval-results/p0-integration-tests.md` to replace the broken `grep|cut` pattern with the script reference.
- Files to modify: `infra/.env` (if comments need cleanup), `docs/eval-results/p0-integration-tests.md`
- AC: AC 7

### Slice 2: Deployment-Mode Integration Tests

**Goal:** GitHub and Postgres integration tests that exercise the deployed app through Caddy.

**Story 33.4: P0 Test Conftest (Shared Fixtures)**
Create `tests/p0/conftest.py` with shared fixtures for deployment-mode tests: Caddy base URL (`http://localhost:9080`), httpx client with Basic Auth (credentials from `ADMIN_USER`/`ADMIN_PASSWORD` env vars sourced from `infra/.env`), health gate auto-skip, webhook HMAC signing helpers (reuse `compute_signature`/`build_webhook_headers` from `tests/docker/conftest.py`), and registered repo fixture.
- Files to create: `tests/p0/conftest.py`
- AC: AC 3, AC 4

**Story 33.5: Deployment-Mode GitHub Integration Tests**
Create `tests/p0/test_github_deployed.py` that exercises the deployed app's webhook intake endpoint (`POST /webhook/github`) through Caddy on port 9080. Tests: (1) register a repo via `POST /admin/repos` with Basic Auth, (2) send HMAC-signed webhook payload, (3) verify the app returns 200/202, (4) query `GET /admin/workflows` to verify a TaskPacket was created. Reuses webhook auth helpers from conftest.
- Files to create: `tests/p0/test_github_deployed.py`
- AC: AC 3

**Story 33.6: Deployment-Mode Postgres Integration Tests**
Create `tests/p0/test_postgres_deployed.py` that exercises the deployed app's persistence: (1) send a webhook to create a TaskPacket, (2) query `GET /admin/workflows?repo_id=...` to verify the TaskPacket persists in Postgres, (3) verify the workflow has progressed beyond RECEIVED status (proving context enrichment ran). Tests go through Caddy with Basic Auth.
- Files to create: `tests/p0/test_postgres_deployed.py`
- AC: AC 4

### Slice 3: Results and Polish

**Goal:** Structured results output and documentation.

**Story 33.7: Results Collector and Persistence**
Extend the runner script to produce a structured results file (Markdown with tables) in `docs/eval-results/p0-{date}-{time}.md`. Include: suite name, test count, pass/fail, duration, cost estimate, and failure details. Create or update `docs/eval-results/latest.md` to point to the most recent run.
- Files to modify: `scripts/run-p0-tests.sh`
- Files to create: results template logic (inline in script or `tests/p0/results.py`)
- AC: AC 6

**Story 33.8: False-Pass Validation Test**
Create a manual or scripted validation that intentionally stops the Caddy container, runs the health gate, and confirms the P0 harness refuses to proceed. Document this as a one-time validation in the results file. This is the proof that the harness catches the exact failure mode that motivated this epic.
- Files to modify: none (manual validation, documented in results)
- AC: Success metric: false-pass elimination

**Story 33.9: Documentation Update**
Update `docs/eval-results/p0-integration-tests.md` "How to Re-Run" section to reference `scripts/run-p0-tests.sh`. Add a brief section to the project README or CLAUDE.md noting the P0 test harness exists and how to invoke it.
- Files to modify: `docs/eval-results/p0-integration-tests.md`, optionally `CLAUDE.md`
- AC: AC 5 (documentation aspect)

---

## Meridian Review Status

### Round 1: 2026-03-18 — CONDITIONAL PASS (3 gaps must be resolved before commit)

| # | Question | Verdict | Detail |
|---|----------|---------|--------|
| 1 | Is the goal statement specific enough to test against? | **Pass** | See Q1 below |
| 2 | Are acceptance criteria testable at epic scale? | **Pass** | See Q2 below |
| 3 | Are non-goals explicit? | **Pass** | See Q3 below |
| 4 | Are dependencies identified with owners and dates? | **Gap** | See Q4 below |
| 5 | Are success metrics measurable with existing instrumentation? | **Pass** | See Q5 below |
| 6 | Can an AI agent implement this epic without guessing scope? | **Gap** | See Q6 below |
| 7 | Is the narrative compelling enough to justify the investment? | **Pass** | See Q7 below |

---

#### Q1: Is the goal statement specific enough to test against? — PASS

The title ("Every P0 Test Proves the Deployed Stack Works, Not Just the Source Code") is a testable assertion. The narrative provides a concrete failure mode (Caddy down for 32 hours, all tests passing) as the falsifiable claim. Story 33.10 explicitly validates this. The goal is unambiguous: after this epic, stopping any Docker service must cause P0 tests to fail.

No issues.

---

#### Q2: Are acceptance criteria testable at epic scale? — PASS

All 8 ACs are verifiable by script or inspection:

- AC 1 (health gate): Run with a stopped service, confirm abort. Measurable: 15-second ceiling.
- AC 2-4 (deployment-mode tests): Run pytest against Docker stack, confirm HTTP-based execution.
- AC 5 (runner script): Execute `scripts/run-p0-tests.sh`, confirm single-command operation.
- AC 6 (results persistence): Check `docs/eval-results/` for timestamped file after run.
- AC 7 (env parsing): Confirm no `grep|cut` pattern in runner or docs.
- AC 8 (credential guard): Run with placeholder API key, confirm abort before tests.

One minor note: AC 2 says "at least the intent, primary, and QA eval suites" but the existing eval suite also includes routing (`test_routing_eval.py`). The "at least" qualifier is acceptable but should be tightened in sprint planning to specify which suites are in vs. out.

---

#### Q3: Are non-goals explicit? — PASS

Five non-goals are listed and well-scoped:

1. CI integration (follow-on epic) — good boundary.
2. Performance benchmarking — clear.
3. QA eval scoring fix — correctly identified as out of scope.
4. TLS/Caddy hardening — deferred to Epic 11.
5. Multi-environment support — future work.

The non-goals cover the most likely scope creep vectors. The constraint on backward compatibility (existing in-process tests unchanged) is also valuable.

---

#### Q4: Are dependencies identified with owners and dates? — GAP

**What is documented:** Dependencies section lists Docker stack, real credentials, pg-proxy, and network access. External stakeholders (Anthropic API, GitHub API) are listed.

**What is missing:**

1. **No eval API endpoint exists.** The epic's single highest-risk dependency is buried in Story 33.4 as an "audit" task: "If no suitable endpoint exists, design a minimal `/admin/eval/trigger` endpoint." I verified the codebase — there is NO endpoint in `src/admin/router.py` or anywhere else that can trigger an agent evaluation via HTTP. The admin router has ~25 endpoints (repos, TaskPackets, workflows, metrics, experts, settings) but nothing that invokes the intent/primary/QA agent pipeline and returns results. This is not a "thin endpoint" — it requires: accepting a test case payload, routing it through the agent pipeline (intent builder, primary agent, or QA agent), waiting for completion (synchronous or poll-based), and returning structured output. This is a new feature, not a configuration task, and it is a prerequisite for ALL of Slice 2 (Stories 33.5, 33.6). It must be promoted from a sub-task of Story 33.4 to its own story with explicit scope, endpoint design, and estimation.

2. **No owner or date on any dependency.** The Dependencies section reads like a preconditions list. For a solo developer this may be acceptable, but the epic should at minimum state: "Docker stack must be running before Slice 1 begins" and "Eval endpoint (if needed) must be designed and merged before Slice 2 begins." Sequencing constraints are implicit in the slice ordering but never stated as hard gates.

3. **Caddy auth pass-through is unaddressed.** The prod compose configures Caddy with `ADMIN_USER` and `ADMIN_PASSWORD_HASH` (basic auth). The epic does not mention how deployment-mode tests will authenticate through Caddy. The existing `tests/docker/conftest.py` hits `localhost:8000` directly (dev compose), bypassing Caddy entirely. If tests go through Caddy on 9080 (as the epic prefers), they need basic auth credentials. This is not called out in any story or risk.

**Required fix:** (a) Promote the eval endpoint design to a standalone story with acceptance criteria. (b) Add Caddy basic auth handling to Story 33.7/33.8 or as a shared concern in conftest. (c) State sequencing gates explicitly.

---

#### Q5: Are success metrics measurable with existing instrumentation? — PASS

All six metrics are measurable without new tooling:

- Service-down detection rate: validated by Story 33.10 (stop Caddy, confirm abort).
- Deployment coverage: count of tests in `tests/p0/` vs total P0 count.
- Runner ceremony time: timed in script output (trivial to add).
- False-pass elimination: one-time destructive validation.
- Single-command execution: binary — script exists or it does not.
- Results traceability: file existence check.

The $6 budget ceiling (Constraints) is measurable if the results file includes API cost. Story 33.9 mentions "cost estimate" in the results file — good.

---

#### Q6: Can an AI agent implement this epic without guessing scope? — GAP

**Slice 1 (Stories 33.1-33.3): Yes.** Health checks, shell scripting, and env parsing are well-specified. File paths, service endpoints, and expected behaviors are explicit.

**Slice 2 (Stories 33.4-33.6): No — significant guesswork required.**

1. **Story 33.4 is a design spike masquerading as a story.** It says "Survey existing endpoints... Document findings. If no suitable endpoint exists, design a minimal `/admin/eval/trigger` endpoint." An AI agent given this story would need to: discover there is no eval endpoint (confirmed — there is not), design a new endpoint, decide on sync vs. async execution model, determine what "agent output" means for each eval type, and implement it. The story provides no design guidance. An AI agent would guess, and different agents would guess differently.

2. **Stories 33.5-33.6 depend on 33.4's output but specify a concrete interface** ("sends requests to the deployed app via HTTP"). Without knowing what endpoint to call, what request format to use, or what response shape to expect, these stories are unimplementable as written.

3. **Story 33.7 (GitHub deployed tests) is better specified** because the webhook endpoint (`/webhook/github`) exists and is well-documented. However, the story does not mention that the webhook requires: (a) a registered repo with a webhook secret, (b) HMAC-SHA256 signature, and (c) X-GitHub-Delivery header. The existing `tests/docker/conftest.py` has `compute_signature` and `build_webhook_headers` helpers, but Story 33.7 does not reference these or instruct the implementer to reuse them.

4. **Story 33.8 (Postgres deployed tests) assumes an admin/status endpoint** for querying TaskPackets. The admin router does have TaskPacket query endpoints (`/admin/taskpackets` based on the router structure), so this is feasible, but the story should name the specific endpoint.

**Required fix:** (a) Split Story 33.4 into a design spike (output: endpoint spec document) and an implementation story (output: working endpoint). (b) Add the endpoint spec as a prerequisite for Stories 33.5-33.6 with explicit request/response contracts. (c) Add webhook auth requirements to Story 33.7. (d) Name the specific admin endpoint for Story 33.8.

---

#### Q7: Is the narrative compelling enough to justify the investment? — PASS

The narrative is one of the strongest I have reviewed. It opens with a concrete failure ("Caddy was down for 32 hours... these tests would still pass"), explains the root cause (in-process imports bypass the deployed stack), and connects to business risk (every future epic assumes the stack works). The "Why now" section is crisp.

The evidence chain is:
- 35 P0 tests passed (fact, verifiable from Epic 30 results)
- Caddy was down for 32 hours (incident, cited as motivating event)
- Tests use monkeypatch/direct import (verified in codebase: `tests/eval/test_routing_eval.py` uses `monkeypatch.setattr(settings, ...)`)
- Existing Docker test pattern shows the correct approach (verified: `tests/docker/conftest.py`)

The investment (2-3 sprints) is proportionate to the risk being mitigated.

---

### Red Flags

| # | Flag | Severity | Location |
|---|------|----------|----------|
| RF-1 | **No eval API endpoint exists — this is undisclosed new feature work** | High | Story 33.4, entire Slice 2 |
| RF-2 | **Caddy basic auth not addressed for deployment-mode tests** | Medium | Stories 33.5-33.8, prod compose lines 13-14 |
| RF-3 | **Port 8000 not exposed in prod compose — tests cannot hit app directly** | Medium | Assumptions section, `infra/docker-compose.prod.yml` |
| RF-4 | **Story 33.4 is a design spike without exit criteria** | Medium | Story 33.4 |

RF-3 is acknowledged in the Assumptions section ("The production compose does NOT expose port 8000... The preferred approach is through Caddy on 9080") but is never resolved in a story. If tests go through Caddy, RF-2 (basic auth) activates. If the compose is modified to expose 8000, the Constraints section ("No modifications to `docker-compose.dev.yml`") is silent on whether modifying `docker-compose.prod.yml` to expose a test port is allowed. This needs a decision recorded in the epic.

---

### Required Fixes Before Commit

1. **Promote eval endpoint to a first-class story with design spec.** Story 33.4 must be split: (a) a timeboxed design spike that outputs an endpoint contract (URL, method, request schema, response schema, sync vs. poll), and (b) an implementation story gated on that contract. Stories 33.5-33.6 must list the contract as a hard prerequisite.

2. **Resolve the Caddy auth question.** Add a story or sub-task that handles basic auth for tests going through port 9080, OR explicitly decide to expose port 8000 in the prod compose for test access and update the Constraints section accordingly.

3. **Add webhook auth details to Story 33.7.** Reference the existing `tests/docker/conftest.py` helpers (`compute_signature`, `build_webhook_headers`, `registered_repo` fixture) and require the deployment-mode tests to register a repo and sign payloads. Without this, an implementer will hit 401/404 errors and waste a cycle debugging.

### Advisory (Not Blocking)

- AC 2 should clarify whether `test_routing_eval.py` is in or out of scope for deployment-mode variants.
- Story 33.8 should name the specific admin API endpoint for TaskPacket lookup (likely `/admin/taskpackets` or similar).
- The 2-3 sprint estimate may need to expand to 3-4 sprints given the eval endpoint is new feature work, not just test refactoring. Record the estimation reasoning.
- Consider adding a Slice 0 or Sprint 0 for the eval endpoint design spike so Slice 1 (runner/health) and the spike can run in parallel.
