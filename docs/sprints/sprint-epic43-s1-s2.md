# Sprint Plan: Epic 43 Ralph SDK Integration (Sprints 1 + 2)

**Planned by:** Helm
**Date:** 2026-03-22
**Status:** DRAFT -- Awaiting Meridian Review
**Epic:** Epic 43 (Ralph SDK as Primary Agent -- Session Continuity, Circuit Breaking, Cost-Aware Implementation)
**Total Duration:** 2 sprints across 2 weeks
**Capacity:** Single developer, 30 hours per week (5 days x 6 productive hours)
**Epic Source:** `docs/epics/epic-43-ralph-sdk-integration.md` (Meridian PASS 2026-03-22)

---

## Work Stream Architecture

Two sequential sprints covering Slices 1-3 of the epic. Slice 4 (Validation, 8h) is planned after Sprint 2 completes.

```
Sprint 1 (Week of 2026-03-23): Slice 1 -- MVP (Stories 43.1-43.5)
    |
    v  -- Gate: all unit tests green, implement() dispatches to Ralph, feature flag works --
    |
Sprint 2 (Week of 2026-03-30): Slice 2 + Slice 3 (Stories 43.6-43.12)
    |
    v  -- Gate: integration tests green, cost recording verified, heartbeat confirmed --
    |
[Sprint 3 planned after Sprint 2]: Slice 4 -- Validation (Stories 43.13-43.15, ~8h)
```

**Rationale for this sequence:**
1. Slice 1 is pure risk reduction. It proves the SDK imports, the model bridge works, and the feature flag dispatches correctly -- all with `NullStateBackend` and mocked `RalphAgent.run()`. If the SDK does not integrate cleanly, we discover it here without database migration complexity.
2. Slice 2 (state persistence) and Slice 3 (cost + Temporal) are independent of each other in code but share the same integration surface (`primary_agent.py`). Sequencing Slice 2 first gives Slice 3 a real state backend to heartbeat against. Combined they total 24h raw, which fits within a 30h week with buffer.
3. Slice 4 is held back because the E2E test (43.15) requires both state persistence (Slice 2) and cost recording (Slice 3) to be in place. Planning it separately avoids cascading schedule risk if Sprints 1 or 2 slip.

---

## Sprint 1: Slice 1 -- MVP Ralph Agent Replaces PrimaryAgentRunner

**Sprint Duration:** 1 week (2026-03-23 to 2026-03-27)
**Capacity:** 30 hours total, 73% allocation = 22 hours allocated, 8 hours buffer

### Sprint Goal (Testable Format)

**Objective:** The `implement()` and `handle_loopback()` functions in `src/agent/primary_agent.py` dispatch to `RalphAgent` (with `NullStateBackend`) when `THESTUDIO_AGENT_MODE=ralph`. The model bridge converts TheStudio models to/from Ralph SDK models without data loss. The feature flag gates the switch with correct precedence over `agent_isolation`. The `ralph-sdk` package imports successfully from `pyproject.toml`.

**Test:** After all Sprint 1 stories are complete:

1. `python -c "from ralph_sdk import RalphAgent, NullStateBackend, TaskInput, TaskResult"` succeeds -- SDK dependency is installed and importable.
2. `pytest tests/unit/test_ralph_bridge.py -v` passes -- all bridge conversion functions tested: `taskpacket_to_ralph_input` maps goal/constraints/criteria/non_goals/risk_flags/complexity/trust_tier/loopback_context; `ralph_result_to_evidence` converts UUID strings to UUID objects with correct intent_version and loopback_attempt; `build_ralph_config` uses provider model_id and scales max_turns by complexity; `check_ralph_cli_available()` returns False when binary is missing; `build_verification_loopback_context` formats verification failures as markdown.
3. `pytest tests/unit/test_primary_agent_ralph.py -v` passes -- `implement()` with `agent_mode="ralph"` constructs RalphAgent and returns correct EvidenceBundle; `implement()` with `agent_mode="legacy"` uses PrimaryAgentRunner; `handle_loopback()` with `agent_mode="ralph"` passes verification failure context; setting overlap tests confirm `agent_mode` takes precedence over `agent_isolation`; `_validate_execute_tier_isolation()` is NOT called for Ralph mode.
4. `ruff check src/agent/ralph_bridge.py src/agent/primary_agent.py src/settings.py` is clean.
5. All existing tests pass: `pytest` green (no regressions from adding the ralph-sdk dependency or modifying settings).

**Constraint:** 5 working days. No database migrations. No Temporal activity changes. `NullStateBackend` only -- no real state persistence. The `PrimaryAgentRunner` class and all legacy code remain in `primary_agent.py`, gated behind `"legacy"` mode. No production code is deleted.

---

### What's In / What's Out

**In this sprint (5 stories, ~18h estimated):**

| # | Story ID | Description | Est. | Ralph Loops |
|---|----------|-------------|------|-------------|
| 1 | 43.1 | Add ralph-sdk dependency to pyproject.toml | 2h | 1 |
| 2 | 43.2 | Build model bridge: TheStudio <-> Ralph SDK | 4h | 1-2 |
| 3 | 43.3 | Add THESTUDIO_AGENT_MODE setting | 2h | 1 |
| 4 | 43.4 | Refactor primary_agent.py to support Ralph mode | 5h | 2 |
| 5 | 43.5 | Unit tests for Ralph bridge and primary_agent dispatch | 5h | 2 |
| | | **Total** | **18h** | |

**Buffer remaining:** 30h - 18h = 12h (40% buffer). Generous buffer is deliberate for Sprint 1 because this is the first time the Ralph SDK is imported into TheStudio -- unknown integration friction is the primary risk.

**Out of scope:**
- Database migrations (Slice 2)
- Cost recording or budget enforcement (Slice 3)
- Temporal activity heartbeat (Slice 3)
- Observability spans (Slice 4)
- Integration tests requiring a database (Slices 2 + 4)

**Compressible stories (cut if time runs short):**
1. **Story 43.5 test subset** -- The `check_ralph_cli_available()` tests (43.5h) and the setting overlap tests (43.5g) are lower priority than the core bridge and dispatch tests. These can be deferred to Sprint 2 as cleanup.
2. **Story 43.2 loopback context function** -- The `build_verification_loopback_context()` function is only needed by `handle_loopback()` in 43.4. If 43.4 implementation runs long, the loopback path can use a simpler string format and be refined in Sprint 2.

---

### Dependency Review (30-Minute Pre-Planning)

#### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| Ralph SDK v2.0.0 | AVAILABLE at `C:\cursor\ralph\ralph-claude-code\sdk\` | Cannot proceed with any Sprint 1 story | Confirmed: `__version__ = "2.0.0"` in `__init__.py` per epic |
| Claude CLI binary | NOT REQUIRED for Sprint 1 | No impact -- all tests mock `RalphAgent.run()` | Story 43.2 adds `check_ralph_cli_available()` but tests mock it |
| Epic 42 (Execute Tier) | COMPLETE | No impact | Confirmed per epic dependencies |
| Epic 32 (Cost Infrastructure) | COMPLETE | No impact on Sprint 1 (cost integration is Sprint 2) | Confirmed per epic dependencies |

#### Existing Files That Will Be Modified

| File | Current State | Modification |
|------|--------------|--------------|
| `pyproject.toml` | Existing dependencies | Add `ralph-sdk` path dependency (43.1) |
| `src/settings.py` | Has `agent_isolation`, `agent_llm_enabled` | Add `agent_mode` setting (43.3) |
| `src/agent/primary_agent.py` | Uses `PrimaryAgentRunner` | Add Ralph dispatch branch (43.4) |

#### New Files

| File | Story | Purpose |
|------|-------|---------|
| `src/agent/ralph_bridge.py` | 43.2 | Model conversion functions (5 functions) |
| `.gitmodules` | 43.1 | Git submodule for CI ralph-sdk path |
| `tests/unit/test_ralph_bridge.py` | 43.5 | Bridge function unit tests |
| `tests/unit/test_primary_agent_ralph.py` | 43.5 | Primary agent dispatch tests |

#### Internal Dependencies (Story-to-Story)

```
43.1 (SDK dependency) --> 43.2 (model bridge, imports ralph_sdk)
                      \-> 43.3 (settings, no SDK import needed but logically parallel)
                          |
43.2 + 43.3 -----------> 43.4 (primary_agent refactor, uses bridge + settings)
                          |
43.4 ------------------> 43.5 (tests, exercises 43.2 + 43.3 + 43.4)
```

- **43.1 has no dependencies** -- pure dependency management.
- **43.2 depends on 43.1** -- imports `ralph_sdk` types for bridge functions.
- **43.3 is independent of 43.2** -- adds a setting to `src/settings.py`. Can be done in parallel with 43.2 after 43.1.
- **43.4 depends on 43.2 and 43.3** -- uses bridge functions and reads `agent_mode` setting.
- **43.5 depends on 43.4** -- tests exercise the complete dispatch path.

**Critical path:** 43.1 --> 43.2 --> 43.4 --> 43.5 (13h on the critical path out of 18h total)

---

### Ordered Work Items

#### Item 1: Story 43.1 -- Add ralph-sdk Dependency to pyproject.toml

**Estimate:** 2 hours (S size, 1 Ralph loop)
**Rationale for sequence:** Foundation. Every other Sprint 1 story imports from `ralph_sdk`. If the package does not install cleanly, nothing else works.

**Key tasks:**
- Add `ralph-sdk @ file:///C:/cursor/ralph/ralph-claude-code/sdk` as a path dependency in `pyproject.toml`
- Add commented CI form: `# CI: ralph-sdk @ file:///vendor/ralph-sdk`
- Create `.gitmodules` entry for `vendor/ralph-sdk`
- Add `Makefile` target `make vendor-ralph` for `git submodule update --init vendor/ralph-sdk`
- Run `pip install -e ".[dev]"` and verify import: `python -c "from ralph_sdk import RalphAgent, NullStateBackend, TaskInput, TaskResult"`
- Verify existing `pytest` suite still passes (no dependency conflicts)

**Estimation reasoning:** Straightforward dependency addition. The 2h estimate accounts for potential packaging issues (path resolution on Windows, editable install compatibility). If the SDK's `pyproject.toml` has undeclared dependencies, we discover it here.

**Unknowns:**
- Whether `ralph-sdk`'s dependencies conflict with TheStudio's existing pins. Low probability since both use Pydantic v2 and modern async stack.
- Whether the path dependency works correctly on Windows with forward-slash paths.

**Done when:** `from ralph_sdk import RalphAgent` succeeds and `pytest` passes.

---

#### Item 2: Story 43.2 -- Build Model Bridge: TheStudio <-> Ralph SDK

**Estimate:** 4 hours (M size, 1-2 Ralph loops)
**Rationale for sequence:** After SDK is importable. This is the core translation layer that all subsequent stories depend on. Getting the type mappings right here prevents cascading bugs in 43.4.

**Key tasks:**
- Create `src/agent/ralph_bridge.py` with five functions:
  1. `check_ralph_cli_available() -> bool` -- subprocess check with 5s timeout, returns False on failure
  2. `taskpacket_to_ralph_input()` -- maps TheStudio TaskPacketRead + IntentSpecRead to Ralph's TaskPacketInput + IntentSpecInput
     - Complexity mapping: 0-3=LOW, 4-6=MEDIUM, 7-10=HIGH
     - Trust tier mapping: observe->RESTRICTED, suggest->STANDARD, execute->FULL
     - Risk flags: only high/critical severity become SAFETY constraints
  3. `ralph_result_to_evidence()` -- converts Ralph TaskResult to TheStudio EvidenceBundle (UUID string -> UUID object, datetime handling)
  4. `build_ralph_config()` -- constructs RalphConfig from DeveloperRoleConfig + ProviderConfig + complexity
     - max_turns scaling: low=20, medium=30, high=50
  5. `build_verification_loopback_context()` -- formats VerificationResult into markdown for Ralph's loopback_context

**Estimation reasoning:** Five functions, but each has specific type mapping rules documented in the epic. The complexity is in getting the edge cases right (None values, enum conversions, list vs single-value fields). The CLI check function is simple but adds async subprocess handling. 4h accounts for reading Ralph SDK source to confirm exact field names and types.

**Unknowns:**
- Exact field names on `TaskPacketInput` and `IntentSpecInput` -- must read Ralph SDK source to confirm.
- Whether `ralph_sdk.evidence.to_evidence_bundle()` handles all edge cases or if additional mapping is needed.

**Done when:** All five functions implemented, type-annotated, `ruff check` clean. Importable from `src.agent.ralph_bridge`.

---

#### Item 3: Story 43.3 -- Add THESTUDIO_AGENT_MODE Setting

**Estimate:** 2 hours (S size, 1 Ralph loop)
**Rationale for sequence:** Parallel-safe with 43.2 (both depend only on 43.1). Done here because 43.4 needs both the bridge (43.2) and the setting (43.3).

**Key tasks:**
- Add `agent_mode: str = "legacy"` to settings in `src/settings.py`
- Environment variable: `THESTUDIO_AGENT_MODE`
- Valid values: `"legacy"`, `"ralph"`, `"container"`
- Add Pydantic validator rejecting unknown values
- Precedence rule: if both `THESTUDIO_AGENT_MODE` and `THESTUDIO_AGENT_ISOLATION` are set, `agent_mode` takes precedence with a deprecation warning logged
- Ralph mode is always allowed regardless of trust tier (`_validate_execute_tier_isolation()` applies only to container mode)
- Update `docs/URLs.md` with new setting documentation

**Estimation reasoning:** Simple settings addition. The interaction with `agent_isolation` adds complexity (precedence logic, deprecation warning). 2h is appropriate.

**Unknowns:** None. The interaction rules are fully specified in the epic (Story 43.3 description).

**Done when:** Setting validates correctly, `ruff check src/settings.py` clean.

---

#### Item 4: Story 43.4 -- Refactor primary_agent.py to Support Ralph Mode

**Estimate:** 5 hours (M size, 2 Ralph loops)
**Rationale for sequence:** Depends on both 43.2 (bridge functions) and 43.3 (agent_mode setting). This is the integration point where the bridge and settings converge into production code.

**Key tasks:**
- Modify `implement()` to check `settings.agent_mode`:
  - When `"ralph"`: resolve provider, build RalphConfig via bridge, construct RalphAgent with NullStateBackend, convert TaskPacket via bridge, call `await agent.run()`, convert result via bridge
  - When `"legacy"`: existing PrimaryAgentRunner code path (unchanged)
  - When `"container"`: existing container path (unchanged)
- Similarly modify `handle_loopback()` for Ralph path with loopback_context
- Extract `_resolve_provider()` helper from AgentRunner logic
- Preserve all existing code -- no deletions
- All function signatures unchanged (implement() and handle_loopback() contracts preserved)

**Estimation reasoning:** 5h is the largest story in Sprint 1. The refactor touches a critical production file with two code paths (implement + loopback). The provider resolution extraction adds a helper function. This story has the highest risk of merge complexity if the file has been recently modified. The epic explicitly calls this out as a major refactor.

**Unknowns:**
- Whether `_resolve_provider()` extraction from AgentRunner is clean or requires importing private methods.
- How `RalphAgent` construction interacts with TheStudio's async context (event loop compatibility).

**Done when:** Both `implement()` and `handle_loopback()` have working Ralph branches. `ruff check` clean. No existing tests broken.

---

#### Item 5: Story 43.5 -- Unit Tests for Ralph Bridge and Primary Agent Dispatch

**Estimate:** 5 hours (M size, 2 Ralph loops)
**Rationale for sequence:** Last in sprint. Tests all of 43.2 + 43.3 + 43.4 together. Must be last because it exercises the complete dispatch path.

**Key tasks:**
- Create `tests/unit/test_ralph_bridge.py`:
  - (a) `taskpacket_to_ralph_input` maps all fields correctly (8+ test cases for different complexity/trust/risk combinations)
  - (b) `ralph_result_to_evidence` converts types correctly (UUID string -> UUID, datetime handling)
  - (c) `build_ralph_config` uses provider model_id, scales max_turns by complexity
  - (d) `build_verification_loopback_context` formats markdown correctly
  - (h) `check_ralph_cli_available()` returns False when subprocess fails
- Create `tests/unit/test_primary_agent_ralph.py`:
  - (d) `implement()` with `agent_mode="ralph"` constructs RalphAgent (mock `run()` to return canned TaskResult)
  - (e) `implement()` with `agent_mode="legacy"` uses PrimaryAgentRunner
  - (f) `handle_loopback()` with `agent_mode="ralph"` passes verification failure context
  - (g) Setting overlap: `THESTUDIO_AGENT_MODE=ralph` + `THESTUDIO_AGENT_ISOLATION=container` -> `agent_mode` wins, deprecation warning logged. `agent_mode="container"` matches `agent_isolation="container"`. `agent_mode="ralph"` skips `_validate_execute_tier_isolation()`

**Estimation reasoning:** 5h for two test files covering 8+ distinct test scenarios. The mocking setup for RalphAgent.run() and PrimaryAgentRunner requires understanding both APIs. The setting overlap tests need careful environment variable management in fixtures.

**Unknowns:**
- Whether mocking `RalphAgent.run()` is straightforward or requires understanding its internal state machine.
- Whether the existing test fixtures for primary_agent are compatible or need new conftest entries.

**Done when:** Both test files pass. `pytest tests/unit/test_ralph_bridge.py tests/unit/test_primary_agent_ralph.py -v` green. `ruff check` clean on test files.

---

### Sprint 1 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Ralph SDK has undeclared dependencies that conflict with TheStudio | Low | High -- blocks all stories | 43.1 is the canary. If it fails, investigate immediately. Fallback: pin conflicting deps. |
| Ralph SDK Pydantic models are incompatible with TheStudio's Pydantic version | Low | High -- bridge layer cannot convert | Both use Pydantic v2. Confirm exact version in SDK's pyproject.toml during 43.1. |
| `primary_agent.py` has been modified since epic was written | Medium | Medium -- merge conflicts in 43.4 | Read the file before starting 43.4. Adjust bridge calls if signatures changed. |
| Test mocking of RalphAgent.run() requires understanding SDK internals | Medium | Low -- adds time to 43.5 | Budget 2 Ralph loops for 43.5. Read SDK agent.py source during 43.2 to understand return types. |
| Windows path handling for SDK path dependency | Low | Medium -- pip install fails | Test both forward-slash and backslash paths. Use `file:///` URI format. |

---

## Sprint 2: Slice 2 (State Persistence) + Slice 3 (Cost + Temporal Activity)

**Sprint Duration:** 1 week (2026-03-30 to 2026-04-03)
**Capacity:** 30 hours total, 77% allocation = 23 hours allocated, 7 hours buffer

### Sprint Goal (Testable Format)

**Objective:** Ralph's state (session ID, circuit breaker, rate limit counters) persists in PostgreSQL across loopback attempts and activity restarts. Ralph runs are tracked through TheStudio's cost infrastructure with budget enforcement. The Temporal `implement_activity` heartbeats during long Ralph runs and supports clean cancellation.

**Test:** After all Sprint 2 stories are complete:

1. `pytest tests/integration/test_ralph_state.py -v` passes -- all 12 `RalphStateBackend` protocol methods round-trip through PostgreSQL; two backends for different taskpacket_ids do not share state; concurrent writes use upsert correctly; `isinstance(backend, RalphStateBackend)` returns True; session ID TTL discards expired sessions.
2. `pytest tests/unit/test_ralph_cost.py -v` passes -- `ModelCallAudit` is recorded with correct step/role/provider after Ralph run; `PipelineBudget.consume()` is called before launch; `BudgetExceededError` raised when insufficient; `emit_cost_update()` called after run.
3. `pytest tests/unit/test_ralph_activity.py -v` passes -- heartbeat loop emits at least one heartbeat for a 5-second mock run; setting `agent._running = False` causes graceful exit.
4. Database migration applies cleanly: `ralph_agent_state` table created with correct schema (id, taskpacket_id, key_name, value_json, updated_at, unique constraint, index).
5. `ruff check src/agent/ralph_state.py src/agent/primary_agent.py src/agent/ralph_bridge.py src/workflow/activities.py src/settings.py` is clean.
6. All existing tests pass: `pytest` green (no regressions from migration or activity changes).

**Constraint:** 5 working days. Sprint 1 gate must be green before starting Sprint 2. The `PostgresStateBackend` uses `TEXT` columns (not `JSONB`) per epic constraint. The migration must be backward-compatible (new table only, no modifications to existing tables). The legacy and container agent modes must continue to work unchanged.

---

### What's In / What's Out

**In this sprint (7 stories, ~24h estimated):**

| # | Story ID | Description | Slice | Est. | Ralph Loops |
|---|----------|-------------|-------|------|-------------|
| 1 | 43.6 | Create ralph_agent_state table migration | Slice 2 | 2h | 1 |
| 2 | 43.7 | Implement PostgresStateBackend | Slice 2 | 4h | 1-2 |
| 3 | 43.8 | Wire PostgresStateBackend into primary_agent.py | Slice 2 | 3h | 1 |
| 4 | 43.9 | Integration tests for PostgresStateBackend | Slice 2 | 3h | 1 |
| 5 | 43.10 | Cost recording after Ralph run | Slice 3 | 4h | 1-2 |
| 6 | 43.11 | Implement ralph mode in implement_activity with heartbeat | Slice 3 | 5h | 2 |
| 7 | 43.12 | Unit tests for cost recording and activity heartbeat | Slice 3 | 3h | 1 |
| | | **Total** | | **24h** | |

**Buffer remaining:** 30h - 24h = 6h (20% buffer). Tighter than Sprint 1 because Slices 2 and 3 are better-defined (no SDK integration unknowns).

**Out of scope:**
- Health endpoint (Slice 4, Story 43.13)
- Observability spans (Slice 4, Story 43.14)
- E2E integration test (Slice 4, Story 43.15)
- Promoting Ralph to default agent mode

**Compressible stories (cut if time runs short):**
1. **Story 43.9 concurrent write test** -- The concurrent upsert test (43.9c) is the hardest integration test to write correctly. If time is short, defer it to Slice 4 alongside the E2E test. The round-trip and isolation tests are sufficient for confidence.
2. **Story 43.12 heartbeat timing assertion** -- The "at least one heartbeat in 5 seconds" test (43.12d) requires careful async timing. A simpler test that verifies the heartbeat function is called at all (without timing assertion) is acceptable as a fallback.

---

### Dependency Review (30-Minute Pre-Planning)

#### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| Sprint 1 gate green | PREREQUISITE | Cannot start Sprint 2 | No workaround. Sprint 1 must pass. |
| Test database for integration tests | Available (existing test infrastructure) | Cannot run 43.9 | Use existing test DB fixtures from `tests/integration/` |
| `src/db/` session infrastructure | COMPLETE | Cannot build PostgresStateBackend | Confirmed: async_sessionmaker available |
| Cost infrastructure (Epic 32) | COMPLETE | Cannot build cost recording | `ModelCallAudit`, `BudgetEnforcer`, `PipelineBudget` exist |

#### Existing Files That Will Be Modified

| File | Current State | Modification |
|------|--------------|--------------|
| `src/agent/primary_agent.py` | Modified in Sprint 1 (43.4) | Replace NullStateBackend with PostgresStateBackend (43.8), add cost recording (43.10) |
| `src/agent/ralph_bridge.py` | Created in Sprint 1 (43.2) | Add cost estimation helper (43.10) |
| `src/workflow/activities.py` | Has "process" and "container" modes | Add "ralph" mode with heartbeat (43.11) |
| `src/settings.py` | Modified in Sprint 1 (43.3) | Add `ralph_state_backend` and `ralph_timeout_minutes` settings (43.8, 43.11) |

#### New Files

| File | Story | Purpose |
|------|-------|---------|
| `src/db/migrations/xxx_add_ralph_agent_state.py` | 43.6 | New table migration |
| `src/agent/ralph_state.py` | 43.7 | PostgresStateBackend class |
| `tests/integration/test_ralph_state.py` | 43.9 | State backend integration tests |
| `tests/unit/test_ralph_cost.py` | 43.12 | Cost recording unit tests |
| `tests/unit/test_ralph_activity.py` | 43.12 | Activity heartbeat unit tests |

#### Internal Dependencies (Story-to-Story)

```
43.6 (migration) --> 43.7 (PostgresStateBackend, needs table)
                     |
43.7 --------------> 43.8 (wire into primary_agent)
                     |
43.7 --------------> 43.9 (integration tests for backend)
                     |
43.8 + 43.10 ------> 43.11 (activity wrapper uses state + cost)
                     |
43.10 + 43.11 -----> 43.12 (tests for cost + heartbeat)

43.10 is independent of 43.6-43.9 (cost recording uses primary_agent, not state backend directly)
```

**Two tracks within Sprint 2:**

```
Track A (State):  43.6 --> 43.7 --> 43.8 --> 43.9
Track B (Cost):   43.10 (can start after Sprint 1 is done)
Merge point:      43.11 (needs both 43.8 and 43.10)
Final:            43.12 (tests for 43.10 + 43.11)
```

**Recommended linear order** (since solo developer cannot parallelize):
43.6 --> 43.7 --> 43.8 --> 43.9 --> 43.10 --> 43.11 --> 43.12

**Rationale for this order over alternatives:**
- State track (43.6-43.9) first because the migration + backend must exist before the activity wrapper (43.11) can use them.
- 43.9 (state integration tests) before 43.10 (cost) to validate the state backend works correctly before building on top of it. Debugging cost recording issues is harder if you are not sure the state backend is correct.
- 43.10 before 43.11 because the activity wrapper (43.11) calls cost recording functions from 43.10.
- 43.12 last because it tests both 43.10 and 43.11.

**Critical path:** 43.6 --> 43.7 --> 43.8 --> 43.11 --> 43.12 (17h on the critical path out of 24h total)

---

### Ordered Work Items

#### Item 1: Story 43.6 -- Create ralph_agent_state Table Migration

**Estimate:** 2 hours (S size, 1 Ralph loop)
**Rationale for sequence:** Foundation for all Slice 2 stories. The table must exist before the backend can be implemented or tested.

**Key tasks:**
- Create Alembic migration adding `ralph_agent_state` table:
  - `id UUID PK DEFAULT gen_random_uuid()`
  - `taskpacket_id UUID NOT NULL`
  - `key_name VARCHAR(64) NOT NULL`
  - `value_json TEXT NOT NULL DEFAULT '{}'`
  - `updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()`
- Add unique constraint on `(taskpacket_id, key_name)`
- Add index on `taskpacket_id`
- Key names documented: `status`, `circuit_breaker`, `call_count`, `last_reset`, `session_id`, `fix_plan`
- Verify migration applies and rolls back cleanly

**Estimation reasoning:** Standard Alembic migration for a single new table. No complex types (TEXT, not JSONB). 2h accounts for testing apply/rollback cycle.

**Unknowns:** None. Schema is fully specified in the epic.

**Done when:** Migration applies cleanly. `ralph_agent_state` table exists in test DB with correct columns and constraints.

---

#### Item 2: Story 43.7 -- Implement PostgresStateBackend

**Estimate:** 4 hours (M size, 1-2 Ralph loops)
**Rationale for sequence:** After migration (43.6). The backend class is the core deliverable of Slice 2 and is required by 43.8 (wiring) and 43.9 (tests).

**Key tasks:**
- Create `src/agent/ralph_state.py` with `PostgresStateBackend` class
- Constructor takes `taskpacket_id: UUID` and `session_factory: async_sessionmaker`
- Implement all 12 `RalphStateBackend` protocol methods:
  - Each method maps to a single upsert (INSERT ... ON CONFLICT UPDATE) or SELECT on `ralph_agent_state`
  - JSON dict values serialized with `json.dumps()` / `json.loads()`
  - Integer values stored as `{"value": N}`
  - String values stored as `{"value": "..."}`
- Must pass `isinstance(backend, RalphStateBackend)` -- protocol is `@runtime_checkable`
- All operations scoped to `taskpacket_id` to prevent cross-run interference

**Estimation reasoning:** 12 methods sounds like a lot, but they are all variations of upsert/read on a single table with different key names. The complexity is in getting the JSON serialization right and ensuring the upsert works correctly with SQLAlchemy async. 4h accounts for reading the RalphStateBackend protocol source to confirm all 12 method signatures.

**Unknowns:**
- Exact signatures of all 12 protocol methods (must read `ralph_sdk/state.py`).
- Whether SQLAlchemy's `insert().on_conflict_do_update()` works correctly with the async session.

**Done when:** Class implements all 12 methods. `isinstance(PostgresStateBackend(...), RalphStateBackend)` returns True. `ruff check` clean.

---

#### Item 3: Story 43.8 -- Wire PostgresStateBackend into primary_agent.py

**Estimate:** 3 hours (S-M size, 1 Ralph loop)
**Rationale for sequence:** After 43.7 (backend exists). Replaces `NullStateBackend` from Sprint 1 with `PostgresStateBackend` in the Ralph dispatch path.

**Key tasks:**
- Modify Ralph mode in `implement()` and `handle_loopback()`:
  - Construct `PostgresStateBackend(taskpacket_id=..., session_factory=get_async_session_factory())`
  - Replace `NullStateBackend()` from Sprint 1
- Add setting `THESTUDIO_RALPH_STATE_BACKEND` with values `"postgres"` (default) and `"null"` (for testing)
- In `handle_loopback()`, load session ID from state backend before constructing RalphAgent
- Add session ID TTL check: if `updated_at` on session_id row is older than 2 hours, discard (Claude sessions may expire)

**Estimation reasoning:** Moderate change to code already modified in Sprint 1. The TTL check adds a query. 3h is appropriate.

**Unknowns:**
- Whether `get_async_session_factory()` is available in the primary_agent.py context or needs to be injected.

**Done when:** `implement()` with `agent_mode="ralph"` uses `PostgresStateBackend` by default. `handle_loopback()` loads session ID from DB. TTL check discards expired sessions.

---

#### Item 4: Story 43.9 -- Integration Tests for PostgresStateBackend

**Estimate:** 3 hours (S-M size, 1 Ralph loop)
**Rationale for sequence:** After 43.7 and 43.8. Validates the backend against a real database before cost integration builds on top.

**Key tasks:**
- Create `tests/integration/test_ralph_state.py`:
  - (a) Write and read all 12 state operations, verify round-trip
  - (b) Two backends for different taskpacket_ids do not share state
  - (c) Concurrent writes to same key use upsert correctly (no duplicate key errors)
  - (d) `isinstance(backend, RalphStateBackend)` returns True
  - (e) Session ID TTL: write session_id with `updated_at` 3 hours ago, verify `read_session_id()` returns empty string
- Use test database with migration applied

**Estimation reasoning:** 5 test scenarios against a real database. The concurrent write test (c) is the trickiest -- needs asyncio.gather with two competing writes. 3h accounts for database fixture setup.

**Unknowns:**
- Whether the test database infrastructure supports the new migration automatically or requires manual setup.

**Done when:** All 5 test scenarios pass. `pytest tests/integration/test_ralph_state.py -v` green.

---

#### Item 5: Story 43.10 -- Cost Recording After Ralph Run

**Estimate:** 4 hours (M size, 1-2 Ralph loops)
**Rationale for sequence:** Independent of Slice 2 in code, but placed after 43.9 to avoid interleaving untested code. This is the start of Slice 3.

**Key tasks:**
- After `RalphAgent.run()` completes in `primary_agent.py`:
  - Record `ModelCallAudit` with step="primary_agent", role="developer", provider from ProviderConfig
  - Estimate tokens: `result.output` length chars // 4
  - Estimate cost: `result.duration_seconds * provider.cost_per_minute` (fallback: `result.loop_count * 0.05`)
  - Record spend via `BudgetEnforcer.record_spend()`
  - Emit `cost_update` SSE event via `emit_cost_update()`
- Before launching Ralph:
  - Check `PipelineBudget.consume()` -- raise `BudgetExceededError` if insufficient
- Add cost estimation helper to `ralph_bridge.py`

**Estimation reasoning:** Integrates with existing cost infrastructure (Epic 32). Must read `ModelCallAudit`, `BudgetEnforcer`, and `PipelineBudget` to understand their APIs. The estimation heuristic (chars // 4) is simple but the wiring requires touching multiple files. 4h accounts for API discovery.

**Unknowns:**
- Whether `provider.cost_per_minute` exists on `ProviderConfig` or needs to be added.
- Exact `emit_cost_update()` call signature.

**Done when:** Ralph runs produce `ModelCallAudit` records. Budget is checked before launch. `ruff check` clean.

---

#### Item 6: Story 43.11 -- Implement Ralph Mode in implement_activity with Heartbeat

**Estimate:** 5 hours (M size, 2 Ralph loops)
**Rationale for sequence:** The integration point for Slices 2 and 3. Requires both the state backend (43.8) and cost recording (43.10) to be in place.

**Key tasks:**
- Add `"ralph"` case to `implement_activity` dispatch in `src/workflow/activities.py`
- When `settings.agent_mode == "ralph"`:
  - Construct `RalphAgent` with `PostgresStateBackend`
  - Launch `agent.run()` as an asyncio background task
  - Run heartbeat loop: `activity.heartbeat({"loop_count": ..., "status": ...})` every 30 seconds, reading from state backend
  - Await agent task with timeout `settings.ralph_timeout_minutes + 5`
  - On timeout: set `agent._running = False`, await graceful shutdown (up to 30 seconds)
  - On cancellation: same shutdown path
  - Convert `TaskResult` to `ImplementOutput`
- Add new settings: `THESTUDIO_RALPH_TIMEOUT_MINUTES` (default 30)

**Estimation reasoning:** 5h is the largest Sprint 2 story. The heartbeat loop with background task and timeout handling is the most complex async code in the epic. Must understand Temporal's activity heartbeat API. The graceful shutdown path (setting `_running = False` and awaiting exit) requires careful error handling. 2 Ralph loops budgeted.

**Unknowns:**
- Temporal Python SDK's heartbeat API for async activities (need to confirm call signature).
- Whether `agent._running = False` is the correct mechanism or if Ralph provides a `cancel()` method.

**Done when:** `implement_activity` dispatches to Ralph when `agent_mode="ralph"`. Heartbeat emits during long runs. Timeout triggers graceful shutdown. `ruff check` clean.

---

#### Item 7: Story 43.12 -- Unit Tests for Cost Recording and Activity Heartbeat

**Estimate:** 3 hours (S-M size, 1 Ralph loop)
**Rationale for sequence:** Last in sprint. Tests the two most complex Sprint 2 deliverables (cost + heartbeat).

**Key tasks:**
- Create `tests/unit/test_ralph_cost.py`:
  - (a) After mock Ralph run, `ModelCallAudit` recorded with correct step/role/provider
  - (b) `PipelineBudget.consume()` called before Ralph launch; `BudgetExceededError` raised when insufficient
  - (c) `emit_cost_update()` called after Ralph run
- Create `tests/unit/test_ralph_activity.py`:
  - (d) Heartbeat loop emits at least one heartbeat for a 5-second mock run
  - (e) Setting `agent._running = False` causes `run()` to exit within one iteration

**Estimation reasoning:** 5 test scenarios across two files. The heartbeat timing test (d) is the trickiest -- needs async timing control. 3h is appropriate for two focused test files.

**Unknowns:**
- Whether mocking the Temporal activity heartbeat context requires specific test utilities from the Temporal SDK.

**Done when:** Both test files pass. `pytest tests/unit/test_ralph_cost.py tests/unit/test_ralph_activity.py -v` green.

---

### Sprint 2 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Sprint 1 slips, delaying Sprint 2 start | Low-Medium | High -- entire Sprint 2 shifts | Sprint 1 has 40% buffer. If it consumes more than 3 days of buffer, re-plan Sprint 2 dates. |
| Migration conflicts with existing migrations | Low | Medium -- blocks 43.6 | New table only, no modifications. Check migration chain before starting. |
| Temporal heartbeat API is different than expected | Medium | Low-Medium -- adds time to 43.11 | Budget 2 Ralph loops for 43.11. Read Temporal Python SDK source during implementation. |
| Cost infrastructure APIs have changed since Epic 32 | Low | Medium -- adds time to 43.10 | Read `src/admin/model_gateway.py` before starting 43.10. |
| 24h allocation with 20% buffer is tight | Medium | Medium -- risk of incomplete stories | Compressible stories identified. If state track takes longer, defer 43.12 heartbeat timing test. |

---

## Cross-Sprint Summary

| Metric | Sprint 1 | Sprint 2 | Total |
|--------|----------|----------|-------|
| Stories | 5 (43.1-43.5) | 7 (43.6-43.12) | 12 |
| Estimated hours | 18h | 24h | 42h |
| Capacity | 30h | 30h | 60h |
| Allocation % | 60% | 80% | 70% |
| Buffer hours | 12h | 6h | 18h |
| New files | 3 src + 2 test | 2 src + 1 migration + 3 test | 5 src + 1 migration + 5 test |
| Modified files | 2 (settings, primary_agent) | 4 (primary_agent, ralph_bridge, activities, settings) | 4 unique files |

### Sprint Gates

**Sprint 1 -> Sprint 2 gate:**
- `pytest tests/unit/test_ralph_bridge.py tests/unit/test_primary_agent_ralph.py -v` all green
- `from ralph_sdk import RalphAgent` succeeds
- `ruff check .` clean
- No regressions: full `pytest` green

**Sprint 2 -> Sprint 3 gate:**
- `pytest tests/integration/test_ralph_state.py tests/unit/test_ralph_cost.py tests/unit/test_ralph_activity.py -v` all green
- `ralph_agent_state` table exists with correct schema
- `implement_activity` dispatches to all 3 modes (legacy, ralph, container) based on setting
- `ruff check .` clean
- No regressions: full `pytest` green

### What Comes After (Sprint 3, not yet planned)

Slice 4: Validation and Observability (3 stories, ~8h estimated):
- 43.13: Ralph health endpoint and startup probe (1h)
- 43.14: Observability spans for Ralph agent lifecycle (2h)
- 43.15: End-to-end integration test: implement + loopback via Ralph (4h)
- Sprint 3 will be planned after Sprint 2 gate passes, to incorporate any learnings.

---

## Meridian Review Required

This plan is DRAFT. It must pass Meridian review (7 questions + red flags) before Sprint 1 begins on 2026-03-23.

**Meridian review checklist:**
1. Are sprint goals specific enough to test against?
2. Are the gate criteria measurable?
3. Are dependencies identified with status?
4. Is the ordering rationale clear?
5. Are risks identified with mitigations?
6. Can a solo developer execute this in the stated timeframe?
7. Are there red flags (scope creep, hidden dependencies, unrealistic estimates)?
