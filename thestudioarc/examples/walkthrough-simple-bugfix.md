# Pipeline Walkthrough: Simple Bug Fix

**Story:** 14.1 — Pipeline walkthrough example (happy path)
**Scenario:** Fix incorrect HTTP status code in intake webhook — returns 200 instead of 201 on successful task creation.
**Issue:** `acme/platform#412` — "Webhook returns 200 on task creation, should be 201"
**Trust tier:** Execute
**Outcome:** Single-pass success — no loopbacks, draft PR published.

---

## Pipeline at a Glance

```
GitHub Issue #412
      |
  [1. Intake]       webhook → eligibility → TaskPacket (received)
      |
  [2. Context]      enrichment → scope, risk_flags, complexity_index (enriched)
      |
  [3. Intent]       IntentSpec v1 → goal, AC, constraints (intent_built)
      |
  [4. Router]       expert selection → service context pack only (no full consult)
      |
  [5. Assembler]    merge → execution plan + provenance
      |
  [6. Implement]    Primary Agent edits webhook.py → EvidenceBundle (in_progress)
      |
  [7. Verify]       ruff + pytest → verification_passed signal (verification_passed)
      |
  [8. QA]           intent validation → all criteria pass
      |
  [9. Publish]      draft PR + evidence comment + labels (published)
      |
  GitHub PR #413 (draft, awaiting human merge)
```

---

## Stage 1 — Intake

**Upstream:** GitHub `issues.labeled` webhook event
**Downstream:** Context Manager

The Ingress Service receives the webhook, validates the HMAC signature, and hands the normalized event to the Intake Agent. `evaluate_eligibility` checks all gates in order: `agent:run` label present, repo registered, repo not paused, no active workflow. All pass.

`_select_base_role` maps `type:bug` → `BaseRole.DEVELOPER`. No risk labels are present so `overlays=[]`. `EffectiveRolePolicy.compute` produces a standard developer policy with `publishing_posture=ready_after_gate` (Execute tier, no draft-only overlays).

A `TaskPacketRow` is inserted and the workflow is started in Temporal.

**TaskPacket at end of Intake:**

```json
{
  "id": "tp-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "repo": "acme/platform",
  "issue_id": 412,
  "correlation_id": "corr-d4e5f6a7-b8c9-0123-defa-456789012345",
  "status": "received",
  "effective_role": {
    "base_role": "developer",
    "overlays": [],
    "mandatory_expert_classes": [],
    "verification_strictness": "standard",
    "publishing_posture": "ready_after_gate"
  }
}
```

**Labels applied by Intake:** `agent:queued`

---

## Stage 2 — Context

**Upstream:** TaskPacket (received)
**Downstream:** Intent Builder

The Context Manager inspects the repository. It reads the Repo Profile to find entry points, service context pack locations, and risk path triggers. It walks the diff surface implied by the issue — the webhook handler — and records the affected file.

No risk path triggers fire (`src/intake/webhook.py` does not touch auth, billing, migration, or infra paths). The Complexity Index scores the change as `band=low`: single file, single function, no schema changes, no cross-service impact.

`risk_flags` are all false. No overlays are added. TaskPacket status advances to `enriched`.

**TaskPacket at end of Context:**

```json
{
  "status": "enriched",
  "scope": {
    "files_touched": ["src/intake/webhook.py"],
    "entry_points": ["POST /webhook"]
  },
  "risk_flags": {
    "auth": false,
    "migration": false,
    "billing": false,
    "infra": false
  },
  "complexity_index": {
    "score": 1,
    "band": "low",
    "dimensions": { "files": 1, "services": 1, "schema_changes": 0 }
  }
}
```

---

## Stage 3 — Intent

**Upstream:** TaskPacket (enriched) + risk flags + repo standards
**Downstream:** Router

The Intent Builder Agent reads the enriched TaskPacket and the issue body. It produces `IntentSpecRow` v1 — the definition of correctness for this task. The intent is narrow and unambiguous: one return value, one path, no schema changes.

`acceptance_criteria` are written to be directly testable: the first maps to an HTTP assertion in the test suite; the second guards against regression on error paths. TaskPacket status advances to `intent_built` and `intent_spec_id` + `intent_version=1` are recorded.

**IntentSpec v1:**

```json
{
  "id": "intent-7a8b9cde-f012-3456-789a-bcdef0123456",
  "taskpacket_id": "tp-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "version": 1,
  "goal": "Return HTTP 201 Created (not 200 OK) when the intake webhook successfully creates a new TaskPacket.",
  "constraints": [
    "Change must not alter the webhook response body schema",
    "Must remain backward-compatible with GitHub HMAC signature validation"
  ],
  "acceptance_criteria": [
    "POST /webhook returns 201 on successful TaskPacket creation",
    "Existing 400 and 422 error response paths are unaffected"
  ],
  "non_goals": [
    "Do not change the response body structure",
    "Do not alter eligibility logic or TaskPacket field values"
  ]
}
```

**TaskPacket fields updated:**

```json
{
  "status": "intent_built",
  "intent_spec_id": "intent-7a8b9cde-f012-3456-789a-bcdef0123456",
  "intent_version": 1
}
```

---

## Stage 4 — Router

**Upstream:** IntentSpec v1 + EffectiveRolePolicy
**Downstream:** Assembler

The Expert Router evaluates mandatory coverage from `EffectiveRolePolicy.mandatory_expert_classes` — the list is empty (no overlays, no risk triggers). It checks reputation weights for the `developer` base role at `complexity=low`.

Because no mandatory expert classes are required, the Router does not dispatch a full expert consult. It pulls the `intake-module-v2` Service Context Pack, which records the intake webhook's conventions, known patterns, and expected status code semantics. No expert reputation scores are updated at this stage.

**Routing decision:**

```json
{
  "taskpacket_id": "tp-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "experts_consulted": [],
  "service_context_packs": ["intake-module-v2"],
  "mandatory_classes_satisfied": true,
  "consult_budget_used": 0,
  "routing_notes": "Low complexity, no overlays — service context pack sufficient"
}
```

---

## Stage 5 — Assembler

**Upstream:** IntentSpec v1 + service context pack output
**Downstream:** Primary Agent

The Assembler merges the service context pack guidance with the intent spec into a single execution plan. There is only one input source so no conflicts need resolution. Provenance is recorded so the learning pipeline can attribute the outcome to the correct source.

The plan is narrow: one targeted edit, one file, one function call site. The intent spec is the tiebreaker if any ambiguity exists — here there is none.

**Execution plan:**

```json
{
  "plan_id": "plan-e1f2a3b4-c5d6-7890-ef12-34567890abcd",
  "taskpacket_id": "tp-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "intent_spec_id": "intent-7a8b9cde-f012-3456-789a-bcdef0123456",
  "decision": "In src/intake/webhook.py, change status_code=200 to status_code=201 on the successful TaskPacket creation return path.",
  "provenance": [
    { "source": "intake-module-v2", "scope": "service_context_pack" }
  ]
}
```

---

## Stage 6 — Implement

**Upstream:** Execution plan + IntentSpec v1
**Downstream:** Verification Gate

The Primary Agent (Developer role) executes the plan using the tool allowlist from `EffectiveRolePolicy` (`Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`). It reads `src/intake/webhook.py`, locates the success-path `JSONResponse` call, and changes `status_code=200` to `status_code=201`. No other lines are changed.

The agent produces an `EvidenceBundle` (from `src/agent/evidence.py`) summarising what was done. TaskPacket status advances to `in_progress`.

**EvidenceBundle:**

```json
{
  "taskpacket_id": "tp-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "intent_version": 1,
  "files_changed": ["src/intake/webhook.py"],
  "agent_summary": "Changed status_code from 200 to 201 on the TaskPacket creation success path in the webhook handler. No other paths or response body fields were modified.",
  "loopback_attempt": 0
}
```

---

## Stage 7 — Verify

**Upstream:** EvidenceBundle + TaskPacket (in_progress)
**Downstream:** QA Agent

The Verification Gate loads the Repo Profile and reads `required_checks: ["ruff", "pytest"]`. It runs each check in sequence. `run_ruff` lints the changed file — 0 violations. `run_pytest` runs the full test suite — 47 passed, 0 failed (the existing test that asserted a 200 response has been updated by the agent to assert 201).

All checks pass. `update_status` advances the TaskPacket to `verification_passed`. `emit_verification_passed` publishes the signal to JetStream subject `thestudio.verification.<taskpacket_id>`.

**JetStream signal — `verification_passed`:**

```json
{
  "event": "verification_passed",
  "taskpacket_id": "tp-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "correlation_id": "corr-d4e5f6a7-b8c9-0123-defa-456789012345",
  "timestamp": "2026-03-10T14:23:07.441Z",
  "loopback_count": 0,
  "checks": [
    { "name": "ruff", "result": "passed", "details": "0 violations", "duration_ms": 340 },
    { "name": "pytest", "result": "passed", "details": "47 passed, 0 failed", "duration_ms": 4120 }
  ]
}
```

---

## Stage 8 — QA

**Upstream:** Verification signal + IntentSpec v1 + EvidenceBundle
**Downstream:** Publisher

The QA Agent validates the implementation against each acceptance criterion in `IntentSpec v1`. It maps each criterion to a `CriterionResult` (from `src/qa/defect.py`).

Criterion 1: the test suite now asserts HTTP 201 on the success path, confirmed by the pytest output in the evidence bundle. Criterion 2: the 400 and 422 error paths are unchanged — the diff touches only the success return. Both criteria pass. `defect_count=0`, `has_intent_gap=false`.

**QA result:**

```json
{
  "passed": true,
  "defect_count": 0,
  "has_intent_gap": false,
  "criteria_results": [
    {
      "criterion": "POST /webhook returns 201 on successful TaskPacket creation",
      "passed": true,
      "evidence": "pytest: test_webhook_returns_201_on_create PASSED"
    },
    {
      "criterion": "Existing 400 and 422 error response paths are unaffected",
      "passed": true,
      "evidence": "Diff confirms no changes to error return paths"
    }
  ]
}
```

---

## Stage 9 — Publish

**Upstream:** QA result + EvidenceBundle + IntentSpec v1
**Downstream:** GitHub (draft PR)

The Publisher is the only component with GitHub write credentials. It creates a draft PR on the working branch, posts the full evidence comment (marked with `<!-- thestudio-evidence -->` for idempotent updates), applies lifecycle labels, and updates the Projects v2 field to `In Review`.

Because `publishing_posture=ready_after_gate` and both verification and QA passed with zero loopbacks, the PR is created as a draft and will be marked ready-for-review once a human approves. TaskPacket status advances to `published`.

**TaskPacket at end of Publish:**

```json
{
  "status": "published",
  "loopback_count": 0
}
```

**Evidence comment (abbreviated):**

```
<!-- thestudio-evidence -->

## TheStudio Evidence

| Field            | Value                                        |
|------------------|----------------------------------------------|
| TaskPacket ID    | tp-a1b2c3d4-e5f6-7890-abcd-ef1234567890     |
| Correlation ID   | corr-d4e5f6a7-b8c9-0123-defa-456789012345   |
| Intent Version   | v1                                           |
| Verification     | PASSED                                       |
| QA               | PASSED                                       |

### Intent Summary

**Goal:** Return HTTP 201 Created (not 200 OK) when the intake webhook successfully
creates a new TaskPacket.

### Acceptance Criteria

- [x] POST /webhook returns 201 on successful TaskPacket creation
- [x] Existing 400 and 422 error response paths are unaffected

### Verification Results

| Check  | Result | Details                    |
|--------|--------|----------------------------|
| ruff   | PASSED | 0 violations               |
| pytest | PASSED | 47 passed, 0 failed        |

### QA Result

**Result:** PASSED

### Expert Coverage

- No experts consulted

**Policy triggers:**
- None

### Loopback Summary

- Verification loops: 0 (categories: none)
- QA loops: 0 (categories: none)

### Files Changed

- `src/intake/webhook.py`

---
*Generated by TheStudio — AI-augmented software delivery*
```

**Labels applied:** `verification:passed`, `agent:human-review`
**Projects v2 Status field:** `In Review`

---

## Signal and State Summary

| Stage      | TaskPacket Status      | Key Output                              |
|------------|------------------------|-----------------------------------------|
| Intake     | `received`             | TaskPacket created, EffectiveRolePolicy |
| Context    | `enriched`             | scope, risk_flags, complexity_index     |
| Intent     | `intent_built`         | IntentSpec v1 (id + version recorded)  |
| Router     | `intent_built`         | service context pack pulled             |
| Assembler  | `intent_built`         | execution plan + provenance             |
| Implement  | `in_progress`          | EvidenceBundle, webhook.py edited       |
| Verify     | `verification_passed`  | verification_passed signal to JetStream |
| QA         | `verification_passed`  | all criteria pass, 0 defects            |
| Publish    | `published`            | draft PR #413, evidence comment posted  |

**Total loopbacks:** 0
**Intent versions:** 1 (no refinement needed)
**Experts consulted:** 0 (low complexity, no overlays — service context pack sufficient)
