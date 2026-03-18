# Sprint Plan: Epic 30 Sprint 1 -- Real Provider Integration & Validation

**Planned by:** Helm
**Date:** 2026-03-18
**Status:** APPROVED -- Meridian review passed (2026-03-18)
**Sprint Duration:** 1 week (5 working days, 2026-03-18 to 2026-03-22)
**Capacity:** Single developer, 30 hours total (5 days x 6 productive hours), 77% allocation = 23 hours, 7 hours buffer

---

## Sprint Goal (Testable Format)

**Objective:** Build an evaluation harness for TheStudio's LLM-powered agents, then validate that the intent, QA, and primary agents produce correct structured output when switched from `llm_provider=mock` to `llm_provider=anthropic`. Validation uses a labeled dataset of 10 test issues and 10 synthetic evidence bundles, scored by dimension-specific functions.

**Test:** After all four stories (30.1 through 30.4) are complete:

1. `pytest tests/eval/test_eval_harness.py` passes -- 10 labeled test cases load, scoring functions produce numeric scores, result aggregation works.
2. `pytest tests/eval/test_intent_eval.py -m requires_api_key` produces valid `IntentAgentOutput` for at least 8/10 labeled issues. No validation errors on any of the 10.
3. `pytest tests/eval/test_qa_eval.py -m requires_api_key` detects planted defects in at least 7/10 evidence bundles. Clean bundles produce no S0/S1 defects.
4. `pytest tests/eval/test_primary_eval.py -m requires_api_key` produces non-empty agent summary and file change suggestions for 3/3 simple issues. No timeouts.
5. Total API cost for the full eval suite stays under $9 expected ($2 intent + $2 QA + $5 primary). Worst case: $19 ($2 + $2 + $15 if all 3 primary runs hit the $5 per-agent cap).
6. All existing 2,120+ tests pass (`pytest` green, `ruff check .` clean).
7. Eval results documented in `docs/EVAL-SPRINT1-RESULTS.md`.

**Constraint:** 5 working days. Changes confined to `src/eval/` (new package), `tests/eval/` (new test directory), and minor settings/flag fixes. No changes to existing agent configs, pipeline stages, or domain models. API-key-dependent tests are isolated behind a pytest marker and never run in CI without explicit opt-in. Total API spend for the full eval suite must stay under $9.

---

## What's In / What's Out

**In this sprint (4 stories, ~23 estimated hours):**
- Story 30.1: Evaluation Harness & Labeled Test Dataset
- Story 30.2: Intent Agent Real LLM Validation
- Story 30.3: QA Agent Real LLM Validation
- Story 30.4: Primary Agent Real LLM Validation

**Out of scope:**
- Enabling LLM for any agent in CI or production (flags stay False by default)
- Prompt tuning beyond what eval results suggest for parse success
- Eval for the remaining 5 agents (intake, context, router, recruiter, assembler)
- Automated regression suite (eval is manual/on-demand, not CI-gated)
- Changes to the `AnthropicAdapter`, `AgentRunner`, or agent configs (unless parse failures demand it)

---

## Dependency Review (30-Minute Pre-Planning)

### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| `THESTUDIO_ANTHROPIC_API_KEY` env var | Required for 30.2-30.4 | Cannot call real LLM | 30.1 works without it; 30.2-30.4 tests skip gracefully via marker |
| Anthropic Messages API availability | External service | Tests fail with HTTP errors | `httpx` timeout already 120s; retry logic in adapter; budget caps prevent runaway spend |
| `AgentRunner` + `AgentConfig` framework | Implemented (Epic 23) | No agent execution path | Confirmed working with mock provider |
| `IntentAgentOutput` schema | Implemented (`src/intent/intent_config.py`) | Cannot validate intent output | Confirmed: 7 fields, all with defaults |
| `QAAgentOutput` schema | Implemented (`src/qa/qa_config.py`) | Cannot validate QA output | Confirmed: 4 fields, all with defaults |
| `PrimaryAgentRunner` | Implemented (`src/agent/primary_agent.py`) | Cannot run primary agent eval | Confirmed; but see Risk #1 below |

### Internal Dependencies (Story-to-Story)

```
30.1 --> 30.2 --> 30.3
              \-> 30.4
```

- **30.1 has no dependencies** -- pure infrastructure, no API key, no existing code changes
- **30.2 depends on 30.1** -- uses `EvalCase`, `EvalResult`, `run_eval()`, scoring functions, and the labeled dataset
- **30.3 depends on 30.1 + 30.2** -- reuses harness infrastructure; uses real intent specs from 30.2 runs as QA input
- **30.4 depends on 30.1 + 30.2** -- uses real intent specs as primary agent input; reuses harness infrastructure

**Critical path:** 30.1 --> 30.2 --> (30.3 and 30.4 in parallel)

---

## Ordered Work Items

### Day 1-2: Evaluation Infrastructure (No API Key Needed)

#### Item 1: Story 30.1 -- Evaluation Harness & Labeled Test Dataset

**Estimate:** 6 hours (8 story points, M-L size)
**Rationale for sequence:** Foundation for everything else. Zero external dependencies. Can be built and tested entirely offline.

**Key tasks:**
- Create `src/eval/__init__.py`
- Create `src/eval/models.py`:
  - `EvalCase` dataclass: `issue_title`, `issue_body`, `labels`, `risk_flags`, `complexity`, `expected_goal_keywords`, `expected_constraints`, `expected_acs`, `expected_invariant_trigger` (bool), `case_id`, `category`
  - `EvalResult` dataclass: dimension scores (0.0-1.0), `passed` bool, `raw_output`, `parse_success`, `cost_usd`, `duration_ms`
  - `EvalSummary` dataclass: aggregated pass rate, mean scores per dimension, total cost, total duration
- Create `src/eval/scoring.py`:
  - `score_goal_clarity(output, expected_keywords) -> float` -- keyword overlap + non-empty check
  - `score_constraint_coverage(output, expected_constraints) -> float` -- fraction of expected constraints present
  - `score_ac_completeness(output, expected_acs) -> float` -- fraction of expected ACs covered, penalize title-restating
  - `score_invariant_presence(output, expects_invariants) -> float` -- binary: non-empty invariants when expected
  - `score_non_goal_specificity(output) -> float` -- non-empty and not just restating the title
  - `aggregate_scores(results) -> EvalSummary`
- Create `src/eval/dataset.py`:
  - 10 labeled `EvalCase` instances covering: simple bug fix, feature request, security fix, refactoring, documentation, breaking change, multi-file change, performance issue, dependency update, API design
  - Each case has realistic issue title/body (3-10 sentences) and expected outputs
  - `load_intent_dataset() -> list[EvalCase]`
- Create `src/eval/harness.py`:
  - `run_eval(agent_config, cases, settings_overrides) -> list[EvalResult]` -- runs agent against each case, captures output, scores it
  - Handles parse failures gracefully (score 0 on that dimension, continue)
  - Captures cost and duration per case
- Create `tests/eval/__init__.py`
- Create `tests/eval/test_eval_harness.py`:
  - Test dataset loads 10 cases with all required fields
  - Test each scoring function with known inputs/outputs
  - Test `run_eval` with mock adapter (no API key) -- verifies the plumbing
  - Test `aggregate_scores` produces correct summary
  - Test parse failure handling (bad JSON input)
  - At least 12 test cases

**Estimation reasoning:** The dataset is the most time-consuming part -- 10 realistic issues with expected outputs requires careful authoring. Each case needs a believable issue body, appropriate risk flags, and hand-labeled expected keywords/constraints/ACs. The scoring functions are straightforward string matching. The harness is thin glue around `AgentRunner`. 6 hours accounts for the dataset authoring effort (estimated 2.5h) plus the scoring/harness code and tests (3.5h).

**Unknowns:**
- Scoring function granularity: keyword-overlap scoring for "goal clarity" may be too coarse. Starting with keyword overlap + length checks; can refine in later sprints.
- How to handle `AgentRunner` dependencies (budget enforcer, model audit store, tracer) in eval context -- may need lightweight test fixtures that bypass DB.

**Done when:** `pytest tests/eval/test_eval_harness.py` passes. All 10 cases load. Scoring functions produce expected numeric scores for known inputs. Harness runs end-to-end with mock adapter.

---

### Day 2-3: Intent Agent Validation (First Real LLM Test)

#### Item 2: Story 30.2 -- Intent Agent Real LLM Validation

**Estimate:** 6 hours (8 story points, M-L size)
**Rationale for sequence:** Intent is the cheapest agent ($0.50 max budget, single-turn completion). Validates that the entire LLM adapter chain works: `AnthropicAdapter` -> Messages API -> JSON extraction -> `IntentAgentOutput` parse. Every downstream story depends on this working.

**Key tasks:**
- Create `src/eval/intent_eval.py`:
  - `run_intent_eval(cases=None) -> EvalSummary` -- loads dataset, configures intent agent with `llm_provider=anthropic` and `agent_llm_enabled["intent_agent"]=True`, runs eval harness, returns summary
  - Intent-specific scoring: applies all 5 scoring dimensions from 30.1
  - Cost tracking per case
- Create `tests/eval/test_intent_eval.py`:
  - Unit test (no API key): verify eval runner wiring with mock adapter
  - Integration test (marked `@pytest.mark.requires_api_key`): run against real Anthropic API
  - Assert: `IntentAgentOutput` parses without `ValidationError` for all 10 cases
  - Assert: goal field non-empty and contains relevant keywords for >= 8/10
  - Assert: constraints list non-empty for >= 9/10
  - Assert: invariants list non-empty for breaking_change cases
  - Assert: ACs are specific (not just restating title) for >= 8/10
  - Assert: total cost under $2
  - Log detailed per-case results for debugging
- Create `conftest.py` in `tests/eval/` with:
  - `requires_api_key` marker that skips when `THESTUDIO_ANTHROPIC_API_KEY` is empty
  - Shared fixtures for settings overrides (provider=anthropic, flag=True)
- If any cases fail to parse: diagnose whether the issue is in the prompt template or the JSON extraction logic. Document findings. Adjust prompt only if parse success rate is below 90%.

**Estimation reasoning:** The eval runner itself is thin -- most code is in the harness from 30.1. The bulk of the time is running the eval (10 API calls, ~30-60s each), analyzing results, and potentially diagnosing parse failures. If the `IntentAgentOutput` schema's JSON instruction in the system prompt is insufficient for the model to produce valid JSON, prompt tuning may be needed. Budget: 2 hours for code, 2 hours for running + analyzing + documenting, 2 hours buffer for prompt tuning.

**Unknowns:**
- Will the model consistently produce JSON that `_extract_json_block()` can parse? The framework has 3 extraction patterns (raw JSON, fenced JSON, brace-matching). If the model wraps JSON in explanation text without fences, pattern 3 (brace-matching) should catch it -- but this is the first real test.
- Token costs: `claude-sonnet-4-5` pricing at ~$3/M input, ~$15/M output. 10 cases with ~500 token input and ~300 token output each = ~$0.05 total. Well under $2 budget.

**Done when:** Integration test passes with >= 8/10 valid intent outputs. All 10 parse without error. Cost under $2. Results logged with per-case detail.

---

### Day 3-4: QA Agent Validation

#### Item 3: Story 30.3 -- QA Agent Real LLM Validation

**Estimate:** 6 hours (8 story points, M-L size)
**Rationale for sequence:** After 30.2 confirms the LLM adapter chain works, QA agent validation tests more complex reasoning (defect detection, severity classification). QA is still single-turn completion, same cost profile as intent.

**Key tasks:**
- Create `src/eval/qa_dataset.py`:
  - 10 synthetic evidence bundles: 7 with planted defects, 3 clean
  - Planted defect types: intent gap (ambiguous criterion), missing test coverage, security vulnerability (hardcoded secret), regression (broken existing test), implementation bug (wrong return type), performance issue (O(n^2) in hot path), compliance gap (missing audit log)
  - Each bundle includes: `acceptance_criteria`, `evidence` dict (agent_summary, test_results, lint_results, file_changes), `expected_defect_categories`, `expected_defect_count`
  - Clean bundles have complete evidence that genuinely satisfies all criteria
  - `load_qa_dataset() -> list[QAEvalCase]`
- Create `src/eval/qa_eval.py`:
  - `QAEvalCase` dataclass extending `EvalCase` with evidence bundle fields
  - QA-specific scoring:
    - `score_defect_detection(output, expected_count) -> float` -- fraction of planted defects found
    - `score_defect_classification(output, expected_categories) -> float` -- category match rate
    - `score_false_positive_rate(output, is_clean) -> float` -- penalize S0/S1 defects on clean bundles
  - `run_qa_eval(cases=None) -> EvalSummary`
- Create `tests/eval/test_qa_eval.py`:
  - Unit test: verify QA eval runner wiring with mock adapter
  - Integration test (`@pytest.mark.requires_api_key`):
    - Assert: `QAAgentOutput` parses without error for all 10 cases
    - Assert: defects detected in >= 7/10 cases with planted defects
    - Assert: clean cases produce no S0/S1 defects
    - Assert: defect categories match planted types for >= 5/7
    - Assert: total cost under $2

**Estimation reasoning:** The QA dataset is more complex than the intent dataset -- each evidence bundle needs a realistic agent summary, test results, and file changes that either do or do not satisfy acceptance criteria. Authoring 10 convincing bundles (7 with subtle planted defects, 3 genuinely clean) is the bottleneck. The QA agent's system prompt already expects `{acceptance_criteria}` and `{evidence_keys}` template variables, which the eval runner must populate via `AgentContext.extra`. 6 hours: 3 hours dataset authoring, 1.5 hours eval code, 1.5 hours running + analysis.

**Unknowns:**
- QA agent prompt has template variables `{acceptance_criteria}` and `{evidence_keys}` -- the eval runner must pass these via `context.extra` for `build_system_prompt()` to resolve them. Need to verify the exact variable names match.
- The QA system prompt instructs the model to produce JSON with `criteria_results`, `defects`, `intent_gaps`, and `edge_case_concerns`. If the model produces valid JSON but classifies defects differently than expected, the category-matching score will be low. This measures prompt quality, not a code bug.

**Done when:** Integration test passes with >= 7/10 defect detection. Clean bundles are clean. Cost under $2. Results logged.

---

### Day 4-5: Primary Agent Validation

#### Item 4: Story 30.4 -- Primary Agent Real LLM Validation

**Estimate:** 5 hours (5 story points, M size)
**Rationale for sequence:** Most expensive agent ($5 budget per run, multi-turn agentic mode with tool use). Smallest dataset (3 cases) to control cost. Depends on 30.2 for real intent specs.

**Key tasks:**
- **Resolve feature flag mismatch** (see Risk #1): The `PrimaryAgentRunner` uses `AgentConfig(agent_name="developer")` but `settings.agent_llm_enabled` has key `"primary_agent"`. The framework checks `agent_llm_enabled[config.agent_name]` which looks up `"developer"` -- a key that does not exist. Options:
  - (a) Add `"developer": False` to the settings dict (minimal change)
  - (b) Change `agent_name` in the developer config to `"primary_agent"` (breaks audit trail)
  - Recommend option (a): add the key, leave everything else unchanged
- Create `src/eval/primary_eval.py`:
  - Select 3 simplest cases from the intent dataset (simple bug fix, documentation, dependency update)
  - For each: run intent eval first to get a real `IntentAgentOutput`, then construct the primary agent context
  - Primary agent eval does NOT actually execute code -- it runs in completion mode (no tools) to test output generation only. The `claude_agent_sdk` import in agentic mode requires a real repo path; for eval, we test completion-mode output.
  - Alternative: if agentic mode is essential, mock the tool execution and validate the agent's planning/summary output
  - `run_primary_eval(cases=None) -> EvalSummary`
- Create `tests/eval/test_primary_eval.py`:
  - Unit test: verify primary eval runner wiring with mock adapter
  - Integration test (`@pytest.mark.requires_api_key`):
    - Assert: agent produces non-empty summary for all 3 cases
    - Assert: output references at least one file change per case
    - Assert: total cost under $5
    - Assert: no unhandled exceptions or timeouts (120s per case)

**Estimation reasoning:** Smaller dataset (3 cases) but more complex setup -- primary agent needs an intent spec as input, which means running intent eval first or using saved outputs from 30.2. The feature flag mismatch fix is straightforward (add a dict key). The main risk is the agentic mode dependency on `claude_agent_sdk` and a real repo path -- if we cannot run agentic mode in eval, we fall back to completion-mode validation. 5 hours: 1 hour flag fix + eval code, 1.5 hours dataset/context setup, 1.5 hours running + analysis, 1 hour buffer for agentic mode issues.

**Unknowns:**
- **Primary agent uses agentic mode** (`tool_allowlist` is non-empty), which imports `claude_agent_sdk` and needs a real repo path. For eval, we either: (a) provide a temp repo with minimal files, (b) strip tools and run completion mode, or (c) mock the SDK. Decision should be made at implementation time based on what 30.2 reveals about adapter reliability.
- Cost is harder to predict for agentic mode -- multi-turn conversations accumulate tokens. The $5 budget cap in settings is the guardrail.

**Done when:** Integration test passes for 3/3 cases. Non-empty summaries. Cost under $5. Feature flag mismatch resolved. No timeouts.

---

## Capacity Summary

| Story | Estimate | Day | Cumulative |
|-------|----------|-----|------------|
| 30.1 Eval Harness & Dataset | 6.0h | Day 1-2 | 6.0h |
| 30.2 Intent Agent Validation | 6.0h | Day 2-3 | 12.0h |
| 30.3 QA Agent Validation | 6.0h | Day 3-4 | 18.0h |
| 30.4 Primary Agent Validation | 5.0h | Day 4-5 | 23.0h |
| **Total** | **23.0h** | | **77% of 30h capacity** |
| **Buffer** | **7.0h** | | **23%** |

**Allocation rationale:** 77% allocation with 23% buffer. Justified because:
- This is the first time real LLM calls are being made in the project -- unknown failure modes are expected
- Dataset authoring (30.1 and 30.3) involves creative work that is harder to estimate
- API latency is unpredictable: 10 calls could take 5 minutes or 30 minutes
- Prompt tuning, if needed, is open-ended work that the buffer absorbs

---

## Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Feature flag mismatch:** `PrimaryAgentRunner` uses `agent_name="developer"` but `agent_llm_enabled` has key `"primary_agent"`. Framework lookup fails silently (defaults to False = fallback). | Confirmed | High (30.4 blocked without fix) | Add `"developer": False` to `agent_llm_enabled` dict in settings. One-line change. Must be done before 30.4 integration test. |
| 2 | **LLM output does not parse as structured JSON.** Model returns explanation text wrapping JSON, or produces malformed JSON. | Medium | Medium (eval scores 0 on parse-fail cases) | `_extract_json_block()` has 3 extraction patterns. If parse rate is below 90%, add explicit "respond with ONLY JSON" instruction to prompts. Framework already falls back on parse failure. |
| 3 | **API cost exceeds budget.** Unexpected token usage or retries inflate cost. | Low | Medium (sprint budget blown) | Per-agent budget caps in `AgentConfig.max_budget_usd`. Pipeline budget in `PipelineBudget`. Small datasets (10/10/3 cases). Expected: ~$9. Worst case: ~$19 (3 primary runs at $5 cap each). Intent/QA well under $2 each at ~$0.05 actual. |
| 4 | **Anthropic API rate limits or outages.** 429s or 5xx errors during eval runs. | Low | Low (tests skip, retry later) | `httpx` timeout is 120s. Tests marked with `requires_api_key` can be re-run independently. No CI dependency. |
| 5 | **`claude_agent_sdk` import fails in eval environment.** Primary agent agentic mode requires the SDK package. | Medium | Medium (30.4 needs redesign) | Fall back to completion-mode eval (strip tool_allowlist). Validates output quality without tool use. Agentic mode eval deferred to Sprint 2. |
| 6 | **QA agent prompt template variables (`{acceptance_criteria}`, `{evidence_keys}`) not populated correctly.** | Medium | Medium (QA eval produces empty/wrong output) | Read `AgentRunner.build_system_prompt()` -- it populates from `context.extra`. QA eval must pass these keys in `extra` dict. Verify at start of 30.3. |

---

## Compressible Stories (What Gets Cut If Time Runs Short)

**Two compressible stories identified:**

1. **Story 30.4 (Primary Agent Validation) -- first to defer.** The core eval harness and the two single-turn agent validations (intent + QA) deliver the most insight. The primary agent is the most expensive, most complex, and has the most unknowns (agentic mode, SDK dependency, feature flag mismatch). Deferring it to Sprint 2 loses primary agent validation but preserves the harness and the two cheaper agent validations. **Impact of deferral:** We know intent and QA work with real LLM but not the primary agent. Sprint 2 picks this up with lessons learned from 30.2 and 30.3.

2. **Story 30.3 dataset scope can compress from 10 to 5 evidence bundles** (4 planted + 1 clean). This saves ~1.5 hours of dataset authoring while still validating the QA agent's core defect detection capability. The remaining 5 bundles can be added in Sprint 2. **Impact of compression:** Weaker statistical confidence in QA agent accuracy, but still validates the end-to-end flow.

If time runs short, cut 30.4 first, then compress 30.3 dataset.

---

## Key Implementation Notes

### pytest Marker Strategy

All tests that call the real Anthropic API must be marked:

```python
@pytest.mark.requires_api_key
@pytest.mark.slow
```

The `conftest.py` in `tests/eval/` registers these markers and auto-skips when `THESTUDIO_ANTHROPIC_API_KEY` is empty. This ensures `pytest` (without markers) never makes API calls and never fails in environments without keys.

### Settings Override Pattern

Eval tests must temporarily override `settings.llm_provider` and `settings.agent_llm_enabled` without mutating the singleton. Options:
- `monkeypatch` in pytest fixtures
- Dependency injection via `AgentRunner` constructor
- Environment variable overrides in subprocess

Recommend `monkeypatch` for simplicity: it is already used in existing tests and automatically restores state.

### Feature Flag Fix Scope

The `"developer"` vs `"primary_agent"` key mismatch should be fixed in `src/settings.py` by adding `"developer": False` to the `agent_llm_enabled` dict. This is additive -- no existing behavior changes. Both keys can coexist (`"primary_agent"` for the settings dict documentation, `"developer"` for runtime lookup). Document the dual-key situation in a code comment.

---

## Definition of Done (Sprint Level)

- [ ] `src/eval/` package created with models, scoring, harness, dataset, and per-agent eval modules
- [ ] `tests/eval/` directory with unit tests (always run) and integration tests (marker-gated)
- [ ] `pytest tests/eval/test_eval_harness.py` passes without API key
- [ ] `pytest tests/eval/ -m requires_api_key` passes with API key (all 3 agent evals)
- [ ] Intent agent: >= 8/10 valid outputs, 10/10 parse success, cost < $2
- [ ] QA agent: >= 7/10 defect detection, clean bundles clean, cost < $2
- [ ] Primary agent: 3/3 non-empty summaries, cost < $5, no timeouts
- [ ] Feature flag mismatch resolved (`"developer"` key added to `agent_llm_enabled`)
- [ ] All existing 2,120+ tests pass (`pytest` green)
- [ ] `ruff check .` and `ruff format .` clean
- [ ] Eval results documented in `docs/EVAL-SPRINT1-RESULTS.md`
- [ ] Sprint plan reviewed by Meridian before execution begins

---

## Retro Reference

This is the first sprint for Epic 30. No prior eval work exists in the codebase. Lessons from Epic 26 Sprint 1 are reflected in: 77% allocation with 23% buffer, explicit feature-flag mismatch caught during dependency review (not during implementation), compressible story identification, and the "cheapest agent first" sequencing pattern.

The feature flag mismatch (Risk #1) was caught during this 30-minute dependency review -- exactly the kind of dependency that becomes a blocker if discovered mid-sprint. This validates the "dependency review before every scheduling decision" practice.

---

## Meridian Review Required

This sprint plan requires Meridian review before commit. Specifically:

1. Is the 77% allocation realistic given that this is the project's first real LLM integration?
2. Is the sequencing (harness first, cheapest agent next, most expensive last) correct?
3. Is the feature flag mismatch fix (add `"developer"` key) the right approach, or should the primary agent's `agent_name` be changed to `"primary_agent"` for consistency?
4. Should 30.4 be deferred to Sprint 2 proactively, given the agentic mode unknowns?
5. Is the $9 total API cost budget reasonable for initial validation?
6. Does the compressible-stories strategy (cut 30.4 first) protect the sprint goal?
7. Are the pytest marker and settings-override patterns the right testing approach?
