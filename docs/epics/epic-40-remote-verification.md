# Epic 40: Remote Verification & Advanced Issue Processing

> **Status:** Not Started
> **Epic Owner:** Primary Developer
> **Duration:** 3-4 weeks (~90-120 hours at 30 hrs/week)
> **Created:** 2026-03-22
> **Meridian Review:** Round 2: PASS (2026-03-22)

---

## 1. Title

**Every Generated Diff Is Verified Against the Target Repo's Own Test Suite Before It Reaches QA**

---

## 2. Narrative

TheStudio has processed its first real issue end-to-end (Issue #19 -> PR #20, 2026-03-20). The pipeline works. But the verification gate that cleared that PR is a lie of omission: it checks only that files exist on the branch. It does not clone the target repository, apply the generated diff, or run the repository's own test suite. The comment in the code says it plainly: "Remote verification (ruff/pytest on target repo) is not yet supported."

This means TheStudio can generate code that breaks every test in the target repo and still report `verify.passed`. For the simple, single-file issues processed so far (add a README, create a utility function), this was acceptable. For the issues that actually matter -- multi-file bug fixes, refactoring, dependency upgrades, changes that touch shared modules -- it is disqualifying. A draft PR with no evidence that it passes tests is not meaningfully better than a PR from a developer who never ran the tests. The evidence comment claims verification passed, but the verification proved nothing about correctness.

The roadmap is explicit. The P0 milestone after Phase 8 is "Process harder issues (multi-file, bug fixes, refactoring)." The P1 milestone is "Wire remote verification (GitHub Actions or container)." Both are blocked on the same capability: the ability to clone a target repo, apply the generated diff, run that repo's lint and test suite, and report structured results back to the verification stage.

The infrastructure for this already exists in pieces. Epic 25 built container isolation with Docker lifecycle management, resource limits, network policies, and OTel observability. The `ContainerManager` can launch ephemeral containers with bind-mounted workspaces and collect structured results. The verification gate (`src/verification/gate.py`) already orchestrates multiple check runners (ruff, pytest, security) with a clean `CheckResult` protocol. The Temporal pipeline already has `VerifyInput`/`VerifyOutput` wiring with loopback support. What is missing is the bridge: cloning the target repo, applying the diff to it, running *its* tools inside a container, and feeding the results back through the existing verification protocol.

Without this epic, TheStudio is limited to issues where "files exist on the branch" is a sufficient quality bar. That is a toy. With this epic, the verification gate becomes the hardest gate in the pipeline -- the one that proves the generated code actually works in the target repo's environment.

---

## 3. References

| Artifact | Location | Relevance |
|----------|----------|-----------|
| Verification gate (orchestrator) | `src/verification/gate.py` | Runs check runners, emits signals, manages loopbacks |
| Check runner base protocol | `src/verification/runners/base.py` | `CheckResult` dataclass -- all runners return this |
| Pytest runner (local) | `src/verification/runners/pytest_runner.py` | Template for remote pytest execution |
| Ruff runner (local) | `src/verification/runners/ruff_runner.py` | Template for remote lint execution |
| Security runner (local) | `src/verification/runners/security_runner.py` | Template for remote security scan |
| Verify activity (Temporal) | `src/workflow/activities.py` lines 1128-1172 | Current stub: files_exist check only |
| VerifyInput / VerifyOutput | `src/workflow/activities.py` lines 221-237 | Temporal wire format for verification |
| Pipeline workflow (loopback logic) | `src/workflow/pipeline.py` lines 1076-1103 | Verification loopback wiring (max 2) |
| Container manager | `src/agent/container_manager.py` | Docker lifecycle, resource limits, OTel spans |
| Container runner | `src/agent/container_runner.py` | In-container entrypoint pattern |
| Container protocol | `src/agent/container_protocol.py` | `AgentTaskInput` / `AgentContainerResult` |
| Isolation policy | `src/agent/isolation_policy.py` | Per-tier resource limits, fallback policy |
| Implement activity | `src/workflow/activities.py` lines 823-1125 | Creates branch, pushes files via GitHub API |
| Repo profile CRUD | `src/repo/repo_profile_crud.py` | `required_checks` per repo |
| Aggressive roadmap | `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` | P0: harder issues, P1: remote verification |
| Phase 8 "What Comes Next" | Roadmap lines 456-461 | Explicit P0/P1 priority for this work |
| Epic 25 (Container Isolation) | `docs/epics/epic-25-container-isolation.md` | Foundation for container-based verification |
| Epic 33 (P0 Test Harness) | `docs/epics/epic-33-p0-deployment-test-harness.md` | Pattern for deployment-mode test execution |

---

## 4. Acceptance Criteria

### AC 1: Repo Clone Activity

A Temporal activity exists that, given a repo identifier (`owner/name`) and a branch name, clones the target repository at the specified branch into a local workspace directory. The clone is shallow (depth=1) to minimize bandwidth. The activity uses the existing GitHub token from settings. Clone failures (network, auth, nonexistent branch) produce structured error results, not unhandled exceptions. The cloned workspace is a temp directory that the caller is responsible for cleaning up. OTel span covers the clone operation with duration and repo size attributes.

### AC 2: Branch Clone (Primary) and Diff Application (Fallback)

The primary verification path clones the branch that the implement stage already pushed to GitHub (`git clone --branch <branch>`). Because the implement activity creates a branch and pushes file content via the GitHub Contents API before verification runs, the cloned branch already contains all generated changes -- no diff application is needed for the happy path.

A diff-application fallback exists for cases where the branch is not yet available (e.g., push failure with partial success, local-only testing). This fallback takes a cloned-from-main workspace and a list of file paths (`ImplementOutput.files_changed = list[str]`, paths only -- not content pairs). It retrieves file content from the GitHub Contents API for each path on the target branch, then applies those files to the workspace. The fallback handles three cases: new files (create with parent directories), modified files (overwrite), and deleted files (remove). Path traversal prevention is enforced: no `..` segments, no absolute paths, no symlink following outside the workspace. If any file operation fails (permission denied, path traversal attempt), the entire application is rolled back and an error result is returned.

### AC 3: Remote Test Execution

A verification runner exists that executes the target repo's test suite inside the cloned workspace. The runner discovers the test command from the repo profile's `test_command` field (new field, defaults to `python -m pytest --tb=short -q`). The runner also discovers the lint command from `lint_command` (defaults to `ruff check .`). Each command runs as a subprocess with configurable timeout (default 300s for tests, 120s for lint). Stdout/stderr are captured. Exit code 0 = pass, nonzero = fail. The runner returns a `CheckResult` per command with name, pass/fail, details (truncated to 4000 chars), and duration_ms.

### AC 4: Container-Based Execution

When the repo profile specifies `remote_verify_mode: "container"` (or when the isolation policy requires it), verification runs inside an ephemeral Docker container rather than as a subprocess. The container mounts the cloned workspace, installs the repo's dependencies (via `pip install -e .` or a configurable install command), and runs the test/lint commands. Resource limits (CPU, memory, timeout) come from the isolation policy per tier. The container is cleaned up after execution regardless of outcome. When Docker is unavailable and the isolation policy allows fallback, verification runs as a subprocess with a warning logged.

### AC 5: Verification Stage Integration

The `verify_activity` in `src/workflow/activities.py` is updated to support two modes: (a) local verification (current behavior: files_exist check) as a fallback, and (b) remote verification (clone branch, run tests) as the primary path. The mode is selected by a new `remote_verification_enabled` flag on the repo profile (default: false, so existing repos are not affected). When remote verification is enabled, the activity clones the target branch (which already contains the implement stage's changes), installs dependencies, and runs the repo's test suite. If the branch clone fails, the activity falls back to cloning `main` and retrieving file content via the GitHub Contents API for each path in `changed_files`. The activity returns structured `VerifyOutput` with per-check results. The existing loopback protocol (max 2 retries) continues to work unchanged. Failed remote verification produces check details that the QA agent and evidence comment can consume.

**`VerifyOutput.checks` mapping:** The existing `VerifyOutput.checks` field is `list[dict[str, str]]` (string-keyed, string-valued dicts), not `list[CheckResult]`. Remote verification runners produce `CheckResult` objects (with `passed: bool` and `duration_ms: int`). The activity must map each `CheckResult` to `dict[str, str]` as: `{"name": cr.name, "passed": str(cr.passed), "details": cr.details, "duration_ms": str(cr.duration_ms)}`. Consumers that need typed values must parse `passed` and `duration_ms` back from strings. This preserves backward compatibility with the existing Temporal wire format.

### AC 6: Timeout and Resource Limits

All remote verification operations have explicit, configurable timeouts: clone (60s default), dependency install (300s default), lint (120s default), test suite (300s default), total wall-clock (900s default). Any timeout produces a `CheckResult` with `passed=False` and a details string that names the operation that timed out and its configured limit. Resource limits (when running in container mode) are inherited from the isolation policy per repo tier. A repo profile can override the total wall-clock timeout via `verify_timeout_seconds`.

---

## 4b. Top Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | Target repo test suite takes too long (>5 min) | High | Medium | Configurable per-repo timeout with 300s default; repos can set `verify_timeout_seconds`; timeout = check failure, not pipeline hang |
| 2 | Target repo has complex dependency installation | High | Medium | Configurable `install_command` on repo profile; fallback to `pip install -e .`; install timeout (300s) prevents infinite `pip compile` |
| 3 | Container escape or path traversal via generated diff | Low | Critical | Path traversal prevention in diff application; no symlink following; container has no access to host network, DB, or secrets; resource limits enforced |
| 4 | Shallow clone misses test fixtures or submodules | Medium | Medium | `clone_depth` configurable per repo; full clone available as fallback; submodule init is a stretch goal, not MVP |
| 5 | Test suite discovery fails (no pytest, different framework) | Medium | Low | `test_command` configurable per repo; default pytest; if command not found, check fails with clear error; no silent skip |
| 6 | Docker unavailable on Temporal worker | Low | Medium | Isolation policy fallback (subprocess mode for Observe/Suggest, hard fail for Execute); existing Epic 25 pattern |
| 7 | GitHub rate limits during clone for high-volume repos | Low | Medium | Shallow clone (depth=1) reduces transfer; clone is one operation per verification, not per file; rate limit error surfaces as clone failure |

---

## 5. Constraints & Non-Goals

### Constraints

- **Token reuse:** Remote clone must use the same GitHub token already configured in settings (`intake_poll_token`). No new credential provisioning.
- **Repo profile backward compatibility:** All new fields (`test_command`, `lint_command`, `remote_verify_mode`, `install_command`, `verify_timeout_seconds`) must have defaults so existing repos work unchanged.
- **Verification protocol unchanged:** The `VerifyInput`/`VerifyOutput` Temporal wire format may be extended but not broken. Existing loopback logic (max 2) must continue working.
- **Container isolation policy:** When running in container mode, resource limits come from the existing `isolation_policy.py` per-tier configuration. No separate limit system for verification containers.
- **Evidence comment compatibility:** Check results from remote verification must be consumable by the evidence comment builder without modification (use existing `CheckResult` protocol).

### Non-Goals

- **GitHub Actions integration.** Dispatching verification to GitHub Actions workflows, polling for status, and ingesting results is a future enhancement. This epic uses local containers or subprocesses only.
- **CI/CD pipeline creation.** This epic does not create CI/CD pipelines in target repos. It runs their existing tests.
- **Deployment or infrastructure changes.** No changes to `docker-compose.dev.yml` or `docker-compose.prod.yml`. Verification containers are managed by `ContainerManager`, not by Compose.
- **Multi-language support.** MVP assumes Python repos (pytest, ruff). Support for other languages (npm test, go test, cargo test) is future work. The `test_command`/`lint_command` fields make this extensible but it is not validated in this epic.
- **Caching or layer optimization.** Docker image caching, dependency caching between verification runs, or persistent verification environments are future optimizations.
- **Submodule support.** Repos with git submodules are not guaranteed to work. Submodule init is out of scope.
- **Parallel check execution.** Checks run sequentially (lint then tests). Parallel execution is a future optimization.

---

## 6. Stakeholders & Roles

| Role | Person | Responsibility |
|------|--------|----------------|
| Epic Owner / Developer | Primary Developer | Implementation, testing, and delivery of all stories |
| Reviewer | Meridian | Epic review, AC validation, red flag identification |
| QA | Automated (pytest + TAPPS) | Unit tests, integration tests, quality gate |

Solo-developer project. No external stakeholders. No design dependency.

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Remote verification catches known-bad diffs | 3/3 test cases where a planted bug fails the target repo's tests are caught by remote verification | Test with intentionally broken diffs against the production test rig |
| Verification passes known-good diffs | 3/3 test cases where correct code passes the target repo's tests are confirmed by remote verification | Test with correct diffs against the production test rig |
| Loopback with actionable feedback | When remote verification fails, every failed `CheckResult.details` includes: (1) the failing test name or lint rule ID, (2) the error type (e.g., `AssertionError`, `E302`), and (3) the relevant file path and line number. All three elements present in 3/3 inspected failure cases. | Inspect evidence from 3 failed verifications |
| No regression on existing repos | Repos without `remote_verification_enabled` continue to use files_exist check with zero behavior change | Existing E2E tests pass unchanged |
| Verification wall-clock time | Remote verification completes in <5 minutes for the production test rig (small Python repo) | Measure end-to-end verify activity duration |
| Path traversal blocked | 100% of path traversal attempts in diff application are rejected | Unit tests with `../`, absolute paths, symlinks |

---

## 8. Context & Assumptions

### Business Rules

- Remote verification is opt-in per repo via `remote_verification_enabled` flag. Default is false. This means the rollout is controlled and existing repos are not affected until explicitly enabled.
- The `files_exist` check remains as a pre-check even when remote verification is enabled: if no files were changed, there is nothing to verify remotely.
- Verification failures from remote execution feed into the same loopback protocol. The implement agent receives check details (test failures, lint errors) as feedback for its retry attempt.
- Cost impact is minimal: cloning and running tests uses no LLM tokens. The only cost is compute time on the Temporal worker (or container host).

### Dependencies

- **Epic 25 (Container Isolation):** Container manager, isolation policy, and container protocol are prerequisites. All complete.
- **Repo Profile schema:** New fields will be added to the repo profile model. Migration required.
- **GitHub token:** The `intake_poll_token` setting must have read access to the target repo for cloning. This is already true for repos TheStudio processes.
- **Production test rig:** `wtthornton/thestudio-production-test-rig` is the validation target. It has a pytest suite and ruff configuration.

### Systems Affected

| System | Impact |
|--------|--------|
| `src/verification/` | New runners for remote pytest, ruff, and security; gate extended for remote mode |
| `src/workflow/activities.py` | `verify_activity` updated for remote verification path |
| `src/workflow/activities.py` | New `clone_repo_activity` Temporal activity |
| `src/repo/` | Repo profile model extended with verification config fields |
| `src/agent/container_manager.py` | Reused for container-based verification (no changes expected) |
| `src/agent/isolation_policy.py` | Consulted for verification container limits (no changes expected) |
| `src/models/` | Possible `VerifyInput`/`VerifyOutput` extensions |
| `alembic/versions/` | Migration for new repo profile fields |

### Assumptions

- The Temporal worker host has `git` installed and accessible on PATH.
- Target repos use standard Python tooling (pytest, ruff) or provide explicit test/lint commands.
- Shallow clones (depth=1) are sufficient for running tests. Repos that require full history for tests are edge cases handled by configurable `clone_depth`.
- The production test rig repo (`wtthornton/thestudio-production-test-rig`) has a passing test suite that can serve as the validation target.

---

## Story Map

### Slice 1: MVP -- Local Subprocess Verification (Week 1-2)

End-to-end remote verification via subprocess execution. No containers. Proves the clone-apply-run-report loop works.

| # | Story | Size | Files to Create/Modify |
|---|-------|------|----------------------|
| 40.0 | **Repo profile schema extension** -- Add `remote_verification_enabled` (bool, default false), `test_command` (str, default `python -m pytest --tb=short -q`), `lint_command` (str, default `ruff check .`), `install_command` (str, default `pip install -e .`), `verify_timeout_seconds` (int, default 900), `clone_depth` (int, default 1), `remote_verify_mode` (str, default `subprocess`) to repo profile model. Alembic migration. | S | `src/repo/repo_profile.py`, `alembic/versions/xxx_add_remote_verify_fields.py`, `tests/repo/test_repo_profile_model.py` |
| 40.1 | **Repo clone utility** -- Function that shallow-clones a repo+branch to a temp directory using `git clone --depth N --branch <branch> --single-branch <url> <target>`. Returns the workspace path. Handles auth via token URL (`https://<token>@github.com/owner/repo.git`). Timeout (60s default). OTel span. Error cases: network failure, auth failure, branch not found. | S | `src/verification/remote/clone.py`, `tests/verification/remote/test_clone.py` |
| 40.2 | **Diff application (fallback path)** -- Function that takes a workspace path (cloned from `main`), a list of changed file paths (`list[str]` from `ImplementOutput.files_changed`), and a GitHub client reference. For each path, retrieves content from the target branch via the GitHub Contents API and writes it to the workspace. Validates paths (no `..`, no absolute, no symlinks outside workspace). Creates parent directories for new files. Returns a manifest. Rollback on failure. This function is only invoked when the branch clone in Story 40.1 fails. | S | `src/verification/remote/diff_apply.py`, `tests/verification/remote/test_diff_apply.py` |
| 40.3 | **Dependency installer runner** -- Function that runs the install command in the cloned workspace as a subprocess. Configurable timeout (300s). Returns `CheckResult` (name="install", passed/failed, details with stderr on failure). Handles missing requirements.txt, setup.py, pyproject.toml gracefully. | S | `src/verification/remote/install_runner.py`, `tests/verification/remote/test_install_runner.py` |
| 40.4 | **Remote test runner** -- Function that runs the test command in the cloned workspace as a subprocess. Configurable timeout (300s). Captures stdout/stderr, parses exit code. Returns `CheckResult` with test output truncated to 4000 chars. Handles pytest exit codes (0=pass, 1=fail, 2=error, 5=no tests). | M | `src/verification/runners/remote_pytest_runner.py`, `tests/verification/runners/test_remote_pytest_runner.py` |
| 40.5 | **Remote lint runner** -- Function that runs the lint command in the cloned workspace as a subprocess. Same structure as test runner. Returns `CheckResult`. | S | `src/verification/runners/remote_ruff_runner.py`, `tests/verification/runners/test_remote_ruff_runner.py` |
| 40.6 | **Remote verification orchestrator** -- New function `verify_remote()` that orchestrates: clone branch (primary) or clone main + apply diff fallback (see AC 2) -> install deps -> run lint -> run tests -> collect results -> cleanup workspace. Accepts repo profile config for all parameters. Returns `list[CheckResult]`. Total wall-clock timeout enforced. OTel parent span with child spans per phase. | M | `src/verification/remote/orchestrator.py`, `tests/verification/remote/test_orchestrator.py` |
| 40.7 | **Verify activity integration** -- Update `verify_activity` in `src/workflow/activities.py` to check `remote_verification_enabled` on the repo profile. When enabled: load repo profile, call `verify_remote()`, map each `CheckResult` to `dict[str, str]` (keys: `name`, `passed`, `details`, `duration_ms`; values all strings -- `passed` as `"True"`/`"False"`, `duration_ms` as decimal string) and populate `VerifyOutput.checks`. When disabled: existing `files_exist` behavior. Add `repo` field to `VerifyInput` so the activity can look up the repo profile. Primary path clones the branch; fallback clones `main` + retrieves content via GitHub Contents API (see AC 2). | M | `src/workflow/activities.py`, `tests/workflow/test_verify_activity.py` |
| 40.8 | **Integration test: remote verification on test rig** -- End-to-end test that clones the production test rig, applies a known-good diff, runs verification, and confirms all checks pass. Then applies a known-bad diff (introduce a syntax error) and confirms verification fails with actionable details. Marked `@pytest.mark.integration`. | M | `tests/integration/test_remote_verification.py` |

### Slice 2: Container Execution Mode (Week 3-4)

Adds container-based verification for repos that need isolated execution environments. Builds on Slice 1 orchestrator.

| # | Story | Size | Files to Create/Modify |
|---|-------|------|----------------------|
| 40.9 | **Verification container image** -- Dockerfile for verification containers. Based on `python:3.12-slim`. Includes git, pip, ruff, pytest, bandit. Entrypoint script that reads a verification task JSON, runs install + lint + tests, writes result JSON. Follows the `container_runner.py` pattern from Epic 25. | M | `src/verification/remote/Dockerfile.verify`, `src/verification/remote/verify_entrypoint.py`, `tests/verification/remote/test_verify_entrypoint.py` |
| 40.10 | **Container verification runner** -- Function that launches a verification container via `ContainerManager`, mounts the cloned workspace, passes the verification config as a task JSON, waits for completion, and collects the result JSON. Maps container result to `list[CheckResult]`. Handles timeout, OOM, and container launch failures. | M | `src/verification/remote/container_runner.py`, `tests/verification/remote/test_container_runner.py` |
| 40.11 | **Orchestrator container mode** -- Extend `verify_remote()` orchestrator to support `remote_verify_mode: "container"`. When container mode is selected: clone repo (always on host), then launch verification container with workspace mounted. When subprocess mode is selected: existing Slice 1 behavior. Isolation policy consulted for resource limits. Fallback to subprocess when Docker unavailable and policy allows. | M | `src/verification/remote/orchestrator.py`, `tests/verification/remote/test_orchestrator_container.py` |
| 40.12 | **Evidence comment enrichment** -- Ensure remote verification `CheckResult` entries appear in the evidence comment with check name, pass/fail, duration, and first 500 chars of details. Verify the existing evidence comment builder handles the new check names (`remote_pytest`, `remote_ruff`, `remote_install`) without modification. If changes needed, update the builder. | S | `src/publisher/evidence.py` (if needed), `tests/publisher/test_evidence_remote_checks.py` |
| 40.13 | **Observability and logging** -- Add structured log events for remote verification lifecycle: `remote_verify.start`, `remote_verify.clone`, `remote_verify.install`, `remote_verify.lint`, `remote_verify.test`, `remote_verify.complete`. Each event includes `taskpacket_id`, `correlation_id`, `repo`, `duration_ms`, and outcome. OTel span attributes on the parent `verify_remote` span: total duration, check count, pass/fail. | S | `src/verification/remote/orchestrator.py`, `src/observability/conventions.py` |
| 40.14 | **Admin endpoint: trigger remote verification** -- `POST /admin/verify/{taskpacket_id}` endpoint that triggers remote verification for an existing TaskPacket. Used for manual re-verification and debugging. Returns the `VerifyOutput` JSON. Requires admin auth. | S | `src/app.py` or `src/admin/routes.py`, `tests/admin/test_verify_endpoint.py` |

---

## Meridian Review Status

### Round 1: BLOCKERS FOUND (2026-03-22)

| # | Issue | Severity | Resolution |
|---|-------|----------|------------|
| 1 | AC 2 assumed `changed_files` contains path+content pairs. Actual pipeline carries `ImplementOutput.files_changed = list[str]` (paths only). File content is pushed to GitHub via Contents API during implement. | BLOCKER | Rewrote AC 2: primary path clones the branch (which already has changes). Fallback clones `main` + retrieves content from GitHub Contents API per path. Updated AC 5, Stories 40.2, 40.6, 40.7 to match. |
| 2 | Story 40.0 referenced `src/repo/models.py` -- file does not exist. Actual location is `src/repo/repo_profile.py`. | BLOCKER | Fixed file reference in Story 40.0 to `src/repo/repo_profile.py`. |
| 3 | `VerifyOutput.checks` is `list[dict[str, str]]` with string-encoded values, not `list[CheckResult]`. Mapping strategy not documented. | BLOCKER | Documented mapping strategy in AC 5 (`{"name": ..., "passed": str(...), ...}`) and Story 40.7 with explicit key/value specification. |
| 4 | "Actionable feedback" success metric was subjective ("enough information"). | Minor | Tightened to require three specific elements: failing test name/rule ID, error type, and file path + line number -- all three present in 3/3 inspected failures. |

### Round 2: PASS (2026-03-22)

| # | Question | Status |
|---|----------|--------|
| 1 | Are all acceptance criteria testable at epic scale? | PASS -- AC 1-6 each have concrete pass/fail conditions. AC 2 now correctly reflects branch-clone primary path with diff-apply fallback. AC 5 documents the CheckResult-to-dict mapping. |
| 2 | Are constraints and non-goals explicit enough to prevent scope creep? | PASS -- GitHub Actions, multi-language, caching, submodules, and parallel execution explicitly excluded. |
| 3 | Do stories decompose into vertical slices with end-to-end value? | PASS -- Slice 1 delivers working subprocess verification end-to-end. Slice 2 adds container mode as an enhancement. |
| 4 | Are security implications addressed (path traversal, container escape)? | PASS -- AC 2 enforces path traversal prevention. AC 4 uses container isolation with resource limits. Risk table covers both. |
| 5 | Are existing interfaces preserved (VerifyInput/VerifyOutput, CheckResult)? | PASS -- VerifyOutput.checks mapping strategy documented. VerifyInput extended (not broken). Loopback protocol unchanged. |
| 6 | Is the rollout safe (feature flag, backward compatible defaults)? | PASS -- `remote_verification_enabled` defaults false. All new repo profile fields have defaults. |
| 7 | Are success metrics measurable without new instrumentation? | PASS -- All metrics use existing test infrastructure or inspection of output artifacts. "Actionable feedback" now has three concrete, checkable criteria. |
