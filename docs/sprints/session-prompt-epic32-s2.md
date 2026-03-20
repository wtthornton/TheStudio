# Session Prompt: Epic 32 Slice 2 — Budget Controls + Slice 1 Completion

## Context

Phase 7 is in progress. Epic 30 is **fully delivered** (3 sprints, Stories 30.1-30.14). All pre-existing test failures are resolved — **1783/1783 unit tests passing, zero failures.**

The roadmap critical path has shifted to Epic 32 (Model Routing & Cost Optimization). Slice 1 is partially complete (3 of 6 stories done). Slice 2 (budget controls) is next per the roadmap. Full epic spec: `docs/epics/epic-32-model-routing-cost-optimization.md`.

## What's Done

### Epic 30 (Real Provider Integration & Validation) — COMPLETE
- Sprint 1: Eval harness, 6 agent eval suites, Postgres + GitHub integration, real Claude validation
- Sprint 2: Full pipeline Docker validation, failure catalog (9 modes), cost baselines
- Sprint 3: Stories 30.12 (Suggest tier validation, 16 tests), 30.13 (gateway audit fix, 9/9), 30.14 (approval bypass, 20 tests)

### Epic 32 Slice 1 — PARTIALLY COMPLETE
- **Story 32.0** (baselines): COMPLETE — $0.087/issue measured. See `docs/eval-results/sprint2-cost-baselines.md`
- **Story 32.1** (cost optimization feature flags): COMPLETE — `cost_optimization_routing_enabled` in settings, feature-flagged off
- **Story 32.5** (feature-flag gate): COMPLETE — `ModelRouter.resolve_class` checks the flag
- **Stories 32.2, 32.3, 32.4**: NOT YET DONE — eval comparison mode, routing rules update

### Failure Catalog Status
Key items relevant to this session:
- **F5** (max_tokens truncation): Should fix — increase max_tokens for intent/assembler agents
- **F7** (router template variables): Eval calibration task
- ~~**F8** (assembler qa_handoff schema)~~: **Already fixed** — `@field_validator("criterion", mode="before")` in `assembler_config.py` coerces `list[str]` to `str`
- **F9** (eval scoring calibration): Affects quality reporting for intake/context

### All Pre-existing Test Failures Resolved
- `test_all_env_settings_covered` — added `anthropic_auth_mode`, `anthropic_refresh_token`, `anthropic_oauth_client_id` to SETTING_DEFINITIONS
- `test_auth_headers_sent` — updated from `"token"` to `"Bearer"` format (Epic 31 change)
- `test_workflow.py` — WorkflowStep count updated to 13, rationale assertions relaxed
- `test_workflow_pipeline.py` — mocked `workflow.now()` and set `_approved` flag

## What's Next (Priority Order)

### 1. Epic 32 Slice 2: Budget Controls (3.5 days est.)

The highest operational safety value. Prevents runaway costs before scaling up issue volume.

**Story 32.6: Trust-tier budget caps in Settings and PipelineBudget (1.5 days)**
- Per-tier budget caps already exist in `src/settings.py` as `cost_optimization_budget_tiers`:
  ```python
  cost_optimization_budget_tiers: dict[str, float] = {
      "observe": 2.00, "suggest": 5.00, "execute": 8.00,
  }
  ```
- Wire these caps from settings into `PipelineBudget` in `src/agent/framework.py`
- `PIPELINE_BUDGET_DEFAULTS` (lines 45-49) currently has different values ($5.00/$8.50/$10.00) — reconcile with `cost_optimization_budget_tiers` or replace
- Budget caps should be the authoritative source when `cost_optimization_routing_enabled` is True
- Key files: `src/settings.py`, `src/agent/framework.py`, `src/admin/settings_service.py`

**Story 32.7: Budget cap admin UI controls (1 day)**
- Expose budget caps in the Admin Settings UI
- Key files: `src/admin/ui_router.py`, `src/admin/templates/settings.html`

**Story 32.8: Graceful budget-exceeded handling in AgentRunner (1 day)**
- When budget cap is hit, pipeline halts with `BudgetExceededError`
- Error includes step name, cumulative spend, and cap that was exceeded
- TaskPacket status reflects budget exhaustion (not a silent failure)
- Key files: `src/agent/framework.py`

### 2. Finish Epic 32 Slice 1: Routing Rules (2 days est.)

**Story 32.3: Model-class comparison mode in eval harness (1 day)**
- Extend eval harness to support running the same test against FAST vs BALANCED
- Compare quality scores to validate model downgrades
- Key files: `src/eval/harness.py`, `src/eval/models.py`

**Story 32.4: Update DEFAULT_ROUTING_RULES (0.5 day)**
- Split `"expert_routing"` into `"router"` + `"recruiter"` (or keep combined)
- Set both to FAST (Haiku)
- Preserve `security: STRONG` overlay override for assembler
- Key file: `src/admin/model_gateway.py`

### 3. Fix F5 — Increase max_tokens for Intent/Assembler (15 min)

Intent and assembler agents hit the 2,048 max_tokens limit. Increase to 4,096.
- Key files: `src/intent/intent_config.py`, `src/assembler/assembler_config.py`

## Key Files

| File | Purpose |
|------|---------|
| `docs/epics/epic-32-model-routing-cost-optimization.md` | Full epic spec with all 5 slices |
| `src/settings.py` | Feature flags, budget caps settings (lines 90-98) |
| `src/agent/framework.py` | AgentRunner, PipelineBudget (lines 45-93), BudgetExceededError, _record_audit |
| `src/admin/model_gateway.py` | ModelRouter, DEFAULT_ROUTING_RULES, RoutingRule, ModelCallAudit |
| `src/admin/model_spend.py` | SpendReport aggregation |
| `src/admin/settings_service.py` | SETTING_DEFINITIONS (add new settings here) |
| `src/eval/harness.py` | Eval infrastructure |
| `src/assembler/assembler_config.py` | AssemblerAgentOutput, criterion coerce validator (F8 fix) |
| `docs/eval-results/sprint2-cost-baselines.md` | Measured per-agent cost data |
| `docs/FAILURE_CATALOG.md` | F5, F7, F9 open; F8 fixed |

## Existing Infrastructure to Build On

**PipelineBudget** (already exists in `src/agent/framework.py`):
- `PIPELINE_BUDGET_DEFAULTS`: per-tier budget defaults (lines 45-49)
- `PipelineBudget` dataclass with `max_total_usd`, `consume()`, `remaining`, `used` (lines 52-93)
- `BudgetEnforcer` with `check_budget()` and `record_spend()`
- `BudgetExceededError` exception class
- AgentRunner checks budget before each LLM call

**Settings budget tiers** (already exists in `src/settings.py`):
- `cost_optimization_budget_tiers`: per-tier USD caps (`observe: 2.00`, `suggest: 5.00`, `execute: 8.00`)
- `cost_optimization_routing_enabled`: feature flag for cost routing (off by default)

**ModelRouter** (already exists in `src/admin/model_gateway.py`):
- `DEFAULT_ROUTING_RULES`: step → model class mapping
- `resolve_class()`: reads rules + feature flag
- `cost_routing_gate_enabled` flag already wired (Story 32.5)

**SpendReport** (already exists in `src/admin/model_spend.py`):
- `by_provider`, `by_step`, `by_model` breakdowns
- Reads from ModelCallAudit records

## Codebase Health

- **1783 unit tests passing**, zero failures
- **~244 integration tests** (Stories 30.9, 30.10, 30.12, 30.14 plus prior)
- Pre-existing failures: ALL RESOLVED
- Ruff clean, no lint issues
- F8 (assembler schema): Fixed

## Budget

- Epic 32 Slice 2 estimate: 3.5 days
- Slice 1 remaining: 2 days (Stories 32.3, 32.4)
- Bug fixes (F5): ~15 min
- Total: ~5.5 days

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
| Cost optimization reduces per-issue spend by >= 50% | Pending (Epic 32) |
