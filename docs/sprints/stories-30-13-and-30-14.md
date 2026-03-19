# Stories 30.13 and 30.14 — Epic 30: Real Provider Integration & Validation

> **Epic:** 30 — Validate Real Providers End-to-End
> **Sprint:** 3 (Feature Flag Activation & Deployment)
> **Created:** 2026-03-19
> **Meridian Review:** v2 — Rewritten after Meridian review rejected v1

---

## Story 30.13: Fix Model Gateway Audit Enforcement Tests

### 1. Title

**Gateway Enforcement Tests Must Enable LLM Feature Flags and Populate Overlays**

### 2. Narrative

Epic 11 established a contract: every activity that calls an LLM must route through `ModelRouter` and record a `ModelCallAudit` entry. The test suite in `tests/unit/test_gateway_enforcement.py` enforces this contract across five LLM-using activities.

**Root cause (verified by code inspection):**

`AgentRunner.run()` already records `ModelCallAudit` entries — the `_record_audit()` method at `src/agent/framework.py:411-440` creates a `ModelCallAudit` with step, provider, model, tokens, and cost, then stores it via `get_model_audit_store().record(audit)`. This was added in Epic 23 and works correctly.

The test fails because of **two independent bugs:**

**Bug 1: Feature flag default blocks audit recording.** `settings.agent_llm_enabled` defaults all agents to `False` (src/settings.py:49-60). When the flag is off, `AgentRunner.run()` takes the fallback path at line 239 (`return await self._run_fallback(...)`) and never reaches the LLM call or audit recording at line 304-311. The test calls `context_activity()` without enabling the feature flag, so the fallback runs, 0 audit records are created, and `assert len(records) >= 1` fails.

**Bug 2: `_record_audit` does not populate the `overlays` field.** The `ModelCallAudit` dataclass has an `overlays: list[str]` field (model_gateway.py:113), but `_record_audit()` at framework.py:421-431 never sets it. The test at line 69 asserts `"security" in records[0].overlays`, which would also fail even if Bug 1 were fixed. The overlays are available in the `AgentContext.overlays` list (used for provider resolution at line 385/397) but not threaded into the audit entry.

**What _implement_in_process does differently:** The implement activity (activities.py:747-760) calls `router.select_model()` and `audit_store.record()` directly — it does NOT use `AgentRunner`. Its tests pass because this explicit path always records audit regardless of feature flags. There is no double-counting risk because `_implement_in_process` and `AgentRunner` are mutually exclusive paths.

**Why now:** Epic 30 is flipping providers from mock to real. Without fixing these tests, we cannot verify the audit contract for the 6 agents that use `AgentRunner`. Epic 32 cost dashboards depend on complete audit data.

### 3. References

| Artifact | Location |
|----------|----------|
| Failing test | `tests/unit/test_gateway_enforcement.py:40-47` |
| AgentRunner.run() — feature flag check | `src/agent/framework.py:232-239` |
| AgentRunner._record_audit() — existing, works | `src/agent/framework.py:411-440` |
| AgentRunner._resolve_provider() — overlays used | `src/agent/framework.py:385, 397` |
| _implement_in_process — separate path, not AgentRunner | `src/workflow/activities.py:747-760` |
| settings.agent_llm_enabled — all False default | `src/settings.py:49-60` |
| ModelCallAudit.overlays — field exists, not populated | `src/admin/model_gateway.py:113` |

### 4. Acceptance Criteria

**AC 1: Tests enable the feature flag for the agent under test.**
Each gateway enforcement test that expects audit records must set `settings.agent_llm_enabled[agent_name] = True` (via `monkeypatch` or `patch`) before calling the activity. This allows `AgentRunner.run()` to reach the LLM path and record audit.

**AC 2: `_record_audit` populates the `overlays` field.**
`AgentRunner._record_audit()` sets `ModelCallAudit.overlays` from `context.overlays`. The security overlay test (`test_intent_activity_with_security_overlay`) passes with `"security" in records[0].overlays`.

**AC 3: All six gateway enforcement tests pass.**
- `test_context_activity_records_audit` — PASS (feature flag enabled, audit recorded)
- `test_intent_activity_records_audit` — PASS
- `test_intent_activity_with_security_overlay` — PASS (overlays populated)
- `test_implement_activity_records_audit` — PASS (no regression, separate path)
- `test_qa_activity_records_audit` — PASS
- `test_no_audit_for_non_llm_activities` — PASS (no regression)

**AC 4: Fallback path does NOT record audit.**
When `agent_llm_enabled[agent_name] = False` (default), calling an activity produces 0 audit records. This is correct behavior — no LLM call means no audit.

### 4b. Top Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM mock in tests returns unexpected format | Parse failure falls through to fallback, no audit | Tests must mock `_call_llm_completion` to return valid `LLMResponse` |
| `_implement_in_process` has separate audit path | Confusion about two audit paths | Document that implement uses explicit recording, others use AgentRunner |
| Enabling feature flag in test affects global state | Test pollution | Use `monkeypatch` or `patch` (auto-reverted per test) |

### 5. Constraints & Non-Goals

- **In scope:** Fix the test setup (enable feature flags), add `overlays` to `_record_audit`, verify all 6 tests pass.
- **Not in scope:** Changing how `_implement_in_process` records audit (it uses a separate, working path).
- **Not in scope:** Making AgentRunner work differently — only fixing the overlays gap and the test setup.
- **Not in scope:** Cost dashboard UI or reporting (Epic 32).
- **Constraint:** Tests must mock the LLM call (no real API calls in unit tests).

### 6. Stakeholders & Roles

| Role | Who |
|------|-----|
| Owner / Implementer | Primary Developer |
| QA | Automated (pytest, existing test suite) |
| Downstream dependency | Epic 32 cost dashboard relies on complete audit data |

### 7. Success Metrics

| Metric | Target |
|--------|--------|
| `test_gateway_enforcement.py` pass rate | 6/6 tests passing (currently ~3/6) |
| Overlays field populated | Security overlay test passes with `"security" in records[0].overlays` |
| Regression | Zero new test failures |

### 8. Context & Assumptions

- **Verified:** `AgentRunner.run()` at line 304-311 already calls `_record_audit()` after successful LLM calls. No new audit wiring needed.
- **Verified:** `_record_audit()` at line 421-431 does NOT set `overlays` on `ModelCallAudit`. This is a one-line fix.
- **Verified:** `_implement_in_process()` does NOT use `AgentRunner` — it calls `router.select_model()` and `audit_store.record()` directly. No double-counting risk.
- **Verified:** `settings.agent_llm_enabled` defaults all False. The tests must enable the flag to exercise the LLM path.
- **Verified:** `AgentContext.overlays` is populated from `context.risk_flags` in `intent_activity` (risk_flags={"security": True} → overlays=["security"]).

### Implementation Notes (AI-Implementable)

**Fix 1: Add `overlays` to `_record_audit()` (src/agent/framework.py:421-431)**

Change the `ModelCallAudit` construction to include overlays:

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

**Fix 2: Update tests to enable feature flags (tests/unit/test_gateway_enforcement.py)**

Each test that expects audit records must:
1. Enable the agent's feature flag via `monkeypatch` or `patch`
2. Mock the LLM call to return a valid `LLMResponse` (so the LLM path completes)

Example for `test_context_activity_records_audit`:

```python
@pytest.mark.asyncio
async def test_context_activity_records_audit(self, monkeypatch):
    # Enable the context agent's LLM flag
    monkeypatch.setattr(
        "src.settings.settings.agent_llm_enabled",
        {**settings.agent_llm_enabled, "context_agent": True},
    )
    # ... (may also need to mock _call_llm_completion)
    await context_activity(ContextInput(...))
    records = get_model_audit_store().query(step="context")
    assert len(records) >= 1
    assert records[0].provider == "anthropic"
```

**Files to modify:**
- `src/agent/framework.py` — add `overlays` to `_record_audit()` ModelCallAudit construction
- `tests/unit/test_gateway_enforcement.py` — enable feature flags in test setup, mock LLM calls

**Estimate:** 1-2 hours (S size, 2 story points)

---

## Story 30.14: Add Approval Auto-Bypass Feature Flag for Dev/Test Environments

### 1. Title

**Dev and Test Pipelines Skip the Approval Gate Without Compromising Production Safety**

### 2. Narrative

The pipeline's Step 8.5 approval gate (lines 623-717 of `src/workflow/pipeline.py`) is a critical safety mechanism: before a Suggest or Execute tier repo publishes a PR, a human must approve it. This is enforced by a `frozenset` constant — `APPROVAL_REQUIRED_TIERS = frozenset({"suggest", "execute"})` — with no runtime override.

This rigidity creates two problems today:

**Problem 1: Execute tier is untestable outside Temporal.** The approval gate uses `workflow.wait_condition()` and `workflow.now()`, which are Temporal sandbox APIs. They throw `RuntimeError` outside a Temporal worker context. Story 30.10 (preflight + container isolation validation) had to test with `observe` tier instead of `execute` tier because there was no way to skip the approval gate in an integration test.

**Problem 2: Approval gate has no value in mock environments.** When `github_provider=mock`, the `post_approval_request_activity` posts a comment to a mock GitHub client that nobody reads. When `llm_provider=mock`, the entire pipeline output is deterministic. Requiring human approval for a deterministic mock result is pure friction.

The fix is a feature flag — `THESTUDIO_APPROVAL_AUTO_BYPASS` — that skips the entire approval block when enabled. Off by default. Blocked from being enabled in full production mode by a `@model_validator`.

**Why now:** Epic 30 Sprint 3 is validating Suggest tier (Story 30.12) and will soon validate Execute tier. Without this flag, Execute-tier integration tests require a running Temporal worker with signal infrastructure.

### 3. References

| Artifact | Location |
|----------|----------|
| Approval gate (hardcoded) | `src/workflow/pipeline.py:76, 623-717` |
| PipelineInput / PipelineOutput | `src/workflow/pipeline.py:181-221` |
| PipelineInput wiring point | `src/ingress/workflow_trigger.py:33-41` |
| Settings class + validators | `src/settings.py:7-155` |
| Feature flag architecture | `docs/FEATURE-FLAGS.md` |
| Docker Compose (dev) | `docker-compose.dev.yml` |
| Docker Compose (staging) | `infra/docker-compose.yml` |
| Docker Compose (prod) | `infra/docker-compose.prod.yml` |
| Preflight flag (pattern to follow) | `src/settings.py:63-64` |

### 4. Acceptance Criteria

**AC 1: Feature flag exists with safe default.**
`src/settings.py` contains `approval_auto_bypass: bool = False`. Environment variable `THESTUDIO_APPROVAL_AUTO_BYPASS=true` enables it. Default behavior is unchanged.

**AC 2: Production safety validator rejects unsafe combinations.**
A `@model_validator` on `Settings` raises `ValueError` when ALL THREE conditions are true simultaneously:
- `approval_auto_bypass = True`
- `github_provider = "real"`
- `llm_provider = "anthropic"`

This is a two-condition guard (real GitHub + real LLM) because these are the conditions under which the approval gate provides real safety value. `agent_isolation` is NOT checked — container isolation is an orthogonal security boundary. You could have real providers without container isolation (early production), and approval should still be mandatory.

The error message must explain why this combination is blocked.

**AC 3: Pipeline skips approval gate when bypass is enabled.**
When `PipelineInput.approval_auto_bypass = True` and `repo_tier in APPROVAL_REQUIRED_TIERS`, the pipeline does NOT call `post_approval_request_activity`, does NOT call `workflow.wait_condition()`, and does NOT call `escalate_timeout_activity`. It proceeds directly to Step 9 (Publish).

**AC 4: Pipeline output records that approval was bypassed.**
`PipelineOutput` has a new field `approval_bypassed: bool = False`. When the approval gate is skipped due to the bypass flag, this field is set to `True`.

**AC 5: Workflow trigger threads the setting into PipelineInput.**
`src/ingress/workflow_trigger.py` must read `settings.approval_auto_bypass` and pass it through to the workflow arg dict. Currently (line 35-38) it passes only `taskpacket_id` and `correlation_id`. The new field must be added.

**AC 6: Docker Compose files include the new environment variable.**
All three Docker Compose files include `THESTUDIO_APPROVAL_AUTO_BYPASS`:
- Dev: `"${THESTUDIO_APPROVAL_AUTO_BYPASS:-true}"` (approval is friction in dev)
- Staging: `"${THESTUDIO_APPROVAL_AUTO_BYPASS:-true}"` (no human operator in staging)
- Prod: `"${THESTUDIO_APPROVAL_AUTO_BYPASS:-false}"` (never auto-bypass in production)

**AC 7: Feature flag documentation updated.**
`docs/FEATURE-FLAGS.md` lists the new flag in the Pipeline Feature Flags table. `docs/deployment.md` includes the flag in the deployment configuration section.

**AC 8: Integration tests validate all paths.**
A new test file `tests/integration/test_story_30_14_approval_bypass.py` contains tests for:
- Default off: Settings default is `False`
- Enable via env: `THESTUDIO_APPROVAL_AUTO_BYPASS=true` enables
- Validator rejects: `approval_auto_bypass=True` + `github_provider=real` + `llm_provider=anthropic` raises `ValueError`
- Validator allows mock GitHub: `approval_auto_bypass=True` + `github_provider=mock` + `llm_provider=anthropic` succeeds
- Validator allows mock LLM: `approval_auto_bypass=True` + `github_provider=real` + `llm_provider=mock` succeeds
- Pipeline bypass: Execute tier with `approval_auto_bypass=True` skips approval, `output.approval_bypassed=True`
- Pipeline no-bypass: Observe tier is unaffected regardless of flag
- Docker Compose: All 3 files contain `THESTUDIO_APPROVAL_AUTO_BYPASS`

### 4b. Top Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Bypass accidentally enabled in production | Unsupervised PR publication | `@model_validator` blocks bypass + real GitHub + real LLM (AC 2) |
| Workflow trigger doesn't thread the flag | Flag exists but never reaches pipeline | AC 5 explicitly requires wiring in workflow_trigger.py |
| Staging bypass means approval never tested pre-prod | Approval path bit-rots | Non-blocking observation — staging can optionally set false for approval testing |

### 5. Constraints & Non-Goals

- **In scope:** Feature flag, safety validator, pipeline conditional, output field, workflow trigger wiring, Docker Compose, documentation, integration tests.
- **Not in scope:** Changing the approval gate logic itself (timeout, escalation, rejection).
- **Not in scope:** Per-tier bypass granularity. Binary flag: all tiers or no tiers.
- **Not in scope:** Runtime flag mutation. Set at startup, immutable.
- **Constraint:** Validator checks exactly two conditions beyond the bypass flag: `github_provider == "real"` AND `llm_provider == "anthropic"`. Not three. See AC 2 rationale.
- **Constraint:** Flag uses `THESTUDIO_` prefix per convention.

### 6. Stakeholders & Roles

| Role | Who |
|------|-----|
| Owner / Implementer | Primary Developer |
| QA | Automated (pytest, new integration test file) |
| Affected downstream | Story 30.12 (Suggest tier validation) can use bypass |
| Affected downstream | Future Execute tier testing no longer needs Temporal worker |

### 7. Success Metrics

| Metric | Target |
|--------|--------|
| New integration tests | >= 8 test cases, all passing |
| Existing test suite | Zero regressions |
| Execute-tier testability | Pipeline test can run Execute tier without Temporal worker |
| Documentation | Flag in FEATURE-FLAGS.md and deployment.md |

### 8. Context & Assumptions

- **Verified:** `Settings` class validator has access to `self.github_provider`, `self.llm_provider`, `self.agent_isolation` at validation time.
- **Verified:** `PipelineInput` is a `@dataclass`. Adding a field with default is backward-compatible.
- **Verified:** `PipelineOutput` is a `@dataclass`. Adding `approval_bypassed: bool = False` is backward-compatible.
- **Verified:** `src/ingress/workflow_trigger.py:33-41` constructs the workflow arg dict. This is where `approval_auto_bypass` must be threaded from `settings`.
- **Verified:** `APPROVAL_REQUIRED_TIERS = frozenset({"suggest", "execute"})` at pipeline.py:76 is the gate condition.
- **Dependency:** No dependency on other stories.

### Implementation Notes (AI-Implementable)

**Step 1: Settings (src/settings.py)**

Add after `slack_approval_webhook_url` (line 101):

```python
# Approval auto-bypass (Story 30.14)
approval_auto_bypass: bool = False  # Skip approval gate for ALL tiers when True
```

Add a new `@model_validator(mode="after")`:

```python
@model_validator(mode="after")
def _reject_approval_bypass_in_production(self) -> "Settings":
    if (
        self.approval_auto_bypass
        and self.github_provider == "real"
        and self.llm_provider == "anthropic"
    ):
        raise ValueError(
            "THESTUDIO_APPROVAL_AUTO_BYPASS cannot be true when "
            "github_provider=real and llm_provider=anthropic. "
            "The approval gate is a safety-critical control for real PR publication. "
            "Set approval_auto_bypass=false or use mock providers for testing."
        )
    return self
```

**Step 2: PipelineInput + PipelineOutput (src/workflow/pipeline.py)**

Add to `PipelineInput` (after `project_item_id`):
```python
approval_auto_bypass: bool = False
```

Add to `PipelineOutput` (after `approved_by`):
```python
approval_bypassed: bool = False
```

**Step 3: Pipeline conditional (src/workflow/pipeline.py line 624)**

Change:
```python
if params.repo_tier in APPROVAL_REQUIRED_TIERS:
```

To:
```python
if params.repo_tier in APPROVAL_REQUIRED_TIERS and not params.approval_auto_bypass:
```

Add after the approval block closing:
```python
elif params.repo_tier in APPROVAL_REQUIRED_TIERS and params.approval_auto_bypass:
    workflow.logger.info(
        "approval.auto_bypass",
        extra={
            "taskpacket_id": params.taskpacket_id,
            "repo_tier": params.repo_tier,
        },
    )
    output.approval_bypassed = True
```

**Step 4: Workflow trigger wiring (src/ingress/workflow_trigger.py)**

Update the `start_workflow` arg dict (line 35-38) to include:
```python
arg={
    "taskpacket_id": str(taskpacket_id),
    "correlation_id": str(correlation_id),
    "approval_auto_bypass": settings.approval_auto_bypass,
},
```

**Step 5: Docker Compose files**

Add to each file's app environment:
- `docker-compose.dev.yml`: `THESTUDIO_APPROVAL_AUTO_BYPASS: "${THESTUDIO_APPROVAL_AUTO_BYPASS:-true}"`
- `infra/docker-compose.yml`: `THESTUDIO_APPROVAL_AUTO_BYPASS: "${THESTUDIO_APPROVAL_AUTO_BYPASS:-true}"`
- `infra/docker-compose.prod.yml`: `THESTUDIO_APPROVAL_AUTO_BYPASS: "${THESTUDIO_APPROVAL_AUTO_BYPASS:-false}"`

**Step 6: Documentation**

Add row to `docs/FEATURE-FLAGS.md` Pipeline Feature Flags table:
```
| `approval_auto_bypass` | `bool` | `False` | 30 | Skip human approval gate (dev/test only; blocked when github_provider=real + llm_provider=anthropic) |
```

**Step 7: Integration tests**

Create `tests/integration/test_story_30_14_approval_bypass.py` with tests per AC 8.

**Files to create:**
- `tests/integration/test_story_30_14_approval_bypass.py`

**Files to modify:**
- `src/settings.py`
- `src/workflow/pipeline.py`
- `src/ingress/workflow_trigger.py`
- `docker-compose.dev.yml`
- `infra/docker-compose.yml`
- `infra/docker-compose.prod.yml`
- `docs/FEATURE-FLAGS.md`
- `docs/deployment.md`

**Estimate:** 3-4 hours (M size, 5 story points)

---

## Done-When Checklist

### Story 30.13
- [ ] `_record_audit()` sets `overlays` from `context.overlays`
- [ ] Tests enable `agent_llm_enabled` for the agent under test
- [ ] Tests mock `_call_llm_completion` to return valid response
- [ ] `pytest tests/unit/test_gateway_enforcement.py -v` shows 6/6 passing
- [ ] No duplicate audit entries for implement activity
- [ ] `pytest` full suite has zero regressions

### Story 30.14
- [ ] `approval_auto_bypass` field exists in Settings with `False` default
- [ ] `@model_validator` rejects bypass + real GitHub + real LLM (2 conditions, NOT 3)
- [ ] Pipeline skips approval gate when `approval_auto_bypass=True`
- [ ] `PipelineOutput.approval_bypassed` is `True` when gate is skipped
- [ ] `workflow_trigger.py` threads `settings.approval_auto_bypass` into PipelineInput
- [ ] All 3 Docker Compose files have the env var with correct defaults
- [ ] `docs/FEATURE-FLAGS.md` updated
- [ ] `docs/deployment.md` updated
- [ ] `tests/integration/test_story_30_14_approval_bypass.py` has >= 8 tests, all passing
- [ ] `pytest` full suite has zero regressions
