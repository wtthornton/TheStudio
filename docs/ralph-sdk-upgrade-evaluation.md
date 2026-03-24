# Ralph SDK Upgrade Evaluation

**Date:** 2026-03-23 (gap analysis updated 2026-03-24)
**Current SDK Version:** 2.0.2 (vendored)
**Current CLI Version:** 2.2.0 (WSL)
**Evaluator:** TheStudio team

---

## Executive Summary

Ralph v2.2.0 shipped today with 8 production bug fixes and v2.1.0 features — all
in the **bash CLI only**. The Python SDK (`ralph_sdk`) is unchanged at v2.0.2.
There is no SDK upgrade available.

However, a feature gap analysis reveals **12 capabilities** present in the bash CLI
that the SDK lacks, plus **11 integration pain points** in TheStudio's current
bridge layer. This document captures what TheStudio needs from Ralph to improve
quality, functionality, and speed — organized as concrete SDK enhancement requests.

### Gap Status Summary (2026-03-24)

| Section | Feature | Priority | Status |
|---------|---------|---------|--------|
| 1.1 | Stall detection | P0 | ✅ Implemented (vendored) |
| 1.2 | Progressive context loading | P0 | ✅ Implemented (vendored) |
| 1.3 | Task decomposition detection | P1 | ✅ Implemented (vendored) |
| 1.4 | Cost tracking + budget guardrails | P1 | ✅ Implemented (vendored) |
| 1.5 | Dynamic model routing | P1 | ❌ **NOT IMPLEMENTED** — see §1.5 |
| 1.6 | Completion indicator decay | P1 | ✅ Implemented (vendored) |
| 1.7 | Error categorization | P2 | ❌ **NOT IMPLEMENTED** — see §1.7 |
| 1.8 | Prompt cache split | P2 | ❌ **NOT IMPLEMENTED** — see §1.8 |
| 1.9 | Metrics JSONL collection | P2 | ⚠️ Partial (cost only) — see §1.9 |
| 1.10 | Session lifecycle / Continue-As-New | P2 | ⚠️ Partial (TTL only) — see §1.10 |
| 1.11 | Adaptive timeout | P3 | 🔵 Deferred |
| 1.12 | Permission denial detection | P3 | 🔵 Deferred |
| 2.1 | Structured `files_changed` | P1 | ✅ Implemented (vendored) |
| 2.2 | Cancel semantics / `CancelResult` | P1 | ✅ Documented + wired (activities.py) |
| 2.3 | Structured heartbeat / `ProgressSnapshot` | P2 | ⚠️ Partial (plain string) — see §2.3 |
| 2.4 | Token-based rate limiting | P2 | 🔵 Deferred |

**Remaining open gaps (with implementation paths):** §1.5, §1.7, §1.8, §1.9, §1.10, §2.3 — all documented below.

---

## 1. SDK Feature Gaps (CLI Has, SDK Doesn't)

These features exist in the bash CLI (v2.2.0) but are missing from the Python SDK.
Each is a request for the Ralph SDK to implement.

### 1.1 Stall Detection (Priority: P0)

**What:** The CLI detects three stuck states; the SDK detects none.

| Stall Type | CLI Implementation | SDK Gap |
|---|---|---|
| Fast-trip (broken invocations) | `MAX_CONSECUTIVE_FAST_FAILURES=3` — trips CB on 0-tool runs <30s | SDK retries indefinitely on broken tool access |
| Deferred-test stall | `CB_MAX_DEFERRED_TESTS=5` — trips CB if tests stay deferred >5 loops | SDK has no awareness of `TESTS_STATUS: DEFERRED` |
| Consecutive timeout | `MAX_CONSECUTIVE_TIMEOUTS=5` — trips CB on repeated timeouts | SDK treats each timeout independently |

**Why it matters:** TheStudio's epic-boundary QA strategy (`TESTS_STATUS: DEFERRED`) means
every mid-epic loop marks tests deferred. If Ralph loops without making progress while
deferring tests, it burns budget silently. LOGFIX-6 exists because this happened in production.

**Request:** Add `FastTripDetector` and `StallDetector` to `circuit_breaker.py`. Accept
configurable thresholds: `fast_trip_max` (default 3), `deferred_stall_max` (default 5),
`consecutive_timeout_max` (default 5).

---

### 1.2 Progressive Context Loading (Priority: P0)

**What:** CLI's `lib/context_management.sh` trims `fix_plan.md` to only the current
epic section + next N unchecked items. SDK loads the entire plan every iteration.

**Why it matters:** TheStudio fix plans can span multiple epics with 50+ tasks.
Loading all of them wastes context window tokens and confuses the agent with
irrelevant completed work.

**Request:** Add `ContextManager` to the SDK with:
- `build_progressive_context(plan: str, max_items: int = 10) -> str` — returns
  trimmed plan showing current section + N unchecked items
- `estimate_tokens(text: str) -> int` — 4-char heuristic for budget awareness
- Summary markers: `(15 completed items above)` for elided sections

---

### 1.3 Task Decomposition Detection (Priority: P1)

**What:** CLI detects oversized tasks via 4-factor heuristic: file count >= 5,
previous timeout, complexity >= 4, consecutive no-progress >= 3. SDK has no
equivalent.

**Why it matters:** TheStudio routes tasks by complexity band but only at the
intake level. Once Ralph is running, there's no detection that a task is too
large for a single loop iteration.

**Request:** Add `detect_decomposition_needed(status: RalphStatus, config: RalphConfig) -> DecompositionHint`
returning `{"decompose": bool, "reasons": list[str], "recommendation": str}`.

---

### 1.4 Cost Tracking and Budget Guardrails (Priority: P1)

**What:** CLI tracks per-model token costs (`lib/tracing.sh` lines 185-284),
enforces budget alerts at configurable thresholds, and provides cost dashboards.
SDK has no cost awareness.

**Why it matters:** TheStudio has `BudgetEnforcer` but it estimates cost from
`duration_seconds * cost_per_minute` (fragile). Accurate per-token cost tracking
from the SDK would replace this heuristic. Additionally, CLI issue #223 confirms
the rate limiter counts invocations, not tokens — budget accuracy needs improvement.

**Request:** Add `CostTracker` to the SDK:
- `record_iteration_cost(model: str, input_tokens: int, output_tokens: int)` — per-model pricing
- `get_session_cost() -> float` — cumulative USD
- `check_budget(budget_usd: float, alert_threshold: float = 0.8) -> BudgetStatus`
- Per-model rates as config (default to March 2026 Claude pricing)

---

### 1.5 Dynamic Model Routing (Priority: P1)

**What:** CLI's `lib/complexity.sh` routes trivial tasks to Haiku, standard to
Sonnet, and complex/architectural to Opus. SDK uses a static model from config.

**Why it matters:** TheStudio processes a mix of task complexities. Routing a
one-line docstring fix to Opus wastes ~10x the cost vs Haiku. The CLI's
5-level classifier (TRIVIAL through ARCHITECTURAL) with retry escalation
would directly reduce TheStudio's per-task costs.

**Request:** Add `select_model(task: str, complexity: ComplexityBand, retry_count: int = 0) -> str`
to the SDK config layer. Support per-band model overrides via config.

#### Current State (2026-03-24)

**Gap status: NOT IMPLEMENTED.**

`RalphConfig.model` is a static string (default `"claude-sonnet-4-20250514"`).
`build_ralph_config()` in `ralph_bridge.py` does not use the TaskPacket's complexity
band to select a model — the `model_id` parameter is explicitly noted as unused in Slice 1
(comment at `ralph_bridge.py:242`). `COMPLEXITY_MAX_TURNS` in `converters.py:86–91` maps
complexity to max turn counts but not to models. `CostTracker` accumulates per-model costs
but does not route based on them.

**What exists today:**
- `ComplexityBand` enum in `vendor/ralph-sdk/converters.py` (TRIVIAL/LOW/MEDIUM/HIGH/ARCHITECTURAL)
- `COMPLEXITY_MAX_TURNS` map: `{TRIVIAL: 20, LOW: 30, MEDIUM: 30, HIGH: 50, ARCHITECTURAL: 50}`
- `ATTR_RALPH_MODEL` in `src/observability/conventions.py` (telemetry only — records the model used but does not influence selection)
- `CostTracker.record_iteration_cost(model, input_tokens, output_tokens)` — accumulates cost but routing is not wired

**What is missing:**
- `ModelSelector` or `select_model()` function in the SDK
- Per-band model override map in `RalphConfig` (e.g. `model_per_band: dict[ComplexityBand, str]`)
- Retry escalation logic (escalate to a more capable model after N retries)
- `build_ralph_config()` in `ralph_bridge.py` passing TaskPacket complexity to model selection

#### Implementation Path

1. Add to `vendor/ralph-sdk/config.py`:
   ```python
   model_per_band: dict[str, str] = Field(default_factory=lambda: {
       "TRIVIAL": "claude-haiku-4-20250514",
       "LOW": "claude-haiku-4-20250514",
       "MEDIUM": "claude-sonnet-4-20250514",
       "HIGH": "claude-sonnet-4-20250514",
       "ARCHITECTURAL": "claude-opus-4-20250514",
   })
   retry_escalation_threshold: int = 2  # escalate model after N retries
   ```

2. Add `select_model(complexity: str, retry_count: int, config: RalphConfig) -> str` to
   `vendor/ralph-sdk/converters.py` or a new `model_routing.py`.

3. Wire in `src/agent/ralph_bridge.py`'s `build_ralph_config()`: pass
   `task_packet.complexity_band` and set `config.model = select_model(...)`.

4. Emit `ATTR_RALPH_MODEL` span attribute after selection so routing decisions are
   observable in Tempo/Jaeger.

---

### 1.6 Completion Indicator Decay (Priority: P1)

**What:** CLI resets `completion_indicators` to `[]` when productive work occurs
(files modified or tasks completed) with `exit_signal=false`. SDK's dual-condition
exit gate doesn't decay stale indicators.

**Why it matters:** Without decay, a false "done" signal early in a multi-loop
run can combine with a later legitimate "done" to trigger premature exit before
all tasks are actually complete.

**Request:** In `agent.py`, reset the completion indicator count when
`status.exit_signal == False` and progress was detected (files changed > 0 or
task completed). This matches the CLI fix at `ralph_loop.sh:951-953`.

---

### 1.7 Error Categorization (Priority: P2)

**What:** CLI categorizes errors into expected-scope (permission denials for
built-in tools) vs system errors (crashes, hangs). SDK treats all errors
generically.

**Why it matters:** TheStudio's loopback logic needs to know whether a failure
is retryable (permission denial → adjust tools) vs terminal (crash → circuit
break). Generic error handling causes unnecessary retries on terminal failures
and premature circuit breaks on fixable issues.

**Request:** Add `ErrorCategory` enum: `PERMISSION_DENIED`, `TIMEOUT`,
`PARSE_FAILURE`, `TOOL_UNAVAILABLE`, `SYSTEM_CRASH`, `UNKNOWN`. Have
`parsing.py` return the category alongside the status.

#### Current State (2026-03-24)

**Gap status: NOT IMPLEMENTED.**

`RalphStatus.error` is a raw `str`. `RalphLoopStatus` has an `ERROR` variant but
provides no sub-typing. `parse_ralph_status()` in `parsing.py` uses a 3-strategy
chain (JSON block → JSONL → text fallback) but returns a flat status with an
unstructured error string. The `CircuitBreaker` in `circuit_breaker.py` detects
"same error repeated" by string comparison, which is fragile.

`src/agent/primary_agent.py`'s loopback handler receives only `evidence.error_summary`
(a freeform string) to decide whether to retry. There is no code path that distinguishes
a permission denial (fixable by adjusting allowed tools) from a SYSTEM_CRASH (should
trip the circuit breaker immediately).

**What exists today:**
- `RalphLoopStatus` enum: `IN_PROGRESS`, `COMPLETED`, `ERROR`, `TIMEOUT`, `DRY_RUN`
- `TaskResult.error: str | None` (unstructured)
- `CircuitBreaker`: sliding window on failure count — does not use error type
- `parsing.py`: detects `STATUS: BLOCKED` text; no other error classification

**What is missing:**
- `ErrorCategory` enum
- Pattern-based classifier (regex on error text → category)
- `recoverability: bool` flag to guide loopback vs. circuit-break decisions
- Circuit breaker integration: fast-trip on `SYSTEM_CRASH`, hold-off on `PERMISSION_DENIED`

#### Implementation Path

1. Add to `vendor/ralph-sdk/` (new file `error_categories.py`):
   ```python
   from enum import Enum

   class ErrorCategory(str, Enum):
       PERMISSION_DENIED = "permission_denied"
       TIMEOUT = "timeout"
       PARSE_FAILURE = "parse_failure"
       TOOL_UNAVAILABLE = "tool_unavailable"
       SYSTEM_CRASH = "system_crash"
       RATE_LIMITED = "rate_limited"
       UNKNOWN = "unknown"

   RECOVERABLE = {ErrorCategory.PERMISSION_DENIED, ErrorCategory.RATE_LIMITED}
   TERMINAL    = {ErrorCategory.SYSTEM_CRASH, ErrorCategory.PARSE_FAILURE}
   ```

2. Update `parsing.py`: after determining `RalphLoopStatus.ERROR`, run a
   pattern-match pass on the error string to set `error_category`.

3. In `circuit_breaker.py`: fast-trip (open immediately) on `TERMINAL` categories;
   apply normal sliding window for `RECOVERABLE` categories.

4. In `ralph_bridge.py`'s `ralph_result_to_evidence()`: include `error_category`
   in the evidence bundle so TheStudio's loopback handler can make typed decisions.

---

### 1.8 Prompt Cache Optimization (Priority: P2)

**What:** CLI's `ralph_build_cacheable_prompt()` separates the prompt into a
stable prefix (identity, build instructions, tool permissions) and dynamic
suffix (loop count, progress, current task). This maximizes Claude's prompt
cache hits.

**Why it matters:** Prompt caching can reduce input token costs by up to 90%
for repeated prefixes. TheStudio's multi-loop runs send similar prompts each
iteration — cache optimization has a direct dollar impact.

**Request:** Add `build_prompt(task: str, context: str, config: RalphConfig) -> PromptParts`
where `PromptParts` has `stable_prefix: str` and `dynamic_suffix: str`. Let
TheStudio's bridge layer control the split point.

#### Current State (2026-03-24)

**Gap status: NOT IMPLEMENTED.**

`agent.py`'s `_build_iteration_prompt()` (lines 634–648) concatenates all
prompt components linearly into a single string. `build_progressive_context()`
trims the fix_plan but does not separate the output into a cacheable stable
prefix and a dynamic suffix. The `loopback_context` from `ralph_bridge.py:108`
is injected at the prompt prefix but is itself dynamic (it includes loop state).

No `PromptParts` dataclass exists. The SDK does not expose any control over
cache-boundary placement to calling code.

**What exists today:**
- `build_progressive_context()` in `context_management.py`: trims plan to current section + N items
- `task_input.agent_instructions` field on `RalphInput`: a separate string that is mixed in at build time
- `loopback_context` string injected at start of prompt in `ralph_bridge.py`

**What is missing:**
- `PromptParts(stable_prefix: str, dynamic_suffix: str)` dataclass
- `build_prompt(task, context, config) -> PromptParts` function
- Stable prefix definition: identity block + CLAUDE.md contents + tool permissions (changes rarely)
- Dynamic suffix definition: loop count, current task excerpt, recent progress summary
- Cache hit/miss tracking (requires SDK-side instrumentation)

#### Implementation Path

1. Add to `vendor/ralph-sdk/` (new file `prompts.py`):
   ```python
   from dataclasses import dataclass

   @dataclass
   class PromptParts:
       stable_prefix: str   # identity + instructions + tool permissions
       dynamic_suffix: str  # loop N, current task, recent progress

   def build_prompt(
       agent_instructions: str,
       task_description: str,
       loop_count: int,
       progress_summary: str,
   ) -> PromptParts:
       stable_prefix = agent_instructions  # changes only with config updates
       dynamic_suffix = (
           f"## Loop {loop_count}\n\n"
           f"**Current task:** {task_description}\n\n"
           f"{progress_summary}"
       )
       return PromptParts(stable_prefix=stable_prefix, dynamic_suffix=dynamic_suffix)
   ```

2. Update `agent.py`'s `_build_iteration_prompt()` to use `build_prompt()` and
   concatenate `stable_prefix + "\n\n" + dynamic_suffix` for the actual API call.

3. Instrument with `ATTR_RALPH_CACHE_HIT` in `src/observability/conventions.py`
   once the Anthropic SDK exposes cache usage in its response metadata.

---

### 1.9 Metrics Collection (Priority: P2)

**What:** CLI records per-iteration metrics to monthly JSONL files
(`lib/metrics.sh`) and provides aggregated dashboards (success rate, avg loops,
CB trips, cost per iteration). SDK collects no metrics.

**Why it matters:** TheStudio's observability (Epic 43, Story 43.14) added
OTEL spans but lacks structured loop-level metrics. For the Analytics &
Learning epic (Epic 39), TheStudio will need to query historical Ralph
performance — this data doesn't exist today.

**Request:** Add `MetricsCollector` protocol with `record(iteration: IterationMetric)`
and `query(period: str) -> list[IterationMetric]`. Ship a `NullMetricsCollector`
and a `JsonlMetricsCollector` (like the CLI's monthly files).

#### Current State (2026-03-24)

**Gap status: ~50% IMPLEMENTED (cost tracking exists; JSONL metrics do not).**

`CostTracker` in `vendor/ralph-sdk/cost_tracking.py` records per-model token counts
and computes session cost in USD. `TaskResult` captures `duration_seconds`,
`tokens_in`, `tokens_out`, and `loop_count`. OTEL spans (Story 43.14) emit
`ATTR_RALPH_*` attributes at the run and iteration level. However, there is no
persistent, queryable JSONL log of per-iteration metrics, and `ralph_state.py`
stores only `status.json` (point-in-time state), not an append-only history.

**What exists today:**
- `CostTracker`: `record_iteration_cost(model, input_tokens, output_tokens)` → `session_cost_usd`
- `TaskResult`: `duration_seconds`, `tokens_in`, `tokens_out`, `loop_count`, `exit_code`
- `RalphStatus`: `loop_count`, `work_type`, `completed_task`, `tests_status`, `circuit_breaker_state`
- OTEL span attributes: `ATTR_RALPH_TOKENS_IN`, `ATTR_RALPH_TOKENS_OUT`, `ATTR_RALPH_COST_USD`,
  `ATTR_RALPH_DURATION_MS`, `ATTR_RALPH_MODEL` (emit once per run, not per iteration)

**What is missing:**
- `IterationMetric` dataclass (timestamp, loop, work_type, files_changed, tests_status,
  duration_ms, tokens_in, tokens_out, cost_usd, error_category, circuit_breaker_state)
- `MetricsCollector` protocol with `record()` / `query()` / `summarize()`
- `JsonlMetricsCollector`: append-only log to monthly files (`YYYY-MM.jsonl`)
- `NullMetricsCollector`: no-op default for environments without persistence
- Epic 39 Analytics queries (`throughput`, `bottlenecks`, `cost_per_task`) cannot
  be answered without this per-iteration history

#### Implementation Path

1. Add to `vendor/ralph-sdk/` (new file `metrics.py`):
   ```python
   from typing import Protocol, runtime_checkable
   from pydantic import BaseModel
   from datetime import datetime

   class IterationMetric(BaseModel):
       timestamp: datetime
       session_id: str
       loop: int
       work_type: str
       files_changed: int
       tests_status: str
       duration_ms: int
       tokens_in: int
       tokens_out: int
       cost_usd: float
       error_category: str | None = None
       circuit_breaker_state: str = "CLOSED"
       exit_signal: bool = False

   @runtime_checkable
   class MetricsCollector(Protocol):
       def record(self, metric: IterationMetric) -> None: ...
       def query(self, period: str) -> list[IterationMetric]: ...

   class NullMetricsCollector:
       def record(self, metric: IterationMetric) -> None: pass
       def query(self, period: str) -> list[IterationMetric]: return []

   class JsonlMetricsCollector:
       """Appends one JSON line per iteration to ~/.ralph/metrics/YYYY-MM.jsonl"""
       ...
   ```

2. Add `metrics_collector: MetricsCollector = NullMetricsCollector()` to `RalphConfig`.

3. In `agent.py`'s `run_iteration()`: after each completed iteration, call
   `config.metrics_collector.record(IterationMetric(...))`.

4. In `src/agent/ralph_bridge.py`'s `build_ralph_config()`: wire in a
   `JsonlMetricsCollector` (or a future `PostgresMetricsCollector` for Epic 39).

---

### 1.10 Session Lifecycle Management (Priority: P2)

**What:** CLI tracks session history, enforces expiry (`CLAUDE_SESSION_EXPIRY_HOURS=24`),
and implements Continue-As-New for long sessions (CTXMGMT-3, in progress). SDK
persists session IDs but never expires or rotates them.

**Why it matters:** TheStudio's `clear_session_if_stale(ttl_seconds=7200)` in
`ralph_state.py` is a TheStudio-side workaround for this SDK gap. If the SDK
managed session lifecycle natively, the workaround could be removed and
session rotation would be consistent across all SDK consumers.

**Request:**
- Add `session_expiry_hours: int = 24` to `RalphConfig`
- Implement automatic session rotation when expiry is reached
- Track session history (previous session IDs with timestamps)
- Implement Continue-As-New: reset session after N iterations, carrying only
  essential state (current task, progress summary, key findings)

#### Current State (2026-03-24)

**Gap status: ~60% IMPLEMENTED (TTL exists; Continue-As-New and session history do not).**

`RalphConfig.session_expiry_hours` (default 24, max 168) exists in
`vendor/ralph-sdk/config.py`. `PostgresStateBackend` in `ralph_state.py`
stores `session_id` with `updated_at TIMESTAMPTZ` and implements
`clear_session_if_stale(ttl_seconds)` which deletes the row when the TTL is
exceeded, forcing a new session on the next run. `agent.py:747–753` loads
and saves the session ID on each run.

However, Temporal Continue-As-New (resetting the workflow and carrying forward
essential state after N iterations) is not integrated. There is no parent/child
session linkage in `ralph_agent_state` table, no multi-session aggregation, and
`clear_session_if_stale()` is called by TheStudio's code rather than the SDK itself.

**What exists today:**
- `RalphConfig.session_expiry_hours: int = 24` (config field exists)
- `RalphConfig.session_continuity: bool = True` (enables session ID reuse)
- `PostgresStateBackend.clear_session_if_stale(ttl_seconds)` in `ralph_state.py:221–276`
- `agent.py`: `_load_session()` / `_save_session()` pair
- `ralph_agent_state` table: `session_id TEXT`, `updated_at TIMESTAMPTZ`

**What is missing:**
- SDK-native session expiry check (currently TheStudio must call `clear_session_if_stale()` manually)
- `parent_session_id` column in `ralph_agent_state` for session chain tracing
- Continue-As-New: carry `current_task`, `progress_summary`, `key_findings` into new session
- `max_iterations_before_rotation: int` config field
- Session history query: `list_sessions(task_id)` → `[{session_id, created_at, loop_count, outcome}]`
- Temporal integration: signal Temporal workflow to schedule a new activity with fresh session

#### Implementation Path

1. Add to `RalphConfig` in `vendor/ralph-sdk/config.py`:
   ```python
   max_iterations_before_rotation: int = 50  # trigger Continue-As-New after N loops
   ```

2. In `agent.py`'s main `run()` loop: after each iteration, check if
   `loop_count >= config.max_iterations_before_rotation`. If so, call
   `_rotate_session(carry_forward: RotationPayload)` which:
   - Saves `{current_task, progress_summary, key_findings}` as the seed for the new session
   - Clears the current session ID
   - Emits a `SESSION_ROTATED` event (observable via OTEL span attribute)

3. Add `parent_session_id TEXT` column to migration in
   `src/db/migrations/048_ralph_agent_state.py` (or a new migration `052_ralph_session_history.py`).

4. Temporal integration in `src/workflow/activities.py`: detect the `SESSION_ROTATED`
   event from `TaskResult` and re-schedule `_implement_ralph_with_heartbeat()` as a
   new activity invocation (Continue-As-New pattern), carrying rotation payload forward.

5. Once SDK-native expiry is implemented, remove the manual `clear_session_if_stale()`
   call from `ralph_bridge.py` / `primary_agent.py`.

---

### 1.11 Adaptive Timeout (Priority: P3)

**What:** CLI's `ADAPTIVE_TIMEOUT_ENABLED` adjusts timeout dynamically based on
historical iteration durations (requires `ADAPTIVE_TIMEOUT_MIN_SAMPLES=5`).
SDK uses a static `timeout_minutes`.

**Why it matters:** A 30-minute timeout is too long for trivial tasks and too
short for architectural changes. Adaptive timeouts reduce waste on fast tasks
and prevent premature kills on slow ones.

**Request:** Add `AdaptiveTimeout` that tracks iteration durations and adjusts
the timeout using a multiplier (default 2x) with min/max bounds.

---

### 1.12 Permission Denial Detection (Priority: P3)

**What:** CLI distinguishes between bash command denials (fixable via
`ALLOWED_TOOLS`) and built-in tool denials (filesystem scope). SDK has no
permission denial awareness.

**Why it matters:** When Claude loses access to tools mid-run (sandboxed mode,
permission revocation), the SDK doesn't detect this and continues looping
uselessly.

**Request:** Parse Claude output for permission denial patterns and expose
them as a `PermissionDenialEvent` on the status. Distinguish between
user-fixable (add to allowed tools) and scope-locked (filesystem boundaries).

---

## 2. TheStudio Integration Pain Points (SDK Fixes Needed)

These are bugs or limitations discovered in TheStudio's Ralph integration that
require SDK changes to fix properly.

### 2.1 Changed-Files Extraction is Fragile (Priority: P1)

**Problem:** TheStudio uses a regex heuristic to extract changed file paths from
Ralph's freeform output — look for lines starting with `"- "` containing dots or
slashes. This is duplicated in both `ralph_bridge.py:203-218` and
`primary_agent.py:125-141`. False positives are common.

**Request:** Have the SDK return `files_changed: list[str]` as a structured field
on `TaskResult`, populated from actual `git diff` output or Claude's tool use
records (Write/Edit calls). TheStudio should not be parsing freeform text for this.

---

### 2.2 Cancel Semantics are Undocumented (Priority: P1)

**Problem:** TheStudio's Temporal activity calls `agent.cancel()` on timeout
(`activities.py:954`), then waits 10s, then force-cancels the asyncio task.
It's unclear whether `cancel()` actually stops the subprocess or just sets a flag.

**Request:** Document `RalphAgent.cancel()` behavior. Guarantee that it:
1. Sends SIGTERM to the Claude subprocess
2. Returns a `CancelResult` with the partial output collected so far
3. Completes within a configurable grace period (default 10s)

#### Current State (2026-03-24)

**Gap status: ✅ FULLY IMPLEMENTED (51-cancel).**

`cancel()` in `vendor/ralph-sdk/ralph_sdk/agent.py`:
1. Sets `_running = False` and calls `proc.terminate()` (SIGTERM) — guaranteed.
2. Returns `CancelResult(partial_output=self._output_buffer, ...)` — buffer is
   updated at the end of every `_run_iteration` call after stdout is decoded.
   When cancel races an in-flight `communicate()`, `partial_output` reflects
   the previous iteration; once the process exits the activity's grace wait
   allows `communicate()` to resolve and `_output_buffer` to be updated.
3. Grace wait (10 s) is caller responsibility per the documented contract in
   `CancelResult` docstring and `activities.py:960-961`.

`CancelResult` now carries `partial_output: str = ""`.

---

### 2.3 Heartbeat Data is Unstructured (Priority: P2)

**Problem:** TheStudio's heartbeat sends `f"ralph_running elapsed={elapsed_s}s"`
as a plain string. Temporal dashboards can't extract loop count, work type, or
progress.

**Request:** Add `get_progress() -> ProgressSnapshot` to `RalphAgent` returning:
```python
class ProgressSnapshot(BaseModel):
    loop_count: int
    work_type: str
    current_task: str | None
    elapsed_seconds: float
    circuit_breaker_state: str
```
TheStudio can then serialize this into the heartbeat.

#### Current State (2026-03-24)

**Gap status: ~30% IMPLEMENTED (heartbeat fires; payload is a plain string).**

`_implement_ralph_with_heartbeat()` in `src/workflow/activities.py` sends a
Temporal heartbeat every 30 s using:
```python
activity.heartbeat(f"ralph_running elapsed={elapsed_s}s timeout={timeout_s}s")
```
This plain string is visible in the Temporal UI but cannot be queried, graphed, or
alerted on. `RalphAgent` exposes no `get_progress()` method. The fields that would
constitute a `ProgressSnapshot` are scattered across internal state:
- `_loop_count` in `agent.py` (private attribute)
- `_last_status.work_type` (accessible after `run_iteration()` returns)
- `_last_status.circuit_breaker_state`
- `CostTracker.get_session_cost()` is callable but not included in heartbeats

**What exists today:**
- `_implement_ralph_with_heartbeat()`: 30 s heartbeat timer, timeout detection
- `RalphStatus`: `loop_count`, `work_type`, `completed_task`, `next_task`, `circuit_breaker_state`
- `CostTracker.get_session_cost() -> float` (callable during run)
- `ATTR_RALPH_TURNS`, `ATTR_RALPH_COST_USD` in `conventions.py` (emitted on span close, not mid-run)

**What is missing:**
- `get_progress() -> ProgressSnapshot` method on `RalphAgent`
- `ProgressSnapshot` Pydantic model (see request above)
- `_implement_ralph_with_heartbeat()` using `agent.get_progress()` instead of
  constructing a string from elapsed time alone
- Downstream alerting: Temporal can alert on `loop_count` stagnation or
  `circuit_breaker_state == "OPEN"` only if these fields are in the heartbeat payload

#### Implementation Path

1. Add `ProgressSnapshot` to `vendor/ralph-sdk/agent.py` (or a new `progress.py`):
   ```python
   class ProgressSnapshot(BaseModel):
       loop_count: int
       work_type: str
       current_task: str | None
       elapsed_seconds: float
       circuit_breaker_state: str
       cost_usd: float
       files_changed_total: int
       tests_status: str
   ```

2. Add `get_progress() -> ProgressSnapshot` to `RalphAgent`:
   ```python
   def get_progress(self) -> ProgressSnapshot:
       return ProgressSnapshot(
           loop_count=self._loop_count,
           work_type=self._last_status.work_type if self._last_status else "UNKNOWN",
           current_task=self._last_status.completed_task if self._last_status else None,
           elapsed_seconds=(time.monotonic() - self._run_start_time),
           circuit_breaker_state=self._circuit_breaker.state.value,
           cost_usd=self._cost_tracker.get_session_cost(),
           files_changed_total=self._files_changed_session,
           tests_status=self._last_status.tests_status if self._last_status else "NOT_RUN",
       )
   ```

3. Update `src/workflow/activities.py`'s `_implement_ralph_with_heartbeat()`:
   ```python
   snapshot = agent.get_progress()
   activity.heartbeat(snapshot.model_dump_json())
   ```

4. Add a Temporal Search Attribute or custom metric derived from `loop_count` and
   `circuit_breaker_state` so the Temporal UI can surface stalled runs.

---

### 2.4 Rate Limiter Counts Invocations, Not Tokens (Priority: P2)

**Problem:** Ralph issue #223. The rate limiter tracks calls per hour, not token
consumption. A single high-token call counts the same as a trivial one. This
makes TheStudio's budget enforcement inaccurate.

**Request:** Add optional token-based rate limiting alongside invocation-based.
Accept `max_tokens_per_hour` in config. Track cumulative input + output tokens.

---

## 3. Upstream Unfinished Work That Impacts TheStudio

These are items on Ralph's own roadmap that TheStudio is waiting for.

| Item | Phase | Status | TheStudio Impact |
|---|---|---|---|
| **CTXMGMT-3: Continue-As-New** | 14 | Open | Multi-loop tasks (bug fixes, refactoring) exceed 20 iterations. Without session reset, context fills with stale attempts. **Single most impactful unfinished story.** |
| **ENABLE-5: Task normalization/dedup** | 15 | Open | Duplicate tasks in fix_plan.md waste loops when using `ralph --batch` |
| **ENABLE-6: `--dry-run` and `--json`** | 15 | Open | TheStudio's Temporal activity could validate config before committing to a real run |
| **Issue #225: E2E integration tests** | — | Open | SDK regressions only surface in TheStudio's tests, making debugging harder |

---

## 4. Prioritized Request Summary

### P0 — Blocks Production Quality

| # | Request | Section | Effort Est. |
|---|---|---|---|
| 1 | Stall detection (fast-trip, deferred-test, consecutive timeout) | 1.1 | 1-2 days |
| 2 | Progressive context loading | 1.2 | 1-2 days |
| 3 | Structured `files_changed` on TaskResult | 2.1 | 0.5 day |

### P1 — Significant Quality/Cost Improvement

| # | Request | Section | Effort Est. |
|---|---|---|---|
| 4 | Task decomposition detection | 1.3 | 1 day |
| 5 | Cost tracking and budget guardrails | 1.4 | 2 days |
| 6 | Dynamic model routing | 1.5 | 1 day |
| 7 | Completion indicator decay | 1.6 | 0.5 day |
| 8 | Document and harden `cancel()` semantics | 2.2 | 0.5 day |

### P2 — Observability and Accuracy

| # | Request | Section | Effort Est. |
|---|---|---|---|
| 9 | Error categorization | 1.7 | 1 day |
| 10 | Prompt cache optimization | 1.8 | 1 day |
| 11 | Metrics collection | 1.9 | 1-2 days |
| 12 | Session lifecycle management + Continue-As-New | 1.10 | 2 days |
| 13 | Structured heartbeat/progress snapshot | 2.3 | 0.5 day |
| 14 | Token-based rate limiting | 2.4 | 1 day |

### P3 — Future Value

| # | Request | Section | Effort Est. |
|---|---|---|---|
| 15 | Adaptive timeout | 1.11 | 1 day |
| 16 | Permission denial detection | 1.12 | 1 day |

**Total estimated effort:** ~17-21 days for all items.
**P0 items only:** 2.5-4.5 days.

---

## 5. Recommendation

**Do not upgrade the vendored SDK** — there is no new SDK version to pull.
The v2.2.0 changes are CLI-only.

**Do upgrade the local WSL Ralph CLI** to v2.2.0 for development loop quality:
```bash
wsl bash -lc 'cd ~/.ralph && git pull'
```
If `~/.ralph` is not a git repository, clone your Ralph CLI source into that path first, then pull.

**Tracking (executed 2026-03-23):** TheStudio epic **Epic 51** — [`docs/epics/epic-51-ralph-vendored-sdk-parity.md`](epics/epic-51-ralph-vendored-sdk-parity.md) — captures P0–P1 vendor work and bridge fixes. Rollup: [`docs/epics/EPIC-STATUS-TRACKER.md`](epics/EPIC-STATUS-TRACKER.md). Meridian review: [`docs/epics/MERIDIAN-REVIEW-EPIC-51.md`](epics/MERIDIAN-REVIEW-EPIC-51.md).

**Upstream (executed 2026-03-23):** [frankbria/ralph-claude-code#226](https://github.com/frankbria/ralph-claude-code/issues/226) — SDK parity umbrella issue. Index: [`docs/ralph-upstream-issues.md`](ralph-upstream-issues.md).

**Next step:** Implement P0 in `vendor/ralph-sdk/`; contribute patches upstream as issue #226 evolves.
