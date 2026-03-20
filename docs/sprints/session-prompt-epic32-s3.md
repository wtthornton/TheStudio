# Session Prompt: Epic 32 Slice 1 Completion + Slice 3 Start

## Context

Phase 7 is in progress. Epic 30 is **fully delivered** (3 sprints). Epic 32 Slice 2 (budget controls) is **fully delivered** (Stories 32.6-32.8). All pre-existing test failures remain resolved — **1783+ unit tests passing, zero failures.**

The roadmap critical path: finish Slice 1 remaining stories, then start Slice 3 (prompt caching). Full epic spec: `docs/epics/epic-32-model-routing-cost-optimization.md`.

## What's Done

### Epic 30 (Real Provider Integration & Validation) — COMPLETE
- Sprint 1-3: Eval harness, 6 agent eval suites, Postgres + GitHub integration, Docker validation, failure catalog, suggest tier validation, gateway audit, approval bypass. 1783/1783 tests passing.

### Epic 32 Slice 1 — PARTIALLY COMPLETE
- **Story 32.0** (baselines): COMPLETE — $0.087/issue measured. See `docs/eval-results/sprint2-cost-baselines.md`
- **Story 32.1** (cost optimization feature flags): COMPLETE — `cost_optimization_routing_enabled` in settings, feature-flagged off
- **Story 32.5** (feature-flag gate): COMPLETE — `ModelRouter.resolve_class` checks the flag
- **Stories 32.2, 32.3, 32.4**: NOT YET DONE — see below

### Epic 32 Slice 2 (Budget Controls) — COMPLETE
- **Story 32.6**: `get_budget_for_tier(tier)` in `src/agent/framework.py` — when `cost_optimization_routing_enabled=True`, returns tighter caps from `settings.cost_optimization_budget_tiers` (observe=$2, suggest=$5, execute=$8). Falls back to `PIPELINE_BUDGET_DEFAULTS` when disabled. 4 tests.
- **Story 32.7**: Budget Controls admin UI card — new partial `settings_budget_controls.html` with per-tier inputs ($0.50-$50 range). GET/POST routes in `ui_router.py`. Shows routing-disabled warning. Audit-logged.
- **Story 32.8**: Pipeline budget exhaustion now **raises `BudgetExceededError`** (with `step` kwarg) instead of silently falling back. Error includes step name, cumulative spend, and cap. 3 tests + 1 updated test.

### Failure Catalog Updates
- **F5** (max_tokens): **Fixed** — already at 4096 in `framework.py` and `LLMRequest`
- **F8** (assembler schema): **Fixed** — `@field_validator` coerces `list[str]` to `str`
- **F7** (router template variables): Open — eval calibration task
- **F9** (eval scoring calibration): Open — affects quality reporting for intake/context

## What's Next (Priority Order)

### 1. Finish Epic 32 Slice 1: Remaining Routing Stories (2 days est.)

**Story 32.3: Model-class comparison mode in eval harness (1 day)**
- Extend eval harness to support running the same test against FAST vs BALANCED
- Compare quality scores to validate model downgrades don't regress quality
- Need a way to specify model_class override per eval run
- Key files: `src/eval/harness.py`, `src/eval/models.py`

**Story 32.4: Update DEFAULT_ROUTING_RULES (0.5 day)**
- Split `"expert_routing"` into `"router"` + `"recruiter"` (or keep combined)
- Set both to FAST (Haiku)
- **Must preserve `security: STRONG` overlay override for assembler** (Meridian Round 2 note)
- Key file: `src/admin/model_gateway.py`

**Story 32.2: Eval suites for target agents (1 day — optional, can defer)**
- Eval suites for the 4 target agents (intake, context, expert_routing, assembler) comparing FAST vs BALANCED
- May depend on Story 32.3 being done first
- Key files: `src/eval/intake_eval.py`, `src/eval/context_eval.py`, `src/eval/routing_eval.py`, `src/eval/assembler_eval.py`

### 2. Epic 32 Slice 3: Prompt Caching (3 days est.)

**Story 32.9: Prompt caching headers in AnthropicAdapter (1.5 days)**
- Send system prompts with Anthropic's `cache_control` headers
- `LLMRequest.system` is currently `str` — needs to become `list[dict]` (content blocks) for caching
- Must maintain backward compatibility with string system prompts
- Key files: `src/adapters/llm.py`, `tests/adapters/test_llm.py`

**Story 32.10: Cache token tracking in LLMResponse and ModelCallAudit (1 day)**
- `LLMResponse` gains `cache_creation_input_tokens` and `cache_read_input_tokens`
- `ModelCallAudit` records cache metrics
- Cost estimation uses cached input rates when cache hits occur
- Key files: `src/adapters/llm.py`, `src/admin/model_gateway.py`, `src/agent/framework.py`

**Story 32.11: Cache hit rate in SpendReport (0.5 day)**
- `SpendReport` adds `cache_hit_rate` aggregation
- Key files: `src/admin/model_spend.py`, `tests/admin/test_model_spend.py`

### 3. Fix F7 — Router template variables (15 min)
- Router agent's system prompt template has `{base_role}`, `{overlays}`, `{risk_flags}`, `{required_classes}`
- Eval `router_context_builder` must inject these into `context.extra`
- Key files: `src/eval/routing_eval.py`, `src/routing/routing_config.py`

## Key Files

| File | Purpose |
|------|---------|
| `docs/epics/epic-32-model-routing-cost-optimization.md` | Full epic spec with all 5 slices |
| `src/settings.py` | Feature flags, budget caps settings |
| `src/agent/framework.py` | AgentRunner, PipelineBudget, get_budget_for_tier, BudgetExceededError raise |
| `src/admin/model_gateway.py` | ModelRouter, DEFAULT_ROUTING_RULES, RoutingRule, BudgetExceededError (with step kwarg) |
| `src/admin/model_spend.py` | SpendReport aggregation |
| `src/admin/ui_router.py` | Budget controls routes (GET/POST), settings partials |
| `src/admin/templates/partials/settings_budget_controls.html` | Budget tier admin UI |
| `src/adapters/llm.py` | LLMRequest, LLMResponse, AnthropicAdapter — target for prompt caching |
| `src/eval/harness.py` | Eval infrastructure — target for comparison mode |
| `docs/FAILURE_CATALOG.md` | F5 fixed, F7/F9 open |

## Existing Infrastructure to Build On

**get_budget_for_tier** (new in `src/agent/framework.py`):
- Returns settings-based caps when `cost_optimization_routing_enabled=True`
- Falls back to `PIPELINE_BUDGET_DEFAULTS` when disabled
- Used by workflow code to create `PipelineBudget` with the right cap

**BudgetExceededError** (updated in `src/admin/model_gateway.py`):
- Now accepts optional `step` kwarg
- Message format: `"Budget exceeded for task {id} at step '{step}': ${spent} spent of ${limit} limit"`
- Raised by AgentRunner when pipeline budget is exhausted (Story 32.8)

**Budget Controls UI** (new in `src/admin/ui_router.py`):
- GET `/admin/ui/partials/settings/budget-controls` — renders per-tier inputs
- POST `/admin/ui/partials/settings/budget-controls` — validates $0.50-$50 range, persists JSON, audit-logged
- Shows routing-disabled warning when `cost_optimization_routing_enabled=False`

**LLMRequest** (in `src/adapters/llm.py`):
- `system: str` — needs to become `str | list[dict]` for prompt caching
- `enable_caching: bool = False` — already exists as a flag
- `max_tokens: int = 4096` — already set correctly (F5 resolved)

**ModelRouter** (in `src/admin/model_gateway.py`):
- `resolve_class()` already checks `cost_optimization_routing_enabled` flag (Story 32.5)
- `DEFAULT_ROUTING_RULES` — currently has `expert_routing` as combined step

## Codebase Health

- **1783+ unit tests passing**, zero failures
- **~244 integration tests** (across Epics 30, 32)
- Pre-existing failures: ALL RESOLVED
- Ruff clean, no lint issues
- F5 fixed, F8 fixed

## Phase 7 Exit Criteria Status

| Criterion | Status |
|-----------|--------|
| Intent agent valid specs >= 8/10 with real Claude | **Met** |
| QA agent catches planted defects >= 7/10 | Partial (scoring needs tuning) |
| Primary agent valid output 3/3 simple issues | **Met** |
| Postgres integration 6/6 | **Met** |
| GitHub integration 4/4 | **Met** |
| Full pipeline processes real GitHub issue into draft PR | Pending |
| Cost model documented with accurate estimates | **Met** |
| Deployment runbook enables cold start | **Met** |
| Cost optimization reduces per-issue spend by >= 50% | Pending (Epic 32 Slices 3-5) |

## Budget

- Slice 1 remaining (Stories 32.3, 32.4): ~1.5 days
- Slice 3 (prompt caching, Stories 32.9-32.11): ~3 days
- Bug fixes (F7): ~15 min
- Total: ~4.5 days
