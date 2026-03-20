# Session Prompt: Epic 32 Slice 4 + Remaining Cleanup

## Context

Phase 7 is in progress. Epic 30 is **fully delivered** (3 sprints). Epic 32 Slices 1-3 are **fully delivered** (Stories 32.0-32.11). All pre-existing test failures remain resolved — **2069+ unit tests passing** (1 pre-existing flaky container reaper test excluded).

The roadmap critical path: Epic 32 Slice 4 (cost dashboard), then Slice 5 (Batch API). Full epic spec: `docs/epics/epic-32-model-routing-cost-optimization.md`.

## What's Done

### Epic 30 (Real Provider Integration & Validation) — COMPLETE
- Sprint 1-3: Eval harness, 6 agent eval suites, Postgres + GitHub integration, Docker validation, failure catalog, suggest tier validation, gateway audit, approval bypass. 1783/1783 tests passing.

### Epic 32 Slice 1 — COMPLETE
- **Story 32.0** (baselines): $0.087/issue measured
- **Story 32.1** (feature flags): `cost_optimization_routing_enabled` in settings
- **Story 32.2** (eval suites): Eval suites for intake, context, routing, assembler agents
- **Story 32.3** (comparison mode): `run_comparison_eval()` in `src/eval/harness.py`, `ModelComparisonResult` in `src/eval/models.py` — 5 tests
- **Story 32.4** (routing rules): **Fixed step name mismatch** — renamed `"expert_routing"` → `"routing"` in `DEFAULT_ROUTING_RULES` and `_COST_OPTIMIZED_STEPS`. Both router and recruiter agents use `pipeline_step="routing"`, which now matches the rule key. Security overlay override preserved.
- **Story 32.5** (feature-flag gate): `ModelRouter.resolve_class` checks `cost_optimization_routing_enabled`

### Epic 32 Slice 2 (Budget Controls) — COMPLETE
- **Story 32.6**: `get_budget_for_tier(tier)` in `src/agent/framework.py`
- **Story 32.7**: Budget Controls admin UI card in `settings_budget_controls.html`
- **Story 32.8**: `BudgetExceededError` with `step` kwarg, raised on budget exhaustion

### Epic 32 Slice 3 (Prompt Caching) — COMPLETE
- **Story 32.9**: Prompt caching headers already implemented in `AnthropicAdapter`:
  - `_build_system_payload()` converts system prompt to content blocks with `cache_control: {"type": "ephemeral"}`
  - Beta header `prompt-caching-2024-07-31` added when `enable_caching=True` and `cost_optimization_caching_enabled=True`
  - Cache tokens extracted from usage response (`cache_creation_input_tokens`, `cache_read_input_tokens`)
- **Story 32.10**: Cache token tracking added to `ModelCallAudit` (`cache_creation_tokens`, `cache_read_tokens`). `AgentRunner._record_audit` passes cache tokens from `LLMResponse` to audit records. 2 new tests.
- **Story 32.11**: `SpendReport` gains `total_cache_creation_tokens`, `total_cache_read_tokens`, `cache_hit_rate`. `get_spend_report()` computes cache hit rate from audit records. 5 new tests.

### Failure Catalog Updates
- **F5** (max_tokens): **Fixed** — already at 4096
- **F7** (router template variables): **Fixed** — `fmt.update(context.extra)` resolves all 4 template variables
- **F8** (assembler schema): **Fixed** — `@field_validator` coerces `list[str]` to `str`
- **F9** (eval scoring calibration): Open — affects quality reporting for intake/context

### Flaky Test
- `tests/agent/test_container_manager.py::TestContainerManagerReaper::test_reap_old_containers` — pre-existing timing-sensitive failure, not caused by any recent changes

## What's Next (Priority Order)

### 1. Epic 32 Slice 4: Cost Dashboard (3.5 days est.)

**Story 32.12: Per-repo and per-day aggregation in SpendReport (1 day)**
- Add `by_repo` breakdown to `SpendReport` (group by repo from `ModelCallAudit`)
- Add `by_day` breakdown for time-series view
- Key files: `src/admin/model_spend.py`, `tests/unit/test_model_spend.py`

**Story 32.13: Cost dashboard template and route (1.5 days)**
- New admin route `GET /admin/ui/cost-dashboard`
- Template showing total cost, breakdowns by step/provider/model, cache hit rate
- HTMX partials for time window selector (24h, 7d, 30d)
- Key files: `src/admin/ui_router.py`, `src/admin/templates/cost_dashboard.html`

**Story 32.14: Budget utilization widget (1 day)**
- Show active tasks vs. budget caps per trust tier
- Visual budget gauge (used / limit) for each tier
- Key files: `src/admin/templates/cost_dashboard.html`, `src/admin/model_spend.py`

### 2. Epic 32 Slice 5: Batch API (3 days est.)

**Story 32.15: Batch API support in AnthropicAdapter (2 days)**
- Add `AnthropicAdapter.batch_submit()` for non-interactive calls
- Endpoint: `POST /v1/messages/batches`, poll via `GET /v1/messages/batches/{id}`
- Returns a `BatchResult` with results when complete
- Key files: `src/adapters/llm.py`, `tests/adapters/test_llm.py`

**Story 32.16: Per-agent batch mode config flag (0.5 day)**
- Add `batch_eligible: bool = False` to `AgentConfig`
- Context enrichment agent is batch-eligible; interactive agents are not
- Key files: `src/settings.py`, `src/agent/framework.py`

**Story 32.17: Batch cost discount in audit recording (0.5 day)**
- When a call is batched, apply 50% discount to cost estimation
- Record `batch: bool` flag in `ModelCallAudit`
- Key files: `src/admin/model_gateway.py`, `src/agent/framework.py`

### 3. Fix F9 — Eval scoring calibration (30 min)
- Intake/context eval scoring dimensions don't match their output schemas
- Custom scoring functions exist but pass thresholds may not account for different scales
- Key files: `src/eval/intake_eval.py`, `src/eval/context_eval.py`

### 4. Update Epic Status Tracker
- Mark Slices 1 and 3 as COMPLETE
- Update test count, story statuses
- Key file: `docs/epics/EPIC-STATUS-TRACKER.md`

## Key Files

| File | Purpose |
|------|---------|
| `docs/epics/epic-32-model-routing-cost-optimization.md` | Full epic spec with all 5 slices |
| `src/settings.py` | Feature flags, budget caps settings |
| `src/agent/framework.py` | AgentRunner, PipelineBudget, _record_audit (now with cache tokens) |
| `src/admin/model_gateway.py` | ModelRouter, DEFAULT_ROUTING_RULES (routing step fixed), ModelCallAudit (cache fields added), BudgetExceededError |
| `src/admin/model_spend.py` | SpendReport (cache_hit_rate added), get_spend_report() |
| `src/admin/ui_router.py` | Budget controls routes, settings partials — extend for cost dashboard |
| `src/adapters/llm.py` | LLMRequest, LLMResponse (cache fields), AnthropicAdapter (caching implemented) |
| `src/eval/harness.py` | run_comparison_eval(), run_eval() |
| `docs/FAILURE_CATALOG.md` | F5/F7/F8 fixed, F9 open |

## Existing Infrastructure to Build On

**ModelCallAudit** (in `src/admin/model_gateway.py`):
- Now has `cache_creation_tokens: int = 0` and `cache_read_tokens: int = 0`
- `to_dict()` includes both fields
- Ready for `batch: bool` field (Story 32.17)

**SpendReport** (in `src/admin/model_spend.py`):
- Has `total_cache_creation_tokens`, `total_cache_read_tokens`, `cache_hit_rate`
- `to_dict()` includes all cache metrics
- `_aggregate()` groups by any key function — extend for by_repo, by_day
- Ready for per-repo and per-day breakdowns (Story 32.12)

**AnthropicAdapter** (in `src/adapters/llm.py`):
- `_build_system_payload()` handles cache_control content blocks
- Beta header appended when caching enabled
- Cache tokens extracted from API response usage
- `complete()` method ready to be complemented with `batch_submit()` (Story 32.15)

**DEFAULT_ROUTING_RULES** (in `src/admin/model_gateway.py`):
- Step `"routing"` (was `"expert_routing"`) now matches `pipeline_step="routing"` used by router/recruiter agents
- `_COST_OPTIMIZED_STEPS` also uses `"routing"`
- Security overlay override on assembler preserved

**AgentRunner._record_audit** (in `src/agent/framework.py`):
- Now passes `cache_creation_tokens` and `cache_read_tokens` from LLMResponse to ModelCallAudit
- Ready for batch mode flag (Story 32.17)

## Codebase Health

- **2069+ unit tests passing** (1 pre-existing flaky container reaper test)
- **~244 integration tests** (across Epics 30, 32)
- Pre-existing failures: ALL RESOLVED
- F5, F7, F8 fixed; F9 open (eval calibration)

## Phase 7 Exit Criteria Status

| Criterion | Status |
|-----------|--------|
| Intent agent valid specs >= 8/10 with real Claude | **Met** |
| QA agent catches planted defects >= 7/10 | Partial (F9 — scoring needs tuning) |
| Primary agent valid output 3/3 simple issues | **Met** |
| Postgres integration 6/6 | **Met** |
| GitHub integration 4/4 | **Met** |
| Full pipeline processes real GitHub issue into draft PR | Pending |
| Cost model documented with accurate estimates | **Met** |
| Deployment runbook enables cold start | **Met** |
| Cost optimization reduces per-issue spend by >= 50% | Partial — routing + caching done, batch API pending |

## Budget

- Slice 4 (cost dashboard, Stories 32.12-32.14): ~3.5 days
- Slice 5 (Batch API, Stories 32.15-32.17): ~3 days
- Bug fix (F9): ~30 min
- Total: ~7 days
