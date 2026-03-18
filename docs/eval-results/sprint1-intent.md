# Sprint 1 Intent Agent Eval Results

> **Date:** 2026-03-18
> **Story:** 30.2 (Intent Agent Real LLM Validation)
> **Model:** claude-sonnet-4-6 (balanced class)
> **Provider:** Anthropic Messages API (`api.anthropic.com/v1/messages`)
> **API Version:** 2023-06-01

---

## Summary

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Valid intent specs | >= 8/10 | **10/10** | PASS |
| Parse success rate | 100% | **100%** | PASS |
| Total cost | < $2.00 | **$0.13** | PASS |
| Avg duration per case | -- | **25.6s** | Documented |
| Total duration (10 cases) | -- | **256.5s** | Documented |

**All acceptance criteria met. Intent agent produces high-quality structured output with real Claude.**

---

## Dimension Scores (Mean Across 10 Cases)

| Dimension | Mean Score | Notes |
|-----------|-----------|-------|
| Goal clarity | **0.93** | All goals actionable, keyword-relevant |
| Constraint coverage | **0.86** | 2 cases scored 0.50 (see below) |
| AC completeness | **0.96** | Near-perfect extraction of explicit + implicit ACs |
| Invariant presence | **1.00** | Perfect — invariants present for all breaking-change cases |
| Non-goal specificity | **1.00** | Perfect — specific, non-trivial non-goals for all cases |

---

## Per-Case Results

| Case ID | Category | Pass | Goal | Constraints | ACs | Invariants | Non-Goals | Cost | Duration |
|---------|----------|------|------|-------------|-----|------------|-----------|------|----------|
| bug_fix_01 | bug_fix | YES | 0.86 | 1.00 | 1.00 | 1.00 | 1.00 | $0.004 | 15.9s |
| feature_02 | feature | YES | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | $0.005 | 23.3s |
| security_03 | security | YES | 0.82 | 1.00 | 1.00 | 1.00 | 1.00 | $0.007 | 33.1s |
| refactor_04 | refactor | YES | 0.82 | 0.80 | 1.00 | 1.00 | 1.00 | $0.005 | 24.2s |
| docs_05 | documentation | YES | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | $0.005 | 20.6s |
| breaking_06 | breaking_change | YES | 0.82 | 1.00 | 1.00 | 1.00 | 1.00 | $0.036 | 37.7s |
| multi_file_07 | multi_file | YES | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | $0.031 | 31.4s |
| perf_08 | performance | YES | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | $0.005 | 22.0s |
| dep_update_09 | dependency_update | YES | 1.00 | 1.00 | 0.85 | 1.00 | 1.00 | $0.005 | 20.2s |
| api_design_10 | api_design | YES | 1.00 | 0.75 | 0.76 | 1.00 | 1.00 | $0.030 | 28.0s |

---

## Cost Analysis

| Metric | Value |
|--------|-------|
| Total cost (10 cases) | **$0.1345** |
| Average cost per case | **$0.0135** |
| Cheapest case | bug_fix_01 ($0.004) |
| Most expensive case | breaking_06 ($0.036) |
| Projected cost per 100 issues | ~$1.35 |
| Budget ceiling per agent call | $0.50 (configured) |
| Sprint 1 intent budget | $2.00 |
| Actual spend vs budget | **6.7%** |

**Cost is negligible.** Even at scale (100 issues/day), intent agent cost would be ~$1.35/day. The $0.50 per-call budget cap will never be hit at current token usage.

---

## Observations

### Strengths
1. **Perfect parse rate** — all 10 cases produced valid JSON matching `IntentAgentOutput` schema. The `_extract_json_block()` parser handled all outputs correctly.
2. **Invariant extraction** — the model correctly identified invariants for all breaking-change cases (refactor, breaking_change, multi_file, performance, dependency_update). This was the highest-risk dimension.
3. **Non-goal inference** — even when issues had no "out of scope" section, the model inferred reasonable non-goals.
4. **AC synthesis** — the model went beyond extracting explicit checkboxes to synthesize implicit acceptance criteria.

### Weaknesses (Minor)
1. **Constraint coverage at 0.50 for feature_02 and multi_file_07** — the scoring uses substring matching against expected constraint keywords ("tests", "backward"). The model expressed these concepts with different wording. This is a scoring sensitivity issue, not an agent quality issue.
2. **Longer duration for complex cases** — security_03 (33.1s) and breaking_06 (37.7s) took 50-80% longer than simple cases. Expected behavior for higher-complexity issues.
3. **Higher cost for complex cases** — breaking_06 ($0.036) and api_design_10 ($0.030) cost 6-7x more than simple cases. Still well under budget.

### Failure Modes Observed
None. All 10 cases succeeded on first attempt. No timeouts, no parse failures, no rate limits.

---

## Recommendations

1. **Proceed to Story 30.3 (QA Agent)** — the LLM adapter chain is proven: settings -> provider resolution -> AnthropicAdapter -> Messages API -> JSON extraction -> Pydantic parse. This same chain will work for QA and primary agents.
2. **No prompt changes needed** — 10/10 pass rate exceeds the 8/10 target. The intent system prompt in `src/intent/intent_config.py` is effective as-is.
3. **Scoring function refinement** — consider fuzzy matching for constraint coverage scoring to reduce false negatives from synonym usage. Low priority since all cases still pass.
4. **OAuth adapter (future)** — investigate supporting Claude Max subscription OAuth tokens (`sk-ant-oat01-...`) as an alternative auth method in `AnthropicAdapter`. This would let the $200/month Max plan cover pipeline API costs.
