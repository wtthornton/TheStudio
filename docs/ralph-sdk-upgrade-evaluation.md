# Ralph SDK Upgrade Evaluation

**Date:** 2026-03-23
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

**Tracking (executed 2026-03-23):** TheStudio epic **Epic 51** — [`docs/epics/epic-51-ralph-vendored-sdk-parity.md`](epics/epic-51-ralph-vendored-sdk-parity.md) — captures P0–P1 vendor work and bridge fixes. Rollup: [`docs/epics/EPIC-STATUS-TRACKER.md`](epics/EPIC-STATUS-TRACKER.md).

**Next step:** Optionally file parallel upstream issues in the Ralph repo for the same requests; implement P0 in `vendor/ralph-sdk/` without blocking on upstream releases.
