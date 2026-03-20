# Session Prompt: Epic 33 Sprint 2 — Eval Guard, Results Persistence, Validation

## Context

**Phase 8, Sprint 2** (2026-03-20). Sprint 1 is complete and fully validated.

**What was done in Sprint 1 (2026-03-20):**
- Full P0 test harness delivered: health gate, runner script, conftest, deployment-mode tests
- 8 health gate unit tests (mocked, run without Docker stack)
- 14 P0 deployed tests all passing against the live Docker stack through Caddy HTTPS (9443)
- Runner script (`scripts/run-p0-tests.sh`) with credential guards for API key, PG password (rejects `thestudio_dev`), ADMIN_USER, ADMIN_PASSWORD, THESTUDIO_WEBHOOK_SECRET
- 2 pre-existing test failures fixed (date-dependent `test_model_spend`, stale mock in `test_workflow_trigger`)
- Key architectural discovery: `/admin/workflows` queries Temporal, not Postgres. Postgres tests now assert TaskPacket creation (201) and uniqueness constraint (409), not Temporal workflow listing.

**Test health:** 1,850 unit tests, 14 P0 deployed, 4 GitHub integration, 6 Postgres integration. All passing. 84% coverage.

**Latest P0 results:** `docs/eval-results/p0-20260320-125706.md` — all suites PASS.

---

## Sprint 2 Goal

Deliver eval test stack-health guard (AC 2), structured results persistence with cost tracking (AC 6), false-pass validation (Story 33.8), and documentation update (Story 33.9).

**Full epic:** `docs/epics/epic-33-p0-deployment-test-harness.md`
**Sprint 1 plan (reference):** `docs/sprints/session-prompt-epic33-s1.md`

---

## Story Execution Order

Execute stories in this exact order:

### Story 33.6: Eval Test Stack-Health Guard (AC 2) — 4h

The eval tests (`tests/eval/`) run in-process (no HTTP endpoint). The guard is a **preflight check** in the runner script, NOT an HTTP eval endpoint.

**What to build:**
Add a preflight step to `scripts/run-p0-tests.sh` (before the eval suite runs) that validates:
1. Docker stack is healthy (already done — health gate runs first)
2. The container's `THESTUDIO_LLM_PROVIDER` is `anthropic` (not `mock`)
3. The container's `THESTUDIO_ANTHROPIC_API_KEY` matches the host env key

**How to check container config:**
```bash
# Read env vars from running container
docker compose -f infra/docker-compose.prod.yml exec app printenv THESTUDIO_LLM_PROVIDER
docker compose -f infra/docker-compose.prod.yml exec app printenv THESTUDIO_ANTHROPIC_API_KEY
```

Compare with host env. If mismatched, abort eval suite with clear error message.

**Done when:**
- `--skip-eval` still skips the preflight entirely
- Running with `THESTUDIO_LLM_PROVIDER=mock` in container causes eval abort with message "Container LLM provider is 'mock', not 'anthropic' — eval results would be meaningless"
- Matching config proceeds to eval tests normally
- 1+ test for the preflight logic (can mock `docker compose exec`)

### Story 33.7: Results Persistence with Cost Tracking (AC 6) — 5h

The runner already saves basic results to `docs/eval-results/p0-{timestamp}.md`. Enhance it.

**What to add:**
1. **Cost tracking**: After each suite, extract API cost from pytest output or env. For eval tests, parse the `Total cost: $X.XX` line from eval harness output. For non-eval suites, cost is $0.
2. **Structured fields**: Add to the results Markdown:
   - Per-suite: test count, pass count, fail count, skip count, duration, cost
   - Total: aggregate cost, total duration, overall pass/fail
   - Git info: current commit SHA, branch name, dirty state
   - Failure details: for each failed test, include the test name and first line of the failure message
3. **Latest pointer**: Update `docs/eval-results/latest.md` to point to the new results file (already done — verify it works)

**Done when:**
- Results file includes cost for eval suite (non-zero when eval runs)
- Results file includes git commit SHA
- Failed tests are listed with their failure reason
- `docs/eval-results/latest.md` points to the most recent run

### Story 33.8: False-Pass Validation (3h)

Create `tests/p0/test_false_pass.py` — a test that intentionally verifies the health gate catches failures.

**Tests:**
1. `test_health_gate_catches_caddy_down` — mock Caddy probe to fail, assert health gate reports Caddy as failed (already covered in `test_health_gate.py` — verify and reference)
2. `test_runner_rejects_empty_api_key` — run runner script with empty `THESTUDIO_ANTHROPIC_API_KEY`, assert exit code nonzero and stderr contains error message
3. `test_runner_rejects_placeholder_password` — run runner script with `POSTGRES_PASSWORD=thestudio_dev`, assert exit code nonzero

**Implementation:** These tests invoke the runner script as a subprocess with modified env vars. They prove the guards work in practice, not just in unit test mocks.

**Done when:**
- All 3 tests pass
- Tests prove the runner correctly rejects bad credentials (not just that the Python code does)

### Story 33.9: Documentation Update (2h)

Update deployment docs to reference the P0 test harness.

**Files to update:**
- `docs/GITHUB_SETUP_GUIDE.md` — add section: "Running P0 Deployment Tests"
- `docs/epics/EPIC-STATUS-TRACKER.md` — update Epic 33 status to "Complete" with delivered items
- `docs/epics/epic-33-p0-deployment-test-harness.md` — mark all ACs as delivered with evidence

**Done when:**
- A developer reading the setup guide knows how to run `./scripts/run-p0-tests.sh`
- Epic status tracker reflects Epic 33 complete
- Epic file has AC-by-AC delivery evidence

---

## Technical Reference

**Key files to read before starting:**
- `scripts/run-p0-tests.sh` — current runner (enhance for Stories 33.6, 33.7)
- `tests/p0/test_health_gate.py` — existing 8 health gate tests (reuse for Story 33.8)
- `tests/p0/conftest.py` — P0 fixtures, health gate integration
- `tests/p0/health.py` — health gate module
- `infra/docker-compose.prod.yml` — prod stack (service names for `docker compose exec`)
- `src/eval/harness.py` — eval harness (check for cost output format)
- `docs/eval-results/p0-20260320-125706.md` — latest results (current format to enhance)

**Runner script current flow:**
```
source infra/.env → validate credentials → health gate → p0-deployed suite →
eval suite (if not --skip-eval) → github-integration → postgres-integration →
generate results summary
```

**Exposed ports (prod compose):**
- 9080 (HTTP → redirect to HTTPS)
- 9443 (HTTPS, self-signed cert)
- 5434 (pg-proxy to Postgres)
- Temporal (7233) and NATS (4222) NOT exposed to host

**Docker compose project name:** `thestudio-prod`
**Container naming:** `thestudio-prod-app-1`, `thestudio-prod-postgres-1`, etc.

---

## Risks

| # | Risk | Mitigation |
|---|------|------------|
| R1 | `docker compose exec` may not work if container has no shell | All containers are based on Alpine or Debian — `printenv` should work |
| R2 | Eval test cost output format may vary | Check `src/eval/harness.py` for exact format; parse flexibly |
| R3 | Runner script subprocess tests may be slow | Keep timeout reasonable (10s); the script exits fast on credential failure |
| R4 | Git dirty state detection on Windows/WSL | Use `git status --porcelain` which works cross-platform |

---

## Constraints

- New files in `tests/p0/`, updates to `scripts/run-p0-tests.sh`, and docs only
- NO modifications to `src/` production code
- Eval tests cost ~$5/run — use `--skip-eval` during development
- Stories 33.6–33.8 must not break the existing 14 P0 deployed tests

---

## Definition of Done (Sprint Level)

1. Runner with `THESTUDIO_LLM_PROVIDER=mock` in container → eval suite aborted with clear message
2. Runner with real config → eval suite runs (may skip with `--skip-eval`)
3. Results file includes per-suite cost, git SHA, failure details
4. False-pass tests prove runner rejects empty API key and placeholder PG password
5. Documentation updated: setup guide, epic tracker, epic file
6. All existing tests still pass (`pytest tests/unit/ tests/p0/test_health_gate.py` green, P0 deployed green)

---

## After Sprint 2 Completes

**Epic 33 should be fully delivered.** All 8 ACs covered:
- AC 1: Health gate (Sprint 1) ✓
- AC 2: Eval guard (Story 33.6)
- AC 3: GitHub deployment tests (Sprint 1) ✓
- AC 4: Postgres deployment tests (Sprint 1) ✓
- AC 5: Runner script (Sprint 1) ✓
- AC 6: Results persistence (Story 33.7)
- AC 7: Env file parsing (Sprint 1 — uses `source`) ✓
- AC 8: Credential guard (Sprint 1) ✓

**Next milestone:** Process a real GitHub issue through the deployed stack at Observe tier. This is the first real production run of TheStudio.
