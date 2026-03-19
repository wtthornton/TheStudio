# Session Prompt: Epic 30 Sprint 3 — Story 30.13 + Story 30.12

## Context

Epic 30 Sprint 3 (Feature Flag Activation & Deployment) is in progress. Sprint plan: `docs/sprints/sprint-epic30-s3.md`. Meridian review: 7/7 PASS, plan is COMMITTABLE.

## What's Done

- **Sprint plan** committed and Meridian-reviewed (7/7 PASS)
- **Items 1-6** (bug fixes F7/F8/F9, eval re-run, Story 30.11 deployment runbook, Story 30.9 Projects v2 + Portfolio) completed in prior sessions
- **Item 7 — Story 30.10** (Preflight + Container Isolation): COMPLETE — 40 tests passing
- **Story 30.14** (Approval Auto-Bypass Feature Flag): COMPLETE — 20 tests passing
  - `approval_auto_bypass: bool = False` added to `src/settings.py` with `@model_validator` blocking bypass + real GitHub + real LLM
  - `PipelineInput.approval_auto_bypass` and `PipelineOutput.approval_bypassed` added to `src/workflow/pipeline.py`
  - Pipeline gate updated: `if params.repo_tier in APPROVAL_REQUIRED_TIERS and not params.approval_auto_bypass:`
  - `elif` bypass branch logs `approval.auto_bypass` and sets `output.approval_bypassed = True`
  - `src/ingress/workflow_trigger.py` threads `settings.approval_auto_bypass` into workflow arg dict
  - `src/admin/settings_service.py` — `approval_auto_bypass` added to `SETTING_DEFINITIONS`
  - All 3 Docker Compose files have `THESTUDIO_APPROVAL_AUTO_BYPASS` (dev/staging=true, prod=false)
  - `docs/FEATURE-FLAGS.md` and `docs/deployment.md` updated
  - `tests/integration/test_story_30_14_approval_bypass.py` — 20 tests, all passing
  - `tests/unit/test_workflow_trigger.py` — arg dict assertion updated for new field

## What's Next (Priority Order)

### 1. Commit Story 30.14 work (if not already committed)

All changes are tested and lint-clean. Files changed:
- `src/settings.py` — approval_auto_bypass field + safety validator
- `src/workflow/pipeline.py` — PipelineInput/Output fields + gate conditional + elif bypass
- `src/ingress/workflow_trigger.py` — threads approval_auto_bypass into arg dict
- `src/admin/settings_service.py` — SETTING_DEFINITIONS entry
- `docker-compose.dev.yml` — THESTUDIO_APPROVAL_AUTO_BYPASS (default true)
- `infra/docker-compose.yml` — THESTUDIO_APPROVAL_AUTO_BYPASS (default true)
- `infra/docker-compose.prod.yml` — THESTUDIO_APPROVAL_AUTO_BYPASS (default false)
- `docs/FEATURE-FLAGS.md` — new row in Pipeline Feature Flags table
- `docs/deployment.md` — Approval Auto-Bypass section
- `tests/integration/test_story_30_14_approval_bypass.py` — 20 tests (NEW)
- `tests/unit/test_workflow_trigger.py` — updated arg dict assertion

### 2. Story 30.13: Fix Model Gateway Audit Tests (1-2h, S)

Fix the pre-existing `test_gateway_enforcement.py` failure. Full spec: `docs/sprints/stories-30-13-and-30-14.md`.

**Two independent bugs:**

**Bug 1: Feature flag default blocks audit recording.**
`settings.agent_llm_enabled` defaults all agents to `False` (`src/settings.py:49-60`). When the flag is off, `AgentRunner.run()` takes the fallback path at line 239 and never reaches the LLM call or audit recording. The test calls activities without enabling the feature flag, so 0 audit records are created.

**Bug 2: `_record_audit` does not populate the `overlays` field.**
`ModelCallAudit` has an `overlays: list[str]` field (`src/admin/model_gateway.py:113`), but `_record_audit()` at `src/agent/framework.py:421-431` never sets it. The security overlay test asserts `"security" in records[0].overlays`, which fails.

**Fix 1 — Add `overlays` to `_record_audit()` (`src/agent/framework.py:421-431`):**
```python
audit = ModelCallAudit(
    correlation_id=context.correlation_id,
    task_id=context.taskpacket_id,
    step=self.config.pipeline_step,
    role=self.config.agent_name,
    overlays=list(context.overlays) if context.overlays else [],  # NEW
    provider=provider.provider,
    model=provider.model_id,
    tokens_in=tokens_in,
    tokens_out=tokens_out,
    cost=cost,
)
```

**Fix 2 — Update tests (`tests/unit/test_gateway_enforcement.py`):**
Each test that expects audit records must:
1. Enable the agent's feature flag via `monkeypatch` or `patch` on `settings.agent_llm_enabled`
2. Mock the LLM call to return a valid `LLMResponse` (so the LLM path completes)
3. `test_no_audit_for_non_llm_activities` should remain unchanged (verify/publish don't use LLM)
4. `test_intent_activity_with_security_overlay` should pass with `"security" in records[0].overlays` after Fix 1

**Important: `_implement_in_process` has a separate audit path.**
The implement activity (`src/workflow/activities.py:747-760`) calls `router.select_model()` and `audit_store.record()` directly — it does NOT use `AgentRunner`. Its test (`test_implement_activity_records_audit`) may already pass. Don't break it.

**Done-when checklist:**
- [ ] `_record_audit()` sets `overlays` from `context.overlays`
- [ ] Tests enable `agent_llm_enabled` for the agent under test
- [ ] Tests mock `_call_llm_completion` to return valid response
- [ ] `pytest tests/unit/test_gateway_enforcement.py -v` shows 6/6 passing
- [ ] No duplicate audit entries for implement activity
- [ ] `pytest` full suite has zero new regressions

**Key files:**
- `src/agent/framework.py` — `_record_audit` at line 411-440, feature flag check at 232-239
- `src/admin/model_gateway.py` — `ModelCallAudit` dataclass (overlays field at line 113)
- `tests/unit/test_gateway_enforcement.py` — 6 tests to fix
- `src/settings.py` — `agent_llm_enabled` dict at lines 49-60

### 3. Story 30.12: Suggest Tier Validation (6h, compressible)

Most complex item. Requires real GitHub operations. Now unblocked by Story 30.14 (approval bypass). Defer if time runs short.

## Pre-existing Test Failures (NOT caused by Story 30.14)

These all fail on `master` before any Story 30.14 changes:
- `tests/unit/test_gateway_enforcement.py` — Story 30.13 addresses this
- `tests/unit/test_workflow.py::TestWorkflowStep::test_all_steps` — expects 11 steps, enum has more
- `tests/unit/test_workflow.py::TestWorkflowStep::test_step_order` — step index mismatch (preflight)
- `tests/unit/test_workflow.py::TestRouterActivity::test_router_with_no_overlays` — rationale string changed
- `tests/unit/test_workflow.py::TestRouterActivity::test_router_with_security_overlay` — same
- `tests/unit/test_workflow_pipeline.py::TestActivityCallArguments::test_publish_receives_repo_tier_and_qa_passed` — NotInWorkflowEventLoopError
- `tests/unit/test_github_adapter.py::TestResilientGitHubClient::test_auth_headers_sent` — pre-existing
- `tests/unit/test_settings_integration.py::TestSettingDefinitions::test_all_env_settings_covered` — missing `anthropic_auth_mode` in SETTING_DEFINITIONS (pre-existing from Epic 31)

## Sprint Budget

- Story 30.14 used ~1.5h of estimated 3-4h (under budget)
- Remaining: ~13.5h available
- Story 30.13: 1-2h estimate
- Story 30.12: 6h estimate (compressible)
- Buffer: ~5.5h

## Key Files

- Sprint plan: `docs/sprints/sprint-epic30-s3.md`
- Stories 30.13/30.14: `docs/sprints/stories-30-13-and-30-14.md`
- Settings: `src/settings.py`
- Pipeline: `src/workflow/pipeline.py`
- AgentRunner: `src/agent/framework.py` (`_record_audit` at 411-440, feature flag at 232-239)
- Model gateway: `src/admin/model_gateway.py` (ModelCallAudit dataclass)
- Gateway tests: `tests/unit/test_gateway_enforcement.py`
- Feature flags: `docs/FEATURE-FLAGS.md`
- Deployment: `docs/deployment.md`
