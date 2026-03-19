# Sprint 2: Per-Agent Cost Baselines (Story 32.0)

> **Date:** 2026-03-18
> **Environment:** Docker prod stack (`thestudio-prod-app-1`)
> **API:** Real Anthropic API (`sk-ant-api03-*`)
> **Test:** `tests/integration/test_docker_full_pipeline.py::TestCostBaselines`

## Measured Baselines

| Agent | Model | Model Class | Tokens In | Tokens Out | Cost | Latency |
|-------|-------|-------------|-----------|------------|------|---------|
| intake_agent | claude-haiku-4-5 | FAST | 74 | 118 | $0.0007 | 1.8s |
| context_agent | claude-haiku-4-5 | FAST | 73 | 922 | $0.0047 | 8.9s |
| intent_agent | claude-sonnet-4-6 | BALANCED | 76 | 2,048 | $0.0309 | 38.5s |
| router_agent | claude-sonnet-4-6 | BALANCED | 73 | 932 | $0.0142 | 16.4s |
| assembler_agent | claude-sonnet-4-6 | BALANCED | 76 | 2,048 | $0.0309 | 35.3s |
| qa_agent | claude-sonnet-4-6 | BALANCED | 79 | 340 | $0.0053 | 8.7s |
| **Total (6 agents)** | | | | | **$0.0868** | |

## Projections

| Metric | Value |
|--------|-------|
| Per-issue cost (9 agents, estimated) | ~$0.13 |
| Monthly @ 10 issues/day | ~$39 |
| Monthly @ 50 issues/day | ~$195 |
| Monthly @ 100 issues/day | ~$390 |

## Key Observations

1. **Cost is much lower than projected.** Original estimates ($2-8/issue) were based on the stale `cost_per_1k_tokens` values. After fixing ProviderConfig pricing (Story 31.1), actual costs are 15-60x lower.

2. **Intent and assembler are the most expensive agents** — both hit max_tokens (2,048) regularly. These are BALANCED class and should stay BALANCED per Epic 32 analysis.

3. **Router/recruiter costs are moderate** ($0.014). Downgrading to FAST (Haiku) could save ~60% on this step. Epic 32 Story 32.4 targets this.

4. **Intake and context are already on FAST** (Haiku) and cost < $0.005 combined. No optimization needed.

5. **QA agent is efficient** at $0.005 — stays on BALANCED for quality.

## Cost Optimization Impact (Epic 32)

| Optimization | Savings | From → To |
|-------------|---------|-----------|
| Route expert_routing to FAST | ~$0.010/issue | router from $0.014 to ~$0.004 |
| Route assembler to FAST | ~$0.025/issue | assembler from $0.031 to ~$0.006 |
| Prompt caching (60% hit rate) | ~$0.008/issue | System prompt token savings |
| **Total projected savings** | **~$0.043/issue (50%)** | |

## Comparison: Estimated vs Actual

| Source | Per-Issue Cost | Notes |
|--------|---------------|-------|
| Epic 30 narrative estimate | $2-8 | Wildly overestimated |
| Epic 31 billing session | $2.08 for 80+ calls | Included all test overhead |
| This measurement (6 agents) | $0.087 | Clean single-issue baseline |
| This measurement (9 agents est.) | ~$0.13 | Extrapolated |
