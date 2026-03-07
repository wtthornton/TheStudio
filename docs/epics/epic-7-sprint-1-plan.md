# Epic 7 Sprint 1 Plan — Platform Maturity Foundations

> Helm — Planner & Dev Manager | Created: 2026-03-07

---

## Sprint Goal

**Objective:** Tool Hub catalog and policy engine, Model Gateway routing and audit, and compliance scorecard service are implemented with APIs and tested.

**Test:** `GET /admin/tools/catalog` returns 3+ tool suites. `POST /admin/models/route` returns a model selection for a given step/role/tier. `GET /admin/repos/{id}/compliance` returns a scorecard with 7 checks. All new tests pass.

**Constraint:** No UI pages this sprint — service + API layer only. UI deferred to Sprint 2.

---

## Retro Actions from Epic 6 Sprint 1

| Action | How addressed |
|--------|---------------|
| Fix TemplateResponse deprecation | Story 7.9 (cleanup story at end of sprint if time allows; otherwise Sprint 2) |
| Test isolation guard for PackRegistry | Add conftest fixture in Story 7.1 setup |
| Commit per-track | Commit after each track completes (3 commits minimum) |

---

## Stories

### Track A: Tool Hub (AC 1-6)

**Story 7.1 — Tool Catalog Schema & Registry**
- `ToolSuite` dataclass: name, description, tools (list of `ToolEntry`), approval_status (observe/suggest/execute), version, created_at
- `ToolEntry` dataclass: name, description, capability_category, read_only (bool)
- `ToolCatalog` service: register_suite(), get_suite(), list_suites(), promote_suite(), get_tools_for_tier()
- Seed 3 standard suites: code-quality (ruff, mypy, bandit, dead-code), context-retrieval (doc-fetch, pack-lookup, memory-search), documentation (readme-gen, changelog, link-validation)
- Tests: schema validation, registration, promotion lifecycle, tier filtering
- **Estimate:** Medium — well-defined schema, follows PackRegistry pattern

**Story 7.2 — Tool Profile & Policy Engine**
- `ToolProfile` dataclass: profile_id, repo_id, enabled_suites (list), tier_scope (observe/suggest/execute)
- `ToolPolicyEngine` service: check_access(role, overlays, repo_tier, tool_suite, tool_name) -> allowed/denied
- Integrates with EffectiveRolePolicy concept: role allowlist + overlay restrictions + tier gates
- Default profiles: observe (code-quality read-only), suggest (code-quality + context-retrieval), execute (all suites)
- Tests: access checks for each role/tier combo, deny cases, overlay restrictions
- **Estimate:** Medium — policy logic is the core complexity
- **Depends on:** 7.1

**Story 7.3 — Tool Hub API & Audit**
- `GET /admin/tools/catalog` — list all suites with approval status
- `GET /admin/tools/catalog/{suite_name}` — suite detail with tools
- `POST /admin/tools/catalog/{suite_name}/promote` — promote approval status (requires admin)
- `GET /admin/tools/profiles` — list profiles by repo
- `POST /admin/tools/check-access` — check if a tool call is allowed (role, overlays, tier, suite, tool)
- Tool call audit: extend AuditService with `tool_access_checked` and `tool_access_denied` event types
- Tests: all endpoints, RBAC enforcement, audit logging
- **Estimate:** Medium — follows existing router pattern
- **Depends on:** 7.1, 7.2

### Track B: Model Gateway (AC 7-12)

**Story 7.4 — Model Class & Routing Rules**
- `ModelClass` enum: FAST, BALANCED, STRONG
- `ProviderConfig` dataclass: provider, model_id, model_class, cost_per_1k_tokens, rate_limit_tpm, priority, enabled
- `RoutingRule` dataclass: step, default_class, role_overrides (dict), overlay_overrides (dict), tier_overrides (dict)
- `ModelRouter` service: select_model(step, role, overlays, repo_tier, complexity) -> ProviderConfig
- Seed default routing rules per arch doc: intake=FAST, context=FAST, intent=BALANCED, expert_routing=BALANCED, assembler=BALANCED, primary_agent=BALANCED, qa_eval=BALANCED
- Seed 3 provider configs (mock): fast-model, balanced-model, strong-model
- Tests: routing for each step, role override escalation, overlay escalation, tier override, fallback when provider disabled
- **Estimate:** Large — routing logic with multiple override layers

**Story 7.5 — Fallback Chains & Budget Enforcement**
- `FallbackChain`: when selected provider unavailable, try next provider at same class, then escalate to next class
- `BudgetSpec` dataclass: per_task_max_spend, per_step_token_cap, conservative_mode (bool)
- `BudgetEnforcer` service: check_budget(task_id, step) -> allowed/exceeded; record_spend(task_id, step, cost, tokens)
- Budget exceeded -> raises `BudgetExceededError`
- Conservative mode -> blocks STRONG class
- Tests: fallback selection, budget tracking, budget exceeded, conservative mode
- **Estimate:** Medium-Large — fallback logic needs thorough testing
- **Depends on:** 7.4

**Story 7.6 — Model Gateway API & Audit**
- `POST /admin/models/route` — simulate routing decision (step, role, overlays, tier, complexity) -> selected model
- `GET /admin/models/providers` — list provider configs
- `PATCH /admin/models/providers/{provider_id}` — enable/disable provider
- `GET /admin/models/audit` — query model call audit records (filter by task, step, provider, date range)
- `POST /admin/models/budget/{repo_id}` — set per-repo budget
- `ModelCallAudit` dataclass: id, correlation_id, task_id, step, role, overlays, provider, model, tokens_in, tokens_out, cost, latency_ms, error_class, fallback_chain, created_at
- AuditService extended with `model_call_recorded` event type
- Tests: all endpoints, audit record creation, budget setting, RBAC
- **Estimate:** Medium — follows existing router pattern
- **Depends on:** 7.4, 7.5

### Track C: Compliance Scorecard (AC 13-15)

**Story 7.7 — Compliance Scorecard Service**
- `ScorecardCheck` dataclass: name, description, passed (bool), details (str)
- `ComplianceScorecard` dataclass: repo_id, checks (list of ScorecardCheck), overall_pass (bool), evaluated_at
- `ComplianceScorecardService`: evaluate(repo_id) -> ComplianceScorecard
- 7 checks: (a) branch_protection_enabled, (b) required_reviewers_configured, (c) standard_labels_present, (d) projects_v2_configured, (e) evidence_format_valid, (f) idempotency_guard_active, (g) execution_plane_healthy
- Each check returns pass/fail with detail string
- Tests: all 7 checks pass/fail scenarios, overall pass requires all green, partial failure
- **Estimate:** Medium — straightforward check logic

**Story 7.8 — Compliance Scorecard API & Promotion Gate**
- `GET /admin/repos/{id}/compliance` — run and return scorecard
- `PATCH /admin/repos/{id}/tier` — extend existing endpoint to require scorecard pass for execute promotion
- Scorecard result cached for 1 hour (avoid re-running on every tier check)
- Audit log: `compliance_scorecard_evaluated` event
- Tests: API endpoint, promotion blocked on scorecard fail, promotion allowed on pass, cache behavior
- **Estimate:** Small-Medium — extends existing tier endpoint
- **Depends on:** 7.7

### Track D: Operational Targets (AC 20-23)

**Story 7.9 — Lead Time, Cycle Time & Reopen Target Tracking**
- Extend `MetricsService` with:
  - `get_lead_time(repo_filter, window_days)` -> LeadTimeMetrics (p50, p95, p99, sample_count)
  - `get_cycle_time(repo_filter, window_days)` -> CycleTimeMetrics (p50, p95, p99, sample_count)
  - `get_reopen_target(repo_filter, window_days)` -> ReopenTargetMetrics (current_rate, target=0.05, met, sample_count)
- `GET /admin/metrics/lead-time` — lead time stats
- `GET /admin/metrics/cycle-time` — cycle time stats
- `GET /admin/metrics/reopen-target` — reopen rate vs <5% target
- Handles insufficient data (like success gate pattern)
- Tests: metrics calculation, API endpoints, insufficient data handling
- **Estimate:** Medium — follows SuccessGateService pattern

---

## Order of Work

```
Track A: 7.1 -> 7.2 -> 7.3
Track B: 7.4 -> 7.5 -> 7.6
Track C: 7.7 -> 7.8
Track D: 7.9 (independent)

Parallel: Tracks A, B, C, D are independent of each other.
Within each track: stories are sequential (dependencies noted above).
```

**Recommended execution order:**
1. 7.1 + 7.4 + 7.7 + 7.9 (all foundation stories, parallel)
2. 7.2 + 7.5 + 7.8 (second layer, parallel)
3. 7.3 + 7.6 (API layers, parallel)

---

## What's Out This Sprint

- Admin UI pages for Tool Hub, Model Gateway, Compliance Scorecard (Sprint 2)
- Policy & Guardrails Console UI (Sprint 2)
- Model Spend Dashboard UI (Sprint 2)
- Quarantine Operations UI (Sprint 2)
- Merge Mode Controls UI (Sprint 2)
- TemplateResponse deprecation fix (Sprint 2 cleanup)

---

## Capacity & Buffer

- 9 stories across 4 tracks
- Tracks are parallel; within each track, stories are sequential
- ~80% commitment; Story 7.9 is the buffer candidate (can defer to Sprint 2 if tracks A/B run long)
- Commit after each track completes

---

## Risks

| Risk | Mitigation |
|------|------------|
| Model Gateway routing logic is the largest story (7.4) | Start it first; if complex, split role/overlay/tier overrides into separate sub-stories |
| Tool policy engine edge cases | Define clear deny-by-default policy; test edge cases explicitly |
| Compliance scorecard checks may need repo profile data that doesn't exist yet | Use mock/stub data for checks that reference external state (branch protection, GitHub labels) |
