# Epic 19 — Close Critical Architecture Gaps: Gateway Wiring, Security Scans, Reputation Persistence

**Author:** Saga
**Date:** 2026-03-12
**Status:** Complete — Implemented in Sprint 19 (2026-03-12)
**Target Sprint:** Sprint 19 (completed)

---

## 1. Title

Close Critical Architecture Gaps: Gateway Wiring, Security Scans, Reputation Persistence — Wire the built-but-bypassed Model Gateway into agent LLM calls, add the missing security scan runner to the verification gate, and move reputation weights from volatile memory to PostgreSQL so the system enforces the contracts its architecture documents promise.

## 2. Narrative

TheStudio's architecture documents describe three capabilities that are built or partially built but not connected. Today, each one silently violates a documented contract:

**The Model Gateway exists but nobody calls it.** `src/admin/model_gateway.py` contains a fully functional `ModelRouter` with routing rules per pipeline step, fallback chains, budget enforcement, and audit logging. Meanwhile, `src/agent/primary_agent.py` constructs a `DeveloperRoleConfig` with a hardcoded model name from `settings.agent_model` and passes it directly to the Claude Agent SDK. The gateway's routing rules, cost-tier logic, overlay-aware escalation, and per-task budget caps are all dead code from the agent's perspective. Every LLM call the agent makes ignores the operational controls the platform was designed to enforce.

**The verification gate runs without security scans.** Doc 13 (Verification Gate) lists security scans as a required check alongside formatting, linting, and tests. The evidence bundle spec calls for "security scan summary when applicable." The `src/verification/gate.py` runner map contains exactly two entries: `ruff` and `pytest`. There is no `security_runner.py` in the runners directory. Code ships through the gate without any security check — not a relaxed check, not a deferred check, no check at all. The gate contract says this should not happen.

**Reputation weights vanish on restart.** The reputation engine (`src/reputation/engine.py`) stores all expert weights in module-level dictionaries: `_weights` and `_weight_history`. A DB table (`expert_reputation`) exists from migration 008, but the engine never reads from or writes to it. Every restart resets all expert trust to zero. This is a correctness problem the moment real traffic flows: the Router will select experts with no historical context, and tier transitions (shadow to probation to trusted) will never stick.

These three items are the first batch of critical gaps identified in the architecture-vs-implementation mapping (items C1, C4, C7). They are independent of each other — no dependency edges connect them — which means they can be worked in parallel. Fixing them moves the system from "demo-grade" to "the contracts it documents are actually enforced."

## 3. References

| Artifact | Location |
|----------|----------|
| Architecture-vs-implementation mapping | `docs/architecture-vs-implementation-mapping.md` (lines 422-559) |
| Triage items C1, C4, C7 | `docs/architecture-vs-implementation-mapping.md` (lines 426, 429, 432) |
| Model Gateway implementation | `src/admin/model_gateway.py` |
| Model routing architecture | `thestudioarc/26-model-runtime-and-routing.md` |
| Primary Agent | `src/agent/primary_agent.py` |
| Developer Role config | `src/agent/developer_role.py` |
| Verification Gate architecture | `thestudioarc/13-verification-gate.md` |
| Verification Gate implementation | `src/verification/gate.py` |
| Runner base interface | `src/verification/runners/base.py` |
| Ruff runner (pattern to follow) | `src/verification/runners/ruff_runner.py` |
| Reputation Engine architecture | `thestudioarc/06-reputation-engine.md` |
| Reputation Engine implementation | `src/reputation/engine.py` |
| Reputation models | `src/reputation/models.py` |
| Expert reputation migration (008) | `src/db/migrations/008_trust_tier_persistence.py` |
| Coding standards | `thestudioarc/20-coding-standards.md` |
| Pipeline stage mapping | `.claude/rules/pipeline-stages.md` |

## 4. Acceptance Criteria

### C1: Model Gateway Wired into Primary Agent

1. **Agent calls route through ModelRouter.** `primary_agent.implement()` and `primary_agent.handle_loopback()` call `ModelRouter.select_model()` (or `select_with_fallback()`) to determine the model for each agent invocation, instead of reading `settings.agent_model` directly.
2. **Routing context is populated.** The `select_model()` call receives `step="primary_agent"`, the agent's `role` (currently `"developer"`), any active overlays from the TaskPacket's `EffectiveRolePolicy` or risk flags, the repository's trust tier, and the complexity index.
3. **Budget enforcer is active per task.** Before each agent call, the budget enforcer's `check_budget()` is called with the TaskPacket ID. If budget is exceeded, the agent call does not proceed and the TaskPacket transitions to a failed state with a clear budget-exceeded reason.
4. **Spend is recorded after each call.** After the agent returns, `record_spend()` is called with the TaskPacket ID, step name, estimated cost, and token count. (Token count estimated as prompt_chars/4 + response_chars/4 until the Claude Agent SDK exposes a usage field; the estimation formula is documented in code comments.)
5. **Audit trail exists.** A `ModelCallAudit` record is created for each agent invocation with correlation_id, task_id, step, role, provider, model, and cost fields populated.
6. **Fallback on provider failure.** If the selected provider is unavailable (e.g., `NoProviderAvailableError`), the system attempts fallback via `select_with_fallback()` before failing the task.
7. **DeveloperRoleConfig.model is derived from gateway.** The `model` field in `DeveloperRoleConfig` is set from the `ProviderConfig.model_id` returned by the gateway, not from `settings.agent_model`. The `max_budget_usd` field is set from the `BudgetSpec.per_task_max_spend`.
8. **Existing tests pass.** All existing agent and model gateway tests continue to pass. New tests cover: (a) agent calls route through gateway, (b) budget enforcement blocks over-budget calls, (c) fallback chain activates on provider failure, (d) audit records are created.

### C4: Security Scan Runner

9. **Runner exists.** `src/verification/runners/security_runner.py` implements `run_security_scan()` returning a `CheckResult`, following the same pattern as `ruff_runner.py` and `pytest_runner.py`.
10. **Runner performs at least one meaningful check.** The initial implementation runs `bandit` (Python security linter) against changed files. If `bandit` is not installed, the check fails closed with a clear "bandit binary not found" message (consistent with gate-fails-closed policy).
11. **Gate integrates the runner.** `src/verification/gate.py` adds `"security"` to the `_RUNNERS` map and `_run_check()` dispatches to `run_security_scan()` when `check_name == "security"`.
12. **Repo Profile controls activation.** Security scanning runs only when `"security"` is in the repo profile's `required_checks` list. Repos without it in their profile are unaffected.
13. **Evidence bundle includes security results.** When the security runner executes, its `CheckResult` appears in the `VerificationResult.checks` list alongside ruff and pytest results, and is included in the evidence comment.
14. **Timeout and error handling.** The runner has a configurable timeout (default 120s). Timeout, missing binary, and unexpected errors all produce `CheckResult(passed=False)` — the gate fails closed.
15. **Tests exist.** Unit tests cover: (a) runner returns pass for clean code, (b) runner returns fail for code with known issues, (c) runner fails closed on missing binary, (d) runner fails closed on timeout, (e) gate dispatches to security runner when configured.

### C7: Reputation PostgreSQL Persistence

16. **Engine reads from and writes to PostgreSQL.** The reputation engine's `update_weight()` and `query_weights()` operations persist to and read from the `expert_reputation` table (created by migration 008).
17. **Migration gap closed.** If the existing migration 008 schema is missing any fields required by the current `ExpertWeight` model (e.g., `last_indicator_at`, `drift_signal` vs `drift_direction`), a new migration (019) adds or renames the missing columns.
18. **In-memory store becomes cache layer.** The module-level `_weights` dict is retained as a read cache. On write, data goes to DB first, then cache is updated. On read (query), the engine checks cache first and falls back to DB. Cache invalidation occurs on write.
19. **Weight history for drift detection.** The `_weight_history` dict (used for drift computation) is populated from DB on first access for a given (expert_id, context_key) pair. Recent weight values are stored in a `weight_history` JSONB column or a separate `expert_weight_history` table.
20. **Data survives restart.** After writing weights, restarting the application, and querying, the previously written weights are returned with correct values for weight, confidence, trust_tier, drift_signal, and sample_count.
21. **Async database access.** All DB operations use `AsyncSession` from SQLAlchemy async, consistent with the rest of the codebase.
22. **Existing API unchanged.** The `ReputationEngineProtocol` interface is unchanged. Callers (Router, admin API) do not need modification. The `InMemoryReputationEngine` class continues to work but now delegates to the DB-backed implementation.
23. **Tests exist.** Unit tests cover: (a) write-then-read roundtrip through DB, (b) data survives simulated restart (clear cache, re-query), (c) drift history is loaded from DB, (d) concurrent updates do not corrupt data, (e) cache hit avoids DB query (verified via mock).

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Claude Agent SDK does not expose token usage after calls | High | Medium — budget tracking is approximate | Estimate tokens from prompt + response length; add TODO for SDK usage API when available |
| `bandit` not available in all CI/dev environments | Medium | Medium — security check fails closed, blocking verification | Document `bandit` as a dev dependency in `pyproject.toml`; runner gives clear "not found" message |
| Migration 008 schema diverges from current `ExpertWeight` fields | Medium | Low — fixable with migration 019 | Compare schema before writing code; migration is idempotent |
| In-memory cache and DB can drift under concurrent writes | Medium | Medium — stale reads affect routing | Write-through pattern: DB first, cache second; single writer per process in Phase 0 |
| `DeveloperRoleConfig` is a frozen dataclass — cannot mutate `model` after creation | Low | Low — just construct with gateway-derived values | Create config after gateway selection, not before |

## 5. Constraints & Non-Goals

### Constraints

- **No changes to `ModelRouter` or `BudgetEnforcer` interfaces.** The gateway is already built; this epic wires it in, not redesigns it.
- **No changes to `ReputationEngineProtocol`.** Callers must not need modification.
- **Gate fails closed.** Security runner errors, timeouts, and missing binaries all produce `passed=False`.
- **Async-only DB access.** Reputation persistence uses `AsyncSession`, not sync SQLAlchemy.
- **Migration must be idempotent.** Running it twice must not error or duplicate data.
- **Python 3.12+, existing dependencies only** (except `bandit` as a new dev dependency for the security runner).
- **Existing tests must not break.** All current test suites pass after these changes.

### Non-Goals

- **Not replacing the Claude Agent SDK call mechanism.** The agent still calls the SDK; it just gets its model selection from the gateway.
- **Not building a full SAST/DAST pipeline.** The security runner is a single tool (`bandit`) in Phase 0. Dependency auditing (`pip-audit`), secret scanning, and container scanning are future work.
- **Not adding new provider backends.** The gateway already supports multiple providers; this epic does not add OpenAI, Gemini, or other providers.
- **Not building a reputation admin UI.** Persistence enables future UI (V12); this epic does not build the UI.
- **Not implementing attribution principles (V6).** V6 depends on C7 but is a separate work item.
- **Not adding event sourcing for weight updates.** Weight history is stored for drift detection, not as a full event log.
- **Not modifying the Repo Profile schema.** Repos that want security scanning must add `"security"` to their `required_checks` list via the existing admin API.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Platform Lead (TBD — assign before sprint start) | Accepts epic scope, reviews AC completion |
| Tech Lead | Backend Engineer (TBD — assign before sprint start) | Owns implementation across all three work streams |
| QA | QA Engineer (TBD — assign before sprint start) | Validates AC, writes integration tests for restart-survival and gate behavior |
| Saga | Epic Creator | Authored this epic; available for scope clarification |
| Meridian | VP Success | Reviews this epic before commit; reviews sprint plan |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Gateway adoption | 100% of agent LLM calls route through `ModelRouter` | Grep codebase: zero direct `settings.agent_model` references in agent call paths |
| Budget enforcement active | Budget check runs before every agent invocation | Audit log contains `ModelCallAudit` records for every `implement()` and `handle_loopback()` call |
| Security scan availability | Security runner callable by any repo with `"security"` in `required_checks` | `run_security_scan()` passes unit tests; gate dispatches to it correctly |
| Reputation durability | Weights survive application restart | Integration test: write weight, clear cache, query — values match |
| Zero regression | All pre-existing tests pass | CI green on merge |
| Time to implement | Complete within one sprint (2 weeks) for all three items | Sprint burndown tracked in sprint plan; stories marked complete in epic story map |

## 8. Context & Assumptions

### Systems Affected

| System | Impact |
|--------|--------|
| `src/agent/primary_agent.py` | Modified: calls gateway instead of settings for model selection |
| `src/agent/developer_role.py` | Modified: `DeveloperRoleConfig` constructed with gateway-derived model and budget |
| `src/admin/model_gateway.py` | Unchanged (already built); consumed by agent for the first time |
| `src/verification/gate.py` | Modified: adds `"security"` to runner map and `_run_check()` dispatch |
| `src/verification/runners/security_runner.py` | New file |
| `src/reputation/engine.py` | Modified: DB read/write layer added; in-memory becomes cache |
| `src/reputation/models.py` | Possibly modified: add SQLAlchemy model if needed for ORM-based persistence |
| `src/db/migrations/019_reputation_weight_history.py` | New file (if schema gap exists) |
| `pyproject.toml` | Modified: add `bandit` to dev dependencies |

### Assumptions

1. **Claude Agent SDK does not yet expose per-call token usage.** Budget tracking will estimate from prompt/response length until the SDK adds a usage field. This is a known approximation.
2. **`bandit` is the right Phase 0 security tool.** It covers common Python vulnerabilities (SQL injection patterns, hardcoded secrets, insecure function use). More tools can be added later as additional runners.
3. **Migration 008 created the `expert_reputation` table.** If this migration has not been run in a given environment, the reputation persistence code must handle the missing table gracefully (or the deployment docs must require running migrations).
4. **Single-process writes for Phase 0.** The write-through cache pattern assumes a single writer process. Multi-process deployments would need cache invalidation via NATS or similar, which is out of scope.
5. **The `InMemoryBudgetEnforcer` is sufficient for Phase 0.** Budget state is per-process and resets on restart. DB-backed budget tracking is a future enhancement.
6. **Repo profiles default to `["ruff", "pytest"]` for `required_checks`.** Security scanning is opt-in: repos must explicitly add `"security"` to their profile.

### Dependencies

- **No upstream blockers.** C1, C4, and C7 are all standalone per the dependency graph.
- **Downstream unblocks:** C7 completion unblocks V6 (Attribution Principles). C4 completion has a nice-to-have interaction with V5 (Failure Categorization).

---

## Story Map

Stories are ordered by risk reduction (highest-risk slices first) and grouped by work stream. All three streams can proceed in parallel.

### Stream A: Gateway Wiring (C1)

| # | Story | Value | Files to modify/create |
|---|-------|-------|----------------------|
| A1 | **Gateway-aware DeveloperRoleConfig construction** — Refactor `implement()` and `handle_loopback()` to call `ModelRouter.select_model()` and construct `DeveloperRoleConfig` from the returned `ProviderConfig` | Agent respects routing rules | `src/agent/primary_agent.py`, `src/agent/developer_role.py` |
| A2 | **Budget check before agent call** — Call `BudgetEnforcer.check_budget()` before `_run_agent()`; fail task with budget-exceeded status if over limit | Cost control is enforced | `src/agent/primary_agent.py` |
| A3 | **Spend recording after agent call** — Call `BudgetEnforcer.record_spend()` after `_run_agent()` returns, with estimated cost and tokens | Spend tracking is live | `src/agent/primary_agent.py` |
| A4 | **Audit record per invocation** — Create and store `ModelCallAudit` for each `_run_agent()` call with correlation_id, task_id, step, provider, model | Observability for model usage | `src/agent/primary_agent.py` |
| A5 | **Fallback on provider failure** — Wrap `_run_agent()` in try/except; on `NoProviderAvailableError` or provider failure, call `select_with_fallback()` and retry | Resilience to provider outages | `src/agent/primary_agent.py` |
| A6 | **Tests for gateway wiring** — Unit tests: routing context is correct, budget blocks over-limit, spend is recorded, audit records exist, fallback activates | Confidence in wiring | `tests/agent/test_primary_agent_gateway.py` |

### Stream B: Security Scan Runner (C4)

| # | Story | Value | Files to modify/create |
|---|-------|-------|----------------------|
| B1 | **Implement security_runner.py** — Create `run_security_scan()` following the `ruff_runner.py` pattern: subprocess call to `bandit`, timeout handling, fail-closed on errors | Security check exists | `src/verification/runners/security_runner.py` |
| B2 | **Wire security runner into gate** — Add `"security"` to `_RUNNERS` map; add dispatch branch in `_run_check()` | Gate can run security checks | `src/verification/gate.py` |
| B3 | **Add bandit to dev dependencies** — Add `bandit` to `pyproject.toml` dev extras | Runner has its tool available | `pyproject.toml` |
| B4 | **Tests for security runner and gate integration** — Unit tests: pass/fail scenarios, missing binary, timeout, gate dispatch | Confidence in runner behavior | `tests/verification/test_security_runner.py`, `tests/verification/test_gate_security.py` |

### Stream C: Reputation Persistence (C7)

| # | Story | Value | Files to modify/create |
|---|-------|-------|----------------------|
| C1 | **SQLAlchemy model for expert_reputation** — Create ORM model mapped to the `expert_reputation` table (migration 008 schema); add weight_history JSONB column via migration 019 if needed | ORM layer exists | `src/reputation/db_models.py`, `src/db/migrations/019_reputation_weight_history.py` |
| C2 | **DB-backed write path** — Modify `update_weight()` to write to DB first (upsert), then update in-memory cache | Writes are durable | `src/reputation/engine.py` |
| C3 | **DB-backed read path with cache** — Modify `query_weights()`, `get_weight()`, and query functions to check cache first, fall back to DB on miss | Reads are fast but durable | `src/reputation/engine.py` |
| C4 | **Drift history from DB** — Store recent weight values in DB (JSONB array or separate table); load into `_weight_history` on cache miss | Drift detection survives restart | `src/reputation/engine.py`, `src/reputation/db_models.py` |
| C5 | **AsyncSession integration** — Ensure all DB calls use `AsyncSession`; wire session dependency into engine methods (pass session or use a session factory) | Consistent async patterns | `src/reputation/engine.py` |
| C6 | **Tests for persistence** — Unit/integration tests: write-read roundtrip, restart survival, drift history load, concurrent updates, cache-hit verification | Confidence in durability | `tests/reputation/test_engine_persistence.py` |

---

## Meridian Review Status

**Round 1: Conditional PASS — 4 fixes applied**

| # | Question | Status |
|---|----------|--------|
| 1 | Are acceptance criteria testable without ambiguity? | PASS |
| 2 | Are constraints and non-goals explicit enough to prevent scope creep? | PASS |
| 3 | Are success metrics measurable with current tooling? | PASS |
| 4 | Are dependencies and blockers correctly identified? | PASS |
| 5 | Is the story map ordered by risk reduction? | PASS |
| 6 | Can an AI agent implement from this epic alone? | PASS |
| 7 | Are there red flags (missing auth, env vars, untestable criteria)? | PASS |
