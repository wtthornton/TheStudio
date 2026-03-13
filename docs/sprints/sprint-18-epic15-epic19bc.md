# Sprint 18 Plan: Epic 15 (E2E Integration) + Epic 19 Streams B+C (Security Runner + Reputation DB)

**Planned by:** Helm
**Date:** 2026-03-12
**Status:** Meridian R1 CONDITIONAL PASS — 3 gaps fixed, awaiting R2 confirmation
**Epics:** `docs/epics/epic-15-e2e-integration-real-repo.md`, `docs/epics/epic-19-critical-gap-batch-1.md`
**Roadmap:** `docs/sprints/sprint-roadmap-epics-15-22.md` (Sprint 18 section)
**Sprint Duration:** 2 weeks (10 working days, 2026-03-31 to 2026-04-11)
**Capacity:** Single developer, 80% commitment = 8 effective days, 2 days buffer

---

## Sprint Goal (Testable Format)

**Objective:** Deliver an in-process integration test harness that chains all 9 pipeline stages with realistic mock data, wire the missing security scan runner into the verification gate, and persist reputation weights to PostgreSQL. By sprint end, the pipeline is proven end-to-end with data-fidelity tests, security scanning is available for any repo that opts in, and reputation weights survive application restart.

**Test:** After all stories are complete:
1. `pytest tests/integration/test_full_pipeline.py -v` passes — all 9 stages produce valid, non-empty output with realistic data flowing stage-to-stage.
2. `pytest tests/integration/test_pipeline_workflow.py -v` passes — existing 5 tests unchanged, new `TestRealisticPipeline` class uses mock providers with data-shape assertions.
3. Loopback tests assert exact `verification_loopbacks=1` and `qa_loopbacks=1` counts with realistic data; exhaustion test confirms `success=False` at `MAX_VERIFICATION_LOOPBACKS=2`.
4. Evidence comment test validates all 7 required sections of `format_full_evidence_comment()` output using pipeline-produced data, including `<!-- thestudio-evidence -->` marker.
5. `TIMING: total=...` line printed to stdout with per-stage breakdown; total < 5 seconds.
6. `docs/pipeline-latency-baseline.md` exists with initial measurements and methodology.
7. `docs/ONBOARDING.md` covers all 7 sections: prerequisites, GitHub App setup, Admin API registration, Admin UI registration, webhook verification, tier explanation, troubleshooting.
8. `pytest tests/verification/test_security_runner.py -v` passes — bandit pass, fail, missing binary, and timeout scenarios.
9. `pytest tests/verification/test_gate_security.py -v` passes — gate dispatches to security runner when `"security"` in `required_checks`.
10. `pytest tests/reputation/test_engine_persistence.py -v` passes — write-read roundtrip, restart survival (clear cache, re-query matches), drift history from DB, cache-hit avoids DB.
11. `ruff check src/verification/runners/security_runner.py src/reputation/engine.py src/reputation/db_models.py tests/integration/ tests/verification/ tests/reputation/` exits 0.
12. `pytest` (full suite) exits 0 — zero regressions.

**Constraint:** 8 effective working days. Stories interleaved across 3 streams (Epic 15 = 7 stories, Epic 19 Stream B = 3 stories, Epic 19 Stream C = 6 stories). Single developer works one story at a time, switching streams at natural stopping points. No Docker, no real API keys, no external services required for integration tests. Mock providers return realistically shaped data — no empty strings, no zero IDs.

---

## What's In / What's Out

**In Sprint 18 (16 stories, 8 estimated days):**
- 15.1: Mock provider harness (1 day)
- 15.2: Full pipeline smoke test (1 day)
- 15.3: Loopback integration tests (0.5 day)
- 15.4: Evidence comment validation (0.5 day)
- 15.5: Temporal data-fidelity test (0.5 day)
- 15.6: Pipeline latency baseline (0.5 day)
- 15.7: Real repo onboarding guide (0.5 day)
- B1: Security runner implementation (0.5 day)
- B2: Wire security runner into gate (0.25 day)
- B4: Security runner + gate tests (0.75 day)
- C1: SQLAlchemy model + migration 019 (0.5 day)
- C2: DB-backed write path (0.5 day)
- C3: DB-backed read path with cache (0.5 day)
- C4: Drift history from DB (0.5 day)
- C5: AsyncSession integration (0.25 day)
- C6: Persistence tests (0.75 day)

**Eliminated from original roadmap:**
- B3 (Add bandit dep): bandit is **already in** `pyproject.toml` dev extras (line 39). No work needed.

**Deferred:**
- Sprint 17 retro-informed adjustments (Sprint 17 has not completed yet; retro lessons applied from Epic 15 Meridian reviews instead)

**Rationale for stream order:** Epic 15 stories are the highest-value — they create the test harness reused by all future epics. Stream B (security runner) is a contained 1.5-day effort that can slot into gaps. Stream C (reputation DB) is the highest-risk work and is scheduled for days 5-7 so that days 1-4 build momentum and any Stream C overrun consumes buffer, not other stories.

---

## Ordered Backlog

### Days 1-2: Epic 15 Foundation (Stories 15.1-15.2)

#### Story 15.1: In-Process Integration Test Harness with Mock Providers (Est: 1 day)

**Sequence rationale:** Every subsequent integration test depends on the mock provider fixtures. This is the foundation stone for the sprint.

**Work:**
- Create `tests/integration/conftest.py` with shared fixtures for mock LLM provider, mock GitHub client, in-memory DB session, mock `ModelRouter`, mock `ToolPolicyEngine`
- Create `tests/integration/mock_providers.py` with mock activity implementations for all 9 stages:
  - Real `intake_activity` and `router_activity` used (pure functions, no external deps)
  - Mock activities for context, intent, assembler, implement, verify, QA, publish
  - Each returns properly typed dataclass instances matching the activity output types in `src/workflow/activities.py`

**Knowns:**
- Activity input/output dataclass patterns are at `src/workflow/activities.py` lines 22-199 — 18 dataclasses total
- Existing mock pattern in `test_pipeline_workflow.py` uses inline `@activity.defn` overrides (lines 137-151, 180-194)
- `PipelineInput` factory helper `_eligible_input()` exists at lines 52-69 of `test_pipeline_workflow.py`

**Unknowns:**
- Whether `intake_activity` calls anything beyond `evaluate_eligibility()` that needs mocking. Decision: read the function body before implementing. If it touches DB or settings, wrap with a fixture.
- Whether `router_activity` calls `get_model_router()` at execution time. Decision: check line references; if it does, the mock `ModelRouter` fixture handles it.

**Confidence:** 85%. Pure fixture creation with well-defined output shapes. Risk: discovering an activity has a hidden side effect requiring an extra mock.

**Files to create:**
- `tests/integration/conftest.py`
- `tests/integration/mock_providers.py`

**Files to read (dependencies):**
- `src/workflow/activities.py` (lines 22-199) — all I/O dataclass shapes
- `tests/integration/test_pipeline_workflow.py` (lines 52-69, 83-93) — existing mock patterns
- `src/intake/intake_agent.py` — `evaluate_eligibility()` deps
- `src/routing/router.py` — `route()` deps

---

#### Story 15.2: Full Pipeline Smoke Test — Webhook to Draft PR (Est: 1 day)

**Sequence rationale:** Depends on 15.1 (fixtures). Proves the chain works. Gives confidence to all subsequent stories.

**Work:**
- Create `tests/integration/test_full_pipeline.py` with `test_full_pipeline_happy_path()`
- Construct `PipelineInput` with realistic fields (UUID taskpacket_id, labels `["agent:run", "type:bug"]`, repo `"test-org/test-repo"`, issue title + body)
- Execute activity chain in sequence: intake → context → intent → router → assembler → implement → verify → QA → publish
- Each stage receives output of previous stage (not hardcoded inputs)
- Assert each stage produced valid output (non-empty fields, correct types)
- Assert final output: `success=True`, `pr_number > 0`, `pr_url` non-empty

**Knowns:**
- `PipelineOutput` has `success`, `step_reached`, `rejection_reason`, `pr_number`, `pr_url`, `marked_ready`, `verification_loopbacks`, `qa_loopbacks` (lines 152-162 of pipeline.py)
- Mock publish returns `pr_number=42`, `pr_url="https://github.com/test-org/test-repo/pull/42"`

**Unknowns:**
- The exact data-passing pattern between stages. Decision: inspect existing workflow `run()` method (lines 174-358 of pipeline.py) to see how outputs feed into next inputs, then replicate that chain in the test without Temporal.

**Confidence:** 85%. Straightforward chaining. Risk: data-contract mismatch between stages discovered during test (which is the point).

**Files to create:**
- `tests/integration/test_full_pipeline.py`

**Pytest marker:** No marker. Runs on every `pytest` invocation (matching existing tests in `tests/integration/`).

---

### Day 3: Epic 15 (Story 15.3) + Epic 19 Stream B Start (Story B1)

#### Story 15.3: Loopback Integration Tests (Est: 0.5 day, morning)

**Sequence rationale:** Depends on 15.1 (fixtures). Tests gate-fails-closed invariant with realistic data.

**Work:**
- Extend `tests/integration/test_pipeline_workflow.py` with new test class `TestRealisticLoopback`:
  - `test_verification_loopback_with_realistic_data()`: mock verify fails first call, passes second. Assert `verification_loopbacks=1`, re-implementation receives verification failure details, final output `success=True`.
  - `test_verification_exhaustion_with_realistic_data()`: mock verify always fails. Assert `success=False`, `step_reached="verify"`, `verification_loopbacks=2` (matching `MAX_VERIFICATION_LOOPBACKS`).
  - `test_qa_loopback_with_realistic_data()`: mock QA fails first, passes second. Assert `qa_loopbacks=1`, `success=True`.
- Uses mock providers from 15.1 (`mock_providers.py`), not inline stubs

**Knowns:**
- Existing classes `TestVerificationLoopback` (line 130), `TestQALoopback` (line 173), `TestGateExhaustion` (line 216) — do not duplicate; extend with realistic data
- `MAX_VERIFICATION_LOOPBACKS = 2`, `MAX_QA_LOOPBACKS = 2` (pipeline.py lines 129-130)
- Loopback counter tracked in `PipelineOutput.verification_loopbacks` and `qa_loopbacks` (lines 160-162)

**Unknowns:** None. Clear pattern to follow from existing tests.

**Confidence:** 90%.

**Files to modify:**
- `tests/integration/test_pipeline_workflow.py` — EXTEND with `TestRealisticLoopback` class

---

#### Story B1: Implement Security Runner (Est: 0.5 day, afternoon)

**Sequence rationale:** Independent of Epic 15. Follows `ruff_runner.py` pattern exactly.

**Work:**
- Create `src/verification/runners/security_runner.py` with `run_security_scan()`:
  - Async function following `run_ruff()` pattern (ruff_runner.py lines 14-62)
  - Parameters: `changed_files: list[str]`, `repo_path: str`, `timeout: int = 120`
  - Returns: `CheckResult` (from `base.py` lines 6-13)
  - Runs `bandit -r` via `asyncio.create_subprocess_exec` against changed files
  - Timeout handling: `CheckResult(name="security", passed=False, details="Timeout...")`
  - Missing binary: `CheckResult(name="security", passed=False, details="bandit not found...")`
  - Gate fails closed: any error → `passed=False`
  - Duration tracking in milliseconds (matching ruff_runner pattern)

**Knowns:**
- `run_ruff()` pattern at `src/verification/runners/ruff_runner.py` lines 14-62 — exact template
- `CheckResult` at `src/verification/runners/base.py` lines 6-13 — 4 fields: name, passed, details, duration_ms
- bandit already installed in dev deps (`pyproject.toml` line 39)
- DEFAULT_TIMEOUT = 120 (matching ruff_runner line 11)

**Unknowns:**
- bandit CLI flags for scanning specific files vs directories. Decision: use `bandit -r -f json` for parseable output; fall back to text if JSON parsing fails.
- Whether bandit returns non-zero on findings (it does — exit code 1 for findings). Map accordingly.

**Confidence:** 90%. Direct template copy from ruff_runner with tool substitution.

**Files to create:**
- `src/verification/runners/security_runner.py`

---

### Day 4: Stream B Completion (Stories B2 + B4) + Epic 15 (Story 15.4)

#### Story B2: Wire Security Runner into Gate (Est: 0.25 day)

**Sequence rationale:** Depends on B1 (runner exists). Connects runner to the verification gate.

**Work:**
- Add `"security": "security"` to `_RUNNERS` map at `src/verification/gate.py` line 46-49
- Add dispatch branch in `_run_check()` at lines 62-81: `elif check_name == "security": return await run_security_scan(changed_files, repo_path)`
- Import `run_security_scan` from runners module
- Security runs only when `"security"` in repo profile's `required_checks` list (existing mechanism at lines 115-117)

**Knowns:**
- `_RUNNERS` map at gate.py lines 46-49: currently `{"ruff": "ruff", "pytest": "pytest"}`
- `_run_check()` dispatcher at lines 62-81: if/elif chain routing check_name to runner functions
- Repo profile `required_checks` filtering at lines 115-117: already filters which checks run
- No changes needed to repo profile — repos opt in by adding `"security"` to their `required_checks`

**Unknowns:** None.

**Confidence:** 95%.

**Files to modify:**
- `src/verification/gate.py`

---

#### Story B4: Security Runner + Gate Integration Tests (Est: 0.75 day)

**Sequence rationale:** Depends on B1 + B2. Validates the full chain.

**Work:**
- Create `tests/verification/test_security_runner.py`:
  - `test_clean_code_passes()`: scan a file with no security issues → `passed=True`
  - `test_vulnerable_code_fails()`: scan a file with a known bandit issue (e.g., `eval()`) → `passed=False`, details contain finding
  - `test_missing_binary_fails_closed()`: mock `asyncio.create_subprocess_exec` to raise `FileNotFoundError` → `passed=False`, details contain "bandit not found"
  - `test_timeout_fails_closed()`: mock subprocess to hang → `passed=False`, details contain "Timeout"
  - `test_empty_files_returns_pass()`: no changed files → `passed=True` (consistent with ruff_runner behavior)
- Create `tests/verification/test_gate_security.py`:
  - `test_gate_dispatches_to_security_runner()`: mock security runner, verify `_run_check("security", ...)` calls it
  - `test_gate_skips_security_when_not_configured()`: repo profile without `"security"` in `required_checks` → security runner not called
  - `test_gate_includes_security_in_results()`: when security runs, `VerificationResult.checks` includes a `CheckResult` with `name="security"`

**Knowns:**
- Existing test patterns in `tests/verification/` for ruff and pytest runners
- `VerificationResult.checks` is `list[CheckResult]` (gate.py lines 52-59)

**Unknowns:** None.

**Confidence:** 90%.

**Files to create:**
- `tests/verification/test_security_runner.py`
- `tests/verification/test_gate_security.py`

---

#### Story 15.4: Evidence Comment Validation — End-to-End Format Check (Est: 0.5 day)

**Sequence rationale:** Depends on 15.1 (fixtures provide pipeline data). Independent of B stories.

**Work:**
- Extend `tests/integration/test_evidence_validation.py` with new test class `TestFullEvidenceComment`:
  - Run pipeline via mock providers (15.1 harness)
  - Collect outputs from each stage to construct inputs for `format_full_evidence_comment()`:
    - `evidence: EvidenceBundle` from implement output
    - `intent: IntentSpecRead` from intent output
    - `verification: VerificationResult` from verify output
    - `correlation_id: UUID` from PipelineInput
    - `qa_result: QAResultSummary` from QA output (optional)
    - `expert_coverage: ExpertCoverageSummary` from routing output (optional)
    - `loopback: LoopbackSummary` from pipeline state (optional)
  - Assert output contains all 7 sections (non-empty):
    1. `<!-- thestudio-evidence -->` marker
    2. `## TheStudio Evidence` header with TaskPacket ID, Correlation ID, Intent Version, Verification status
    3. `### Intent Summary` with non-empty goal
    4. `### Acceptance Criteria` with at least one checkbox
    5. `### What Changed` with at least one file path
    6. `### Verification Results` with at least one table row
    7. Footer: `Generated by TheStudio`
  - Optional sections: "No experts consulted" / "No loopbacks" are acceptable non-placeholder defaults

**Knowns:**
- `format_full_evidence_comment()` at `src/publisher/evidence_comment.py` lines 115-123: takes 7 params
- Supporting dataclasses at lines 88-113: `ExpertCoverageSummary`, `LoopbackSummary`, `QAResultSummary`
- Existing 9 tests in `TestEvidenceCommentFormat` (lines 63-138) cover basic `format_evidence_comment()` — do not duplicate

**Unknowns:**
- Exact mapping from mock activity outputs to `format_full_evidence_comment()` parameters. Decision: read the function body (lines 206-250) to understand which fields it reads from each parameter.

**Confidence:** 85%.

**Files to modify:**
- `tests/integration/test_evidence_validation.py` — EXTEND with `TestFullEvidenceComment` class

---

### Day 5: Epic 15 (Story 15.5) + Stream C Start (Story C1)

#### Story 15.5: Temporal Workflow Data-Fidelity Test (Est: 0.5 day, morning)

**Sequence rationale:** Depends on 15.1 (mock providers). Extends existing Temporal tests with realistic data.

**Work:**
- Add `TestRealisticPipeline` class to `tests/integration/test_pipeline_workflow.py`:
  - `test_realistic_happy_path()`: uses mock providers from `mock_providers.py`, asserts data shape on every stage output (non-empty UUIDs, populated acceptance criteria, non-zero PR number)
  - `test_realistic_loopback()`: configurable verify mock fails then passes, asserts re-implementation receives failure details, `verification_loopbacks=1`
- Tests use `WorkflowEnvironment.start_local()` and `Worker` with mock activity implementations
- Activity execution order tracked via mock call recording

**Knowns:**
- Temporal test setup pattern at `test_pipeline_workflow.py` lines 88-93: `WorkflowEnvironment.start_local()` + `Worker`
- Existing 5 tests in 4 classes (lines 83-279) — all must continue to pass unchanged
- No `@pytest.mark.integration` marker (matching existing tests)

**Unknowns:** None. Pattern is established.

**Confidence:** 85%.

**Files to modify:**
- `tests/integration/test_pipeline_workflow.py` — EXTEND with `TestRealisticPipeline` class

---

#### Story C1: SQLAlchemy Model + Migration 019 (Est: 0.5 day, afternoon)

**Sequence rationale:** Foundation for all Stream C stories. Must reconcile schema gap.

**Work:**
- Create `src/reputation/db_models.py` with SQLAlchemy ORM model `ExpertReputationRow` mapped to `expert_reputation` table
- Create `src/db/migrations/019_reputation_weight_history.py`:
  - **Schema gap fixes (rename to match code models):**
    - Rename `drift_direction` column → `drift_signal` (model uses `DriftSignal` enum, not `drift_direction`)
    - Rename `drift_score` column → remove (model computes drift from history, does not store a score)
    - Rename `last_outcome_at` column → `last_indicator_at` (model field name)
  - **New column:**
    - Add `weight_history JSONB DEFAULT '[]'` — stores recent weight values for drift detection (replaces `_weight_history` in-memory dict)
  - Migration is idempotent (ADD COLUMN IF NOT EXISTS, rename via safe pattern)
  - Rollback DDL reverses all changes

**Knowns — SCHEMA GAP ANALYSIS:**

| Migration 008 Column | ExpertWeight Model Field | Match? | Action |
|---|---|---|---|
| `expert_id UUID` | `expert_id: UUID` | MATCH | None |
| `context_key VARCHAR(255)` | `context_key: str` | MATCH | None |
| `expert_version INTEGER` | `expert_version: int` | MATCH | None |
| `weight FLOAT` | `weight: float` | MATCH | None |
| `raw_weight_sum FLOAT` | `raw_weight_sum: float` | MATCH | None |
| `sample_count INTEGER` | `sample_count: int` | MATCH | None |
| `confidence FLOAT` | `confidence: float` | MATCH | None |
| `trust_tier trust_tier` | `trust_tier: TrustTier` | MATCH | None |
| `tier_changed_at TIMESTAMPTZ` | (not in model) | EXTRA | Keep — useful metadata |
| `last_outcome_at TIMESTAMPTZ` | `last_indicator_at: datetime` | NAME MISMATCH | Rename column |
| `drift_direction drift_direction` | `drift_signal: DriftSignal` | NAME + TYPE MISMATCH | Rename column + enum type |
| `drift_score FLOAT` | (not in model) | EXTRA | Keep — backward compat |
| `created_at TIMESTAMPTZ` | `created_at: datetime` | MATCH | None |
| `updated_at TIMESTAMPTZ` | `updated_at: datetime` | MATCH | None |
| (missing) | (weight_history for drift) | MISSING | Add JSONB column |

**Decision on renames vs aliases:** Use column aliases in the ORM model rather than renaming database columns. This avoids a destructive migration. The ORM model maps `drift_signal` to column `drift_direction` and `last_indicator_at` to column `last_outcome_at`. Migration 019 only adds the `weight_history` JSONB column.

**Unknowns:**
- Whether the `drift_direction` PostgreSQL enum type has the same values as `DriftSignal`. Migration 008 creates `drift_direction` with values `improving, stable, declining` (line 36). Model `DriftSignal` has `IMPROVING, STABLE, DECLINING` (lines 28-33). Values match (case-insensitive in PG enums). No migration needed for the enum type.

**Confidence:** 80%. Schema analysis is complete. The column alias approach eliminates the destructive rename risk.

**Files to create:**
- `src/reputation/db_models.py`
- `src/db/migrations/019_reputation_weight_history.py`

---

### Days 6-7: Stream C Core (Stories C2-C5) + Epic 15 (Story 15.6)

#### Story C2: DB-Backed Write Path (Est: 0.5 day)

**Sequence rationale:** Depends on C1 (ORM model). Write path must work before read path.

**Work:**
- Modify `src/reputation/engine.py` `update_weight()` (lines 217-307):
  - After computing new `ExpertWeight`, upsert to DB via `AsyncSession`
  - Pattern: DB write first → update in-memory `_weights` cache second
  - Use `INSERT ... ON CONFLICT (expert_id, context_key) DO UPDATE` for upsert
  - Append to `weight_history` JSONB array in DB (for drift detection)
  - Session passed as parameter or injected via factory

**Knowns:**
- `update_weight()` at lines 217-307: creates/updates `ExpertWeight`, stores in `_weights` dict
- Primary key is `(expert_id, context_key)` (migration 008 lines 42-60)
- Existing codebase uses `AsyncSession` throughout (e.g., verification gate at gate.py line 85)

**Unknowns:**
- How to reconcile sync `ReputationEngineProtocol` (engine.py lines 38-52) with async DB calls. The Protocol defines sync methods (`def update_weight`, `def query_weights`). Adding `await` would make them `async` and break the interface.

**Decision — Separate Async Wrapper Class:**
Create `AsyncReputationEngine` in `src/reputation/engine.py` (or a new `src/reputation/async_engine.py`) that:
  1. Holds a reference to the existing sync `InMemoryReputationEngine` for cache operations
  2. Adds `async def update_weight_persistent()` and `async def query_weights_persistent()` methods that write/read DB via `AsyncSession` and then delegate to the sync engine for cache
  3. The sync `ReputationEngineProtocol` and `InMemoryReputationEngine` are **completely unchanged**
  4. Callers that want persistence use `AsyncReputationEngine`; callers that don't (tests, in-memory mode) use `InMemoryReputationEngine` as before
  5. The Router and admin API call sites are updated to use the async wrapper in production, but this is a thin change (swap the engine instance, use `await`)

This avoids the impossible "sometimes sync, sometimes async" function problem. The Protocol stays sync. The async layer is additive.

**Confidence:** 75%. First async DB integration in the reputation module. The wrapper pattern is clean but requires verifying all caller sites.

**Files to create/modify:**
- `src/reputation/engine.py` — add `AsyncReputationEngine` class (or `src/reputation/async_engine.py` as new file)

**Regression check:** After modifying engine.py, run `pytest tests/reputation/ -v` to confirm all existing tests pass. The sync `InMemoryReputationEngine` and `ReputationEngineProtocol` must be unchanged.

---

#### Story C3: DB-Backed Read Path with Cache (Est: 0.5 day)

**Sequence rationale:** Depends on C1 (ORM model) and C2 (write path). Read path with cache-first semantics.

**Work:**
- Add `async def query_weights_persistent()` and `async def get_weight_persistent()` to `AsyncReputationEngine`:
  - Check sync engine's `_weights` cache first (delegate to `InMemoryReputationEngine.query_weights()`)
  - On cache miss, query DB via `AsyncSession`
  - Populate sync engine's cache from DB result
  - Return result
- The sync `query_weights()` and `get_weight()` on `InMemoryReputationEngine` are **unchanged**

**Knowns:**
- `query_weights()` at lines 310-347: filters `_weights` dict by expert_id, context_key, repo, trust_tier, min_confidence
- `ReputationEngineProtocol` interface at lines 38-52: 7 methods, all must remain unchanged
- `AsyncReputationEngine` wraps the sync engine (from C2 decision)

**Unknowns:** None. Cache-then-DB is a standard pattern.

**Confidence:** 80%.

**Regression check:** Run `pytest tests/reputation/ -v` — all existing tests must pass.

**Files to modify:**
- `src/reputation/engine.py` (or `src/reputation/async_engine.py`)

---

#### Story C4: Drift History from DB (Est: 0.5 day)

**Sequence rationale:** Depends on C1 (JSONB column) and C2 (write path stores history).

**Work:**
- Modify drift computation in `_compute_drift()` (lines 130-160):
  - Currently reads from `_weight_history` dict (in-memory, line 57)
  - Add DB fallback: on cache miss for a `(expert_id, context_key)` pair, load `weight_history` JSONB from DB
  - Populate `_weight_history` cache from DB result
  - `DRIFT_WINDOW_SAMPLES = 10` (line 138) — only recent 10 values needed

**Knowns:**
- `_weight_history` at line 57: `dict[tuple[UUID, str], list[float]]`
- `_compute_drift()` at lines 130-160: uses linear regression over `DRIFT_WINDOW_SAMPLES`
- JSONB column stores array of floats — direct mapping

**Unknowns:** None.

**Confidence:** 85%.

**Files to modify:**
- `src/reputation/engine.py`

---

#### Story C5: AsyncSession Integration (Est: 0.25 day)

**Sequence rationale:** Cross-cutting concern. Ensures all DB calls use consistent async patterns.

**Work:**
- Verify all DB operations in C2/C3/C4 use `AsyncSession`
- Wire session dependency: add session factory or accept session parameter consistently
- Ensure no sync DB calls leak in (grep for `Session` without `Async` prefix)
- Add `__init__.py` exports if needed

**Knowns:**
- Existing pattern: `async def verify(session: AsyncSession, ...)` at gate.py line 85
- SQLAlchemy async session factory pattern used throughout `src/db/`

**Unknowns:** None.

**Confidence:** 90%.

**Files to modify:**
- `src/reputation/engine.py` (finalize session wiring)

---

#### Story 15.6: Pipeline Latency Baseline (Est: 0.5 day)

**Sequence rationale:** Depends on 15.2 (full pipeline test). Adds timing instrumentation.

**Work:**
- Add timing instrumentation to `test_full_pipeline_happy_path()` in `test_full_pipeline.py`:
  - Wrap each stage call with `time.perf_counter()` start/stop
  - Print: `TIMING: total=1.234s intake=0.012s context=0.045s ...`
  - Assert total < 5 seconds
- Create `docs/pipeline-latency-baseline.md`:
  - Date, hardware/OS, Python version, dependency versions
  - Per-stage timing from first run
  - Expected variance (mocks near-zero; real providers 10-100x slower)
  - Methodology for re-running

**Knowns:**
- `time.perf_counter()` is the correct timer for wall-clock measurements
- All mock providers should complete in microseconds

**Unknowns:** None.

**Confidence:** 95%.

**Files to modify:**
- `tests/integration/test_full_pipeline.py` — add timing

**Files to create:**
- `docs/pipeline-latency-baseline.md`

---

### Day 8: Stream C Tests (Story C6) + Epic 15 (Story 15.7) + Buffer Start

#### Story C6: Persistence Tests (Est: 0.75 day)

**Sequence rationale:** Depends on C2-C5. Validates the full persistence chain.

**Work:**
- Create `tests/reputation/test_engine_persistence.py`:
  - `test_write_read_roundtrip()`: update_weight → query_weights → values match
  - `test_data_survives_restart()`: update_weight → clear `_weights` and `_weight_history` caches → query_weights from DB → values match original
  - `test_drift_history_loaded_from_db()`: update_weight multiple times → clear `_weight_history` → trigger drift computation → drift values correct (loaded from JSONB)
  - `test_cache_hit_avoids_db()`: update_weight (populates cache) → mock session to track queries → query_weights → assert no DB query executed
  - `test_concurrent_updates_no_corruption()`: two concurrent update_weight calls for same expert → both complete without error, final weight reflects both updates
- Tests use `aiosqlite` (already in dev deps, line 43) or pytest-asyncio fixtures with in-memory SQLite

**Knowns:**
- `aiosqlite` at pyproject.toml line 43 — already available for async SQLite testing
- `ExpertWeight` fields at models.py lines 54-95 — all fields to assert in roundtrip
- `TrustTier` states: SHADOW, PROBATION, TRUSTED (lines 14-25)

**Unknowns:**
- Whether SQLAlchemy async works with `aiosqlite` for the JSONB column (SQLite doesn't have native JSONB). Decision: store as JSON text in SQLite for tests; PostgreSQL uses native JSONB in production. The ORM model handles the mapping.

**Confidence:** 75%. Async SQLite + JSONB compatibility is the main risk.

**Decision gate (time-boxed):** Spend max 2 hours on aiosqlite + JSONB. Use SQLAlchemy's `JSON` type adapter (which stores as TEXT in SQLite). If the JSON column does not round-trip correctly within 2 hours, **switch to mocking `AsyncSession`** for test assertions — mock the DB layer and verify the engine's write-through and cache-miss logic without a real database. Do NOT spend buffer days on aiosqlite compatibility. PostgreSQL integration tests are deferred to the Docker test rig (Epic 18).

**Files to create:**
- `tests/reputation/test_engine_persistence.py`

---

#### Story 15.7: Real Repo Onboarding Guide (Est: 0.5 day)

**Sequence rationale:** Documentation only. Independent of all code stories. Slotted last as the most compressible story.

**Work:**
- Extend `docs/ONBOARDING.md` with 7 sections:
  1. Prerequisites (reference `docs/deployment.md`)
  2. GitHub App setup (permissions, webhook URL, secret)
  3. Admin API registration (`POST /admin/repos`)
  4. Admin UI registration (Settings > Repositories)
  5. Webhook verification (create test issue, check Admin UI)
  6. Tier explanation (Observe/Suggest/Execute behaviors)
  7. Troubleshooting (signature failures, repo not found, intake rejection)
- Fix Step 3 per Meridian R2 finding: clarify Observe tier creates TaskPacket, NOT draft PR
- Verify every API endpoint mentioned against actual router definitions

**Knowns:**
- `docs/ONBOARDING.md` exists with basic content (Epic 15 prep)
- `POST /admin/repos` endpoint exists (confirmed in docker test fixtures)
- `add_comment()` at github_client.py line 107 — uses Issues API (works for both issues and PRs)

**Unknowns:** None.

**Confidence:** 95%.

**Files to modify:**
- `docs/ONBOARDING.md`

---

### Days 9-10: Buffer

**Buffer allocation (2 days):**
- Day 9: Full regression testing. Run `pytest` full suite, `ruff check`, `mypy` on all new/modified files. Fix any failures.
- Day 10: Edge case testing, code review preparation, any spillover.

**Named buffer consumers (most likely to least likely):**
1. **Story C6 overrun** (75% confidence) — async SQLite + JSONB compatibility issue
2. **Story C2 overrun** (75% confidence) — async session lifecycle in reputation engine
3. **Story 15.1 overrun** — hidden side effect in an activity function requiring extra mocking
4. **Regression failures** from any Stream C modification to `src/reputation/engine.py`

**Compressible stories (what gets cut if time runs short):**
1. **15.7 (onboarding guide)** — documentation only, zero code impact. Can move to Sprint 19.
2. **15.6 (latency baseline)** — timing instrumentation is a nice-to-have. The test itself (15.2) proves the pipeline works; timing can be added later.
3. **C4 (drift history from DB)** — drift detection works in-memory during a single process lifetime. DB persistence is a correctness improvement but not blocking for Sprint 19's gateway wiring.

---

## Dependencies

### Internal (between stories)

```
15.1 (mock providers)
  ├──→ 15.2 (full pipeline) ──→ 15.6 (latency baseline)
  ├──→ 15.3 (loopback tests)
  ├──→ 15.4 (evidence validation)
  └──→ 15.5 (Temporal data-fidelity)
15.7 (onboarding guide) — independent of all code stories

B1 (security runner) ──→ B2 (wire into gate) ──→ B4 (tests)

C1 (ORM model + migration) ──→ C2 (write path) ──→ C3 (read path) ──→ C4 (drift history)
                                                                          └──→ C5 (async session)
                                                                               └──→ C6 (tests)
```

### Cross-stream dependencies

**None.** Epic 15, Stream B, and Stream C are fully independent code paths:
- Epic 15: `tests/integration/`
- Stream B: `src/verification/runners/`, `src/verification/gate.py`
- Stream C: `src/reputation/`, `src/db/migrations/`

No file is touched by more than one stream.

### External (blocking items)

| Dependency | Status | Risk |
|---|---|---|
| `temporalio` SDK for `WorkflowEnvironment` | VERIFIED — already in deps, used by existing tests | None |
| `pytest-asyncio` for async test support | VERIFIED — pyproject.toml line 31 | None |
| `bandit` for security runner | VERIFIED — pyproject.toml line 39 | None |
| `aiosqlite` for async SQLite testing | VERIFIED — pyproject.toml line 43 | JSONB compat risk (see C6) |
| Migration 008 schema | VERIFIED — schema gap analyzed, column aliases planned | None |
| Sprint 17 (Epic 16) | INDEPENDENT — no file overlap, no blocking dependency | None |

---

## Estimation Summary

| Stream | Story | Days | Confidence | Key Risk |
|--------|-------|------|------------|----------|
| Epic 15 | 15.1: Mock providers | 1 | 85% | Hidden activity side effects |
| Epic 15 | 15.2: Full pipeline smoke | 1 | 85% | Data-contract mismatches (the point of the test) |
| Epic 15 | 15.3: Loopback tests | 0.5 | 90% | None — clear pattern |
| Epic 15 | 15.4: Evidence validation | 0.5 | 85% | Mapping mock outputs to format_full params |
| Epic 15 | 15.5: Temporal data-fidelity | 0.5 | 85% | None — established pattern |
| Epic 15 | 15.6: Latency baseline | 0.5 | 95% | None — timing + docs |
| Epic 15 | 15.7: Onboarding guide | 0.5 | 95% | None — documentation |
| Stream B | B1: Security runner | 0.5 | 90% | bandit CLI flag selection |
| Stream B | B2: Wire into gate | 0.25 | 95% | None |
| Stream B | B4: Runner + gate tests | 0.75 | 90% | None |
| Stream C | C1: ORM model + migration | 0.5 | 80% | Schema gap analysis (completed) |
| Stream C | C2: DB write path | 0.5 | 75% | Async session lifecycle |
| Stream C | C3: DB read path + cache | 0.5 | 80% | Cache invalidation edge cases |
| Stream C | C4: Drift history from DB | 0.5 | 85% | JSONB array handling |
| Stream C | C5: AsyncSession integration | 0.25 | 90% | None — cross-cutting wiring |
| Stream C | C6: Persistence tests | 0.75 | 75% | aiosqlite + JSONB compat |
| | **Total story work** | **8** | | |
| | Buffer | 2 | | C6 or C2 overrun most likely |
| | **Sprint total** | **10** | | |

---

## Capacity and Buffer

- **Available:** 10 working days (2 weeks)
- **Committed:** 8 days of story work (80%)
- **Buffer:** 2 days (20%) — explicitly reserved, not allocated to stories
- **Effective allocation:** 80%

---

## Retro Actions

**Prior sprint:** Sprint 17 has not yet executed (starts 2026-03-17). Retro lessons applied from the Epic 15 Meridian review trail and roadmap planning:

1. **Every story names existing files it extends** — Stories 15.3, 15.4, 15.5 all specify "EXTEND with {class name}" and list the existing classes that must not be duplicated.
2. **Pytest markers match existing convention** — No `@pytest.mark.integration` on mock-based tests. Only Stream C persistence tests may use the marker if they require a real database.
3. **Source code line numbers verified before planning** — All file references include verified line numbers from the current codebase (verified 2026-03-12).
4. **Schema gap fully analyzed before sprint start** — The migration 008 vs ExpertWeight model mismatch is documented in Story C1 with a clear decision (column aliases, not renames). This avoids Day 5 surprises.

---

## Key Decisions Made in This Plan

1. **Column aliases instead of column renames for reputation schema.** Migration 008 uses `drift_direction` and `last_outcome_at`; the code model uses `drift_signal` and `last_indicator_at`. Rather than a destructive `ALTER TABLE RENAME COLUMN`, the ORM model maps code field names to existing column names. Migration 019 only adds the `weight_history` JSONB column.

2. **Story B3 eliminated.** bandit is already in `pyproject.toml` dev extras (line 39). Verified 2026-03-12.

3. **Async wrapper class for reputation DB.** The sync `ReputationEngineProtocol` and `InMemoryReputationEngine` are unchanged. A new `AsyncReputationEngine` wraps the sync engine, adding `async def update_weight_persistent()` and `query_weights_persistent()` methods that write/read DB and delegate to the sync engine for cache. This avoids the impossible "sometimes sync, sometimes async" function problem. Production callers use the async wrapper; tests use the sync engine directly.

4. **Stream C scheduled for days 5-7.** The highest-risk work (75% confidence on C2 and C6) runs after 4 days of momentum from Epic 15 and Stream B. Any overrun consumes buffer days 9-10, not other stories.

5. **Compressible stories identified.** If time is short: drop 15.7 (docs), then 15.6 (timing), then C4 (drift history DB). Core deliverables (integration tests, security runner, write/read persistence) are protected.

---

## Definition of Done for Sprint 18

- [ ] `tests/integration/conftest.py` and `mock_providers.py` exist with documented fixtures
- [ ] `tests/integration/test_full_pipeline.py` passes with 9-stage chain and realistic data
- [ ] `tests/integration/test_pipeline_workflow.py` has `TestRealisticPipeline` and `TestRealisticLoopback` classes; all 5 existing tests unchanged and passing
- [ ] `tests/integration/test_evidence_validation.py` has `TestFullEvidenceComment` class validating all 7 sections
- [ ] `TIMING: total=...` printed to stdout; total < 5s with mocks
- [ ] `docs/pipeline-latency-baseline.md` exists with initial measurements
- [ ] `docs/ONBOARDING.md` covers all 7 sections; Observe tier behavior corrected
- [ ] `src/verification/runners/security_runner.py` exists, runs bandit, fails closed on errors
- [ ] `src/verification/gate.py` dispatches to security runner when `"security"` in required_checks
- [ ] `tests/verification/test_security_runner.py` covers pass, fail, missing binary, timeout
- [ ] `tests/verification/test_gate_security.py` covers dispatch, skip, result inclusion
- [ ] `src/reputation/db_models.py` exists with ORM model mapped to `expert_reputation` table
- [ ] `src/db/migrations/019_reputation_weight_history.py` adds `weight_history` JSONB column
- [ ] `src/reputation/engine.py` writes to DB first, then cache; reads cache-first with DB fallback
- [ ] `tests/reputation/test_engine_persistence.py` covers roundtrip, restart survival, drift history, cache hit
- [ ] `ReputationEngineProtocol` interface unchanged — no caller modifications needed
- [ ] `ruff check` exits 0 on all new/modified files
- [ ] `pytest` (full suite) exits 0 — zero regressions
- [ ] Code committed to feature branch, ready for Meridian review

---

## Meridian Review Status

### Round 1: Conditional PASS — 3 gaps fixed

**Date:** 2026-03-12
**Verdict:** Conditional PASS — all 3 gaps addressed

| # | Gap | Severity | Resolution |
|---|-----|----------|------------|
| 1 | No explicit regression check after modifying reputation engine | Medium | Added "Regression check: run `pytest tests/reputation/ -v`" to Stories C2, C3, and C5 |
| 2 | Sync `ReputationEngineProtocol` conflicts with async DB calls — plan was silent on sync/async boundary | High | Resolved: separate `AsyncReputationEngine` wrapper class. Sync protocol and `InMemoryReputationEngine` completely unchanged. Async wrapper adds persistent methods. Key decision #3 updated. |
| 3 | aiosqlite JSONB risk had no decision gate | Medium | Added time-boxed gate to Story C6: 2 hours max on aiosqlite, then switch to mocking AsyncSession |

**Passed items:**
- Sprint goal: 12 testable verification criteria — PASS
- Story ordering with rationale — PASS
- Dependencies verified with source code line numbers — PASS
- Per-story estimation with confidence and risk — PASS
- Retro actions (from Epic 15 Meridian reviews, Sprint 17 not yet executed) — PASS
- Capacity 80/20 with named buffer consumers — PASS
- Async-readable with key decisions documented — PASS
- Schema gap analysis (column aliases, not renames) — PASS
- Story B3 elimination (bandit already in deps) — PASS
- Compressible story ordering — PASS
- Cross-stream file independence — PASS

### Round 2: Pending confirmation
