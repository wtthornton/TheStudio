# Epic 32: Model Routing & Cost Optimization

> **Status:** Draft
> **Epic Owner:** Primary Developer (solo)
> **Duration:** 3-4 months (8 sprints)
> **Created:** 2026-03-18
> **Meridian Review:** Round 1: Pending

---

## 1. Title

**Cut Pipeline LLM Costs ~58% Through Intelligent Model Routing, Caching, and Budget Controls**

---

## 2. Narrative

### The Problem

Epic 30 Sprint 1 ripped the curtain off the cost picture. The intent agent alone costs $0.023 per issue against real Claude Sonnet. Projecting across all 9 pipeline agents, a full issue costs $2-8 depending on complexity. At 50 issues/day that is $3,000-12,000/month in API spend --- enough to make the platform economically unviable before it ships to a second user.

The irony: we already solved the *routing* problem. `ModelRouter` in `src/admin/model_gateway.py` assigns intake and context to FAST (Haiku), but every other agent defaults to BALANCED (Sonnet) even when cheaper models would produce identical results. The expert routing step (which covers both the router and recruiter agents under the combined `"expert_routing"` step name) and the assembler agent all do structured classification or merge work --- tasks where Haiku 4.5 matches Sonnet quality at one-fifth the cost. We have the infrastructure. We just never tuned it.

> **Step Name Mapping:** The codebase uses different naming conventions across modules. `DEFAULT_ROUTING_RULES` in `model_gateway.py` uses step names (`"expert_routing"` covers both router and recruiter as one rule), while `agent_llm_enabled` in `settings.py` uses agent names (`"router_agent"`, `"recruiter_agent"`). Story 32.4 must update the `"expert_routing"` rule or split it into two rules to match the per-agent granularity in settings.

Meanwhile, the Anthropic API offers two cost levers we are not pulling at all: **prompt caching** (reduced input costs for repeated system prompts) and the **Batch API** (50% discount on non-interactive calls). Our system prompts are 80-90% static across issues --- the same agent persona, rules, and output schema, with only the issue-specific context changing. That is textbook cache-eligible content.

### Why Now

The cost data from Epic 30 is fresh. Epic 31 fixed the pricing model so our cost estimates are now accurate. The eval harness (`src/eval/`) exists and can validate that downgrading agents to cheaper models does not degrade output quality. Every day we delay this work, we burn money on API calls that a FAST-class model handles just as well.

### What Success Looks Like

A pipeline operator configures per-issue budget caps by trust tier, sees a real-time cost dashboard broken down by agent and repo, and knows that cheap agents run on cheap models without quality loss --- because eval scores prove it.

---

## 3. References

| Artifact | Location | Relevance |
|----------|----------|-----------|
| Model Gateway (router, budget, audit) | `src/admin/model_gateway.py` | Foundation --- ModelRouter, RoutingRule, BudgetSpec, ModelCallAudit already exist |
| Model Spend aggregation | `src/admin/model_spend.py` | SpendReport with by_provider, by_step, by_model breakdowns |
| Agent Framework | `src/agent/framework.py` | AgentRunner.build_system_prompt, PipelineBudget, PIPELINE_BUDGET_DEFAULTS |
| LLM Adapter | `src/adapters/llm.py` | AnthropicAdapter --- httpx-based, no caching or batch support yet |
| Settings | `src/settings.py` | Feature flags pattern, agent_llm_enabled, llm_provider |
| Eval harness | `src/eval/harness.py` | Eval infrastructure for validating model downgrades |
| Admin UI router | `src/admin/ui_router.py` | Jinja2 templates, existing spend report integration |
| Architecture: Model Runtime | `thestudioarc/26-model-runtime-and-routing.md` | Routing rules spec |
| Epic 30 (Real Provider Integration) | `docs/epics/epic-30-real-provider-integration.md` | Cost discovery findings |
| Epic 31 (OAuth Token Support) | `docs/epics/epic-31-anthropic-max-oauth-adapter.md` | Fixed ProviderConfig pricing |
| Anthropic API Docs | External | Prompt caching, Batch API, 2026 pricing |

---

## 4. Acceptance Criteria

### AC 1: Optimized Agent-to-Model Routing
Router, recruiter, and assembler agents route to FAST (Haiku) by default. Routing rules are updated in `DEFAULT_ROUTING_RULES`. The change is gated behind a feature flag `cost_optimization_routing_enabled` (default: False). When the flag is off, existing BALANCED routing applies unchanged.

### AC 2: Eval Validation for Model Downgrades
The 4 agents targeted for FAST routing (intake, context, expert_routing, assembler) each have an eval test suite that runs against both FAST and BALANCED models. The `expert_routing` eval covers both router and recruiter behavior (they share one routing rule). Eval scores for each downgraded agent must meet a configurable quality threshold (default: 80% of BALANCED baseline score) before the routing change takes effect.

> **Step-to-agent mapping for routing rules:**
>
> | Routing step (`DEFAULT_ROUTING_RULES`) | Settings agent(s) (`agent_llm_enabled`) | Current class | Target class |
> |---|---|---|---|
> | `intake` | `intake_agent` | FAST | FAST (no change) |
> | `context` | `context_agent` | FAST | FAST (no change) |
> | `expert_routing` | `router_agent`, `recruiter_agent` | BALANCED | FAST |
> | `assembler` | `assembler_agent` | BALANCED | FAST (pending eval) |
> | `intent` | `intent_agent` | BALANCED | BALANCED (no change) |
> | `primary_agent` | `developer` / `primary_agent` | BALANCED | BALANCED (no change) |
> | `qa_eval` | `qa_agent` | BALANCED | BALANCED (no change) |

### AC 3: Per-Issue Budget Caps by Trust Tier
BudgetSpec and PipelineBudget support per-trust-tier budget caps configurable via settings: $2.00 for Observe, $5.00 for Suggest, $8.00 for Execute. When a budget cap is hit, the pipeline halts gracefully with a BudgetExceededError that includes the step and cumulative spend. Budget caps are exposed in the Admin Settings UI.

### AC 4: Prompt Caching for System Prompts
The AnthropicAdapter sends system prompts with Anthropic's cache_control headers. System prompt content that is identical across issues (agent persona, rules, output schema) is marked as cacheable. The LLMResponse captures cache_creation_input_tokens and cache_read_input_tokens from the API response. Cost estimation uses cached input rates when cache hits occur.

### AC 5: Cost Tracking Dashboard
The Admin UI includes a Cost Dashboard page showing: (a) per-agent cost breakdown for the selected time window, (b) per-repo cost breakdown, (c) per-day trend chart data (JSON), (d) cache hit rate percentage, (e) budget utilization per active task. The dashboard reads from ModelCallAudit records via the existing SpendReport infrastructure.

### AC 6: Batch API Support for Non-Interactive Agents
The LLM adapter supports Anthropic's Batch API for agents that do not require real-time responses. Context enrichment is the primary candidate. Batch mode is a per-agent config flag. The adapter polls for batch completion and returns results through the same LLMResponse interface. Batch calls record a 50% cost discount in the audit trail.

### AC 7: No Regression in Mock-Mode Tests
All existing tests pass unchanged when feature flags are off. No new external dependencies are added. Mock adapter behavior is unaffected by caching and batch changes.

### 4b. Top Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | Haiku quality insufficient for router/recruiter/assembler | Medium | High | Eval harness validates before routing change takes effect; flag reverts to BALANCED |
| R2 | Prompt caching API changes or undocumented behavior | Low | Medium | Cache is additive; falls back to uncached request if headers are rejected |
| R3 | Batch API latency too high for acceptable pipeline throughput | Medium | Medium | Batch only for context enrichment initially; interactive agents never batched |
| R4 | Budget caps too aggressive, causing legitimate issues to fail | Medium | High | Caps are configurable; defaults are 2-4x the expected per-issue cost |
| R5 | Cost tracking overhead impacts pipeline latency | Low | Low | Audit writes are async; SpendReport queries are admin-only |

---

## 5. Constraints & Non-Goals

### Constraints

- **No new dependencies.** Prompt caching and Batch API use the existing httpx client with additional headers/endpoints.
- **Feature flags for everything.** Every optimization is off by default and independently toggleable.
- **Mock-mode tests unchanged.** MockLLMAdapter gets no caching or batch behavior --- those are Anthropic-specific.
- **Solo developer.** Stories must be independently deliverable in 1-2 day increments.
- **Existing infrastructure.** ModelRouter, BudgetSpec, ModelCallAudit, SpendReport, and the Admin UI template system are the foundation. Extend, do not replace.

### Non-Goals

- **Multi-provider routing** (e.g., OpenAI fallback). This epic is Anthropic-only.
- **Automatic model selection based on prompt complexity.** Routing is rule-based per agent, not dynamic per request.
- **Cost alerting or Slack notifications.** The dashboard is read-only; alerting is a future epic.
- **Token-level prompt optimization** (e.g., shortening system prompts). This epic routes to cheaper models and caches prompts; it does not rewrite them.
- **Usage-based billing or chargeback.** Cost tracking is for operational visibility, not customer billing.
- **Real-time streaming cost display.** Dashboard updates on page refresh, not via WebSocket.

---

## 6. Stakeholders & Roles

| Role | Person | Responsibility |
|------|--------|----------------|
| Epic Owner / Developer | Primary Developer | All implementation, testing, eval runs |
| Reviewer | Meridian (persona) | Epic review, sprint review, quality gates |
| Planner | Helm (persona) | Sprint breakdown, sequencing |
| Architecture | Saga (persona) | Epic definition, scope boundaries |

---

## 7. Success Metrics

| Metric | Baseline (Current) | Target | How Measured |
|--------|-------------------|--------|--------------|
| Cost per issue (Observe tier) | TBD — measured in Story 32.0 | < 50% of measured baseline | ModelCallAudit sum per task_id |
| Cost per issue (Suggest tier) | TBD — measured in Story 32.0 | < 50% of measured baseline | ModelCallAudit sum per task_id |
| FAST-routed agents (intake, context, expert_routing, assembler) | 2 of 4 (intake, context) | 4 of 4 (pending eval validation) | DEFAULT_ROUTING_RULES inspection |
| Eval quality score for downgraded agents | Not measured | >= 80% of BALANCED baseline | Eval harness comparison runs |
| Prompt cache hit rate (after warm-up) | 0% (no caching) | > 60% | cache_read_input_tokens / total_input_tokens |
| Monthly API cost at 50 issues/day | $3,000-12,000 projected | $900-3,600 projected | SpendReport monthly aggregation |
| Budget-exceeded incidents (false positives) | N/A | < 5% of issues | BudgetExceededError count / total issues |
| Pipeline latency impact from cost tracking | N/A | < 50ms added per agent call | Latency delta in ModelCallAudit |

### Cost Projection Table

Estimated monthly costs with optimizations applied. Assumes average 9 agent calls per issue, current baseline of $4/issue average.

| Volume | Baseline (No Optimization) | After Routing (AC1) | + Caching (AC4) | + Batch (AC6) | Total Savings |
|--------|---------------------------|--------------------|--------------------|---------------|---------------|
| 10 issues/day | $1,200/mo | $720/mo (40% saved) | $576/mo (52% saved) | $504/mo (58% saved) | **$696/mo saved** |
| 50 issues/day | $6,000/mo | $3,600/mo | $2,880/mo | $2,520/mo | **$3,480/mo saved** |
| 100 issues/day | $12,000/mo | $7,200/mo | $5,760/mo | $5,040/mo | **$6,960/mo saved** |

**Routing breakdown:** 4 of 9 routing steps (intake, context, expert_routing, assembler) targeted for FAST. Intake and context are already FAST. Expert_routing (router + recruiter) and assembler move from Sonnet ($3/$15 per 1M tokens) to Haiku ($1/$5 per 1M tokens) --- a 3-5x cost reduction on ~33% of agent calls. Assembler downgrade contingent on eval results.

**Caching impact:** System prompts average ~2,000 tokens per agent. With 9 agents and >60% cache hit rate, input token costs drop ~20% on top of routing savings.

**Batch impact:** Context enrichment (1 of 9 agents) moves to Batch API for 50% discount on that step. Conservative estimate since only one agent is batch-eligible initially.

---

## 8. Context & Assumptions

### Business Rules

- **Trust tier determines budget ceiling.** Observe tier gets the tightest budget because it is purely informational. Execute tier gets the most because it produces auto-merged PRs and must not be constrained into low-quality output.
- **Quality gates before cost optimization.** No agent is downgraded to a cheaper model until eval scores confirm acceptable quality. The eval threshold is configurable but defaults to 80% of the BALANCED baseline.
- **Budget exhaustion fails the pipeline gracefully.** A budget-exceeded task gets a clear error in its TaskPacket status. It does not silently produce low-quality output.

### Dependencies

- **Epic 30 Sprint 1 (Stories 30.1-30.4):** Must be complete — eval harness, intent eval, QA eval, and primary agent eval provide the foundation for model-class comparison. **Status: Complete as of 2026-03-18.** Slice 1 of this epic can start once integration tests pass with a real API key.
- **Epic 30 Sprint 2 (Stories 30.5-30.6):** Postgres backend and real GitHub provider. Not strictly blocking Slice 1 (routing/eval), but required before Slice 4 (cost dashboard with persistent audit data).
- **Epic 31 (OAuth Token Support):** Deferred indefinitely due to TOS risk. This epic uses API keys only. No dependency.
- **Eval harness (`src/eval/`):** Must support configurable model class per eval run. If not, Story 32.3 extends it.
- **Anthropic Batch API:** Available as of 2025 (GA). Uses `/v1/messages/batches` endpoint. Confirmed available for API key auth. **Risk:** Batch API terms may change; Slice 5 includes a compatibility check before implementation.

### Systems Affected

| System | Change |
|--------|--------|
| `src/admin/model_gateway.py` | Updated DEFAULT_ROUTING_RULES; new feature flag checks in ModelRouter.resolve_class |
| `src/agent/framework.py` | PipelineBudget reads trust-tier caps from settings; AgentRunner passes cache headers |
| `src/adapters/llm.py` | AnthropicAdapter gains prompt caching headers, Batch API support, cache token tracking |
| `src/admin/model_spend.py` | SpendReport adds by_repo, by_day, cache_hit_rate aggregations |
| `src/admin/ui_router.py` | New cost dashboard route |
| `src/admin/templates/` | New cost dashboard template |
| `src/settings.py` | New feature flags and budget cap settings |
| `src/eval/` | New eval suites for 5 agents; model-class comparison mode |

### Assumptions

- Anthropic's prompt caching API uses `cache_control` blocks in the system message array and returns `cache_creation_input_tokens` and `cache_read_input_tokens` in the usage response. If the API shape differs, Story 32.9 adapts. **Note:** `LLMRequest.system` is currently typed as `str`. Prompt caching requires it to become `list[dict]` (content blocks with `cache_control`). Story 32.9 must handle this type change with backward compatibility.
- Anthropic's Batch API endpoint is `/v1/messages/batches`. Batch requests accept the same body format as synchronous messages. Results are polled via GET.
- Haiku 4.5 can reliably produce structured JSON output matching agent output schemas for classification and routing tasks. Eval Story 32.2 validates this before routing changes take effect.
- The existing `InMemoryModelAuditStore` is sufficient for development and low-volume production. PostgreSQL-backed audit (`src/admin/persistence/pg_model_audit.py`) handles high-volume scenarios.

---

## Story Map

### Slice 1: Baseline Measurement & Routing Optimization (Highest Risk Reduction)

**Goal:** Measure real per-agent costs, prove that cheap agents work on cheap models, then flip the routing.

**Blocked by:** Epic 30 Stories 30.1-30.4 (eval harness + LLM validation for intent, QA, primary agents). These are complete as of 2026-03-18.

**Planned start:** 2026-03-25 (after Epic 30 Sprint 1 integration tests are validated with real API key).

| Story | Title | Files to Modify/Create | Estimate |
|-------|-------|----------------------|----------|
| 32.0 | Establish measured per-agent cost baselines | Run 10 full pipeline executions on real Anthropic API, record per-agent token counts and costs via ModelCallAudit. Produce a baseline cost table (mean ± stddev per agent) that replaces "$2-8 estimated" in success metrics. | 1 day |
| 32.1 | Add cost optimization feature flags to Settings | `src/settings.py` | 0.5 day |
| 32.2 | Eval suites for 4 target agents (intake, context, expert_routing, assembler) | `src/eval/intake_eval.py`, `src/eval/context_eval.py`, `src/eval/routing_eval.py`, `src/eval/assembler_eval.py`, `tests/eval/` | 2.5 days |
| 32.3 | Model-class comparison mode in eval harness | `src/eval/harness.py`, `src/eval/models.py` | 1 day |
| 32.4 | Update DEFAULT_ROUTING_RULES: split `expert_routing` into `router` + `recruiter` (or keep combined) and set to FAST | `src/admin/model_gateway.py` | 0.5 day |
| 32.5 | Feature-flag gate in ModelRouter.resolve_class | `src/admin/model_gateway.py`, `tests/admin/test_model_gateway.py` | 1 day |

### Slice 2: Budget Controls (Operational Safety)

**Goal:** Prevent runaway costs before scaling up issue volume.

| Story | Title | Files to Modify/Create | Estimate |
|-------|-------|----------------------|----------|
| 32.6 | Trust-tier budget caps in Settings and PipelineBudget | `src/settings.py`, `src/agent/framework.py`, `tests/agent/test_framework.py` | 1.5 days |
| 32.7 | Budget cap admin UI controls | `src/admin/ui_router.py`, `src/admin/templates/settings.html` | 1 day |
| 32.8 | Graceful budget-exceeded handling in AgentRunner | `src/agent/framework.py`, `tests/agent/test_framework.py` | 1 day |

### Slice 3: Prompt Caching (Cost Reduction Layer 2)

**Goal:** Reduce input token costs for repeated system prompts.

| Story | Title | Files to Modify/Create | Estimate |
|-------|-------|----------------------|----------|
| 32.9 | Prompt caching headers in AnthropicAdapter | `src/adapters/llm.py`, `tests/adapters/test_llm.py` | 1.5 days |
| 32.10 | Cache token tracking in LLMResponse and ModelCallAudit | `src/adapters/llm.py`, `src/admin/model_gateway.py`, `src/agent/framework.py` | 1 day |
| 32.11 | Cache hit rate in SpendReport | `src/admin/model_spend.py`, `tests/admin/test_model_spend.py` | 0.5 day |

### Slice 4: Cost Dashboard (Visibility)

**Goal:** Operator can see where money goes and whether optimizations are working.

| Story | Title | Files to Modify/Create | Estimate |
|-------|-------|----------------------|----------|
| 32.12 | Per-repo and per-day aggregation in SpendReport | `src/admin/model_spend.py` | 1 day |
| 32.13 | Cost dashboard template and route | `src/admin/ui_router.py`, `src/admin/templates/cost_dashboard.html` | 1.5 days |
| 32.14 | Budget utilization widget (active tasks vs. caps) | `src/admin/templates/cost_dashboard.html`, `src/admin/model_spend.py` | 1 day |

### Slice 5: Batch API (Cost Reduction Layer 3)

**Goal:** 50% discount on non-interactive agent calls.

| Story | Title | Files to Modify/Create | Estimate |
|-------|-------|----------------------|----------|
| 32.15 | Batch API support in AnthropicAdapter | `src/adapters/llm.py`, `tests/adapters/test_llm.py` | 2 days |
| 32.16 | Per-agent batch mode config flag | `src/settings.py`, `src/agent/framework.py` | 0.5 day |
| 32.17 | Batch cost discount in audit recording | `src/admin/model_gateway.py`, `src/agent/framework.py` | 0.5 day |

**Total estimated effort:** ~19 working days across 8 sprints (~3 months with buffer).

---

## Meridian Review Status

**Round 1: CONDITIONAL PASS** (2026-03-18)

Verdict: 4 PASS, 3 CONDITIONAL. Three must-fix gaps identified:
1. ~~RF5: Step name mismatch between routing rules and settings~~ — Fixed: added step-to-agent mapping table in AC2 and narrative
2. ~~RF4: Success metrics use "$2-8 estimated" baselines~~ — Fixed: added Story 32.0 for measured baselines; metrics reference Story 32.0
3. ~~Q4: Missing dependency gates and dates~~ — Fixed: added specific Epic 30 story references, planned start date, Batch API availability

Should-fix items also addressed: title percentage corrected to ~58%, AC2 agent list clarified, LLMRequest.system type change documented, Batch API availability risk noted.

**Round 2: PASS** (2026-03-18)

All 7 questions passed. No red flags. Minor observations (non-blocking):
- AC3 budget caps intentionally tighten existing PIPELINE_BUDGET_DEFAULTS — Story 32.6 should override, not create
- Story 32.4 must preserve assembler's `security: STRONG` overlay override when changing base class to FAST

| # | Question | Status |
|---|----------|--------|
| 1 | Are acceptance criteria testable without ambiguity? | PASS |
| 2 | Are all non-goals explicit and reasonable? | PASS |
| 3 | Do success metrics have baselines and targets? | PASS |
| 4 | Are dependencies identified and sequenced? | PASS |
| 5 | Is the story map ordered by risk reduction? | PASS |
| 6 | Can Claude/Cursor implement each story from the epic alone? | PASS |
| 7 | Are feature flags and rollback paths defined? | PASS |
