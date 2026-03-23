# Ralph SDK 2.3.0 Upgrade Plan

**Date:** 2026-03-23
**From:** SDK 2.0.2 (vendored) + CLI 2.2.0 (WSL)
**To:** SDK 2.1.0 (bundled in Ralph CLI 2.3.0)
**Source:** `C:\cursor\ralph\ralph-claude-code\sdk\`

---

## Executive Summary

Ralph v2.3.0 ships SDK v2.1.0 — a major upgrade adding **3 new modules** (`context.py`, `cost.py`, `metrics.py`) and significant expansions to `agent.py`, `circuit_breaker.py`, `config.py`, `parsing.py`, and `status.py`. It addresses all 16 requests from the [upgrade evaluation](ralph-sdk-upgrade-evaluation.md). No new pip dependencies are introduced.

The upgrade resolves two production-impact issues:
1. **Stall detection** — Ralph can now detect fast-trip, deferred-test, and consecutive-timeout stalls (P0, was LOGFIX-6)
2. **Structured files_changed** — eliminates the fragile regex heuristic duplicated in `ralph_bridge.py` and `primary_agent.py` (P0)

**Estimated effort:** 4-5 days for Phases 1-3 (high-value integration), 2-3 additional days for Phase 4 (optimization).

---

## What's New in SDK 2.1.0

### New Modules

| Module | Contents | Resolves |
|--------|----------|----------|
| `context.py` | `ContextManager`, `PromptParts`, `PromptCacheStats`, `split_prompt()`, `estimate_tokens()` | Eval 1.2, 1.8 |
| `cost.py` | `CostTracker`, `TokenRateLimiter`, `select_model()`, `CostComplexityBand`, `DEFAULT_PRICING` | Eval 1.4, 1.5, 2.4 |
| `metrics.py` | `MetricsCollector` protocol, `JsonlMetricsCollector`, `NullMetricsCollector`, `MetricEvent` | Eval 1.9 |

### Expanded Modules

| Module | New APIs | Resolves |
|--------|----------|----------|
| `circuit_breaker.py` | `CircuitBreaker` (active), `FastTripDetector`, `DeferredTestDetector`, `ConsecutiveTimeoutDetector`, `StallDetectorResult` | Eval 1.1 |
| `agent.py` | `DecompositionHint`, `IterationRecord`, `detect_decomposition_needed()`, `ProgressSnapshot`, `ContinueAsNewState`, `CancelResult`, `compute_adaptive_timeout()` | Eval 1.3, 1.6, 1.10, 2.2, 2.3, 1.11 |
| `config.py` | 25+ new config fields: stall thresholds, decomposition, cancel grace, adaptive timeout, session lifecycle, budget, model routing, token rate limit | All |
| `status.py` | `ErrorCategory` enum, `classify_error()`, `permission_denials` field on `RalphStatus` | Eval 1.7 |
| `parsing.py` | `PermissionDenialEvent`, `detect_permission_denials()`, `extract_files_changed()` | Eval 1.12, 2.1 |

### New Exports (53 total, up from 25)

Key new public symbols: `CircuitBreaker`, `FastTripDetector`, `DeferredTestDetector`, `ConsecutiveTimeoutDetector`, `StallDetectorResult`, `CostTracker`, `CostComplexityBand`, `TokenRateLimiter`, `select_model`, `ContextManager`, `PromptParts`, `split_prompt`, `estimate_tokens`, `MetricsCollector`, `JsonlMetricsCollector`, `MetricEvent`, `ErrorCategory`, `classify_error`, `ProgressSnapshot`, `ContinueAsNewState`, `CancelResult`, `DecompositionHint`, `detect_decomposition_needed`, `compute_adaptive_timeout`, `PermissionDenialEvent`, `detect_permission_denials`, `extract_files_changed`.

---

## Pre-Upgrade Checklist

- [ ] Vendor SDK tests pass against current codebase: `cd vendor/ralph-sdk && pytest`
- [ ] TheStudio's Ralph integration tests pass: `pytest tests/ -k ralph`
- [ ] No uncommitted changes in `vendor/ralph-sdk/`
- [ ] Current `vendor/ralph-sdk/` is backed up (git handles this)

---

## Phase 1: Vendor the New SDK (Day 1)

**Goal:** Replace vendored SDK files, fix version string, verify imports.

### Steps

1. **Copy new SDK source** from Ralph repo to vendor directory:
   ```bash
   # Clear old source (keep .gitkeep)
   rm -rf vendor/ralph-sdk/ralph_sdk/ vendor/ralph-sdk/tests/ vendor/ralph-sdk/build/

   # Copy new source
   cp -r /mnt/c/cursor/ralph/ralph-claude-code/sdk/ralph_sdk vendor/ralph-sdk/
   cp -r /mnt/c/cursor/ralph/ralph-claude-code/sdk/tests vendor/ralph-sdk/
   cp /mnt/c/cursor/ralph/ralph-claude-code/sdk/pyproject.toml vendor/ralph-sdk/
   ```

2. **Bump version string** in `vendor/ralph-sdk/ralph_sdk/__init__.py`:
   ```python
   __version__ = "2.1.0"  # was "2.0.2"
   ```

3. **Verify no new dependencies**: `pyproject.toml` dependencies are unchanged (`pydantic>=2.0,<3.0`, `aiofiles>=24.0`). No pip install needed.

4. **Run vendor tests**:
   ```bash
   cd vendor/ralph-sdk && pytest tests/ -v
   ```

5. **Run TheStudio import check**:
   ```python
   python -c "from ralph_sdk import CostTracker, ContextManager, CircuitBreaker, extract_files_changed, ErrorCategory; print('OK')"
   ```

### Risks
- **`__init__.py` still says 2.0.2** — must manually set to 2.1.0
- New modules import from each other (`agent.py` imports from `cost.py`, `context.py`, `metrics.py`) — all must land together

---

## Phase 2: High-Value Integration (Days 2-3)

**Goal:** Wire the three highest-impact features into TheStudio's integration layer.

### 2A. Structured `files_changed` (P0 — replaces fragile regex)

**Files to change:** `src/agent/ralph_bridge.py`, `src/agent/primary_agent.py`

The new SDK's `TaskResult` already has `files_changed: list[str]` populated by `extract_files_changed()` (parses JSONL tool_use records for Write/Edit/MultiEdit calls). This replaces the duplicated `_parse_changed_files()` heuristic.

```python
# ralph_bridge.py — BEFORE
def ralph_result_to_evidence(result: TaskResult, ...) -> EvidenceBundle:
    summary_parts = [...]
    agent_summary = "\n\n".join(summary_parts)
    changed_files = _parse_changed_files(agent_summary)  # <-- fragile regex
    return EvidenceBundle(..., files_changed=changed_files, ...)

# ralph_bridge.py — AFTER
def ralph_result_to_evidence(result: TaskResult, ...) -> EvidenceBundle:
    summary_parts = [...]
    agent_summary = "\n\n".join(summary_parts)
    # SDK 2.1.0: Use structured files_changed from JSONL tool_use parsing
    changed_files = result.files_changed or _parse_changed_files(agent_summary)
    return EvidenceBundle(..., files_changed=changed_files, ...)
```

- Keep `_parse_changed_files()` as fallback for legacy/edge cases
- Remove the duplicate `_parse_changed_files()` from `primary_agent.py` (lines 125-141)

### 2B. Stall Detection via Circuit Breaker (P0)

**Files to change:** `src/agent/primary_agent.py`, `src/agent/ralph_bridge.py`

The new `CircuitBreaker` class integrates `FastTripDetector`, `DeferredTestDetector`, and `ConsecutiveTimeoutDetector`. Pass the config to enable them.

```python
# ralph_bridge.py — build_ralph_config() update
def build_ralph_config(...) -> RalphConfig:
    return RalphConfig(
        project_name="thestudio-task",
        project_type="python",
        max_turns=effective_max_turns,
        output_format="json",
        session_continuity=True,
        # SDK 2.1.0: Stall detection thresholds
        cb_max_consecutive_fast_failures=3,
        cb_max_deferred_tests=10,
        cb_deferred_tests_warn_at=5,
        cb_max_consecutive_timeouts=5,
    )
```

The `RalphAgent` internally creates a `CircuitBreaker` with these thresholds — no additional wiring needed. Stall detection is automatic once config is passed.

### 2C. Cost Tracking via SDK (P1 — replaces heuristic)

**Files to change:** `src/agent/primary_agent.py`

Replace the hardcoded `_RALPH_COST_PER_1K_*` constants with the SDK's `CostTracker` and accurate `total_cost_usd` from the `TaskResult`.

```python
# primary_agent.py — BEFORE
_RALPH_COST_PER_1K_INPUT = 0.003  # Claude Sonnet estimate
_RALPH_COST_PER_1K_OUTPUT = 0.015
estimated_cost = (
    tokens_in * _RALPH_COST_PER_1K_INPUT / 1000
    + tokens_out * _RALPH_COST_PER_1K_OUTPUT / 1000
)

# primary_agent.py — AFTER
# SDK 2.1.0: CostTracker with per-model pricing is built into RalphAgent.
# result.total_cost_usd is populated by the agent's internal CostTracker.
estimated_cost = result.total_cost_usd
```

Also configure budget guardrails in `build_ralph_config()`:
```python
max_budget_usd=settings.agent_max_budget_usd,
budget_warning_pct=50.0,
budget_critical_pct=80.0,
```

---

## Phase 3: Medium-Value Integration (Days 3-4)

### 3A. Error Categorization (P2)

**Files to change:** `src/agent/primary_agent.py`

Use `result.status.error_category` for programmatic error handling in the loopback logic:

```python
from ralph_sdk import ErrorCategory

if result.status.error_category == ErrorCategory.TIMEOUT:
    # Retryable — increase timeout on next attempt
    ...
elif result.status.error_category == ErrorCategory.SYSTEM_CRASH:
    # Terminal — circuit break immediately
    ...
elif result.status.error_category == ErrorCategory.RATE_LIMITED:
    # Retryable after backoff
    ...
```

### 3B. ProgressSnapshot for Heartbeats (P2)

**Files to change:** `src/workflow/activities.py`

Replace the plain string heartbeat with structured data:

```python
# BEFORE
heartbeat_details = f"ralph_running elapsed={elapsed_s}s"

# AFTER — SDK 2.1.0 ProgressSnapshot
progress = agent.get_progress()
heartbeat_details = json.dumps({
    "loop_count": progress.loop_count,
    "work_type": progress.work_type,
    "current_task": progress.current_task,
    "elapsed_seconds": progress.elapsed_seconds,
    "circuit_breaker_state": progress.circuit_breaker_state,
})
```

### 3C. Cancel Semantics Hardening (P1)

**Files to change:** `src/workflow/activities.py`

The new `agent.cancel()` returns a `CancelResult` with partial output and force-kill status. Wire this into the activity cancellation handler:

```python
# BEFORE
agent.cancel()
await asyncio.sleep(10)  # hope it stops

# AFTER — SDK 2.1.0 hardened cancel
cancel_result = await agent.cancel()
if cancel_result.was_forced:
    logger.warning("Ralph agent required SIGKILL after grace period")
# cancel_result.partial_output available for evidence
```

### 3D. Session Lifecycle with Continue-As-New (P2)

Configure session rotation to prevent context window bloat on long runs:

```python
# ralph_bridge.py — build_ralph_config() update
max_session_iterations=20,
max_session_age_minutes=120,
continue_as_new_enabled=True,
```

This enables the SDK to automatically rotate sessions after 20 iterations or 2 hours, carrying only essential state (`ContinueAsNewState`). TheStudio's `clear_session_if_stale()` workaround can be removed once this is verified.

---

## Phase 4: Optimization Features (Days 5-6, optional)

These are lower-priority but provide cost and performance improvements.

### 4A. Progressive Context Loading

Use `ContextManager.trim_fix_plan()` when building the task prompt to reduce token waste:

```python
from ralph_sdk import ContextManager

ctx = ContextManager(max_unchecked_items=5)
trimmed_plan = ctx.trim_fix_plan(full_fix_plan)
```

### 4B. Dynamic Model Routing

Use `select_model()` in `build_ralph_config()` to route trivial tasks to Haiku:

```python
from ralph_sdk.cost import select_model, CostComplexityBand

model = select_model(
    complexity=CostComplexityBand.TRIVIAL,  # mapped from TaskPacket complexity
    retry_count=loopback_attempt,
)
```

### 4C. Prompt Cache Optimization

Use `split_prompt()` to separate stable prefix from dynamic suffix:

```python
from ralph_sdk import split_prompt

parts = split_prompt(full_prompt, loop_context={"loop": loop_count})
# parts.stable_prefix — cacheable across iterations
# parts.dynamic_suffix — changes each iteration
```

### 4D. Metrics Collection

Wire `JsonlMetricsCollector` into `RalphAgent` for historical performance data:

```python
from ralph_sdk import JsonlMetricsCollector

agent = RalphAgent(
    config=config,
    metrics_collector=JsonlMetricsCollector(ralph_dir=".ralph"),
)
```

### 4E. Adaptive Timeout

Enable for long-running task types:

```python
adaptive_timeout_enabled=True,
adaptive_timeout_min_samples=5,
adaptive_timeout_multiplier=2.0,
adaptive_timeout_min_minutes=5,
adaptive_timeout_max_minutes=60,
```

### 4F. Token-Based Rate Limiting

Replace invocation-count rate limiting with token-aware limits:

```python
max_tokens_per_hour=500_000,  # set based on budget
```

---

## TheStudio Code Removal After Upgrade

These TheStudio workarounds become redundant with SDK 2.1.0:

| Workaround | Location | Replaced By |
|------------|----------|-------------|
| `_parse_changed_files()` regex heuristic | `ralph_bridge.py:203-218`, `primary_agent.py:125-141` | `TaskResult.files_changed` (JSONL tool_use parsing) |
| `_RALPH_COST_PER_1K_*` constants | `primary_agent.py` | `CostTracker` with `DEFAULT_PRICING` |
| `clear_session_if_stale()` TTL workaround | `ralph_state.py` | SDK session lifecycle (`session_expiry_hours`, Continue-As-New) |
| Hardcoded cost estimation formula | `primary_agent.py:306-309` | `result.total_cost_usd` |
| Plain string heartbeat | `activities.py` | `ProgressSnapshot` |

---

## Migration Test Plan

### Unit Tests

- [ ] `test_ralph_bridge.py` — `ralph_result_to_evidence()` uses `result.files_changed`
- [ ] `test_ralph_bridge.py` — `build_ralph_config()` passes stall detection thresholds
- [ ] `test_primary_agent.py` — Cost recorded from `result.total_cost_usd`
- [ ] `test_primary_agent.py` — Error categorization used in loopback logic
- [ ] Vendor tests pass: `cd vendor/ralph-sdk && pytest tests/ -v`

### Integration Tests

- [ ] Ralph agent completes a simple task with new SDK (smoke test)
- [ ] Stall detection trips circuit breaker on simulated fast-trip scenario
- [ ] Cancel returns `CancelResult` within grace period
- [ ] Heartbeat includes structured `ProgressSnapshot`
- [ ] `files_changed` populated from JSONL (not regex) on a real run

### Regression

- [ ] Existing Ralph tests (`pytest tests/ -k ralph`) still pass
- [ ] Health endpoint `/health/ralph` returns 200
- [ ] Temporal workflow executes end-to-end with new SDK

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SDK version string not bumped (still says 2.0.2) | Certain | Low | Manually set to 2.1.0 in `__init__.py` |
| New `agent.py` imports break if module missing | Low | High | All 3 new modules must land together |
| `CancelResult` behavior differs on Windows vs Unix | Medium | Medium | Test cancel on both platforms |
| `ContextManager` trims plan too aggressively | Low | Medium | Keep full plan as fallback; tune `max_unchecked_items` |
| `CircuitBreaker` stall thresholds too sensitive | Low | Medium | Start with CLI defaults; tune via config |

---

## Recommended Execution Order

1. **Phase 1** (vendor) — Day 1, single commit
2. **Phase 2A** (files_changed) — Day 2, highest signal/effort ratio
3. **Phase 2B** (stall detection) — Day 2, config-only change
4. **Phase 2C** (cost tracking) — Day 3, removes hardcoded constants
5. **Phase 3A-D** (error/progress/cancel/session) — Days 3-4
6. **Phase 4** (optimization) — Days 5-6, as capacity allows
7. **Code removal** — After Phase 3 is verified in staging

---

## Update to Evaluation Document

The [upgrade evaluation](ralph-sdk-upgrade-evaluation.md) should be updated to reflect that:
- SDK v2.1.0 is now available (bundled in Ralph CLI v2.3.0)
- All 16 requests (P0 through P3) are addressed by the new SDK
- The recommendation changes from "do not upgrade" to "upgrade the vendored SDK"
