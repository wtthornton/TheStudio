# Epic 51: Accurate Cost Tracking, Stall Detection, and Structured Agent Output via Ralph SDK 2.1.0 Upgrade

> **Status:** DRAFT -- Pending Meridian Review
> **Epic Owner:** Primary Developer
> **Duration:** 2-3 weeks (4 slices, 14 stories)
> **Created:** 2026-03-23
> **Priority:** P0/P1 -- Resolves two production-impact issues and eliminates five TheStudio workarounds
> **Depends on:** Epic 43 (Ralph SDK Integration) COMPLETE, Ralph CLI 2.3.0 ships SDK 2.1.0
> **Capacity:** Solo developer, 30 hours/week

---

## 1. Title

**Accurate Cost Tracking, Stall Detection, and Structured Agent Output via Ralph SDK 2.1.0 Upgrade -- Replace Five TheStudio Workarounds with SDK-Native Capabilities**

---

## 2. Narrative

TheStudio integrated the Ralph SDK (v2.0.2) in Epic 43. The integration works. It also has five workarounds that were necessary because the SDK lacked capabilities that Ralph's CLI already had.

**Workaround 1: Fragile `_parse_changed_files()` regex.** Both `ralph_bridge.py` (lines 203-218) and `primary_agent.py` (lines 125-141) contain duplicate regex heuristics that extract file paths from freeform agent output by looking for lines starting with `"- "` that contain dots or slashes. This fires false positives on bullet-list documentation and misses files mentioned in other formats. The SDK 2.1.0 now populates `TaskResult.files_changed` from structured JSONL tool_use records (Write/Edit/MultiEdit calls) -- no regex, no guessing.

**Workaround 2: No stall detection.** Ralph can loop indefinitely without making progress. The `LOGFIX-6` production incident occurred because the agent deferred tests for 15+ iterations while burning budget. The SDK 2.1.0 adds `CircuitBreaker` with three detectors: `FastTripDetector` (0-tool runs under 30s), `DeferredTestDetector` (>N deferred-test loops), and `ConsecutiveTimeoutDetector`. All are config-driven -- TheStudio passes thresholds and the SDK handles the rest.

**Workaround 3: Hardcoded cost estimation.** `primary_agent.py` uses `_RALPH_COST_PER_1K_INPUT = 0.003` and `_RALPH_COST_PER_1K_OUTPUT = 0.015` -- static constants that are wrong whenever the model changes (Haiku vs Sonnet vs Opus have wildly different rates). The SDK 2.1.0 includes `CostTracker` with `DEFAULT_PRICING` that maps model IDs to accurate per-token rates. `result.total_cost_usd` replaces the heuristic formula.

**Workaround 4: Unstructured heartbeat.** The Temporal activity heartbeat sends `f"ralph_running elapsed={elapsed_s}s"` as a plain string. Dashboards cannot extract loop count, work type, or circuit breaker state. The SDK 2.1.0 adds `ProgressSnapshot` with structured fields.

**Workaround 5: Session TTL managed by TheStudio.** `ralph_state.py` has `clear_session_if_stale(ttl_seconds=7200)` -- a TheStudio-side session expiry workaround. The SDK 2.1.0 manages session lifecycle natively with configurable expiry and Continue-As-New rotation.

Ralph CLI 2.3.0 shipped with SDK 2.1.0 bundled. It introduces 3 new modules (`context.py`, `cost.py`, `metrics.py`), expands 5 existing modules, adds 28 new public symbols (53 total, up from 25), and requires no new pip dependencies. All 16 requests from the upgrade evaluation (`docs/ralph-sdk-upgrade-evaluation.md`) are addressed.

Why now: Every Ralph run currently records inaccurate costs and has no stall protection. At Execute tier (Epic 42), bad cost data means incorrect budget enforcement, and stalled loops mean wasted spend on auto-merged garbage. Each day we delay costs real money.

---

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| Plan | `docs/ralph-sdk-230-upgrade-plan.md` | Full upgrade plan with before/after code, phased execution, test plan, and risk assessment |
| Evaluation | `docs/ralph-sdk-upgrade-evaluation.md` | Original 16-request gap analysis; all items resolved by SDK 2.1.0 |
| Source (Ralph) | `C:\cursor\ralph\ralph-claude-code\sdk\ralph_sdk\` | SDK 2.1.0 source: `context.py`, `cost.py`, `metrics.py` (new), expanded `agent.py`, `circuit_breaker.py`, `config.py`, `parsing.py`, `status.py` |
| Source (TheStudio) | `vendor/ralph-sdk/ralph_sdk/` | Current vendored SDK v2.0.2 -- the files being replaced |
| Source (TheStudio) | `src/agent/ralph_bridge.py` | `_parse_changed_files()` (lines 203-218), `build_ralph_config()` (lines 221-249) -- primary change targets |
| Source (TheStudio) | `src/agent/primary_agent.py` | `_parse_changed_files()` duplicate (lines 125-141), `_RALPH_COST_PER_1K_*` constants (lines 62-66), cost formula (lines 306-309) -- removal targets |
| Source (TheStudio) | `src/workflow/activities.py` | `_implement_ralph_with_heartbeat()` (line 880) -- heartbeat and cancel hardening targets |
| Source (TheStudio) | `src/agent/ralph_state.py` | `clear_session_if_stale()` -- session TTL workaround being replaced |
| Source (TheStudio) | `src/settings.py` | `ralph_session_ttl_seconds`, `ralph_timeout_minutes`, `agent_max_budget_usd` -- config fields to extend |
| Epic | `docs/epics/epic-43-ralph-sdk-integration.md` | Foundation: RalphAgent wiring, PostgresStateBackend, ralph_bridge converters |
| Epic | `docs/epics/epic-32-model-routing-cost.md` | Cost optimization infrastructure that `CostTracker` supplements |
| Epic | `docs/epics/epic-42-execute-tier-promotion.md` | Execute tier depends on accurate cost tracking and stall detection |
| OKRs | `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md` | Implementation quality and autonomous operation KRs |

---

## 4. Acceptance Criteria

### AC1: Vendored SDK Is v2.1.0 with All New Modules

The `vendor/ralph-sdk/ralph_sdk/` directory contains SDK v2.1.0 source including `context.py`, `cost.py`, `metrics.py` (3 new modules) and expanded `agent.py`, `circuit_breaker.py`, `config.py`, `parsing.py`, `status.py`. `__init__.py` exports 53 symbols and `__version__` is `"2.1.0"`. Vendor tests (`cd vendor/ralph-sdk && pytest tests/ -v`) pass. Import check succeeds: `from ralph_sdk import CostTracker, ContextManager, CircuitBreaker, extract_files_changed, ErrorCategory`.

**Testable:** Run `python -c "from ralph_sdk import __version__; assert __version__ == '2.1.0'"` and `pytest vendor/ralph-sdk/tests/ -v`.

### AC2: `files_changed` Uses Structured SDK Data, Not Regex

`ralph_result_to_evidence()` in `ralph_bridge.py` uses `result.files_changed` as the primary source for the `files_changed` field in `EvidenceBundle`. The `_parse_changed_files()` regex is retained as a fallback (called only when `result.files_changed` is empty/None). The duplicate `_parse_changed_files()` in `primary_agent.py` (lines 125-141) is deleted.

**Testable:** A unit test creates a `TaskResult` with `files_changed=["src/foo.py", "tests/test_foo.py"]` and empty output. `ralph_result_to_evidence()` returns those exact files. A second test with `files_changed=[]` and output containing `"- src/bar.py"` falls back to the regex.

### AC3: Stall Detection Is Active via Circuit Breaker Config

`build_ralph_config()` in `ralph_bridge.py` passes stall detection thresholds to `RalphConfig`: `cb_max_consecutive_fast_failures=3`, `cb_max_deferred_tests=10`, `cb_deferred_tests_warn_at=5`, `cb_max_consecutive_timeouts=5`. No additional TheStudio code is required -- the SDK's `CircuitBreaker` uses these thresholds internally.

**Testable:** A unit test calls `build_ralph_config()` and asserts the four stall detection fields are set. Integration: a mock Ralph run that produces 4 fast-trip iterations (0 tools, <30s each) trips the circuit breaker.

### AC4: Cost Is Recorded from `result.total_cost_usd`, Not Heuristic Formula

`_implement_ralph()` in `primary_agent.py` uses `result.total_cost_usd` for the `estimated_cost` variable instead of the `tokens * _RALPH_COST_PER_1K_*` formula. The `_RALPH_COST_PER_1K_INPUT` and `_RALPH_COST_PER_1K_OUTPUT` constants are deleted. Budget guardrails are configured in `build_ralph_config()`: `max_budget_usd`, `budget_warning_pct=50.0`, `budget_critical_pct=80.0`.

**Testable:** A unit test mocks `RalphAgent.run()` to return a `TaskResult` with `total_cost_usd=0.42`. Verifies the `ModelCallAudit.cost` is `0.42` and `BudgetEnforcer.record_spend()` receives `0.42`.

### AC5: Error Categorization Drives Loopback Decisions

`_implement_ralph()` or a helper inspects `result.status.error_category` (an `ErrorCategory` enum) to determine retry strategy: `TIMEOUT` and `RATE_LIMITED` are retryable (with backoff for rate limits), `SYSTEM_CRASH` is terminal (immediate circuit break), `PERMISSION_DENIED` triggers tool adjustment. This replaces generic error handling.

**Testable:** Three unit tests: (1) `ErrorCategory.TIMEOUT` result -> evidence returned, retry allowed. (2) `ErrorCategory.SYSTEM_CRASH` result -> raises terminal error / logs circuit break. (3) `ErrorCategory.RATE_LIMITED` result -> evidence returned with backoff flag set.

### AC6: Heartbeat Contains Structured ProgressSnapshot

`_implement_ralph_with_heartbeat()` in `activities.py` sends `json.dumps({...})` of the `ProgressSnapshot` fields (loop_count, work_type, current_task, elapsed_seconds, circuit_breaker_state) instead of the plain `f"ralph_running elapsed={elapsed_s}s"` string.

**Testable:** A unit test patches the agent with a known `ProgressSnapshot` and captures the heartbeat argument. Verifies it is valid JSON containing all five fields.

### AC7: Cancel Returns CancelResult with Partial Output

`_implement_ralph_with_heartbeat()` handles the new `CancelResult` from `agent.cancel()`: logs `was_forced` status, preserves `partial_output` for evidence. The 10-second sleep-and-hope pattern is replaced by the SDK's grace period.

**Testable:** A unit test mocks `agent.cancel()` to return `CancelResult(was_forced=True, partial_output="half done")`. Verifies the log message and that partial output is accessible.

### AC8: Session Lifecycle Managed by SDK

`build_ralph_config()` passes `max_session_iterations=20`, `max_session_age_minutes=120`, `continue_as_new_enabled=True`. The `clear_session_if_stale()` call in `_implement_ralph()` is removed (or gated behind a "legacy" flag) once SDK session lifecycle is verified.

**Testable:** A unit test calls `build_ralph_config()` and asserts the three session lifecycle fields. The `clear_session_if_stale()` call is absent from the ralph code path.

### AC9: Optimization Features Are Wired Behind Config

Progressive context loading (`ContextManager`), dynamic model routing (`select_model()`), prompt cache (`split_prompt()`), metrics collection (`JsonlMetricsCollector`), adaptive timeout, and token-based rate limiting are configured via `build_ralph_config()` and/or the `RalphAgent` constructor. Each is individually toggleable via settings or config fields. None are required for the high-value path to work.

**Testable:** Unit tests verify each optimization feature is present in the config when the corresponding setting is enabled, and absent when disabled.

### AC10: Five TheStudio Workarounds Are Removed or Demoted to Fallback

| Workaround | Disposition |
|------------|-------------|
| `_parse_changed_files()` in `ralph_bridge.py` | Retained as fallback only |
| `_parse_changed_files()` in `primary_agent.py` | Deleted |
| `_RALPH_COST_PER_1K_*` constants | Deleted |
| Hardcoded cost formula (lines 306-309) | Replaced by `result.total_cost_usd` |
| `clear_session_if_stale()` call | Removed from ralph path |
| Plain string heartbeat | Replaced by JSON ProgressSnapshot |

**Testable:** `grep -r "_RALPH_COST_PER_1K" src/` returns zero hits. `grep -r "clear_session_if_stale" src/agent/primary_agent.py` returns zero hits. `_parse_changed_files` appears in `ralph_bridge.py` only (not `primary_agent.py`).

---

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SDK `__version__` still reads `"2.0.2"` after vendor copy | Certain | Low | Story 51.1 manually sets to `"2.1.0"` -- verified by AC1 import check |
| New modules import each other (`agent.py` -> `cost.py`, `context.py`, `metrics.py`) | Low | High | All 3 new modules must land in a single commit (Slice 1) |
| `CancelResult` behavior differs on Windows vs Unix (SIGTERM semantics) | Medium | Medium | Test cancel on both platforms; document any platform-specific behavior |
| `ContextManager.trim_fix_plan()` trims too aggressively | Low | Medium | Keep full plan as fallback; tune `max_unchecked_items` in Slice 4 |
| `CircuitBreaker` stall thresholds too sensitive for TheStudio's deferred-test pattern | Medium | Medium | Start with CLI defaults (warn at 5, trip at 10); tune via settings if too aggressive |
| `CostTracker.DEFAULT_PRICING` model rates become stale | Low | Low | Rates are overridable via config; update when pricing changes |

---

## 5. Constraints & Non-Goals

### Constraints

- **No new pip dependencies.** SDK 2.1.0 depends only on `pydantic>=2.0,<3.0` and `aiofiles>=24.0`, both already installed. If any new dependency appears, it is a blocking issue.
- **Backward compatibility.** The `implement()` and `handle_loopback()` signatures in `primary_agent.py` remain unchanged. Callers (Temporal activities, tests) must not need modification.
- **Feature-flagged rollout.** `settings.agent_mode = "ralph"` remains the gate. Legacy mode must continue to work with zero changes. No optimization feature activates without explicit config.
- **Vendor directory is source of truth.** The SDK is vendored at `vendor/ralph-sdk/`; no pip install of `ralph-sdk` as a package. The vendor copy is what TheStudio imports.
- **Windows + WSL dual compatibility.** The vendor tests must pass on Windows (where TheStudio runs) and the agent subprocess runs in WSL. `CancelResult` behavior must be verified on both.

### Non-Goals

- **Upgrading the Ralph CLI itself.** This epic vendors the SDK (Python library) only. CLI upgrade (bash scripts in WSL) is a separate operational task.
- **Implementing decomposition detection.** `detect_decomposition_needed()` is available in SDK 2.1.0 but is not wired in this epic. It requires changes to the Router stage (pipeline stage 4), not the Primary Agent. Candidate for a future epic.
- **Completion indicator decay.** SDK 2.1.0 includes this fix internally in `agent.py`. TheStudio does not need to wire anything -- it is automatic. But we do not test for it explicitly in this epic.
- **Permission denial detection.** `PermissionDenialEvent` and `detect_permission_denials()` are available but not wired. Lower priority than the items in scope.
- **Changing any non-Ralph agent.** Only the Primary Agent (`src/agent/primary_agent.py`) and its bridge (`src/agent/ralph_bridge.py`) change. The Unified Agent Framework (`AgentRunner`) and all other pipeline agents are untouched.
- **Modifying `docker-compose.dev.yml` or `docker-compose.prod.yml`.** No infrastructure changes in this epic.

---

## 6. Stakeholders & Roles

| Role | Person | Responsibility |
|------|--------|---------------|
| Epic Owner | Primary Developer | Write stories, implement all slices, run tests |
| Architect | Primary Developer | Validate SDK API surface compatibility, review config field mapping |
| QA | Primary Developer + automated tests | Unit tests per story, integration smoke test, regression suite |
| Upstream SDK | Ralph project | Ships SDK 2.1.0 in CLI 2.3.0 (already done) |
| Reviewer | Meridian (persona) | Epic review, sprint plan review |

---

## 7. Success Metrics

| Metric | Baseline (SDK 2.0.2) | Target (SDK 2.1.0) | How to Measure |
|--------|----------------------|---------------------|----------------|
| Cost estimation accuracy | ~50% (static rates, wrong model) | >95% (per-model pricing from SDK) | Compare `ModelCallAudit.cost` to Anthropic invoice line items |
| Stall detection | None (0 stalls detected) | 100% of fast-trip, deferred-test, and timeout stalls detected | Monitor `CircuitBreakerState` transitions in Ralph logs |
| `files_changed` false positive rate | ~15% (regex heuristic) | <1% (structured JSONL tool_use) | Audit `EvidenceBundle.files_changed` against actual git diff in 20 runs |
| Heartbeat data richness | 1 field (elapsed seconds) | 5 fields (loop_count, work_type, current_task, elapsed, CB state) | Inspect Temporal heartbeat payloads in dashboard |
| TheStudio workaround count | 5 active workarounds | 0-1 (regex fallback retained) | `grep` for workaround markers |
| Time to integrate future SDK updates | N/A (first upgrade) | <1 day for minor version bumps | Track effort on next SDK upgrade |

---

## 8. Context & Assumptions

### Business Rules

- **Budget enforcement is two-layer.** TheStudio's `PipelineBudget` controls per-workflow spend. The SDK's `CostTracker` controls per-agent-run spend. Both must agree. `build_ralph_config()` sets `max_budget_usd` from `settings.agent_max_budget_usd`; `PipelineBudget.consume()` still reserves the max before the run starts.
- **Stall thresholds default to CLI values.** `cb_max_consecutive_fast_failures=3`, `cb_max_deferred_tests=10`, `cb_max_consecutive_timeouts=5`. These can be overridden via environment variables if tuning is needed post-deploy.
- **Session lifecycle config.** `max_session_iterations=20` and `max_session_age_minutes=120` match the CLI defaults. `continue_as_new_enabled=True` allows the SDK to rotate sessions automatically. TheStudio's `ralph_session_ttl_seconds` setting becomes vestigial but is retained for the legacy path.

### Dependencies

- **Ralph CLI 2.3.0 with SDK 2.1.0 already shipped.** Source at `C:\cursor\ralph\ralph-claude-code\sdk\`. No upstream blocking work.
- **Epic 43 COMPLETE.** `RalphAgent` wiring, `PostgresStateBackend`, `ralph_bridge.py` converters, `_implement_ralph()`, `_implement_ralph_with_heartbeat()`, OTEL spans, health endpoint -- all in place.
- **No database migration needed.** SDK 2.1.0 adds no new state keys to `ralph_agent_state`. The existing `PostgresStateBackend` schema handles new state transparently (JSON blobs).
- **No Temporal workflow changes.** The activity signature is unchanged. Heartbeat format changes are backward-compatible (string -> JSON string; Temporal treats both as opaque bytes).

### Systems Affected

| System | Impact |
|--------|--------|
| `vendor/ralph-sdk/` | Full replacement of SDK source files |
| `src/agent/ralph_bridge.py` | `build_ralph_config()` expanded, `ralph_result_to_evidence()` updated, `_parse_changed_files()` demoted |
| `src/agent/primary_agent.py` | Cost constants deleted, cost formula replaced, duplicate `_parse_changed_files()` deleted, error categorization added |
| `src/workflow/activities.py` | Heartbeat format changed, cancel handling updated |
| `src/settings.py` | New settings for budget warning/critical thresholds, optimization feature toggles |
| `src/agent/ralph_state.py` | `clear_session_if_stale()` call removed from ralph code path |
| `tests/` | New unit tests for all changed functions; vendor tests added to CI |

### Assumptions

- **SDK 2.1.0 API is stable.** The new symbols (`CostTracker`, `ContextManager`, `CircuitBreaker`, `ErrorCategory`, `ProgressSnapshot`, `CancelResult`, `extract_files_changed`) will not change signatures before we complete integration.
- **`TaskResult.files_changed` is populated.** The SDK's JSONL tool_use parser (`extract_files_changed()`) works with Claude Code's output format. If it does not, the regex fallback covers the gap while we file an upstream fix.
- **`CancelResult` works on Windows/WSL.** SIGTERM semantics differ between native Windows and WSL. The SDK uses `subprocess.terminate()` which maps to SIGTERM on WSL. If the grace period fails, `subprocess.kill()` (SIGKILL) is the fallback.
- **No cost data migration.** Historical `ModelCallAudit` records with heuristic costs are not retroactively corrected. The accuracy improvement applies to new runs only.

---

## Story Map

### Slice 1: Vendor SDK 2.1.0 (Risk: Import breakage -- do first)

| # | Story | Size | Files to modify/create |
|---|-------|------|----------------------|
| 51.1 | **Vendor SDK 2.1.0 source and verify imports** -- Copy SDK 2.1.0 from Ralph repo to `vendor/ralph-sdk/ralph_sdk/`, copy `tests/` and `pyproject.toml`, set `__version__ = "2.1.0"`, verify all 53 exports import cleanly, run vendor tests. | S | `vendor/ralph-sdk/ralph_sdk/*` (replace all), `vendor/ralph-sdk/tests/*` (replace all), `vendor/ralph-sdk/pyproject.toml` |
| 51.2 | **Update `__init__.py` exports for new SDK symbols** -- Add new public symbols to `__init__.py.__all__`: `CircuitBreaker`, `FastTripDetector`, `DeferredTestDetector`, `ConsecutiveTimeoutDetector`, `StallDetectorResult`, `CostTracker`, `CostComplexityBand`, `TokenRateLimiter`, `select_model`, `ContextManager`, `PromptParts`, `split_prompt`, `estimate_tokens`, `MetricsCollector`, `JsonlMetricsCollector`, `MetricEvent`, `ErrorCategory`, `classify_error`, `ProgressSnapshot`, `ContinueAsNewState`, `CancelResult`, `DecompositionHint`, `detect_decomposition_needed`, `compute_adaptive_timeout`, `PermissionDenialEvent`, `detect_permission_denials`, `extract_files_changed`. Verify import check script. | S | `vendor/ralph-sdk/ralph_sdk/__init__.py` |

### Slice 2: High-Value Integration (Risk reduction -- three production-impact fixes)

| # | Story | Size | Files to modify/create |
|---|-------|------|----------------------|
| 51.3 | **Wire structured `files_changed` from `TaskResult`** -- Update `ralph_result_to_evidence()` to use `result.files_changed` as primary source, fall back to `_parse_changed_files()` when empty. Delete the duplicate `_parse_changed_files()` from `primary_agent.py`. Add unit tests for both paths. | S | `src/agent/ralph_bridge.py`, `src/agent/primary_agent.py`, `tests/test_ralph_bridge.py` |
| 51.4 | **Enable stall detection via `build_ralph_config()`** -- Add `cb_max_consecutive_fast_failures`, `cb_max_deferred_tests`, `cb_deferred_tests_warn_at`, `cb_max_consecutive_timeouts` to `build_ralph_config()`. Add unit test verifying config fields. | S | `src/agent/ralph_bridge.py`, `tests/test_ralph_bridge.py` |
| 51.5 | **Replace cost heuristic with `result.total_cost_usd`** -- Delete `_RALPH_COST_PER_1K_INPUT`, `_RALPH_COST_PER_1K_OUTPUT` constants. Replace cost formula with `result.total_cost_usd`. Add `max_budget_usd`, `budget_warning_pct`, `budget_critical_pct` to `build_ralph_config()`. Add settings for budget thresholds. Unit test: mock `TaskResult.total_cost_usd` and verify audit/spend records. | M | `src/agent/primary_agent.py`, `src/agent/ralph_bridge.py`, `src/settings.py`, `tests/test_primary_agent.py`, `tests/test_ralph_bridge.py` |

### Slice 3: Medium-Value Integration (Observability and resilience)

| # | Story | Size | Files to modify/create |
|---|-------|------|----------------------|
| 51.6 | **Wire error categorization into loopback decisions** -- Import `ErrorCategory` from `ralph_sdk`. Add error category inspection after `agent.run()` in `_implement_ralph()`. Map `TIMEOUT`/`RATE_LIMITED` to retryable, `SYSTEM_CRASH` to terminal, `PERMISSION_DENIED` to tool adjustment. Add unit tests for each category. | M | `src/agent/primary_agent.py`, `tests/test_primary_agent.py` |
| 51.7 | **Structured `ProgressSnapshot` heartbeats** -- Update `_implement_ralph_with_heartbeat()` to call `agent.get_progress()` and serialize `ProgressSnapshot` as JSON for the heartbeat payload. Replace plain string format. Unit test: capture heartbeat arg and verify JSON structure. | S | `src/workflow/activities.py`, `tests/test_activities.py` |
| 51.8 | **Hardened cancel with `CancelResult`** -- Update cancel handling in `_implement_ralph_with_heartbeat()` to await `agent.cancel()`, inspect `CancelResult.was_forced` and `CancelResult.partial_output`. Log force-kill status. Remove the sleep-and-hope pattern. Unit test with mocked `CancelResult`. | S | `src/workflow/activities.py`, `tests/test_activities.py` |
| 51.9 | **SDK session lifecycle replaces `clear_session_if_stale()`** -- Add `max_session_iterations=20`, `max_session_age_minutes=120`, `continue_as_new_enabled=True` to `build_ralph_config()`. Remove the `clear_session_if_stale()` call from `_implement_ralph()` in the ralph code path. Unit test: verify config fields and absence of stale-session call. | S | `src/agent/ralph_bridge.py`, `src/agent/primary_agent.py`, `tests/test_primary_agent.py`, `tests/test_ralph_bridge.py` |

### Slice 4: Optimization Features (Cost/performance improvements, individually toggleable)

| # | Story | Size | Files to modify/create |
|---|-------|------|----------------------|
| 51.10 | **Progressive context loading with `ContextManager`** -- Use `ContextManager.trim_fix_plan()` in the task prompt builder to reduce token waste. Add `ralph_context_max_unchecked_items` setting (default 5). Fallback: full plan when setting is 0 or disabled. Unit test with a multi-section fix plan. | M | `src/agent/ralph_bridge.py`, `src/settings.py`, `tests/test_ralph_bridge.py` |
| 51.11 | **Dynamic model routing with `select_model()`** -- Map `TaskPacket.complexity_index` to `CostComplexityBand`. Call `select_model()` in `build_ralph_config()` to choose model per task. Add `ralph_model_routing_enabled` setting (default False). Unit test: trivial complexity -> Haiku, high -> Sonnet. | M | `src/agent/ralph_bridge.py`, `src/settings.py`, `tests/test_ralph_bridge.py` |
| 51.12 | **Prompt cache optimization with `split_prompt()`** -- Use `split_prompt()` to separate stable prefix from dynamic suffix when building the Ralph prompt. Wire `PromptParts` into the agent setup. Add `ralph_prompt_cache_enabled` setting (default False). Unit test: verify split produces non-empty prefix and suffix. | S | `src/agent/ralph_bridge.py`, `src/settings.py`, `tests/test_ralph_bridge.py` |
| 51.13 | **Metrics collection, adaptive timeout, and token rate limiting** -- Wire `JsonlMetricsCollector` into `RalphAgent` constructor. Add adaptive timeout config (`adaptive_timeout_enabled`, thresholds). Add `max_tokens_per_hour` for token-based rate limiting. All behind feature flags. Unit tests for each config path. | M | `src/agent/primary_agent.py`, `src/agent/ralph_bridge.py`, `src/settings.py`, `tests/test_ralph_bridge.py` |
| 51.14 | **Integration smoke test and workaround removal audit** -- Run Ralph agent end-to-end with a simple task using SDK 2.1.0. Verify: `files_changed` populated from JSONL, cost from `total_cost_usd`, heartbeat is JSON, stall detection thresholds active. Run `grep` audit confirming all five workarounds are removed/demoted per AC10. | M | `tests/integration/test_ralph_sdk_upgrade.py` |

---

## Execution Order

1. **Slice 1** (Stories 51.1-51.2) -- Day 1. Single commit. Must land atomically because new modules cross-import.
2. **Slice 2** (Stories 51.3-51.5) -- Days 2-3. Highest impact-to-effort ratio. Each story is independently committable.
3. **Slice 3** (Stories 51.6-51.9) -- Days 3-5. Observability and resilience improvements. Each story is independently committable.
4. **Slice 4** (Stories 51.10-51.14) -- Days 5-7. Optimization features, each behind a feature flag. Story 51.14 is the final verification gate.
5. **Workaround removal** -- Verified by Story 51.14 after Slices 2-3 are complete.

---

## Meridian Review Status

**Round 1: Pending**

| # | Question | Status |
|---|----------|--------|
| 1 | Are all acceptance criteria testable without human judgment? | Pending |
| 2 | Are constraints and non-goals explicit enough to prevent scope creep? | Pending |
| 3 | Do success metrics have baselines and targets? | Pending |
| 4 | Are dependencies identified and their status verified? | Pending |
| 5 | Is the story map ordered by risk reduction? | Pending |
| 6 | Can each story be completed in a single 15-minute AI loop? | Pending |
| 7 | Are "files to modify/create" listed for every story? | Pending |

**Red Flags:** None yet. Awaiting review.
