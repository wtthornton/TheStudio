# Story 0.6 -- Verification Gate: repo-profile checks with loopback

<!-- docsmcp:start:user-story -->

> **As a** TheStudio platform, **I want** to run repo-profile checks (ruff, pytest) against the Primary Agent's output and emit pass/fail signals to JetStream, looping back to the agent on failure (max 2), **so that** only verified code reaches the Publisher and verification failures are never silently skipped

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L
**Epic:** 0 — Foundation: Prove the Pipe
**Sprint:** 2 (weeks 4-6)
**Depends on:** Story 0.8 (Repo Profile — defines required checks)

<!-- docsmcp:end:sizing -->

---

<!-- docsmcp:start:description -->
## Description

The Verification Gate is a deterministic, non-negotiable quality check. It runs the checks defined in the Repo Profile (Story 0.8) against the code changes produced by the Primary Agent (Story 0.5). Verification is part of the Platform Plane — it does not negotiate results.

**Flow:**
1. Receive evidence bundle from Primary Agent
2. Run each required check (ruff lint, pytest) against the changed code
3. Collect results: pass/fail per check, error details
4. If ALL checks pass: emit `verification_passed` to JetStream, update TaskPacket status
5. If ANY check fails: emit `verification_failed` to JetStream with failure details, trigger loopback to Primary Agent (max 2 loopbacks in Phase 0)
6. If max loopbacks exceeded: emit `verification_exhausted`, mark TaskPacket as failed

**Gates fail closed:** If the verification runner itself errors (e.g., ruff crashes), the gate fails — it does not pass by default.

<!-- docsmcp:end:description -->

---

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Implement Verification Gate orchestrator (`src/verification/gate.py`)
  - Accept TaskPacket ID + evidence bundle
  - Load required checks from Repo Profile
  - Run each check, collect results
  - Determine pass/fail, emit signal, trigger loopback or advance
- [ ] Implement check runners (`src/verification/runners/`)
  - `ruff_runner.py` — run ruff lint on changed files, parse output
  - `pytest_runner.py` — run pytest on repo, parse results (pass/fail/skip counts)
  - Common interface: `run(changed_files, repo_path) -> CheckResult`
- [ ] Implement JetStream signal emission (`src/verification/signals.py`)
  - `verification_passed`: TaskPacket ID, correlation_id, check results summary
  - `verification_failed`: TaskPacket ID, correlation_id, failed checks with details
  - `verification_exhausted`: TaskPacket ID, correlation_id, loopback count
- [ ] Implement loopback trigger (`src/verification/loopback.py`)
  - Package failure evidence for Primary Agent
  - Increment loopback counter on TaskPacket
  - Check max loopbacks (2 for Phase 0) before triggering
- [ ] Update TaskPacket status transitions (`src/models/taskpacket.py`)
  - in_progress -> verification_passed (on pass)
  - in_progress -> verification_failed (on fail, triggers loopback)
  - verification_failed -> in_progress (on loopback retry)
  - verification_failed -> failed (on max loopbacks exceeded)
- [ ] Add OpenTelemetry spans (`src/verification/gate.py`)
  - Span: `verification.run` (full verification cycle)
  - Span: `verification.check` (per individual check)
  - Attributes: correlation_id, check_name, result, loopback_count
- [ ] Write tests (`tests/test_verification_gate.py`)
  - Unit tests for each check runner
  - Integration test: all checks pass -> signal emitted
  - Integration test: check fails -> loopback triggered
  - Integration test: max loopbacks -> task failed
  - Test: runner crash -> gate fails closed

<!-- docsmcp:end:tasks -->

---

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Verification Gate runs all required checks from Repo Profile
- [ ] All checks pass -> `verification_passed` emitted to JetStream
- [ ] Any check fails -> `verification_failed` emitted with failure details
- [ ] Failure triggers loopback to Primary Agent with failure evidence
- [ ] Loopback count tracked; max 2 loopbacks enforced
- [ ] Max loopbacks exceeded -> `verification_exhausted` emitted, TaskPacket status = failed
- [ ] Gate fails closed: runner error = verification failure (not silent pass)
- [ ] OpenTelemetry spans emitted per check and per verification cycle

<!-- docsmcp:end:acceptance-criteria -->

---

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Unit tests for ruff runner (clean code, lint errors, ruff crash)
- [ ] Unit tests for pytest runner (all pass, some fail, no tests found)
- [ ] Integration test: verification pass -> JetStream signal
- [ ] Integration test: verification fail -> loopback -> pass on retry
- [ ] Integration test: 3 failures -> max loopbacks -> task failed
- [ ] Integration test: runner crash -> gate fails closed
- [ ] Code passes ruff lint and mypy type check

<!-- docsmcp:end:definition-of-done -->

---

<!-- docsmcp:start:test-cases -->
## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | All checks pass | Clean code, tests pass | verification_passed signal, status updated |
| 2 | Ruff fails | Lint errors in changed files | verification_failed, loopback triggered |
| 3 | Pytest fails | Test failures | verification_failed, loopback triggered |
| 4 | Loopback success | Fail -> fix -> pass on retry | verification_passed after 1 loopback |
| 5 | Max loopbacks | 3 consecutive failures | verification_exhausted, status = failed |
| 6 | Runner crash | Ruff binary not found | Gate fails closed (not silent pass) |
| 7 | No tests found | Repo has no test files | Configurable: pass or warn (per repo profile) |
| 8 | Mixed results | Ruff passes, pytest fails | verification_failed (all must pass) |

<!-- docsmcp:end:test-cases -->

---

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **Gates fail closed** is a core SOUL.md principle. The Verification Gate is deterministic and non-negotiable.
- **JetStream configuration:**
  - **Stream name:** `THESTUDIO_VERIFICATION`
  - **Subject pattern:** `thestudio.verification.{taskpacket_id}` (e.g., `thestudio.verification.abc123`)
  - **Message payload schema:**
    ```json
    {
      "event": "verification_passed | verification_failed | verification_exhausted",
      "taskpacket_id": "uuid",
      "correlation_id": "uuid",
      "timestamp": "ISO 8601",
      "loopback_count": 0,
      "checks": [
        {
          "name": "ruff",
          "result": "passed | failed | error",
          "details": "string (error output or empty)",
          "duration_ms": 1234
        }
      ]
    }
    ```
  - **Retention:** WorkQueue policy (consumed once by Publisher or Loopback handler)
  - **Delivery:** At-least-once. Consumers must be idempotent on `(taskpacket_id, loopback_count)`.
- **Check runners** execute in subprocess with timeout (default 120s per check). Timeout = failure.
- **Loopback** is implemented as a Temporal activity signal back to the Primary Agent workflow.
- **Architecture references:**
  - Verification Gate: `thestudioarc/13-verification-gate.md`
  - System runtime flow: `thestudioarc/15-system-runtime-flow.md` (Step 7: Verify)
  - SOUL.md: "Verification and QA gates fail closed"

<!-- docsmcp:end:technical-notes -->

---

## Files Affected

| File | Action | Description |
|------|--------|-------------|
| `src/verification/__init__.py` | Create | Package init |
| `src/verification/gate.py` | Create | Verification orchestrator |
| `src/verification/runners/__init__.py` | Create | Runners package |
| `src/verification/runners/ruff_runner.py` | Create | Ruff lint check |
| `src/verification/runners/pytest_runner.py` | Create | Pytest check |
| `src/verification/signals.py` | Create | JetStream signal emission |
| `src/verification/loopback.py` | Create | Loopback trigger + counter |
| `tests/test_verification_gate.py` | Create | Unit and integration tests |

---

<!-- docsmcp:start:dependencies -->
## Dependencies

- **Story 0.8 (Repo Profile):** Defines which checks are required for the registered repo
- **Story 0.5 (Primary Agent):** Produces the evidence bundle that verification checks
- **Consumes:** JetStream for signal emission (infra dependency)

<!-- docsmcp:end:dependencies -->

---

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can develop runners and gate logic with mock inputs
- [x] **N**egotiable -- Which checks run, timeout values, "no tests" behavior are configurable
- [x] **V**aluable -- Without verification, broken code reaches the Publisher
- [x] **E**stimable -- 8 points, well-understood check-runner pattern
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 8 test cases with deterministic pass/fail logic

<!-- docsmcp:end:invest -->

---

*Story created by Saga. Part of Epic 0 — Foundation: Prove the Pipe.*
