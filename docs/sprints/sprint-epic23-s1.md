# Sprint Plan: Epic 23 Sprint 1 — Framework + Primary Agent Conversion

**Planned by:** Helm
**Date:** 2026-03-16
**Status:** In Progress (Stories 1.1-1.9 complete, 1.8 complete 2026-03-16)
**Epic:** `docs/epics/epic-23-unified-agent-framework.md`
**Sprint Duration:** 2 weeks (10 working days)
**Capacity:** Single developer, 60 hours total (10 days x 6 productive hours), 77% allocation = 46 hours, 14 hours buffer

---

## Pre-Sprint Prerequisites (Must Complete Before Sprint Start)

Two investigations are assigned to Tech Lead and must be resolved before sprint planning is finalized. These are called out in Assumption 1 of the epic.

| # | Investigation | Owner | Status | Deadline | Impact on Sprint |
|---|--------------|-------|--------|----------|-----------------|
| P1 | **Claude Agent SDK completion-mode support.** Use existing `AnthropicAdapter` (`src/adapters/llm.py`) for non-tool agents. SDK is a subprocess wrapper — wrong for single-turn calls. | Claude | **COMPLETE** | **2026-03-16** | Story 1.4 estimate unchanged (M). No new client needed. See `docs/investigations/p1-sdk-completion-mode.md`. |
| P2 | **`instructor` library evaluation.** Use native Pydantic `model_validate_json()` + JSON extraction helper. Do not add `instructor`. | Claude | **COMPLETE** | **2026-03-16** | Story 1.5 estimate unchanged (S). No new dependency. See `docs/investigations/epic23-p2-parse-output-strategy.md`. |

**Both prerequisites complete as of 2026-03-16.** Sprint execution begins immediately.

---

## Sprint Goal (Testable Format)

**Objective:** Deliver the `AgentRunner` framework in `src/agent/framework.py` with both execution modes (agentic + completion), structured output parsing, observability, and feature flags -- then prove it by converting the Primary Agent to use it with zero regression. (Prompt injection guard, pipeline budget, and context compression are deferred to Sprint 1b.)

**Test:** After all committed stories are complete:

1. `src/agent/framework.py` exists and contains: `AgentConfig`, `AgentContext`, `AgentResult`, `PipelineBudget`, and `AgentRunner` classes.
2. `AgentRunner` supports two call paths: `_call_llm_agentic()` (tool loop via SDK) and `_call_llm_completion()` (single call, no tools). Path selection is automatic based on `tool_allowlist`.
3. `AgentRunner.run()` follows the documented lifecycle: span -> provider -> budget check (per-agent + pipeline) -> prompt build -> injection scan -> LLM call -> audit -> parse -> result.
4. Feature flag `AGENT_LLM_ENABLED["developer"]` controls whether the Primary Agent uses LLM or falls back to rule-based logic.
5. `pytest tests/agent/test_framework.py` passes with tests covering: provider resolution, budget check, audit recording, fallback dispatch, feature flag, structured output parsing, observability spans.
6. `pytest tests/agent/test_primary_agent_framework.py` passes: `implement()` uses `AgentRunner`, gateway selects model, audit is recorded, evidence bundle is produced.
7. ~~`pytest tests/agent/test_prompt_guard.py`~~ — **Deferred to Sprint 1b** (Story 1.11).
8. ~~`pytest tests/agent/test_pipeline_budget.py`~~ — **Deferred to Sprint 1b** (Story 1.12).
9. ~~`pytest tests/agent/test_context_compression.py`~~ — **Deferred to Sprint 1b** (Story 1.13).
10. All pre-existing tests still pass (`pytest` green, `ruff check .` clean).
11. Primary Agent's `implement()` and `handle_loopback()` create `AgentRunner` with `DeveloperAgentConfig` -- no direct gateway/SDK calls remain in `primary_agent.py`.

**Constraint:** 2 weeks (10 working days). Changes confined to `src/agent/`, `src/settings.py`, and test files. No changes to pipeline orchestration (`src/workflow/`), domain models, or other pipeline nodes. The framework must be production-safe: all LLM paths have fallback behavior, feature flags default to disabled.

---

## What's In / What's Out

**In this sprint (10 stories, ~44 estimated hours):**

| # | Story | Est | Track |
|---|-------|-----|-------|
| 1.1 | `AgentConfig`, `AgentContext`, `AgentResult` dataclasses | 2h | Foundation |
| 1.2 | `AgentRunner` core -- provider, budget, audit | 5h | Foundation |
| 1.7 | Feature flag infrastructure | 2h | Foundation |
| 1.4 | `AgentRunner` -- completion mode | 4h | Foundation |
| 1.3 | `AgentRunner` -- agentic mode (tool loop) | 4h | Foundation |
| 1.5 | Structured output parsing + instrumentation | 3h | Foundation |
| 1.6 | Observability and fallback | 4h | Foundation |
| 1.9 | Framework unit tests | 5h | Validation |
| 1.8 | Refactor Primary Agent to use `AgentRunner` | 6h | Conversion |
| 1.10 | Integration test: Primary Agent through framework | 4h | Validation |

**Deferred to Sprint 1b (3 stories, ~11 estimated hours):**

| # | Story | Est | Reason for Deferral |
|---|-------|-----|-------------------|
| 1.11 | Prompt injection guard | 5h | Defense-in-depth, not on critical path. Framework works without it. Can be inserted into `AgentRunner.run()` lifecycle as a standalone story later. |
| 1.12 | Pipeline budget | 3h | Per-agent budgets already enforced by 1.2. Pipeline-wide budget is an optimization for Sprint 2+ when multiple agents run per task. |
| 1.13 | Context compression | 3h | Only applies to agentic mode (Primary Agent). Current context sizes are manageable. Higher value once tool loops are longer. |

**Rationale for 10/13 split:** 13 stories in a single sprint at 46 productive hours = 3.5h average per story with zero slack. Stories 1.11, 1.12, 1.13 are additive features (guard, budget, compression) that enhance the framework but are not required for the core objective: "framework exists and Primary Agent uses it." Deferring them creates 7 hours of genuine buffer (46h capacity - 39h committed) and removes the risk of a 95%+ allocation sprint.

**Compressible stories (cut if time runs short):**
1. **1.10** (Integration test) -- Framework unit tests (1.9) provide confidence; integration test is stronger validation but can slip 2-3 days into Sprint 1b without blocking Sprint 2.
2. **1.5** (Structured output parsing) -- Can ship with raw string returns initially; parsing can be layered in before Sprint 2 conversions need it.

---

## Dependency Review

### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| Claude Agent SDK (`claude_agent_sdk`) | Installed (confirmed in `primary_agent.py`) | Cannot implement agentic mode | Already available |
| Anthropic Messages API client | Must verify availability | Story 1.4 blocked if P1 investigation says "use Messages API" | P1 investigation must complete pre-sprint |
| Model Gateway (`src/admin/model_gateway.py`) | Implemented (Epic 19) | Cannot resolve providers | Already complete |
| `BudgetEnforcer`, `ModelCallAudit`, `ModelRouter` | Implemented | No budget/audit/routing | Already complete |
| Observability tracing (`src/observability/tracing.py`) | Implemented | No spans | Already complete |
| Settings (`src/settings.py`) | Implemented | Cannot add feature flags | Already complete |
| `instructor` library (if chosen in P2) | Must verify | Story 1.5 approach changes | P2 investigation resolves this |

### Internal Dependencies (Story-to-Story)

```
1.1 (dataclasses) ──┬──> 1.2 (core runner) ──┬──> 1.4 (completion mode)
                     │                         ├──> 1.3 (agentic mode)
                     │                         ├──> 1.5 (structured output)
                     │                         └──> 1.6 (observability + fallback)
                     │
                     └──> 1.7 (feature flags)
                                               │
                     All of 1.2-1.7 ──────────> 1.9 (framework tests)
                                               │
                     1.6 + 1.9 ───────────────> 1.8 (Primary Agent refactor)
                                               │
                     1.8 ─────────────────────> 1.10 (integration test)
```

**Critical path:** 1.1 -> 1.2 -> 1.6 -> 1.9 -> 1.8 -> 1.10

This is a 6-story chain. At estimated hours: 2 + 5 + 4 + 5 + 6 + 4 = 26 hours on the critical path. With 46 productive hours over 10 days, this leaves 20 hours for the 4 parallel stories (1.7, 1.4, 1.3, 1.5) which total 13 hours. Healthy margin.

### Parallel Tracks

**Track A (Critical Path -- Framework Core):** 1.1 -> 1.2 -> 1.6 -> 1.9 -> 1.8 -> 1.10
**Track B (Execution Modes -- parallel after 1.2):** 1.4, 1.3, 1.5
**Track C (Feature Flags -- parallel after 1.1):** 1.7

Track B and C stories feed into 1.9 (tests) and 1.8 (refactor) but can be developed independently once their single upstream dependency is met. In practice with a single developer, these will be interleaved, but the dependency structure allows flexibility in daily ordering.

---

## Ordered Backlog with Rationale

### Day 1-2: Foundation Layer

**1. Story 1.1 -- `AgentConfig`, `AgentContext`, `AgentResult` dataclasses (S, 2h)**

- **Why first:** Every other story imports these types. Zero ambiguity, zero risk. Gets the data contract committed early so all subsequent stories code against real types, not placeholders.
- **Test:** Dataclasses instantiate with defaults, are frozen (immutable), and serialize to dict.
- **Unknown:** None. Purely structural.

**2. Story 1.2 -- `AgentRunner` core: provider, budget, audit (M, 5h)**

- **Why second:** The runner skeleton with `_resolve_provider()`, `_check_budget()`, `_record_audit()` is extracted from `primary_agent.py`. This is the highest-risk story in the foundation because it must correctly abstract patterns currently hardcoded in a working module. Getting this right early surfaces integration issues.
- **Test:** Unit tests for provider resolution (mocked gateway), budget check (mocked enforcer), audit recording (mocked store).
- **Unknown:** The `_resolve_provider` in `primary_agent.py` hardcodes `step="primary_agent"`. The framework version must parameterize this from config. Verify the gateway's `select_model()` accepts arbitrary step names.

**3. Story 1.7 -- Feature flag infrastructure (S, 2h)**

- **Why third:** Small, independent after 1.1. Having feature flags in place means every subsequent story can immediately wire up the toggle. If done later, we'd need to retrofit.
- **Test:** `settings.AGENT_LLM_ENABLED["developer"]` defaults to `False`. Setting it to `True` changes `AgentRunner.run()` behavior.
- **Unknown:** None. Simple dict in settings + check in runner.

### Day 3-5: Execution Modes

**4. Story 1.4 -- `AgentRunner` completion mode (M, 4h)**

- **Why before agentic:** Most Sprint 2 agents use completion mode (non-tool). De-risking this path first validates the more common usage pattern. Also directly validates the P1 investigation outcome.
- **Test:** `_call_llm_completion()` sends a single API call, returns raw text, does not enter a tool loop.
- **Unknown (significant):** Entirely depends on P1 investigation. If SDK has no completion mode, this story creates a second LLM client (Messages API). Estimate could inflate to 6h.

**5. Story 1.3 -- `AgentRunner` agentic mode (M, 4h)**

- **Why after completion:** The agentic mode is an extraction of `_run_agent()` from `primary_agent.py`. Lower novelty than completion mode (pattern already exists), but more code to extract.
- **Test:** `_call_llm_agentic()` wraps `claude_agent_sdk.query()`, respects `tool_allowlist`, `max_turns`, `permission_mode`.
- **Unknown:** The existing `_run_agent()` uses `async for message in query()`. The framework must handle the streaming iterator pattern cleanly. Straightforward but needs care.

**6. Story 1.5 -- Structured output parsing + instrumentation (S, 3h)**

- **Why after execution modes:** Parsing applies to the output of both modes. Needs raw text from either path to validate.
- **Test:** Given a Pydantic schema and matching JSON string, `_parse_output()` returns a validated model instance. On invalid JSON, returns raw string and emits `agent.parse_failure` counter.
- **Unknown:** Depends on P2 (instructor vs raw Pydantic). Low risk either way.

### Day 5-6: Lifecycle Completion

**7. Story 1.6 -- Observability and fallback (M, 4h)**

- **Why here:** This story wires up the complete `run()` lifecycle: span creation, fallback dispatch on failure, feature flag integration, and `build_system_prompt()` / `build_user_prompt()`. It requires all prior foundation pieces to exist.
- **Test:** `run()` creates a span with correct attributes. On LLM failure with `fallback_fn` configured, `used_fallback=True` in result. Feature flag disabled -> immediate fallback.
- **Unknown:** Fallback function signature must match what existing rule-based functions provide. Verify that `evaluate_eligibility`, `build_intent`, etc. can be wrapped in a common `Callable[[AgentContext], str]` signature. (This is a Sprint 2 concern but worth validating the pattern now.)

### Day 6-8: Testing

**8. Story 1.9 -- Framework unit tests (M, 5h)**

- **Why before conversion:** Tests lock down the framework contract before the high-risk refactor (1.8) begins. If the refactor breaks something, these tests identify whether it's a framework bug or a conversion bug.
- **Test:** Full coverage of `AgentRunner` lifecycle: provider resolution, budget check, audit recording, fallback dispatch, feature flag, structured output parsing, observability spans. Minimum 15 test cases.
- **Unknown:** Mocking strategy for `claude_agent_sdk.query()`. Need to verify the SDK's interface is mockable.

### Day 8-9: The Big Conversion

**9. Story 1.8 -- Refactor Primary Agent to use `AgentRunner` (L, 6h)**

- **Why this is the largest story:** `primary_agent.py` is ~410 lines of working production code. The refactor must:
  - Create `DeveloperAgentConfig` with all current settings
  - Replace `_run_agent()`, `_resolve_provider()`, `_record_audit_and_spend()` with `AgentRunner` equivalents
  - Preserve `implement()` and `handle_loopback()` public signatures exactly
  - Keep `_parse_changed_files()` and `EvidenceBundle` construction (these are Primary Agent-specific, not framework concerns)
  - All existing tests must pass without modification
- **Test:** `implement()` and `handle_loopback()` produce identical `EvidenceBundle` results. No direct gateway/SDK calls remain in `primary_agent.py`. All `test_primary_agent*.py` tests pass.
- **Risk flag:** This is the highest-risk story in the sprint. If the framework abstraction doesn't fit the Primary Agent's actual patterns, we discover it here. This is why the framework tests (1.9) come first -- they validate the framework independently before we stress-test it with a real agent.
- **Unknown:** `handle_loopback()` has a different prompt construction pattern than `implement()`. Need to verify `build_user_prompt()` override mechanism handles both paths.

### Day 9-10: Integration Validation

**10. Story 1.10 -- Integration test: Primary Agent through framework (M, 4h)**

- **Why last:** This is the capstone test. It proves the full stack: `implement()` -> `AgentRunner` -> Model Gateway -> (mocked) SDK -> audit + evidence. If this passes, the sprint goal is met.
- **Test:** End-to-end test with database (async session), mocked LLM, real gateway routing, real audit store. Verify: correct model selected, audit record created, evidence bundle has expected fields, feature flag toggle works.
- **Unknown:** Test infrastructure for async DB + mocked LLM + real gateway. May need a test fixture pattern that doesn't exist yet. Budget 1h for fixture setup.

---

## Estimation Summary

| # | Story | Epic Size | Sprint Est | Risk | Confidence |
|---|-------|-----------|-----------|------|------------|
| 1.1 | Dataclasses | S | 2h | Low | High |
| 1.2 | Core runner | M | 5h | Medium | Medium -- abstraction must fit all 8 agents |
| 1.7 | Feature flags | S | 2h | Low | High |
| 1.4 | Completion mode | M | 4h | Medium | Medium -- depends on P1 investigation |
| 1.3 | Agentic mode | M | 4h | Low | High -- extracting existing pattern |
| 1.5 | Structured output | S | 3h | Low | High |
| 1.6 | Observability + fallback | M | 4h | Medium | Medium -- lifecycle wiring complexity |
| 1.9 | Framework tests | M | 5h | Low | High |
| 1.8 | Primary Agent refactor | L | 6h | **High** | Medium -- 410-line production module |
| 1.10 | Integration test | M | 4h | Medium | Medium -- test infrastructure unknown |
| | **Total committed** | | **39h** | | |
| | **Buffer (46 - 39)** | | **7h (15%)** | | |

### Deferred stories (Sprint 1b)

| # | Story | Epic Size | Sprint Est | Notes |
|---|-------|-----------|-----------|-------|
| 1.11 | Prompt injection guard | M | 5h | Can be added to `run()` lifecycle without touching other stories |
| 1.12 | Pipeline budget | S | 3h | `PipelineBudget` class + integration into `AgentContext` |
| 1.13 | Context compression | M | 3h | Agentic-mode only; low urgency until tool loops are longer |
| | **Total deferred** | | **11h** | |

### Estimation Risks and Assumptions

1. **P1 outcome affects 1.4 estimate.** If SDK has completion mode, 1.4 is 3-4h. If we need a separate Messages API client, 1.4 is 5-6h. The 4h estimate assumes a clean SDK path.
2. **1.8 is the riskiest story.** The refactor touches a production module. If the framework abstraction doesn't fit cleanly (e.g., `handle_loopback` needs special lifecycle handling), this story could expand to 8-10h. The 7h buffer absorbs one such expansion.
3. **All stories touch the same file.** Stories 1.1-1.6, 1.12, 1.13 all write to `src/agent/framework.py`. In a single-developer sprint this is fine (no merge conflicts), but the file will be large. Consider whether the file should be split into `framework.py` (runner) and `framework_types.py` (dataclasses) at the end. This is a cleanup task, not a story.
4. **Test infrastructure may not exist.** Stories 1.9 and 1.10 assume we can mock the Claude Agent SDK and the Model Gateway. If the mocking patterns don't exist, add 1-2h to each. The buffer covers this.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| P1 investigation finds SDK has no completion mode | Medium | 1.4 estimate increases 50% | Buffer absorbs it; P1 must finish before sprint starts |
| Primary Agent refactor (1.8) doesn't fit framework abstraction | Low-Medium | 6h story becomes 10h | Framework tests (1.9) run first to validate; 7h buffer available |
| All stories in one file causes review/merge complexity | Low | Confusion, not schedule risk | Single developer; split file as cleanup at end |
| `handle_loopback()` needs a different lifecycle than `implement()` | Medium | 1.8 scope creep | Investigate during 1.2 (core runner design); add `run_mode` parameter if needed |
| Mocking Claude Agent SDK is harder than expected | Low | 1.9 and 1.10 estimates increase | Check SDK interface during 1.3 (agentic mode extraction) |

---

## Sizing Flags: Stories That May Be Mis-Sized

1. **Story 1.2 (M) may be undersized.** "Provider resolution, budget, audit" is three distinct subsystems being abstracted. Each has its own error paths. If the Model Gateway's `select_model()` interface needs adaptation for parameterized step names, this becomes an L.

2. **Story 1.6 (M) is doing a lot.** "Observability and fallback" plus `build_system_prompt()` plus `build_user_prompt()` plus feature flag check in `run()`. This is really the "wire everything together" story. Consider whether the prompt builder methods should split into 1.6a (prompts) and 1.6b (lifecycle wiring). As planned, 4h is tight.

3. **Story 1.5 (S) is correctly sized.** The epic says S, and I agree. Pydantic `model_validate_json()` is well-understood. The instrumentation (counters) is straightforward.

4. **Story 1.8 (L) is correctly sized but carries the most variance.** Could be 4h if the abstraction fits perfectly. Could be 10h if it doesn't. The 6h estimate is the geometric mean of those outcomes.

---

## Daily Plan (Approximate)

| Day | Focus | Stories | Checkpoint |
|-----|-------|---------|------------|
| 1 | Foundation | 1.1 (complete), 1.2 (start) | Dataclasses importable, runner skeleton compiles |
| 2 | Foundation | 1.2 (complete), 1.7 (complete) | Core runner methods work in isolation, flags in settings |
| 3 | Execution modes | 1.4 (complete) | Completion mode sends/receives LLM call |
| 4 | Execution modes | 1.3 (complete), 1.5 (start) | Agentic mode wraps SDK |
| 5 | Lifecycle | 1.5 (complete), 1.6 (start) | Structured output parses Pydantic models |
| 6 | Lifecycle | 1.6 (complete) | `run()` executes full lifecycle end-to-end |
| 7 | Testing | 1.9 (complete) | Framework unit tests green |
| 8 | Conversion | 1.8 (start) | Primary Agent imports framework |
| 9 | Conversion | 1.8 (complete) | All existing Primary Agent tests pass |
| 10 | Integration | 1.10 (complete) | Integration test green; sprint goal met |

**Buffer days:** If any story takes longer than estimated, days 9-10 absorb the slack. If the sprint is on track by day 8, the buffer can be used to pull one deferred story (1.12 Pipeline Budget is the best candidate at 3h).

---

## Sprint 1b Backlog (Deferred)

If Sprint 1 completes on time, these three stories form a 1-week Sprint 1b before Sprint 2 begins. If Sprint 1 runs long, they merge into Sprint 2's backlog.

**Hard constraint (Meridian review 2026-03-16):** Story 1.11 (prompt injection guard) **must ship before Sprint 2 begins**. Sprint 2 routes untrusted GitHub issue content through LLM agents — doing so without injection scanning is a security gap that requires explicit sign-off to waive. Sprint 1b is the expected vehicle; if Sprint 1b is cut, 1.11 must move into Sprint 2 as a P0 prerequisite before any agent conversion stories start.

| Priority | Story | Rationale |
|----------|-------|-----------|
| 1 | 1.11 Prompt injection guard | **MUST ship before Sprint 2.** Security layer for untrusted input flowing to LLM agents. |
| 2 | 1.12 Pipeline budget | Needed once multiple agents run per task (Sprint 2) |
| 3 | 1.13 Context compression | Useful but not urgent until tool loops get longer |

---

## Definition of Done (Sprint Level)

- [ ] All 10 committed stories pass their individual tests
- [ ] `pytest` passes (full suite, not just new tests)
- [ ] `ruff check .` and `ruff format --check .` clean
- [ ] `src/agent/framework.py` contains the complete `AgentRunner` class
- [ ] `src/agent/primary_agent.py` uses `AgentRunner` -- no direct SDK/gateway calls
- [ ] Feature flags default to disabled (safe for production)
- [ ] No changes to pipeline orchestration or domain models
- [ ] Sprint retrospective scheduled

---

## Meridian Review Record

**Reviewed:** 2026-03-16 | **Verdict:** Conditional Pass

**Helm's questions and Meridian's answers:**

1. **Is the 10/13 split justified?** Yes, conditionally. Story 1.11 (injection guard) must ship before Sprint 2 begins — hard constraint added to Sprint 1b backlog.
2. **Is the 2-week sprint length appropriate?** Yes. 39h committed at 77% allocation is conservative and correct.
3. **Is Story 1.8 estimated correctly?** Yes. 6h is reasonable; 7h buffer absorbs variance. No spike needed.
4. **Are P1/P2 tracked with owners and deadlines?** Now yes — Tech Lead named by 2026-03-19, findings due 2026-03-21, sprint start 2026-03-23.

**Fixes applied from Meridian review:**
- Sprint goal test items 7-9 marked as deferred (matched to Sprint 1b stories)
- P1/P2 given calendar dates, owner naming deadline, and fallback sprint start date
- Injection guard (1.11) given hard "must ship before Sprint 2" constraint
- Buffer narrative corrected (2h → 7h)
- Sprint goal objective updated to reflect 10-story scope

---

## Execution Progress

| # | Story | Status | Date | Notes |
|---|-------|--------|------|-------|
| 1.1 | Dataclasses | **Done** | 2026-03-16 | `AgentConfig`, `AgentContext`, `AgentResult` in `framework.py` |
| 1.2 | Core runner | **Done** | 2026-03-16 | `AgentRunner` with `_resolve_provider`, `_check_budget`, `_record_audit` |
| 1.7 | Feature flags | **Done** | 2026-03-16 | `agent_llm_enabled` dict in `settings.py`, registered in settings service |
| 1.4 | Completion mode | **Done** | 2026-03-16 | `_call_llm_completion()` using existing `AnthropicAdapter` |
| 1.3 | Agentic mode | **Done** | 2026-03-16 | `_call_llm_agentic()` wrapping `claude_agent_sdk` |
| 1.5 | Structured output | **Done** | 2026-03-16 | `_parse_output()` with `_extract_json_block()`, span attributes for parse metrics |
| 1.6 | Observability + fallback | **Done** | 2026-03-16 | Full `run()` lifecycle with spans, fallback dispatch, prompt builders |
| 1.9 | Framework tests | **Done** | 2026-03-16 | 31 tests in `test_framework.py` |
| 1.8 | Primary Agent refactor | **Done** | 2026-03-16 | `PrimaryAgentRunner` subclass, `_make_developer_config()` factory. Removed `_run_agent`, `_resolve_provider`, `_estimate_tokens`, `_record_audit_and_spend`. 15 tests updated. Zero regression. |
| 1.10 | Integration test | Pending | | |

**Test count:** 1,745 unit tests passing (1,436 existing + 31 framework + 15 gateway + others). Lint clean.

---

*Plan produced by Helm. References: `thestudioarc/personas/helm-planner-dev-manager.md`, `docs/epics/epic-23-unified-agent-framework.md`, `CLAUDE.md`.*
