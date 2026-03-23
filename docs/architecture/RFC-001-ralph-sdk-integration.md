# RFC-001: Ralph SDK Changes for TheStudio Integration

> **Status:** DRAFT | **Author:** TheStudio Team | **Date:** 2026-03-22
> **Target:** Ralph SDK v2.0.0 | **Effort:** ~2-3 weeks
> **Depends on:** Ralph SDK v1.3.0 (current), TheStudio Agent Framework (`src/agent/framework.py`)

---

## 1. Summary

Ralph is TheStudio's intended Primary Agent (pipeline stage 6: Implement). The Ralph
Python SDK (v1.3.0) was designed with TheStudio embedding in mind — `TaskInput.from_task_packet()`,
`TaskResult.to_signal()`, and `process_task_packet()` all exist. However, line-by-line
analysis reveals the SDK is a proof-of-concept with critical gaps that prevent production
integration.

This RFC requests 8 changes to the Ralph SDK, organized into two tiers:

- **BLOCKING (4 items):** Must be resolved before any integration work begins. The current
  SDK cannot be imported into TheStudio's async runtime without these.
- **HIGH VALUE (4 items):** Should be resolved to avoid building throwaway adapter code on
  the TheStudio side. Each saves 2-5 days of integration effort.

The goal is Ralph SDK v2.0.0 — a production-ready embedding layer that TheStudio can
import directly into its Temporal activities and FastAPI routes.

---

## 2. Motivation

### Why Ralph as Primary Agent?

TheStudio's pipeline stage 6 (`src/agent/primary_agent.py`) currently invokes Claude
Agent SDK directly via `_call_llm_agentic()`. This works but lacks:

- **Session continuity** across multi-loop tasks (complex issues needing multiple passes)
- **Circuit breaker protection** against repeated API failures
- **Cost-aware model routing** (Sonnet for routine work, Opus for complex tasks)
- **Graceful sub-agent degradation** (explorer fails -> fall back to Glob/Grep)
- **Progress tracking harness** (the exact pattern Anthropic recommends for long-running agents)

Ralph implements all five. Its bash loop (`ralph_loop.sh`, 3,887 lines) is battle-tested
with 736+ tests. The SDK is the bridge — but today it's a bridge with missing planks.

### Why Not Adapter-Pattern Around the Gaps?

We evaluated wrapping the current SDK with TheStudio adapters. The cost:

| Gap | Adapter effort | Adapter maintenance debt |
|-----|---------------|------------------------|
| Sync -> Async | 3d (wrap every call in `asyncio.to_thread`) | Permanent perf penalty, no cancellation |
| Dataclass -> Pydantic | 2d (convert at boundary) | Double serialization on every call |
| Signal shape | 1d (map 6 fields to EvidenceBundle) | Breaks on any Ralph output change |
| Correlation ID | 2d (inject after the fact) | Gaps in trace continuity |

**Total adapter cost: ~8 days + ongoing maintenance.** Fixing it upstream costs ~14 days
but produces a clean, maintainable integration with zero adapter debt.

---

## 3. Current Interface Contract

TheStudio's Primary Agent must satisfy this signature:

```python
async def implement(
    session: AsyncSession,          # SQLAlchemy async session
    taskpacket_id: UUID,            # Work item ID
    repo_path: str,                 # Cloned repo on disk
    role_config: DeveloperRoleConfig | None = None,
    *,
    overlays: list[str] | None = None,   # ["security", "hotfix"]
    repo_tier: str = "",                  # "observe" | "suggest" | "execute"
    complexity: str = "",                 # "low" | "medium" | "high"
) -> EvidenceBundle:
```

And for loopback retries:

```python
async def handle_loopback(
    session: AsyncSession,
    taskpacket_id: UUID,
    repo_path: str,
    verification_result: VerificationResult,
    role_config: DeveloperRoleConfig | None = None,
    *,
    overlays: list[str] | None = None,
    repo_tier: str = "",
    complexity: str = "",
) -> EvidenceBundle:
```

**Key models Ralph must produce/consume:**

| Model | Location | Purpose |
|-------|----------|---------|
| `TaskPacket` | `src/models/taskpacket.py` | 20+ field durable work record |
| `IntentSpec` | `src/intent/intent_spec.py` | Goal, constraints, acceptance criteria |
| `EvidenceBundle` | `src/agent/evidence.py` | Files changed, test/lint results, summary |
| `VerificationResult` | `src/verification/gate.py` | Check pass/fail with details |
| `AgentConfig` | `src/agent/framework.py` | Tool allowlist, budget, model class |
| `AgentContext` | `src/agent/framework.py` | Correlation ID, risk flags, repo tier |
| `PipelineBudget` | `src/agent/framework.py` | Per-agent cost tracking |

All models are **Pydantic v2 BaseModel** or **frozen dataclass**. All entry points are
**async**. All operations propagate **correlation_id** via OpenTelemetry spans.

---

## 4. Requested Changes

### BLOCKING-1: Async SDK

**Current state:** Fully synchronous. `subprocess.run()` in `agent.py:280`,
`Path.read_text()` throughout, `time.sleep(2)` at `agent.py:246`.

**Required:** Every public method must have an async implementation.

**Specific changes:**

| Component | Current | Required |
|-----------|---------|----------|
| `RalphAgent.run()` | `subprocess.run()` | `asyncio.create_subprocess_exec()` |
| `RalphAgent.run_iteration()` | Blocking subprocess | `await` subprocess with timeout |
| `RalphAgent.should_exit()` | Synchronous | `async def should_exit()` |
| `RalphAgent.check_rate_limit()` | Reads file synchronously | `async` with `aiofiles` |
| `RalphStatus.load()` / `.save()` | `Path.read_text()` / `.write_text()` | `aiofiles.open()` |
| `CircuitBreakerState.load()` / `.save()` | `Path.read_text()` / `.write_text()` | `aiofiles.open()` |
| Tool handlers | Synchronous file I/O | `async def` with `aiofiles` |
| Inter-loop pause | `time.sleep(2)` | `await asyncio.sleep(2)` |

**Recommendation:** Keep synchronous methods as `_sync` variants for CLI mode.
Add async methods as the primary interface. Example:

```python
class RalphAgent:
    async def run(self) -> TaskResult:
        """Async entry point for platform embedding."""
        ...

    def run_sync(self) -> TaskResult:
        """Synchronous entry point for CLI mode."""
        return asyncio.run(self.run())
```

**Acceptance criteria:**
- `await RalphAgent(config).run()` works in an async context
- No `subprocess.run()` calls in the async path
- CLI mode (`__main__.py`) still works synchronously
- All file I/O uses `aiofiles` in async path

**Dependencies:** `aiofiles` added to `pyproject.toml`

---

### BLOCKING-2: Pydantic v2 Models

**Current state:** Plain `@dataclass` for `TaskInput`, `TaskResult`, `RalphStatus`,
`CircuitBreakerState`, `RalphConfig`. No runtime validation. No schema enforcement.

**Required:** Pydantic v2 `BaseModel` for all models that cross module boundaries.

**Specific changes:**

```python
# BEFORE (current)
@dataclass
class TaskInput:
    prompt: str
    fix_plan: str
    agent_instructions: str
    project_type: str
    context_files: list[str] | None = None
    constraints: list[str] | None = None
    max_turns: int = 50

# AFTER (requested)
class TaskInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt: str = Field(..., min_length=1, max_length=50_000)
    fix_plan: str = Field(default="", max_length=100_000)
    agent_instructions: str = Field(default="")
    project_type: str = Field(default="python")
    context_files: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    max_turns: int = Field(default=50, ge=1, le=200)
```

**Models to convert:**

| Model | Fields | Validation needed |
|-------|--------|-------------------|
| `TaskInput` | 7 | `prompt` non-empty, `max_turns` range |
| `TaskResult` | 6 | `status` enum, `exit_signal` bool coercion |
| `RalphStatus` | 12 | `work_type` enum, timestamps |
| `CircuitBreakerState` | 6 | State enum, `consecutive_failures` >= 0 |
| `RalphConfig` | 30 | `max_calls_per_hour` range, `claude_timeout` range |

**Acceptance criteria:**
- All 5 models are Pydantic v2 `BaseModel`
- Invalid data raises `ValidationError` (not silent defaults)
- `model_dump()` and `model_validate()` work correctly
- JSON schema available via `model_json_schema()`
- Backward-compatible: existing valid data still loads

**Dependencies:** `pydantic>=2.0` added to `pyproject.toml`

---

### BLOCKING-3: TaskPacket Conversion

**Current state:** `TaskInput.from_task_packet()` at `agent.py:101-111`:

```python
@classmethod
def from_task_packet(cls, packet: dict) -> "TaskInput":
    return cls(
        prompt=packet.get("prompt", ""),
        fix_plan=packet.get("fix_plan", ""),
        agent_instructions=packet.get("agent_instructions", ""),
        project_type=packet.get("project_type", "python"),
    )
```

This extracts 4 fields from a dict. TheStudio's TaskPacket has 20+ fields including
`IntentSpec` (goal, constraints, acceptance criteria), `complexity_index`, `risk_flags`,
`context_packs`, `loopback_count`, and `task_trust_tier`.

**Required:** Full conversion that maps TheStudio's rich context into Ralph's execution:

```python
@classmethod
def from_task_packet(
    cls,
    packet: "TaskPacketRead",           # Pydantic model, not dict
    intent: "IntentSpecRead",           # Separate model
    *,
    loopback_context: str = "",         # Verification failure details
    expert_outputs: list[str] | None = None,
) -> "TaskInput":
    """Convert TheStudio TaskPacket + IntentSpec into Ralph TaskInput.

    Maps:
    - intent.goal -> prompt (primary objective)
    - intent.constraints -> constraints
    - intent.acceptance_criteria -> appended to prompt
    - intent.non_goals -> appended to constraints as exclusions
    - packet.complexity_index -> informs max_turns scaling
    - packet.risk_flags -> prepended as safety constraints
    - packet.context_packs -> context_files
    - packet.task_trust_tier -> permission_mode hint
    - loopback_context -> prepended to prompt if non-empty
    """
```

**Acceptance criteria:**
- Accepts Pydantic models (not raw dicts)
- Maps all IntentSpec fields (goal, constraints, acceptance_criteria, non_goals)
- Incorporates risk_flags as constraints ("MUST NOT modify auth code" when `touches_auth=True`)
- Scales max_turns by complexity band (low=20, medium=30, high=50)
- Includes loopback context when provided (for retry attempts)
- Type-safe: mypy passes with strict mode

---

### BLOCKING-4: EvidenceBundle Output

**Current state:** `TaskResult.to_signal()` at `agent.py:124-134`:

```python
def to_signal(self) -> dict:
    return {
        "type": "ralph_result",
        "status": self.status,
        "exit_signal": self.exit_signal,
        "files_changed": self.files_changed,
        "progress_summary": self.progress_summary,
        "work_type": self.work_type,
    }
```

Returns a flat dict with 6 keys. TheStudio requires `EvidenceBundle`:

```python
class EvidenceBundle(BaseModel):
    taskpacket_id: UUID
    intent_version: int
    files_changed: list[str]
    test_results: str = ""
    lint_results: str = ""
    agent_summary: str = ""
    loopback_attempt: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

**Required:** Add `to_evidence_bundle()` method:

```python
class TaskResult(BaseModel):
    # ... existing fields ...

    def to_evidence_bundle(
        self,
        taskpacket_id: UUID,
        intent_version: int,
        loopback_attempt: int = 0,
    ) -> "EvidenceBundle":
        """Convert Ralph result to TheStudio EvidenceBundle.

        Maps:
        - self.files_changed -> files_changed
        - self.progress_summary -> agent_summary
        - self.work_type + raw output -> test_results, lint_results (extracted)
        """
```

**Acceptance criteria:**
- Returns a Pydantic model matching TheStudio's `EvidenceBundle` schema
- Extracts test results from raw output (when work_type=TESTING)
- Extracts lint results from raw output (when present)
- Preserves full raw output in `agent_summary`
- Includes `taskpacket_id`, `intent_version`, `loopback_attempt` from caller

---

### HIGH-1: Correlation ID Threading

**Current state:** Zero correlation tracking in the SDK. No `correlation_id` parameter
on any constructor, method, or tool call. No structured logging with trace context.

**Required:** Thread `correlation_id: UUID` through the entire execution path.

**Specific changes:**

```python
class RalphAgent:
    def __init__(
        self,
        config: RalphConfig,
        *,
        correlation_id: UUID | None = None,   # NEW
        tracer: Tracer | None = None,         # NEW (OpenTelemetry)
    ):
        self.correlation_id = correlation_id or uuid4()
        self._tracer = tracer
```

**Where correlation_id must appear:**

| Location | How |
|----------|-----|
| All log messages | `logger.info("...", extra={"correlation_id": self.correlation_id})` |
| Tool call inputs | `{"correlation_id": str(self.correlation_id)}` in tool kwargs |
| TaskResult | `correlation_id: UUID` field on result model |
| EvidenceBundle | Passed through to `to_evidence_bundle()` |
| Status updates | `status.json` includes `correlation_id` |
| Circuit breaker events | Event log includes `correlation_id` |
| OpenTelemetry spans | `span.set_attribute("ralph.correlation_id", str(self.correlation_id))` |

**Acceptance criteria:**
- `correlation_id` is a required field on `RalphAgent.__init__()` when `mode="embedded"`
- All log messages include correlation_id in structured fields
- `TaskResult` includes correlation_id
- Optional `Tracer` injection for OpenTelemetry (no hard dependency)

---

### HIGH-2: Pluggable State Backend

**Current state:** 10+ state files hardcoded to `.ralph/` filesystem:

| File | Purpose |
|------|---------|
| `.circuit_breaker_state` | CB state JSON |
| `.circuit_breaker_events` | JSONL failure log |
| `.call_count` | Hourly API counter |
| `.last_reset` | Counter reset timestamp |
| `.claude_session_id` | Session persistence |
| `status.json` | Loop status |
| `metrics/YYYY-MM.jsonl` | Monthly metrics |
| `fix_plan.md` | Task queue |

In TheStudio, all state lives in PostgreSQL (via async SQLAlchemy) or Redis. File-based
state breaks in multi-instance, container, and Temporal activity contexts.

**Required:** Abstract state operations behind a `Protocol`:

```python
class RalphStateBackend(Protocol):
    """Backend for Ralph state persistence."""

    async def load_status(self) -> RalphStatus: ...
    async def save_status(self, status: RalphStatus) -> None: ...

    async def load_circuit_breaker(self) -> CircuitBreakerState: ...
    async def save_circuit_breaker(self, state: CircuitBreakerState) -> None: ...
    async def record_circuit_event(self, event: CircuitBreakerEvent) -> None: ...

    async def get_call_count(self) -> int: ...
    async def increment_call_count(self) -> int: ...
    async def reset_call_count(self) -> None: ...

    async def load_session_id(self) -> str | None: ...
    async def save_session_id(self, session_id: str) -> None: ...
    async def clear_session_id(self) -> None: ...

    async def record_metric(self, metric: LoopMetric) -> None: ...
```

**Provide two implementations:**

1. **`FileStateBackend`** (default) — current behavior, reads/writes `.ralph/` files.
   Used in CLI mode. No new dependencies.

2. **`NullStateBackend`** — in-memory only, no persistence. Used for testing and
   stateless environments where the platform manages state externally.

TheStudio will implement a third backend (`PostgresStateBackend`) on our side using
this protocol.

**Acceptance criteria:**
- `RalphAgent.__init__()` accepts `state_backend: RalphStateBackend`
- Default is `FileStateBackend` (backward compatible)
- All file I/O in agent loop routes through the backend
- No direct `Path.read_text()` or `Path.write_text()` in agent.py
- `NullStateBackend` provided for testing

---

### HIGH-3: Active Circuit Breaker

**Current state:** SDK's `CircuitBreakerState` (`status.py:91-172`) is a passive data
model. It has `trip()`, `half_open()`, `close()`, and `reset()` methods but **the agent
loop never calls them**. The `check_rate_limit()` method reads state and returns a bool
but doesn't trigger transitions.

Meanwhile, the bash implementation (`lib/circuit_breaker.sh`) has full active management:
sliding window failure detection, automatic OPEN on threshold, cooldown-based HALF_OPEN
transition, and success-based CLOSED transition.

**Required:** Port the bash circuit breaker logic to the SDK:

```python
class CircuitBreaker:
    """Active circuit breaker with automatic state transitions.

    State machine:
        CLOSED --[failures >= threshold in window]--> OPEN
        OPEN   --[cooldown elapsed]-------------------> HALF_OPEN
        HALF_OPEN --[success]-------------------------> CLOSED
        HALF_OPEN --[failure]-------------------------> OPEN
    """

    def __init__(
        self,
        backend: RalphStateBackend,
        *,
        failure_threshold: int = 5,
        window_minutes: int = 30,
        cooldown_minutes: int = 30,
        no_progress_threshold: int = 3,
    ): ...

    async def record_success(self) -> None:
        """Record successful iteration. Transition HALF_OPEN -> CLOSED."""

    async def record_failure(self, reason: str) -> None:
        """Record failure. May transition CLOSED -> OPEN."""

    async def record_no_progress(self) -> None:
        """Record zero files + zero tasks. May trip after threshold."""

    async def can_proceed(self) -> bool:
        """Check if loop should continue. Handles OPEN -> HALF_OPEN on cooldown."""

    async def get_state(self) -> CircuitBreakerState:
        """Return current state snapshot."""
```

**Acceptance criteria:**
- State transitions happen automatically based on `record_success/failure/no_progress`
- `can_proceed()` handles cooldown check (OPEN -> HALF_OPEN after cooldown)
- Sliding window: only failures within `window_minutes` count toward threshold
- No-progress detection: `no_progress_threshold` consecutive zero-work loops trip the breaker
- All state changes persisted via `RalphStateBackend`
- Matches bash behavior from `lib/circuit_breaker.sh`

---

### HIGH-4: Structured Response Parsing

**Current state:** `_extract_ralph_status()` (`agent.py:454-485`) uses 6 regex patterns
to parse a `---RALPH_STATUS---` text block from Claude's raw output:

```python
patterns = {
    "status": r"STATUS:\s*(.+?)(?:\n|$)",
    "exit_signal": r"EXIT_SIGNAL:\s*(.+?)(?:\n|$)",
    "tasks_completed": r"TASKS_COMPLETED:\s*(.+?)(?:\n|$)",
    "files_modified": r"FILES_MODIFIED:\s*(.+?)(?:\n|$)",
    "progress_summary": r"PROGRESS_SUMMARY:\s*(.+?)(?:\n|$)",
    "work_type": r"WORK_TYPE:\s*(.+?)(?:\n|$)",
}
```

Known bugs:
- JSON-escaped `\n` in JSONL output breaks newline matching (documented as STREAM-3)
- `EXIT_SIGNAL` parsing is case-sensitive: `"True"` and `"TRUE"` don't match
- Multiple `result` objects in JSONL: only the last one is used (no validation)
- No schema version: any format change silently breaks parsing

**Required:** Define a versioned Pydantic schema for the status block:

```python
class RalphStatusBlock(BaseModel):
    """Structured output schema for Ralph agent responses.

    Version field enables forward-compatible parsing.
    """
    model_config = ConfigDict(populate_by_name=True)

    version: int = Field(default=1, ge=1)
    status: RalphLoopStatus           # enum: IN_PROGRESS, COMPLETE, BLOCKED
    exit_signal: bool = False
    tasks_completed: int = Field(default=0, ge=0)
    files_modified: int = Field(default=0, ge=0)
    progress_summary: str = ""
    work_type: WorkType = WorkType.IMPLEMENTATION  # enum
    tests_status: TestsStatus = TestsStatus.NOT_RUN  # enum

class RalphLoopStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"

class WorkType(StrEnum):
    IMPLEMENTATION = "IMPLEMENTATION"
    TESTING = "TESTING"
    DOCUMENTATION = "DOCUMENTATION"
    REFACTORING = "REFACTORING"

class TestsStatus(StrEnum):
    PASSING = "PASSING"
    FAILING = "FAILING"
    DEFERRED = "DEFERRED"
    NOT_RUN = "NOT_RUN"
```

**Parsing strategy:**

```python
def parse_ralph_status(raw_output: str) -> RalphStatusBlock:
    """Parse status from agent output.

    Strategy (ordered by reliability):
    1. JSON path: find ```json block with "version" key -> validate with Pydantic
    2. JSONL path: find {"type": "result"} line -> extract status fields
    3. Text fallback: regex extraction (current behavior, for backward compat)

    Raises ValidationError if no strategy produces valid output.
    """
```

**Acceptance criteria:**
- Agent prompt updated to request JSON output in a fenced code block
- Pydantic validation catches malformed status (not silent defaults)
- Version field enables future schema evolution
- All enums enforce valid values
- Text fallback preserved for backward compatibility with bash loop
- `EXIT_SIGNAL` coercion handles `true/True/TRUE/yes/1` uniformly

---

## 5. Dependency Changes

Ralph SDK `pyproject.toml` additions:

```toml
[project]
dependencies = [
    "pydantic>=2.0,<3.0",
    "aiofiles>=24.0",
]

[project.optional-dependencies]
# OpenTelemetry is optional — only needed for platform embedding
tracing = [
    "opentelemetry-api>=1.20",
]
```

No new dependencies for CLI mode beyond `pydantic` and `aiofiles`.

---

## 6. Migration Path

### Phase 1: Non-Breaking Foundation (v1.4.0)

Add new code alongside existing. No breaking changes.

- Add Pydantic models as parallel classes (`TaskInputV2`, etc.)
- Add `RalphStateBackend` protocol + `FileStateBackend` + `NullStateBackend`
- Add `CircuitBreaker` active class (wraps existing `CircuitBreakerState`)
- Add `RalphStatusBlock` schema + `parse_ralph_status()`
- Add `correlation_id` parameter to `RalphAgent.__init__()` (optional, defaults to `uuid4()`)
- All existing tests continue to pass

### Phase 2: Async Layer (v1.5.0)

Add async methods alongside sync.

- Add `async def run()`, `async def run_iteration()`, etc.
- `run_sync()` wraps async with `asyncio.run()`
- CLI mode (`__main__.py`) uses `run_sync()`
- Add `aiofiles` dependency

### Phase 3: V2 Promotion (v2.0.0)

Promote new models as default. Deprecate old.

- `TaskInput` becomes the Pydantic version (old becomes `TaskInputLegacy`)
- `from_task_packet()` accepts Pydantic models (old dict version deprecated)
- `to_evidence_bundle()` added to `TaskResult`
- Default `RalphAgent` constructor uses async interface
- Bump SDK version to 2.0.0

### Backward Compatibility

| Consumer | Impact |
|----------|--------|
| Ralph CLI (`ralph_loop.sh`) | Uses `run_sync()` — no change |
| Ralph CLI (`__main__.py`) | Uses `run_sync()` — no change |
| TheStudio embedding | Uses `await run()` — new path |
| Existing tests | Pass on v1.4.0 and v1.5.0; some may need updates for v2.0.0 |

---

## 7. What TheStudio Will Build (Not Requested from Ralph)

For clarity, these are TheStudio's responsibilities — not part of this RFC:

| Component | Owner | Description |
|-----------|-------|-------------|
| `PostgresStateBackend` | TheStudio | Implements `RalphStateBackend` with async SQLAlchemy |
| Temporal activity wrapper | TheStudio | Wraps `RalphAgent.run()` in Temporal activity with heartbeat |
| Model Gateway routing | TheStudio | Maps Ralph's complexity assessment to `ModelClass` enum |
| Budget enforcement | TheStudio | Wraps Ralph execution with `PipelineBudget.consume()` |
| Loopback orchestration | TheStudio | Calls `handle_loopback()` with `VerificationResult` |
| OpenTelemetry setup | TheStudio | Provides `Tracer` instance to `RalphAgent.__init__()` |
| Dashboard integration | TheStudio | Exposes Ralph status via SSE stream |

---

## 8. Verification

### How We'll Know It Works

| Change | Verification |
|--------|-------------|
| BLOCKING-1 (Async) | `pytest -k async` passes; `await RalphAgent(config).run()` in async test |
| BLOCKING-2 (Pydantic) | `TaskInput(prompt="")` raises `ValidationError`; `model_json_schema()` returns valid JSON Schema |
| BLOCKING-3 (TaskPacket) | `from_task_packet(mock_taskpacket, mock_intent)` produces TaskInput with all fields mapped |
| BLOCKING-4 (EvidenceBundle) | `result.to_evidence_bundle(...)` returns valid EvidenceBundle; round-trips through JSON |
| HIGH-1 (Correlation) | All log messages in test run include `correlation_id` field |
| HIGH-2 (State Backend) | Full test suite passes with `NullStateBackend`; `FileStateBackend` matches current behavior |
| HIGH-3 (Circuit Breaker) | 5 failures in 30min window triggers OPEN; cooldown triggers HALF_OPEN; success triggers CLOSED |
| HIGH-4 (Structured Parse) | JSON status block parsed correctly; malformed input raises `ValidationError`; text fallback works |

### Integration Test (TheStudio side, post-RFC)

```python
async def test_ralph_thestudio_integration():
    """End-to-end: TaskPacket -> Ralph -> EvidenceBundle."""
    agent = RalphAgent(
        config=RalphConfig.load(),
        correlation_id=uuid4(),
        state_backend=NullStateBackend(),
    )
    task_input = TaskInput.from_task_packet(
        packet=mock_taskpacket(),
        intent=mock_intent_spec(),
    )
    result = await agent.run_iteration(task_input)
    evidence = result.to_evidence_bundle(
        taskpacket_id=mock_taskpacket().id,
        intent_version=1,
    )
    assert isinstance(evidence.files_changed, list)
    assert evidence.taskpacket_id == mock_taskpacket().id
    assert evidence.agent_summary != ""
```

---

## 9. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | Should Ralph SDK depend on TheStudio's Pydantic models directly, or define its own compatible models? | If own models: TheStudio writes the mapper. If shared: Ralph takes a dependency on TheStudio. **Recommendation: Own models + TheStudio mapper.** |
| 2 | Should the async rewrite use `anyio` instead of raw `asyncio` for Trio compatibility? | TheStudio uses `asyncio` exclusively. **Recommendation: `asyncio` only.** |
| 3 | Should `RalphStateBackend` include task queue operations (`load_fix_plan`, `mark_task_complete`)? | TheStudio manages tasks via TaskPacket, not fix_plan.md. **Recommendation: Exclude task queue from backend; TheStudio bypasses fix_plan entirely.** |
| 4 | Should Ralph's agent prompt template be configurable for TheStudio's `DeveloperRoleConfig.system_prompt_template`? | Currently hardcoded in `.ralph/PROMPT.md`. **Recommendation: Accept `system_prompt` override in `run_iteration()`.** |

---

## 10. Timeline

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | Foundation | Pydantic models (BLOCKING-2), State backend protocol (HIGH-2), Structured parsing (HIGH-4) |
| 2 | Async + Core | Async SDK (BLOCKING-1), Active circuit breaker (HIGH-3), Correlation ID (HIGH-1) |
| 3 | Integration | TaskPacket conversion (BLOCKING-3), EvidenceBundle output (BLOCKING-4), Integration tests |

**Total: 3 weeks** to Ralph SDK v2.0.0-rc1.

---

## 11. References

| Document | Location |
|----------|----------|
| TheStudio Agent Framework | `src/agent/framework.py` |
| TheStudio Primary Agent | `src/agent/primary_agent.py` |
| TheStudio Evidence Model | `src/agent/evidence.py` |
| TheStudio Container Protocol | `src/agent/container_protocol.py` |
| TheStudio Observability | `src/observability/conventions.py` |
| Ralph SDK Agent | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\agent.py` |
| Ralph SDK Config | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\config.py` |
| Ralph SDK Status | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\status.py` |
| Ralph SDK Tools | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\tools.py` |
| Ralph Circuit Breaker (bash) | `C:\cursor\ralph\ralph-claude-code\lib\circuit_breaker.sh` |
| Ralph SDK Migration Strategy | `C:\cursor\ralph\ralph-claude-code\docs\sdk-migration-strategy.md` |
| Anthropic: Effective Harnesses | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents |
| 2026 Agentic Coding Trends | https://resources.anthropic.com/2026-agentic-coding-trends-report |
