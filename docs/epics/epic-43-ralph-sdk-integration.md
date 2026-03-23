# Epic 43: Ralph SDK as Primary Agent -- Session Continuity, Circuit Breaking, and Cost-Aware Implementation

> **Status:** APPROVED -- Meridian PASS (2026-03-22)
> **Epic Owner:** Primary Developer
> **Duration:** 3-4 weeks (4 slices, 15 stories)
> **Created:** 2026-03-22
> **Priority:** P1 -- Enables autonomous multi-loop implementation with production-grade resilience
> **Depends on:** Epic 42 (Execute Tier Promotion) COMPLETE, Ralph SDK v2.0.0 (already shipped)
> **Capacity:** Solo developer, 30 hours/week

---

## 1. Title

**Production-Grade Implementation Agent via Ralph SDK Integration -- Session Continuity, Circuit Breaking, and Cost-Aware Routing Replace Direct LLM Calls**

---

## 2. Narrative

TheStudio's Primary Agent (pipeline stage 6: Implement) calls Claude directly through the Unified Agent Framework's `_call_llm_agentic()` method. This invokes the Claude Agent SDK from `src/agent/framework.py`, wrapping it with provider resolution, budget enforcement, and audit recording. It works. It also has five production gaps that get worse as task complexity increases.

**Gap 1: No session continuity.** Every `implement()` call starts a fresh Claude context. When a complex issue needs multiple loopback passes, the agent has no memory of what it tried before -- it gets a text summary of verification failures, not a live session. Ralph's SDK maintains a session ID across loop iterations, meaning the agent remembers what it did, what it tried, and what failed. This is the difference between "fix the test you just broke" and "here is a list of what is broken, figure out the context from scratch."

**Gap 2: No circuit breaking.** If Claude's API starts returning errors, the current implementation retries at the framework level and eventually hits fallback. There is no sliding-window failure detection, no cooldown period, and no automatic recovery. Ralph's active circuit breaker (`circuit_breaker.py`) implements the full state machine: CLOSED -> OPEN after threshold failures in a sliding window, OPEN -> HALF_OPEN after cooldown, HALF_OPEN -> CLOSED on success. This prevents wasting budget hammering a failing API.

**Gap 3: No dual-condition exit.** The current agent runs for `max_turns` turns or until Claude says it is done. Ralph's dual-condition exit gate requires BOTH explicit exit signal AND NLP-detected completion indicators, preventing premature exits from a single ambiguous response. This matters for tasks where the agent says "done" but fix_plan still has unchecked items.

**Gap 4: No structured status parsing.** The current agent returns raw text that `_parse_changed_files()` scans with a simple heuristic (lines starting with "- " that contain dots or slashes). Ralph's 3-strategy parse chain (JSON block -> JSONL -> regex fallback) extracts work type, completion status, test results, and file changes with validation. This feeds better evidence into the Verification gate.

**Gap 5: Rate limiting is absent.** The current implementation trusts the per-agent budget cap to constrain spend but has no hourly rate limit. Ralph tracks calls per hour and pauses when the limit is reached, preventing burst-induced API throttling.

The Ralph SDK (v2.0.0, shipped and tested) solves all five. It is async, uses Pydantic v2 models, has a pluggable state backend, threads correlation IDs, and includes converters that map TaskPacket -> TaskInput and TaskResult -> EvidenceBundle. The SDK was designed for this exact embedding.

What has not been built: the TheStudio-side integration. Zero lines of code in TheStudio import `ralph_sdk`. The `implement_activity` in `src/workflow/activities.py` has two paths (in-process LLM and container) but neither uses Ralph. The in-process path calls `_implement_in_process()` which does a single LLM call and pushes files via GitHub Contents API. The container path serializes an `AgentTaskInput` and launches Docker. Neither provides session continuity, circuit breaking, or structured status parsing.

This epic builds the bridge: a `PostgresStateBackend` so Ralph's state survives container restarts, a Temporal activity wrapper with heartbeat so long-running Ralph loops report progress, a model gateway adapter so Ralph routes through TheStudio's existing cost optimization infrastructure, and a refactored `primary_agent.py` that replaces `PrimaryAgentRunner` with `RalphAgent`. The existing `implement()` and `handle_loopback()` signatures are preserved. The Unified Agent Framework (`AgentRunner`) continues to power all other pipeline agents (Intake, Context, Intent, Router, Assembler, QA). Only the Primary Agent changes.

Why now: Epic 42 completed Execute tier promotion. Auto-merged PRs need the highest implementation quality because there is no human reviewing the code. Ralph's session continuity, circuit breaking, and dual-condition exit directly reduce the risk of auto-merging bad implementations.

---

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| RFC | `docs/architecture/RFC-001-ralph-sdk-integration.md` | Full analysis of SDK gaps (now resolved) and TheStudio integration requirements |
| Source (Ralph) | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\agent.py` | `RalphAgent` class: async `run()`, `run_iteration()`, `should_exit()`, `process_task_packet()` |
| Source (Ralph) | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\state.py` | `RalphStateBackend` protocol (12 async methods), `FileStateBackend`, `NullStateBackend` |
| Source (Ralph) | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\converters.py` | `from_task_packet()` with `TaskPacketInput` + `IntentSpecInput` -> `TaskInput` |
| Source (Ralph) | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\evidence.py` | `to_evidence_bundle()`: `TaskResult` -> `EvidenceBundle` with test/lint extraction |
| Source (Ralph) | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\circuit_breaker.py` | Active `CircuitBreaker` class with sliding window, cooldown, no-progress detection |
| Source (Ralph) | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\parsing.py` | 3-strategy parse chain: JSON block, JSONL, text fallback |
| Source (Ralph) | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\config.py` | `RalphConfig` Pydantic model (30+ fields, loads from `.ralphrc` / env / JSON) |
| Source (TheStudio) | `src/agent/primary_agent.py` | Current `implement()` and `handle_loopback()` -- the functions being replaced |
| Source (TheStudio) | `src/agent/framework.py` | `AgentRunner`, `AgentConfig`, `AgentContext`, `PipelineBudget` -- continues to power non-Primary agents |
| Source (TheStudio) | `src/agent/evidence.py` | TheStudio `EvidenceBundle` -- target output model |
| Source (TheStudio) | `src/agent/container_protocol.py` | `AgentTaskInput`, `AgentContainerResult` -- container I/O contract |
| Source (TheStudio) | `src/agent/developer_role.py` | `DeveloperRoleConfig`, `build_system_prompt()`, `DEVELOPER_SYSTEM_PROMPT` |
| Source (TheStudio) | `src/workflow/activities.py` | `implement_activity` (line 880) -- wraps Primary Agent in Temporal activity |
| Source (TheStudio) | `src/observability/conventions.py` | Span names and attribute keys for agent.implement |
| Source (TheStudio) | `src/admin/model_gateway.py` | `ModelRouter`, `BudgetEnforcer`, `ProviderConfig` -- cost infrastructure |
| Source (TheStudio) | `src/settings.py` | Feature flags: `agent_isolation`, `agent_llm_enabled`, model routing settings |
| Epic | `docs/epics/epic-23-unified-agent-framework.md` | Established AgentRunner pattern; this epic adds a second implementation path |
| Epic | `docs/epics/epic-25-container-isolation.md` | Container mode for Primary Agent; Ralph integration adds a third mode |
| Epic | `docs/epics/epic-32-model-routing-cost.md` | Cost optimization infrastructure that Ralph must route through |
| Epic | `docs/epics/epic-42-execute-tier-promotion.md` | Auto-merge depends on high-quality implementation; Ralph improves it |
| Architecture | `thestudioarc/08-agent-roles.md` | Agent roles and the Developer role specification |
| OKRs | `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md` | Autonomous operation and implementation quality KRs |

---

## 4. Acceptance Criteria

### AC1: Ralph SDK Replaces Direct LLM Calls for the Primary Agent

The `implement()` function in `src/agent/primary_agent.py` uses `RalphAgent` from `ralph_sdk` instead of `PrimaryAgentRunner`. The function signature is unchanged: it accepts the same parameters and returns `EvidenceBundle`. Internally, it constructs a `RalphAgent` with `NullStateBackend` (Slice 1) or `PostgresStateBackend` (Slice 2), converts the TaskPacket and IntentSpec into Ralph's `TaskPacketInput` and `IntentSpecInput` using the SDK's `from_task_packet()` converter, calls `await agent.run()`, and converts the `TaskResult` to TheStudio's `EvidenceBundle` using the SDK's `to_evidence_bundle()` plus a mapping layer for UUID and datetime types.

**Testable:** A unit test mocks `RalphAgent.run()` to return a known `TaskResult`. Calls `implement()` with a mock TaskPacket and IntentSpec. Verifies the returned `EvidenceBundle` has correct `taskpacket_id`, `intent_version`, `files_changed`, `agent_summary`, and `loopback_attempt`. Verifies `RalphAgent.__init__()` received the correct `correlation_id` from the TaskPacket.

### AC2: Handle_Loopback Provides Session Continuity via Ralph State

The `handle_loopback()` function loads the previous Ralph session state (session ID, loop count, circuit breaker state) and passes it to `RalphAgent` so the agent resumes with context from the previous attempt. The loopback verification failure details are mapped into the `loopback_context` field of `TaskPacketInput` via the SDK converter. The `RalphAgent` uses its session continuity mechanism (`--continue <session_id>` in CLI mode) to give Claude the full history of the previous attempt.

**Testable:** A test calls `implement()` followed by `handle_loopback()`. Verifies the second call constructs `RalphAgent` with a state backend that contains the session ID from the first call. Verifies the `TaskPacketInput.loopback_context` includes the verification failure details. The session ID is verified via the state backend's `read_session_id()` method. **Testability timeline:** In Slice 1 (NullStateBackend), only loopback context mapping is testable — session ID persistence requires Slice 2 (PostgresStateBackend). AC2 is partially verified in Slice 1 Story 43.5 and fully verified in Slice 2 Story 43.9 + Slice 4 Story 43.15.

### AC3: PostgresStateBackend Implements RalphStateBackend Protocol

A new `PostgresStateBackend` class in `src/agent/ralph_state.py` implements all 12 methods of the `RalphStateBackend` protocol using async SQLAlchemy. State is stored in a new `ralph_agent_state` table keyed by `(taskpacket_id, key_name)`. The backend is scoped to a single TaskPacket so multiple concurrent pipeline runs do not interfere. All operations use the existing database session infrastructure from `src/db/`.

**Testable:** An integration test creates a `PostgresStateBackend` for a test TaskPacket, writes status/circuit-breaker/session data, reads it back, and verifies all 12 protocol methods round-trip correctly. The test also verifies that two backends for different TaskPackets do not share state. `isinstance(backend, RalphStateBackend)` returns `True` (the protocol is runtime-checkable).

### AC4: Model Gateway Routes Ralph's Claude Calls Through Cost Infrastructure

Ralph's Claude CLI invocations route through TheStudio's Model Gateway for provider selection and cost tracking. A `RalphConfig` is constructed that sets the `claude_code_cmd`, `model`, and `allowed_tools` from the resolved `ProviderConfig`. After each `run()` call, the cost is estimated from the `TaskResult.duration_seconds` and loop count, and recorded via `ModelCallAudit` and `BudgetEnforcer`. The pipeline budget (`PipelineBudget`) is checked before launching Ralph and consumed after completion.

**Testable:** A test creates a `PipelineBudget(max_total_usd=5.0)`, mocks Ralph to report 2.0 USD spent. Verifies `PipelineBudget.used` increases by 2.0 after the call. A second test verifies that when `PipelineBudget.remaining < agent_max_budget_usd`, the implement call raises `BudgetExceededError` without invoking Ralph.

### AC5: Temporal Activity Wrapper with Heartbeat and Timeout

The `implement_activity` in `src/workflow/activities.py` gains a third mode: `"ralph"` (alongside `"process"` and `"container"`). When `THESTUDIO_AGENT_MODE=ralph`, the activity constructs a `RalphAgent` and calls `await agent.run()` inside a Temporal heartbeat loop. The heartbeat reports Ralph's current loop count and status every 30 seconds by reading the state backend. If the Temporal activity times out, Ralph's loop is cancelled via `agent._running = False`. The activity timeout is configurable via settings (default: 30 minutes).

**Testable:** A unit test mocks `RalphAgent.run()` to take 5 seconds. Verifies at least one heartbeat was emitted. A second test sets `RalphAgent._running = True` and verifies that setting it to `False` causes the agent loop to exit within one iteration.

### AC6: Feature Flag Controls Ralph vs Legacy Agent Path

A new setting `THESTUDIO_AGENT_MODE` controls which implementation path the Primary Agent uses: `"legacy"` (current `PrimaryAgentRunner`), `"ralph"` (new Ralph SDK), or `"container"` (existing Docker isolation). Default is `"legacy"`. The flag is checked in `implement_activity`. The existing `agent_llm_enabled.developer` flag continues to gate whether the LLM is called at all (False = fallback regardless of mode). This allows gradual rollout: first test Ralph on low-complexity tasks, then expand.

**Testable:** A test sets `THESTUDIO_AGENT_MODE=ralph` and verifies `implement_activity` constructs a `RalphAgent`. A test sets `THESTUDIO_AGENT_MODE=legacy` and verifies it uses `PrimaryAgentRunner`. A test sets `agent_llm_enabled.developer=False` and verifies fallback is used regardless of agent mode.

### 4b. Top Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Ralph CLI binary not available in deployment** | `RalphAgent.run_iteration()` calls `claude` CLI via subprocess; if the binary is missing, the agent fails with `FileNotFoundError` | Feature flag (`THESTUDIO_AGENT_MODE`) defaults to `"legacy"`. Slice 4 includes a health check that verifies CLI availability before switching modes. Story 43.13 adds a startup probe. |
| **Session ID invalidation between loopbacks** | Claude may expire sessions; reusing a stale session ID could cause errors | Ralph's `run_iteration()` already handles `FileNotFoundError` and falls back to a fresh session. Story 43.5 adds a TTL check on stored session IDs (discard if > 2 hours old). |
| **Cost estimation inaccuracy** | Ralph's duration-based cost estimate may diverge from actual API spend | Story 43.8 records both Ralph's estimate and the Model Gateway's per-call audit. Story 43.14 adds a reconciliation check in the dashboard. |
| **Concurrent TaskPackets sharing state** | If two pipeline runs use the same state backend key, circuit breaker state could bleed across | `PostgresStateBackend` is keyed by `taskpacket_id` (AC3). Unit test verifies isolation. |
| **Ralph loop runs longer than Temporal activity timeout** | Activity gets killed, leaving orphan subprocess | Heartbeat wrapper (AC5) cancels Ralph cleanly. Activity timeout set to `config.timeout_minutes + 5` to give Ralph time to exit gracefully. |

---

## 5. Constraints and Non-Goals

### Constraints

- The Ralph SDK lives in a separate repository (`C:\cursor\ralph\ralph-claude-code\sdk\`). This epic does NOT modify the Ralph SDK. All work is on TheStudio side. If SDK changes are needed, they become a blocking dependency tracked as a risk.
- The `implement()` and `handle_loopback()` function signatures in `src/agent/primary_agent.py` must not change. Downstream callers (Temporal activities, tests) must not be affected by the internal switch to Ralph.
- The Unified Agent Framework (`AgentRunner` in `src/agent/framework.py`) is not modified. It continues to power all non-Primary agents (Intake, Context, Intent, Router, Assembler, QA, Preflight).
- The Ralph SDK is installed as a path dependency (`ralph-sdk @ file:///path/to/sdk`) in development and as a versioned package in production. The `pyproject.toml` gains a new dependency.
- Database migrations must be backward-compatible (nullable columns, new tables only, no column renames).
- The `ralph_sdk` package must be importable without `aiofiles` in test environments where only `NullStateBackend` is used. `aiofiles` is only required by `FileStateBackend`.

### Non-Goals

- **Modifying the Ralph SDK.** This epic consumes the SDK as-is (v2.0.0). SDK improvements are tracked separately in the Ralph repo.
- **Replacing the container isolation path.** The Docker-based `_implement_container()` path from Epic 25 remains available. Ralph integration is a third mode, not a replacement.
- **Multi-agent orchestration.** Ralph runs as a single agent. Orchestrating multiple Ralph instances (e.g., one for implementation, one for testing) is future work.
- **Dashboard visualization of Ralph internals.** Exposing Ralph's loop status, circuit breaker state, and session history via SSE is deferred. This epic records the data; the dashboard work is a follow-on.
- **Ralph CLI installation automation.** This epic assumes the Claude CLI binary is available in the runtime environment. Packaging it into Docker images or deployment artifacts is an infrastructure concern.
- **Prompt template migration.** Ralph uses its own prompt building (`_build_iteration_prompt`). This epic maps TheStudio's `DeveloperRoleConfig.build_system_prompt()` output into Ralph's prompt field but does not refactor TheStudio's prompt templates.
- **Promoting Ralph as default agent mode.** This epic adds Ralph as an opt-in alternative (`agent_mode="ralph"`). Promotion to default (replacing `"legacy"`) is a separate decision after production validation with real tasks. Promotion criteria are out of scope.

---

## 6. Stakeholders and Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner / Tech Lead / QA | Primary Developer (solo) | All implementation, testing, scope decisions |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Ralph replaces direct LLM calls for Primary Agent | 100% of `implement()` calls use Ralph when `THESTUDIO_AGENT_MODE=ralph` | Unit test + feature flag check: `implement_activity` dispatches to Ralph path |
| Session continuity across loopbacks | Session ID reused in >= 80% of loopback calls (remainder: expired sessions) | Query `ralph_agent_state` table: count(loopback_calls with session_id) / count(total_loopbacks) |
| Circuit breaker prevents wasted spend | Zero budget consumed on tasks where circuit breaker is OPEN | Query: sum(cost) where circuit_breaker_state = OPEN should be 0.00 |
| Cost recorded via Model Gateway | 100% of Ralph runs have a corresponding `ModelCallAudit` record | Query: count(implement runs with agent_mode=ralph) = count(ModelCallAudit where step=primary_agent and role=developer) |
| PostgresStateBackend round-trips correctly | All 12 protocol methods pass round-trip test | Integration test suite: 12 write/read assertions |
| No regression in implementation quality | EvidenceBundle.files_changed is non-empty for >= 95% of successful Ralph runs | Query: count(Ralph EvidenceBundles where files_changed is non-empty) / count(successful Ralph runs). Comparison test: both paths produce EvidenceBundle with non-empty files_changed and agent_summary for the same mock task |

---

## 8. Context and Assumptions

### Business Rules

- The Primary Agent is the only pipeline agent that changes. All other agents (Intake, Context, Intent, Router, Assembler, QA, Publisher) continue to use `AgentRunner`.
- Ralph's dual-condition exit gate is stricter than the current `max_turns` limit. This means Ralph may finish earlier (saving cost) or later (producing better output) than the current agent. The `timeout_minutes` setting on `RalphConfig` provides the hard ceiling.
- Ralph invokes Claude CLI as a subprocess, not via the Anthropic HTTP API. This means the Model Gateway cannot intercept individual API calls for per-message cost tracking. Cost is estimated at the run level based on duration and model tier.
- The `PostgresStateBackend` stores state as JSON values in a key-value table. This is intentionally simple -- it mirrors the file-based backend's flat structure. A richer schema (normalized tables for circuit breaker events, session history) is future optimization.

### Dependencies

- **Ralph SDK v2.0.0** -- AVAILABLE. The SDK is at `C:\cursor\ralph\ralph-claude-code\sdk\` with all RFC-001 items implemented: async agent, Pydantic models, state backend protocol, active circuit breaker, structured parsing, correlation ID, converters, evidence bundle output. Version confirmed in `__init__.py`: `__version__ = "2.0.0"`.
- **Claude CLI binary** -- Must be available in the runtime environment at the path specified by `RalphConfig.claude_code_cmd` (default: `claude`). Not installed by TheStudio.
- **Epic 42 (Execute Tier Promotion)** -- COMPLETE. Provides the auto-merge infrastructure that benefits from Ralph's higher-quality implementations.
- **Epic 32 (Model Routing & Cost Optimization)** -- COMPLETE. Provides `ModelRouter`, `BudgetEnforcer`, `PipelineBudget` that Ralph must integrate with.
- **Epic 25 (Container Isolation)** -- COMPLETE. Container mode continues to work alongside Ralph mode. No conflict.

### Systems Affected

| System | Impact |
|--------|--------|
| `src/agent/primary_agent.py` | Major refactor: replace `PrimaryAgentRunner` usage with `RalphAgent`. Both `implement()` and `handle_loopback()` internals change. Signatures preserved. |
| `src/agent/ralph_state.py` | NEW FILE: `PostgresStateBackend` implementing `RalphStateBackend` protocol |
| `src/agent/ralph_bridge.py` | NEW FILE: Adapter functions mapping TheStudio models <-> Ralph SDK models |
| `src/workflow/activities.py` | Modify `implement_activity` to add `"ralph"` mode alongside `"process"` and `"container"` |
| `src/settings.py` | New setting: `THESTUDIO_AGENT_MODE` (legacy/ralph/container) |
| `src/observability/conventions.py` | New span names and attributes for Ralph-specific instrumentation |
| `src/db/migrations/` | New migration: `ralph_agent_state` table |
| `pyproject.toml` | New dependency: `ralph-sdk` (path or versioned) |
| `tests/unit/test_ralph_integration.py` | NEW FILE: Unit tests for Ralph bridge, state backend, activity wrapper |
| `tests/integration/test_ralph_e2e.py` | NEW FILE: Integration test for full implement -> loopback cycle via Ralph |

### Assumptions

- The Ralph SDK's `RalphAgent.run()` method works correctly in TheStudio's async event loop (FastAPI + Temporal). The SDK's async implementation uses `asyncio.create_subprocess_exec()` which is compatible with any asyncio event loop.
- The `claude` CLI binary supports the `--continue <session_id>` flag for session resumption. This is documented in Ralph's bash loop and SDK.
- The Ralph SDK's `NullStateBackend` is sufficient for unit testing and does not require `aiofiles` to be installed.
- The `ralph_sdk` package can be imported without side effects (no global state initialization at import time). Confirmed by reading `__init__.py`.
- TheStudio's `EvidenceBundle` (UUID `taskpacket_id`, int `intent_version`, datetime `created_at`) and Ralph's `EvidenceBundle` (str `taskpacket_id`, str `intent_version`, no `created_at`) have minor type differences that the bridge layer must handle.
- The `PostgresStateBackend` table uses `TEXT` values for JSON state, not `JSONB`, to avoid Postgres-specific operations and keep the migration simple. `JSONB` is a future optimization.

---

## Story Map

### Slice 1: MVP -- Ralph Agent Replaces PrimaryAgentRunner (Risk Reduction)

_Goal: A TaskPacket flows through `implement()` using `RalphAgent` with `NullStateBackend` instead of `PrimaryAgentRunner`. The function signature does not change. Feature flag gates the switch. No database changes yet._

| # | Story | AC | Est | Files to modify/create |
|---|-------|----|-----|----------------------|
| 43.1 | **Add ralph-sdk dependency to pyproject.toml** -- Add `ralph-sdk` as a path dependency for development (`ralph-sdk @ file:///C:/cursor/ralph/ralph-claude-code/sdk`). **CI/production strategy:** the Ralph SDK repo is added as a git submodule at `vendor/ralph-sdk/` and the dependency is `ralph-sdk @ file:///vendor/ralph-sdk` in CI. The `pyproject.toml` includes both forms: the path dependency for local dev (active) and the submodule path for CI (commented with `# CI:`). Add a `Makefile` target `make vendor-ralph` that runs `git submodule update --init vendor/ralph-sdk`. Verify `import ralph_sdk` works. Verify `from ralph_sdk import RalphAgent, NullStateBackend, TaskInput, TaskResult` imports succeed. | AC1 | 2h | `pyproject.toml`, `Makefile`, `.gitmodules` |
| 43.2 | **Build model bridge: TheStudio <-> Ralph SDK** -- Create `src/agent/ralph_bridge.py` with five functions. First: `check_ralph_cli_available() -> bool` — runs `claude --version` via `asyncio.create_subprocess_exec()` with a 5-second timeout; returns False if binary not found or timeout. Called during `implement()` when `agent_mode="ralph"`; if False, logs error and falls back to legacy mode (does not raise). Then four conversion functions: (a) `taskpacket_to_ralph_input(taskpacket: TaskPacketRead, intent: IntentSpecRead, loopback_context: str = "") -> TaskPacketInput` -- maps TheStudio Pydantic models to Ralph's `TaskPacketInput` and `IntentSpecInput` mirror models. Maps `intent.goal` -> `IntentSpecInput.goal`, `intent.constraints` -> list, `intent.acceptance_criteria` -> list, `intent.non_goals` -> list, `taskpacket.risk_flags` -> `RiskFlag` list (only high/critical severity become SAFETY constraints), `taskpacket.complexity_index` -> `ComplexityBand` enum mapping (0-3=LOW, 4-6=MEDIUM, 7-10=HIGH), `taskpacket.task_trust_tier` -> `TrustTier` (observe->RESTRICTED, suggest->STANDARD, execute->FULL). (b) `ralph_result_to_evidence(result: ralph_sdk.TaskResult, taskpacket_id: UUID, intent_version: int, loopback_attempt: int = 0) -> EvidenceBundle` -- converts Ralph's `TaskResult` to TheStudio's `EvidenceBundle`. Calls `ralph_sdk.evidence.to_evidence_bundle()` for test/lint extraction, then maps string fields to UUID/int/datetime types. (c) `build_ralph_config(role_config: DeveloperRoleConfig | None, provider: ProviderConfig, complexity: str) -> RalphConfig` -- constructs `RalphConfig` from TheStudio settings. Sets `model` from `provider.model_id`, `allowed_tools` from `role_config.tool_allowlist` or `DEFAULT_TOOL_ALLOWLIST`, `max_turns` from complexity scaling (low=20, medium=30, high=50), `timeout_minutes` from settings. (d) `build_verification_loopback_context(verification_result: VerificationResult) -> str` -- formats check results into a markdown string for Ralph's loopback_context field. | AC1, AC2 | 4h | `src/agent/ralph_bridge.py` (NEW) |
| 43.3 | **Add THESTUDIO_AGENT_MODE setting** -- Add `agent_mode: str = "legacy"` to `src/settings.py` with env var `THESTUDIO_AGENT_MODE`. Valid values: `"legacy"`, `"ralph"`, `"container"`. Add validation that rejects unknown values. **Interaction with `agent_isolation`:** `agent_mode` replaces `agent_isolation` as the dispatch key in `implement_activity`. When `agent_mode="container"`, behavior is identical to `agent_isolation="container"`. When `agent_mode="ralph"`, the container isolation path is NOT used — Ralph runs as an async subprocess within the activity, not inside Docker. `_validate_execute_tier_isolation()` applies only to `agent_mode="container"`; Ralph mode is always allowed regardless of tier (Ralph has its own circuit breaker for safety). If both `THESTUDIO_AGENT_MODE` and `THESTUDIO_AGENT_ISOLATION` are set, `agent_mode` takes precedence and a deprecation warning is logged. Document in `docs/URLs.md`. | AC6 | 2h | `src/settings.py` |
| 43.4 | **Refactor primary_agent.py to support Ralph mode** -- Modify `implement()` to check `settings.agent_mode`. When `"ralph"`: (a) resolve provider via `_resolve_provider()` helper (extracted from `AgentRunner._resolve_provider` logic, using `get_model_router().select_model(step="primary_agent")`), (b) build `RalphConfig` via `build_ralph_config()`, (c) construct `RalphAgent(config=ralph_config, state_backend=NullStateBackend(), correlation_id=str(taskpacket.correlation_id))`, (d) convert TaskPacket+IntentSpec to `TaskInput` via `taskpacket_to_ralph_input()` then `from_task_packet()`, (e) call `await agent.run()`, (f) convert result via `ralph_result_to_evidence()`. When `"legacy"`: existing `PrimaryAgentRunner` code path (unchanged). Similarly modify `handle_loopback()`: same Ralph construction but with `build_verification_loopback_context()` feeding `loopback_context`. **Note:** The `PrimaryAgentRunner` class and all legacy code remain in the file, gated behind the `"legacy"` mode. Do not delete any existing code. | AC1, AC2, AC6 | 5h | `src/agent/primary_agent.py` |
| 43.5 | **Unit tests for Ralph bridge and primary_agent dispatch** -- Tests: (a) `taskpacket_to_ralph_input` correctly maps all fields (goal, constraints, criteria, non_goals, risk_flags, complexity, trust_tier, loopback_context). (b) `ralph_result_to_evidence` converts UUID strings to UUID objects, sets correct intent_version and loopback_attempt. (c) `build_ralph_config` uses provider model_id, scales max_turns by complexity. (d) `implement()` with `agent_mode="ralph"` constructs RalphAgent (mock `run()` to return a canned TaskResult). (e) `implement()` with `agent_mode="legacy"` uses PrimaryAgentRunner. (f) `handle_loopback()` with `agent_mode="ralph"` passes verification failure context. (g) **Setting overlap tests:** when both `THESTUDIO_AGENT_MODE=ralph` and `THESTUDIO_AGENT_ISOLATION=container` are set, `agent_mode` wins and a deprecation warning is logged. When `agent_mode="container"`, behavior matches `agent_isolation="container"`. When `agent_mode="ralph"`, `_validate_execute_tier_isolation()` is NOT called. (h) `check_ralph_cli_available()` returns False when `claude` binary is not on PATH (mocked subprocess). | AC1, AC2, AC6 | 5h | `tests/unit/test_ralph_bridge.py` (NEW), `tests/unit/test_primary_agent_ralph.py` (NEW) |

**Slice 1 Total: ~15h (1 week)**

### Slice 2: State Persistence -- PostgresStateBackend (Durability)

_Goal: Ralph's state (session ID, circuit breaker, rate limit counters) survives across loopback attempts and activity restarts. The NullStateBackend from Slice 1 is replaced with PostgresStateBackend for production use._

| # | Story | AC | Est | Files to modify/create |
|---|-------|----|-----|----------------------|
| 43.6 | **Create ralph_agent_state table migration** -- New table `ralph_agent_state` with columns: `id UUID PK DEFAULT gen_random_uuid()`, `taskpacket_id UUID NOT NULL`, `key_name VARCHAR(64) NOT NULL`, `value_json TEXT NOT NULL DEFAULT '{}'`, `updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()`. Unique constraint on `(taskpacket_id, key_name)`. Index on `taskpacket_id`. Key names correspond to the 6 state categories: `status`, `circuit_breaker`, `call_count`, `last_reset`, `session_id`, `fix_plan`. | AC3 | 2h | `src/db/migrations/` (NEW migration) |
| 43.7 | **Implement PostgresStateBackend** -- Create `src/agent/ralph_state.py` with `PostgresStateBackend` class implementing all 12 `RalphStateBackend` protocol methods. Constructor takes `taskpacket_id: UUID` and `session_factory: async_sessionmaker`. Each method maps to a single upsert or select on the `ralph_agent_state` table. JSON dict values are serialized/deserialized with `json.dumps()`/`json.loads()`. Integer values (`call_count`, `last_reset`) are stored as `{"value": N}`. String values (`session_id`, `fix_plan`) are stored as `{"value": "..."}`. The class must pass `isinstance(backend, RalphStateBackend)` check (protocol is `@runtime_checkable`). | AC3 | 4h | `src/agent/ralph_state.py` (NEW) |
| 43.8 | **Wire PostgresStateBackend into primary_agent.py** -- Modify the Ralph mode in `implement()` and `handle_loopback()` to construct `PostgresStateBackend(taskpacket_id=taskpacket_id, session_factory=get_async_session_factory())` instead of `NullStateBackend()`. Add a setting `THESTUDIO_RALPH_STATE_BACKEND` with values `"postgres"` (default when agent_mode=ralph) and `"null"` (for testing/stateless). When `"null"`, continue using `NullStateBackend`. Session ID from a previous `implement()` call is loaded from the state backend at the start of `handle_loopback()`, giving Ralph session continuity. Add a session ID TTL check: if `updated_at` on the session_id row is older than 2 hours, discard the session ID (Claude sessions may expire). | AC2, AC3 | 3h | `src/agent/primary_agent.py`, `src/settings.py` |
| 43.9 | **Integration tests for PostgresStateBackend** -- Tests using the test database: (a) write and read all 12 state operations, verify round-trip. (b) Two backends for different taskpacket_ids do not share state. (c) Concurrent writes to the same key use upsert correctly (no duplicate key errors). (d) `isinstance(backend, RalphStateBackend)` returns True. (e) Session ID TTL: write session_id with `updated_at` 3 hours ago, verify `read_session_id()` returns empty string. | AC3 | 3h | `tests/integration/test_ralph_state.py` (NEW) |

**Slice 2 Total: ~12h (1 week)**

### Slice 3: Cost Integration and Temporal Activity (Production Readiness)

_Goal: Ralph's Claude CLI calls are tracked through the cost infrastructure. The Temporal activity heartbeats during long Ralph runs. Budget enforcement prevents overspend._

| # | Story | AC | Est | Files to modify/create |
|---|-------|----|-----|----------------------|
| 43.10 | **Cost recording after Ralph run** -- After `RalphAgent.run()` completes, record a `ModelCallAudit` with: `step="primary_agent"`, `role="developer"`, `provider` from the resolved ProviderConfig, `tokens_in` and `tokens_out` estimated from `result.output` length (same heuristic as `_call_llm_agentic`: chars // 4), `cost` estimated from `result.duration_seconds * provider.cost_per_minute` (new field on ProviderConfig; if absent, fall back to `result.loop_count * 0.05` as a conservative estimate). Record spend via `BudgetEnforcer.record_spend()`. Check `PipelineBudget.consume()` before launching Ralph; raise `BudgetExceededError` if insufficient. After run, emit `cost_update` SSE event via `emit_cost_update()`. | AC4 | 4h | `src/agent/primary_agent.py`, `src/agent/ralph_bridge.py` |
| 43.11 | **Implement ralph mode in implement_activity with heartbeat** -- Add `"ralph"` case to `implement_activity` dispatch. When `settings.agent_mode == "ralph"`: (a) construct `RalphAgent` with `PostgresStateBackend`, (b) launch `agent.run()` as a background task, (c) run a heartbeat loop that calls `activity.heartbeat({"loop_count": ..., "status": ...})` every 30 seconds by reading the state backend, (d) await the agent task with timeout `settings.ralph_timeout_minutes + 5`. On timeout, set `agent._running = False` and await graceful shutdown (up to 30 seconds). On cancellation, same shutdown path. Convert `TaskResult` to `ImplementOutput`. Add new settings: `THESTUDIO_RALPH_TIMEOUT_MINUTES` (default 30). | AC5 | 5h | `src/workflow/activities.py`, `src/settings.py` |
| 43.12 | **Unit tests for cost recording and activity heartbeat** -- Tests: (a) after mock Ralph run, `ModelCallAudit` is recorded with correct step/role/provider. (b) `PipelineBudget.consume()` is called before Ralph launch; BudgetExceededError raised when insufficient. (c) `emit_cost_update()` is called after Ralph run. (d) Activity heartbeat loop emits at least one heartbeat for a 5-second mock run. (e) Setting `agent._running = False` causes `run()` to exit within one iteration. | AC4, AC5 | 3h | `tests/unit/test_ralph_cost.py` (NEW), `tests/unit/test_ralph_activity.py` (NEW) |

**Slice 3 Total: ~12h (1 week)**

### Slice 4: Validation and Observability (Confidence)

_Goal: End-to-end integration test, observability spans, health check, and migration documentation prove the integration works before enabling in production._

| # | Story | AC | Est | Files to modify/create |
|---|-------|----|-----|----------------------|
| 43.13 | **Ralph health endpoint and startup probe** -- Add a `/health/ralph` endpoint in the dashboard that calls `check_ralph_cli_available()` (already in `ralph_bridge.py` from Story 43.2) and returns `{"available": bool, "version": str}`. Add a startup probe in `src/app.py` that logs a warning when `agent_mode="ralph"` and the CLI is unavailable (do not block startup). | AC6 | 1h | `src/dashboard/app.py`, `src/app.py` |
| 43.14 | **Observability spans for Ralph agent lifecycle** -- Add span names to `src/observability/conventions.py`: `SPAN_RALPH_RUN = "ralph.run"`, `SPAN_RALPH_ITERATION = "ralph.iteration"`, `SPAN_RALPH_CIRCUIT_BREAKER = "ralph.circuit_breaker"`. Add attribute keys: `ATTR_RALPH_LOOP_COUNT`, `ATTR_RALPH_SESSION_ID`, `ATTR_RALPH_EXIT_REASON`, `ATTR_RALPH_WORK_TYPE`. Instrument the Ralph mode in `primary_agent.py` with these spans: wrap the `agent.run()` call in `SPAN_RALPH_RUN`, set loop count and exit reason as attributes after completion. Set `ATTR_RALPH_SESSION_ID` for loopback tracing. | AC1, AC2 | 2h | `src/observability/conventions.py`, `src/agent/primary_agent.py` |
| 43.15 | **End-to-end integration test: implement + loopback via Ralph** -- Integration test that exercises the full path: (a) create a TaskPacket and IntentSpec in the test database, (b) call `implement()` with `agent_mode="ralph"` (mocked `RalphAgent.run()` returns a TaskResult with files_changed and agent_summary), (c) verify EvidenceBundle has correct data, (d) verify `ralph_agent_state` table has session_id and status entries, (e) call `handle_loopback()` with a mock VerificationResult, (f) verify the second call loads the session_id from step (d), (g) verify loopback_context contains the verification failure details, (h) verify both calls produced `ModelCallAudit` records. This is the "would it work in production" test. | AC1, AC2, AC3, AC4 | 4h | `tests/integration/test_ralph_e2e.py` (NEW) |

**Slice 4 Total: ~8h (0.5 weeks)**

**Epic Total: ~48h raw + 30% buffer = ~62h effective budget (3-4 weeks at 30h/week)**

---

## Meridian Review Status

### Round 1: CONDITIONAL PASS → Fixes Applied → PASS (2026-03-22)

| # | Question | Status | Notes |
|---|----------|--------|-------|
| 1 | Is the goal statement specific enough to test against? | **PASS** | Five named gaps, clear replacement target, concrete "why now" tied to Epic 42 auto-merge |
| 2 | Are acceptance criteria testable at epic scale? | **PASS** | All 6 ACs have explicit test scenarios. AC2 testability timeline clarified (partial Slice 1, full Slice 2). |
| 3 | Are non-goals explicit? | **PASS** | Seven non-goals including promotion criteria (added in fix round). |
| 4 | Are dependencies identified with owners and dates? | **PASS** | CI install strategy specified (git submodule). CLI check moved to Slice 1. |
| 5 | Are success metrics measurable with existing instrumentation? | **PASS** | "No regression" metric strengthened to >=95% non-empty files_changed. Buffer made explicit (48h + 30%). |
| 6 | Can an AI agent implement without guessing scope? | **PASS** | `agent_mode` vs `agent_isolation` interaction rules specified in Story 43.3. Overlap tests added to Story 43.5. |
| 7 | Are there red flags? | **PASS** | No red flags. |

**Fixes applied (2026-03-22):**
1. Specified `THESTUDIO_AGENT_MODE` vs `agent_isolation` precedence in Story 43.3; overlap tests in Story 43.5(g)
2. Moved `check_ralph_cli_available()` from Story 43.13 to Story 43.2; fallback to legacy on CLI absence
3. Specified CI install strategy (git submodule at `vendor/ralph-sdk/`) in Story 43.1
4. Added AC2 testability timeline note (partial Slice 1, full Slice 2)
5. Made buffer explicit: 48h + 30% = 62h effective
6. Strengthened "no regression" metric: >=95% non-empty files_changed
7. Added promotion criteria to non-goals
