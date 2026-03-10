# Epic 10 — Docker Test Rig Hardening

**Author:** Saga
**Date:** 2026-03-10
**Status:** Draft — Meridian Review Pending (Round 1)

---

## 1. Title

Reliable Docker Tests That Pass for the Right Reasons — Harden the Epic 9 test rig so every failure signals a real problem, never a test infrastructure bug.

## 2. Narrative

Epic 9 delivered a Docker Compose test rig that builds the stack, runs smoke tests, and validates the full intake pipeline in CI. It works. But a review of the delivered code found five defects that undermine confidence in the results:

A dedup test sends two requests expecting the second to be caught as a duplicate, but the test helper generates a fresh delivery ID each time — so the test is not testing dedup at all. The Compose file declares the app depends on PostgreSQL and NATS but not Temporal, meaning the app can start before its workflow engine is ready. The `docker_compose_cmd` helper does not set a working directory, so running pytest from anywhere other than the repo root breaks every lifecycle test. The lifecycle test classes have no ordering guarantee, so pytest can run a dependency-failure test before the graceful-shutdown test that must precede it. And NATS uses `service_started` instead of `service_healthy` despite having a healthcheck, creating a startup race.

None of these are application bugs. They are test infrastructure bugs — the kind that cause intermittent CI failures, waste investigation time, and erode trust in the rig that is supposed to build trust. Left unfixed, developers will start ignoring Docker test failures ("oh, that's just the flaky lifecycle test"), which defeats the entire purpose of Epic 9.

This epic fixes all five issues. The scope is narrow: test code, Compose configuration, and one new dev dependency. No application code changes. No new test scenarios. Just making the existing tests tell the truth.

## 3. References

- Parent epic: `docs/epics/epic-9-docker-test-rig.md`
- Test files under review: `tests/docker/conftest.py`, `tests/docker/test_pipeline_smoke.py`, `tests/docker/test_lifecycle.py`
- Compose file: `docker-compose.dev.yml`
- CI workflow: `.github/workflows/ci.yml`
- Architecture overview: `thestudioarc/00-overview.md`
- Pipeline stage mapping: `.claude/rules/pipeline-stages.md`
- Aggressive roadmap: `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md`

## 4. Acceptance Criteria

**AC-1: Dedup test actually tests deduplication.**
The `test_duplicate_webhook_is_idempotent` test sends two requests with the same `X-GitHub-Delivery` value. The first returns 201 (created). The second returns 200 with a response indicating duplication. The delivery ID is not randomly generated between calls.

**AC-2: App service starts only after all dependencies are healthy.**
`docker-compose.dev.yml` declares `depends_on` for postgres, nats, and temporal, all with `condition: service_healthy`. A `docker compose up` does not start the app container until all three dependency healthchecks pass.

**AC-3: Docker Compose commands work regardless of pytest invocation directory.**
`docker_compose_cmd()` in `conftest.py` explicitly sets `cwd` to the repository root. Running `pytest tests/docker/` from any directory (repo root, `tests/`, `tests/docker/`, or an unrelated directory) produces the same result.

**AC-4: Lifecycle tests execute in a guaranteed order.**
`TestGracefulShutdown` runs before `TestRestartRecovery`, which runs before `TestDependencyFailure`. This ordering is enforced by an explicit mechanism (pytest-ordering markers or equivalent), not by accident of file layout or class naming.

**AC-5: NATS dependency uses health-based readiness.**
The app service's `depends_on` for NATS uses `condition: service_healthy`, matching the pattern already used for PostgreSQL. The NATS service's existing healthcheck is the gate.

## 4b. Risks

1. **pytest-ordering dependency compatibility.** Adding `pytest-order` introduces a new dev dependency. Risk: version conflicts or unexpected interactions with existing pytest plugins. Mitigation: pin version, verify `pytest --co` shows correct ordering before merge, run full test suite to check for regressions.
2. **Temporal healthcheck latency may increase startup time.** Adding `temporal: condition: service_healthy` to the app's `depends_on` means the app waits for Temporal's healthcheck (up to 30s start_period + retries). Risk: CI job exceeds time budget. Mitigation: existing `wait_for_stack.py` already accounts for this delay; the CI job has a 15-minute timeout with plenty of margin.
3. **Working directory detection brittleness.** Detecting the repo root via `git rev-parse --show-toplevel` or relative path from `__file__` could break in edge cases (worktrees, mounted volumes). Mitigation: use `pathlib.Path(__file__).resolve()` to navigate relative to the test file, which is deterministic.

## 5. Constraints & Non-Goals

### Constraints
- No application code changes. All fixes are in test code, Compose configuration, or dev dependencies.
- No new test scenarios. This epic fixes existing tests, not adds new ones.
- The `pytest-order` dependency (or equivalent) is added to `pyproject.toml` dev extras only.
- All changes must pass the existing CI pipeline (lint, unit tests, integration tests) in addition to the Docker smoke job.
- Compose file changes must not break the `docker compose up` workflow for developers who are not running tests.

### Non-Goals
- **No new smoke tests or lifecycle scenarios.** That is future work, not this epic.
- **No refactoring of test helpers beyond what is needed for the five fixes.** Resist the urge to "improve while we're in there."
- **No changes to the CI job structure.** The `docker-smoke` job in `ci.yml` stays as-is; only the tests and Compose file it exercises change.
- **No migration to Docker SDK for Python.** `subprocess`-based container control stays.
- **No changes to application health check endpoints or startup logic.**

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| **Epic Owner** | Engineering Lead | Scope decisions, priority calls |
| **Tech Lead** | Backend Engineer | Fix implementation, Compose changes, test architecture |
| **QA** | Meridian (review) | Acceptance criteria validation, flakiness review |
| **DevOps** | Backend Engineer | Compose dependency ordering, CI verification |
| **Reviewer** | Meridian | Epic and plan review before commit |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Dedup test reliability** | 100% pass rate when dedup logic is correct; 100% fail rate when dedup logic is broken | Manual verification: temporarily disable dedup in app and confirm test fails |
| **Compose startup ordering** | App container starts only after postgres, temporal, and nats healthchecks pass | `docker compose up` log inspection (app start timestamp after dependency healthy timestamps) |
| **Cross-directory pytest invocation** | `pytest tests/docker/` passes from repo root, `tests/`, and home directory | Manual test from 3 directories |
| **Lifecycle test order guarantee** | `pytest --co tests/docker/test_lifecycle.py` shows tests in correct order every run | `pytest --collect-only` output inspection |
| **Docker smoke CI flake rate** | Below 5% over 20 consecutive runs (improvement over pre-fix baseline) | CI job history in GitHub Actions |

## 8. Context & Assumptions

### Assumptions
- Epic 9 deliverables are merged and the `docker-smoke` CI job is running on every PR and push to master.
- The `tests/docker/` directory, `docker-compose.dev.yml`, and `.github/workflows/ci.yml` are in the states shown in the review (current master).
- `pytest-order` (or equivalent) is compatible with Python 3.12+ and the existing pytest version.
- The dedup check in the webhook handler uses `X-GitHub-Delivery` as the idempotency key. This is confirmed by the test's intent and the handler implementation.
- NATS healthcheck (`wget -qO- http://localhost:8222/healthz`) is reliable and fast (under 3 seconds).
- Temporal's `tctl cluster health` healthcheck is the correct readiness signal (already used in Compose, just not wired into the app's `depends_on`).

### Dependencies
- **Epic 9 (Status: Complete).** All test files and CI configuration exist. Owner: Backend Engineer.
- **pytest-order package.** Must be available on PyPI for Python 3.12+. No known blockers.
- **Docker Compose v2.** Required for `depends_on` with `condition: service_healthy`. Already in use.

### Systems Affected
- `tests/docker/conftest.py` — `build_webhook_headers()` signature change, `docker_compose_cmd()` cwd fix
- `tests/docker/test_pipeline_smoke.py` — dedup test fix to reuse delivery ID
- `tests/docker/test_lifecycle.py` — ordering markers added
- `docker-compose.dev.yml` — `depends_on` additions (temporal, nats health)
- `pyproject.toml` — `pytest-order` added to dev dependencies

---

## Story Map

Stories are ordered by risk reduction. Story 10.1 fixes the most dangerous defect (a test that lies). Stories 10.2-10.3 fix Compose startup races. Story 10.4 fixes the cwd bug. Story 10.5 fixes lifecycle ordering. Each story is independently mergeable and testable.

### Story 10.1: Fix Dedup Test to Reuse Delivery ID

**As a** developer reviewing CI results,
**I want** the dedup test to actually send the same delivery ID twice,
**so that** a passing test means deduplication works and a failing test means it does not.

**Details:**
- In `tests/docker/test_pipeline_smoke.py`, the `test_duplicate_webhook_is_idempotent` method calls `build_webhook_headers()` twice. Each call generates a random `X-GitHub-Delivery` UUID via `uuid.uuid4()`. The second request therefore has a different delivery ID and is not a duplicate.
- Fix option A (preferred): Modify `build_webhook_headers()` in `conftest.py` to accept an optional `delivery_id` parameter. When provided, use it instead of generating a new UUID. Update the dedup test to capture headers from the first call and reuse them (or pass the same delivery_id to both calls).
- Fix option B: In the test itself, build headers once and use them for both POST requests.
- Either approach is acceptable. The key invariant is: both requests must carry the same `X-GitHub-Delivery` value.

**Acceptance Criteria:**
- The two POST requests in `test_duplicate_webhook_is_idempotent` send identical `X-GitHub-Delivery` header values.
- First request returns 201. Second request returns 200 with duplicate indication.
- `build_webhook_headers()` still generates a random UUID by default (no regression for other callers).
- Test passes against a running stack with working dedup logic.

**Files to modify:**
- `tests/docker/conftest.py` — add optional `delivery_id` parameter to `build_webhook_headers()`
- `tests/docker/test_pipeline_smoke.py` — fix `test_duplicate_webhook_is_idempotent` to reuse the delivery ID

---

### Story 10.2: Add Temporal to App's depends_on in Compose

**As a** developer starting the stack with `docker compose up`,
**I want** the app to wait for Temporal to be healthy before starting,
**so that** the app does not fail on startup due to Temporal not being ready.

**Details:**
- `docker-compose.dev.yml` line 70-74: the app service's `depends_on` lists `postgres` (healthy) and `nats` (started) but not `temporal`.
- Add `temporal: condition: service_healthy` to the app's `depends_on` block.
- Temporal already has a healthcheck defined (lines 36-40), so this just wires the app to wait for it.

**Acceptance Criteria:**
- `docker-compose.dev.yml` app service `depends_on` includes `temporal` with `condition: service_healthy`.
- `docker compose up` starts the app container only after Temporal's healthcheck passes.
- No change to Temporal's healthcheck configuration itself.
- Stack starts successfully with the new ordering (manual or CI verification).

**Files to modify:**
- `docker-compose.dev.yml` — add temporal to app's `depends_on`

---

### Story 10.3: Change NATS depends_on to service_healthy

**As a** developer starting the stack,
**I want** the app to wait for NATS to be healthy (not just started),
**so that** the app does not attempt NATS connections before the server is ready.

**Details:**
- `docker-compose.dev.yml` line 74: `nats: condition: service_started`.
- NATS has a healthcheck defined (lines 48-52) using `wget -qO- http://localhost:8222/healthz`.
- Change `condition: service_started` to `condition: service_healthy`.

**Acceptance Criteria:**
- `docker-compose.dev.yml` app service `depends_on` for nats uses `condition: service_healthy`.
- NATS healthcheck passes before the app container starts.
- No change to the NATS service healthcheck definition.
- Stack starts successfully with the updated condition.

**Files to modify:**
- `docker-compose.dev.yml` — change nats condition from `service_started` to `service_healthy`

---

### Story 10.4: Set Working Directory in docker_compose_cmd

**As a** developer running Docker tests from any directory,
**I want** `docker_compose_cmd()` to always find `docker-compose.dev.yml`,
**so that** tests do not fail due to the current working directory.

**Details:**
- `conftest.py` lines 116-125: `docker_compose_cmd()` calls `subprocess.run()` with `docker compose -f docker-compose.dev.yml` but does not set `cwd`. If pytest is run from `tests/docker/` or any other non-root directory, the relative path `docker-compose.dev.yml` will not resolve.
- Fix: Compute the repo root from the test file's location. The conftest lives at `tests/docker/conftest.py`, so the repo root is two directories up from `__file__`. Use `pathlib.Path(__file__).resolve().parent.parent.parent` to get the repo root.
- Pass `cwd=repo_root` to `subprocess.run()` in `docker_compose_cmd()`.

**Acceptance Criteria:**
- `docker_compose_cmd()` sets `cwd` to the repository root in its `subprocess.run()` call.
- The repo root is derived from the test file's location (not hardcoded, not dependent on `os.getcwd()`).
- Running `pytest tests/docker/test_lifecycle.py` from the repo root, from `tests/`, and from `tests/docker/` all produce the same behavior.
- No change to the `-f docker-compose.dev.yml` argument (it is now relative to the explicit cwd).

**Files to modify:**
- `tests/docker/conftest.py` — add repo root detection and pass `cwd` to `subprocess.run()`

---

### Story 10.5: Enforce Lifecycle Test Execution Order

**As a** CI pipeline,
**I want** lifecycle tests to run in a guaranteed order (shutdown, then restart, then dependency failure),
**so that** each test starts with the stack in the state left by the previous test.

**Details:**
- `test_lifecycle.py` has three test classes: `TestGracefulShutdown`, `TestRestartRecovery`, `TestDependencyFailure`. These must run in this order because:
  - `TestGracefulShutdown` stops and restarts the app.
  - `TestRestartRecovery` restarts the app again.
  - `TestDependencyFailure` stops Temporal and restarts it.
  - Running them out of order can leave the stack in a broken state.
- pytest does not guarantee class ordering within a module by default.
- Fix: Add `pytest-order` to dev dependencies in `pyproject.toml`. Add `@pytest.mark.order(N)` markers to each test class or method in `test_lifecycle.py`.
- Alternative: Consolidate into a single class with ordered methods. `pytest-order` is preferred because it is explicit and does not require restructuring.

**Acceptance Criteria:**
- `pytest-order` is added to dev dependencies in `pyproject.toml`.
- Each test in `test_lifecycle.py` has an explicit `@pytest.mark.order()` marker.
- `pytest --collect-only tests/docker/test_lifecycle.py` shows tests in order: shutdown, restart, dependency failure.
- Running `pytest tests/docker/test_lifecycle.py` executes tests in the marked order.
- No changes to test logic — only ordering markers added.

**Files to modify:**
- `pyproject.toml` — add `pytest-order` to dev dependencies
- `tests/docker/test_lifecycle.py` — add `@pytest.mark.order()` markers to each test class/method

---

## Meridian Review Status

### Round 1: Pending

This epic has not yet been reviewed by Meridian. Submit for review before implementation begins.
