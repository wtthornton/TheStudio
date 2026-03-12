# Epic 21 — Temporal Workflow Pauses for Human Approval Before Publishing

**Author:** Saga
**Date:** 2026-03-12
**Status:** Draft — Meridian Round 2: COMMITTABLE
**Target Sprint:** After Epic 19/20 spike completion; blocked by Story 0 spike

---

## 1. Title

Temporal Workflow Pauses for Human Approval Before Publishing — Add a durable wait state between QA pass and Publish that blocks on a human signal or 7-day timeout, enforcing the POLICIES.md requirement that Suggest and Execute tier tasks do not publish without human approval.

## 2. Narrative

The pipeline currently runs all nine steps in a straight line. QA passes, Publisher fires, PR appears on GitHub. There is no pause, no gate, no moment where a human says "yes, ship it." For Observe tier repos that is fine — the output is a draft PR, read-only. But POLICIES.md is explicit: Suggest and Execute tiers require human approval before the system publishes. The `EffectiveRolePolicy` already computes `requires_human_review` and the architecture documents (15-system-runtime-flow.md, POLICIES.md) describe a waiting state with 24h/72h/7d reminder cadence and a 7-day timeout escalation. None of that exists in code.

This matters now for three reasons:

**It blocks Execute tier.** C2 (Execute tier end-to-end) depends on C6 (this epic). The dependency graph in the architecture mapping is unambiguous: human approval must exist before the system can auto-merge anything. Without this wait state, enabling Execute tier would mean the system publishes and potentially merges without a human ever reviewing the output.

**It is a policy violation.** The system currently violates a documented invariant. Every Suggest-tier task that completes the pipeline today bypasses a required control. The longer this gap exists, the more tasks run through the unguarded path, and the harder it becomes to retrofit the gate without disrupting in-flight work.

**It requires new Temporal expertise.** The team has not built Temporal timer activities, signal handlers, or long-running wait conditions before. The current workflow uses only `execute_activity` with short timeouts. A 7-day wait with an external resume signal is a fundamentally different pattern — durable timers, signal definitions, condition-based wake-up. This is why the architecture mapping flags C6 as a risk item and why this epic includes a dedicated spike story.

The end state: after QA passes, the workflow checks the repo tier. If Observe, it proceeds directly to Publish (current behavior, unchanged). If Suggest or Execute, the workflow enters a durable wait state. Publisher posts a summary comment requesting human approval. The workflow resumes when it receives an approval signal (from a GitHub comment command, admin API call, or label change) or when the 7-day timer expires. On timeout, the task is escalated and paused — it does not publish.

## 3. References

| Artifact | Location |
|----------|----------|
| POLICIES.md (human approval section) | `thestudioarc/POLICIES.md` lines 44-58 |
| System runtime flow (wait states, timeout table) | `thestudioarc/15-system-runtime-flow.md` lines 431-446, 342 |
| Architecture gap analysis (C6) | `docs/architecture-vs-implementation-mapping.md` line 431 |
| Current pipeline workflow | `src/workflow/pipeline.py` |
| Workflow activities | `src/workflow/activities.py` |
| Publisher module | `src/publisher/publisher.py` |
| TaskPacket status model | `src/models/taskpacket.py` lines 21-51 |
| EffectiveRolePolicy (requires_human_review) | `src/intake/effective_role.py` line 132 |
| Temporal Python SDK docs (signals, timers) | https://docs.temporal.io/develop/python/message-passing |
| Dependency: C2 (Execute tier) depends on this | `docs/architecture-vs-implementation-mapping.md` line 543 |
| V2 (Reminder cadence) follows this | `docs/architecture-vs-implementation-mapping.md` line 440 |

## 4. Acceptance Criteria

1. **Observe tier is unchanged.** When `repo_tier == "observe"`, the workflow proceeds from QA pass directly to Publish with no wait state. All existing tests pass without modification.

2. **Suggest/Execute tier enters a durable wait after QA.** When `repo_tier` is `"suggest"` or `"execute"` and QA passes, the Temporal workflow enters a wait state before executing the publish activity. The wait is implemented using Temporal's `workflow.wait_condition()` (or equivalent Temporal SDK primitive as determined by the spike — Story 0) with a timeout, not a polling loop or sleep activity. The tier check uses `repo_tier` from `PipelineInput`, not `requires_human_review` from `EffectiveRolePolicy`. (`requires_human_review` is computed from tier but may have additional conditions in future; the workflow checks tier directly for simplicity.)

3. **Workflow resumes on approval signal.** A Temporal signal named `approve_publish` (carrying `approved_by: str` and `approval_source: str`) wakes the workflow. The workflow records the approver identity and proceeds to Publish. The workflow records the approval timestamp. Both the wait-entry timestamp (when `AWAITING_APPROVAL` status was set) and approval timestamp are included in `PipelineOutput` for metric computation.

4. **Workflow escalates on 7-day timeout.** If no approval signal arrives within 7 days (168 hours), the workflow does NOT publish. Instead it: (a) transitions the TaskPacket status to a new `AWAITING_APPROVAL_EXPIRED` state, (b) applies the `agent:human-review` label via a dedicated escalation activity, and (c) returns a `PipelineOutput` with `success=False` and a clear `rejection_reason`.

5. **TaskPacket status model extended.** Two new statuses exist: `AWAITING_APPROVAL` (entered when the wait state begins) and `AWAITING_APPROVAL_EXPIRED` (entered on timeout). Allowed transitions are updated: `VERIFICATION_PASSED -> AWAITING_APPROVAL -> PUBLISHED` and `AWAITING_APPROVAL -> AWAITING_APPROVAL_EXPIRED`.

6. **Publisher posts approval request comment.** Before entering the wait state, an activity calls Publisher to post a summary comment on the PR/issue stating what needs approval, why, and how to approve (signal mechanism). This comment includes the TaskPacket ID, intent summary, and QA result.

7. **Approval API endpoint exists.** A FastAPI endpoint (`POST /api/tasks/{taskpacket_id}/approve`) sends the Temporal signal to the running workflow. The endpoint validates that the workflow exists and is in the waiting state before signaling. Returns 404 if workflow not found, 409 if not in waiting state, 200 on success.

8. **PipelineInput and PipelineOutput updated.** `PipelineOutput` gains an `awaiting_approval: bool` field and an `approved_by: str | None` field. `WorkflowStep` enum gains an `AWAITING_APPROVAL` value.

9. **Tests cover all paths.** Unit tests verify: (a) Observe tier skips the wait, (b) Suggest tier enters the wait, (c) approval signal resumes the workflow and proceeds to publish, (d) 7-day timeout triggers escalation and does not publish, (e) the approval API endpoint returns correct status codes. Integration tests use Temporal's test environment with time-skipping to validate the 7-day timeout without waiting 7 real days.

10. **Spike deliverable produced.** A documented spike output (markdown in `docs/spikes/`) covers: Temporal signal handler patterns, `workflow.wait_condition` with timeout, time-skipping in tests, and any SDK version constraints. The spike is completed and reviewed before implementation stories begin.

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Team has no prior Temporal timer/signal experience | High | High — wrong pattern choice causes workflow bugs or data loss | Spike story (Story 0) is mandatory first; prototype in isolation before wiring into pipeline |
| Long-running workflow state bloats Temporal history | Medium | Medium — workflow replay becomes slow | Use `continue_as_new` if history exceeds threshold; document history size expectations in spike |
| Signal delivery race with timeout | Medium | Medium — approval arrives at the exact moment of timeout | Temporal guarantees deterministic resolution; spike must document the SDK's behavior for this edge case |
| Approval API lacks auth | Low | High — anyone can approve a task | API endpoint uses existing admin auth middleware (dev-mode `X-User-ID` for now; production auth is a separate concern) |
| Reminder cadence (24h/72h/7d) adds complexity | Medium | Low — reminders are a nice-to-have on top of the core wait | Reminders are explicitly out of scope (V2); this epic implements the wait and timeout only |

## 5. Constraints & Non-Goals

### Constraints

- The Temporal Python SDK version currently in use (`temporalio` package in `pyproject.toml`) must support signals and `workflow.wait_condition` with timeout. The spike must verify this.
- The wait state is implemented in the workflow definition (`src/workflow/pipeline.py`), not as a separate activity. Temporal activities cannot wait for signals — only workflows can.
- The approval signal must be idempotent: sending it twice does not cause errors or double-publish.
- All changes must maintain backward compatibility with existing Observe-tier workflows that are already running.
- TaskPacket status transitions must remain in `ALLOWED_TRANSITIONS` — no ad-hoc status writes.

### Non-Goals

- **Reminder cadence (24h/72h/7d notifications).** This is V2, listed in the architecture mapping. This epic builds the wait state; reminders are a follow-up.
- **GitHub comment command parsing** (`/approve` in PR comments). The approval mechanism in this epic is the API endpoint and Temporal signal. GitHub-to-signal bridging is future work.
- **GitHub label-based approval** (removing `agent:human-review` triggers approval). Future work.
- **Execute tier end-to-end (C2).** This epic is a prerequisite for C2 but does not implement Execute tier behavior.
- **Auto-merge.** POLICIES.md explicitly defers auto-merge. This epic does not touch merge behavior.
- **Admin UI for approval management.** The API endpoint exists; the UI to call it is future work.
- **Multi-approver workflows.** A single approval signal is sufficient for this epic.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|---------------|
| Epic Owner | TBD (TBD — assign before sprint start) | Scope decisions, acceptance sign-off |
| Tech Lead | TBD (TBD — assign before sprint start) | Temporal pattern review, signal design, workflow architecture |
| Spike Lead | TBD (TBD — assign before sprint start) | Temporal timer/signal research, prototype, documented findings |
| QA | TBD (TBD — assign before sprint start) | Test plan review, timeout/signal edge case validation |
| Meridian Reviewer | Meridian | Epic review, sprint plan review |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Policy compliance | 100% of Suggest/Execute tier tasks enter wait state before publish | Query TaskPacket status transitions: every `PUBLISHED` task with tier != observe must have passed through `AWAITING_APPROVAL` |
| Approval turnaround | Median < 24 hours | Time between `AWAITING_APPROVAL` status and approval signal receipt |
| Timeout escalation rate | < 10% of awaiting tasks hit 7-day timeout | Count of `AWAITING_APPROVAL_EXPIRED` vs total `AWAITING_APPROVAL` entries |
| Zero regression | All existing pipeline tests pass | CI green on all existing test suites after merge |
| Spike completed before implementation | Spike doc exists and is reviewed before Story 1 starts | File exists in `docs/spikes/` with review comments |

## 8. Context & Assumptions

### Business Rules

- POLICIES.md section "Human Approval Wait States" (lines 44-58) is the authoritative source for when to enter the wait state and what happens on timeout.
- The `EffectiveRolePolicy.requires_human_review` field (computed in `src/intake/effective_role.py`) already determines whether a task needs human review. However, the current workflow ignores this field. This epic wires it into the workflow decision.
- Observe tier tasks never enter the wait state, regardless of `requires_human_review`.
- The 7-day timeout is a hard policy boundary. It is not configurable per repo in this epic.

### Dependencies

- **Temporal Python SDK** must support `workflow.wait_condition(fn, timeout=timedelta(days=7))` and `@workflow.signal`. The spike must verify SDK version compatibility.
- **TaskPacket status model** (`src/models/taskpacket.py`) must be extended with two new statuses and transitions. This is a database migration if statuses are stored as enum columns.
- **Publisher** must support posting an "approval requested" comment without creating a PR (the PR already exists at this point in the flow).
- **No dependency on C1-C5, C7, or C8.** This epic is standalone per the dependency graph.

### Systems Affected

| System | Change |
|--------|--------|
| `src/workflow/pipeline.py` | Add signal handler, wait condition, tier-based branching after QA |
| `src/workflow/activities.py` | Add `post_approval_request_activity` and `escalate_timeout_activity` |
| `src/models/taskpacket.py` | Add `AWAITING_APPROVAL` and `AWAITING_APPROVAL_EXPIRED` statuses and transitions |
| `src/publisher/publisher.py` | Add `post_approval_request()` function for the summary comment |
| `src/app.py` (or router file) | Add `POST /api/tasks/{taskpacket_id}/approve` endpoint |
| `tests/` | New test module for approval wait state; updates to existing pipeline workflow tests |
| `docs/spikes/` | New spike document for Temporal timer/signal patterns |

### Assumptions

- The Temporal worker is configured to handle workflows that run for up to 7 days. Default Temporal workflow execution timeout may need to be raised.
- The approval API endpoint is sufficient as the initial approval mechanism. GitHub-native approval (comment commands, label changes) will be layered on later.
- A single approval is sufficient — no multi-party approval chains in this epic.
- The existing test infrastructure supports Temporal time-skipping (via `temporalio.testing.WorkflowEnvironment`).

---

## Story Map

Stories are ordered as vertical slices — each delivers testable value. The spike (Story 0) must complete before any implementation story begins.

### Story 0: Spike — Temporal Signal, Wait Condition, and Timer Patterns

**As a** developer building long-running workflow states,
**I need** a documented reference for Temporal Python SDK signal handlers, `workflow.wait_condition` with timeout, and time-skipping in tests,
**so that** implementation stories can proceed with confidence and a proven pattern.

**Deliverables:**
- Markdown document in `docs/spikes/spike-temporal-signals-and-timers.md`
- Minimal proof-of-concept workflow (can be in a scratch file, does not need to be production code) demonstrating: signal definition, wait_condition with 7-day timeout, time-skipping test
- Document SDK version requirements, any gotchas (history size, determinism constraints, signal-timeout race behavior)
- Review by tech lead before Story 1 starts

**Files to create:** `docs/spikes/spike-temporal-signals-and-timers.md`

**Estimate:** S (1-2 days)

---

### Story 1: Extend TaskPacket Status Model with Approval States

**As a** platform developer,
**I need** `AWAITING_APPROVAL` and `AWAITING_APPROVAL_EXPIRED` statuses in the TaskPacket model,
**so that** the workflow can track tasks waiting for human approval and tasks that timed out.

**Acceptance Criteria:**
- `TaskPacketStatus` enum has `AWAITING_APPROVAL = "awaiting_approval"` and `AWAITING_APPROVAL_EXPIRED = "awaiting_approval_expired"`
- `ALLOWED_TRANSITIONS` updated: `VERIFICATION_PASSED` can transition to `AWAITING_APPROVAL`; `AWAITING_APPROVAL` can transition to `PUBLISHED`, `AWAITING_APPROVAL_EXPIRED`, or `FAILED`; `AWAITING_APPROVAL_EXPIRED` can transition to `FAILED`
- Existing transitions unchanged
- If TaskPacket status is stored as a DB enum column, a new migration adds the two new values. Migration is idempotent.
- Unit tests for new transitions pass; existing transition tests unmodified

**Files to modify:** `src/models/taskpacket.py`, `tests/models/test_taskpacket.py` (or equivalent)

**Estimate:** S

---

### Story 2: Add Approval Signal and Wait Condition to Pipeline Workflow

**As a** Temporal workflow,
**I need** a signal handler for `approve_publish` and a `wait_condition` with 7-day timeout after QA pass,
**so that** Suggest/Execute tier tasks pause for human approval before publishing.

**Acceptance Criteria:**
- `WorkflowStep` enum gains `AWAITING_APPROVAL = "awaiting_approval"`
- `TheStudioPipelineWorkflow` defines `@workflow.signal` handler for `approve_publish` that sets an internal flag and records `approved_by`
- After QA pass, if `repo_tier` is `"suggest"` or `"execute"`, workflow calls `workflow.wait_condition(lambda: self._approved, timeout=timedelta(days=7))`
- If condition met (approved), workflow proceeds to Publish with `approved_by` recorded in output
- If timeout, workflow does NOT proceed to Publish; returns `PipelineOutput` with `success=False`, `rejection_reason="approval_timeout"`, `step_reached="awaiting_approval"`
- `PipelineOutput` gains `awaiting_approval: bool = False` and `approved_by: str | None = None`
- Observe tier path is completely unchanged — no wait, no signal handler needed
- `PipelineInput` unchanged (repo_tier already present)

**Files to modify:** `src/workflow/pipeline.py`

**Estimate:** M

---

### Story 3: Post Approval Request Activity

**As a** workflow entering the approval wait state,
**I need** to post a summary comment on the PR/issue requesting human approval,
**so that** the human reviewer knows what to review and how to approve.

**Acceptance Criteria:**
- New activity `post_approval_request_activity` in `src/workflow/activities.py` with input containing `taskpacket_id`, `pr_url`, `intent_summary`, `qa_result_summary`
- Activity calls a new `post_approval_request()` function in `src/publisher/publisher.py` that posts a GitHub comment with: TaskPacket ID, intent summary, QA result, and instructions for approval
- Comment uses a distinct marker (like `EVIDENCE_COMMENT_MARKER`) so it can be found/updated idempotently
- Activity is called by the workflow before entering the wait state
- Activity uses the existing `PublishInput`/`PublishOutput` pattern for Temporal serialization

**Files to modify:** `src/workflow/activities.py`, `src/workflow/pipeline.py`, `src/publisher/publisher.py`

**Estimate:** M

---

### Story 4: Escalation Activity for Timeout

**As a** workflow that has timed out waiting for approval,
**I need** to apply the `agent:human-review` label and post an escalation comment,
**so that** the task is visibly flagged for human attention.

**Acceptance Criteria:**
- New activity `escalate_timeout_activity` in `src/workflow/activities.py`
- Activity applies `agent:human-review` label to the issue/PR via Publisher's GitHub client
- Activity posts a comment: "Approval wait expired after 7 days. Task paused. Manual action required."
- Activity transitions TaskPacket status to `AWAITING_APPROVAL_EXPIRED`
- Pipeline workflow calls this activity on timeout before returning failure output
- Activity is idempotent — calling it twice does not duplicate labels or comments

**Files to modify:** `src/workflow/activities.py`, `src/workflow/pipeline.py`, `src/publisher/publisher.py`

**Estimate:** M

---

### Story 5: Approval API Endpoint

**As an** operator or external system,
**I need** a `POST /api/tasks/{taskpacket_id}/approve` endpoint,
**so that** I can signal approval to the waiting workflow.

**Acceptance Criteria:**
- FastAPI route at `POST /api/tasks/{taskpacket_id}/approve` with request body `{ "approved_by": "string" }`
- Endpoint looks up the Temporal workflow ID (derived from TaskPacket ID, matching existing convention)
- Sends `approve_publish` signal to the workflow via Temporal client
- Returns 200 with `{ "status": "approved", "taskpacket_id": "..." }` on success
- Returns 404 if TaskPacket or workflow not found
- Returns 409 if workflow is not in the `AWAITING_APPROVAL` state (checked via TaskPacket status in DB)
- Uses existing auth middleware (dev-mode `X-User-ID` header)
- Idempotent: calling approve twice on an already-approved task returns 200 (not error)

**Files to modify/create:** `src/api/approval.py` (new router), `src/app.py` (register router)

**Estimate:** M

---

### Story 6: Temporal Time-Skipping Integration Tests

**As a** developer maintaining the approval wait state,
**I need** integration tests that verify the 7-day timeout without waiting 7 real days,
**so that** CI can validate timeout behavior in seconds.

**Acceptance Criteria:**
- Tests use `temporalio.testing.WorkflowEnvironment` with time-skipping enabled
- Test: Suggest-tier workflow enters wait, no signal sent, time skipped 7 days, workflow returns failure with `rejection_reason="approval_timeout"`
- Test: Suggest-tier workflow enters wait, approval signal sent after simulated 3 days, workflow completes successfully with `approved_by` populated
- Test: Observe-tier workflow completes without entering wait state (regression guard)
- Test: Signal sent to already-timed-out workflow has no effect (no crash)
- All tests run in CI in under 30 seconds

**Files to create:** `tests/workflow/test_approval_wait.py`

**Estimate:** M

---

### Story 7: Unit Tests for Approval API and Edge Cases

**As a** developer,
**I need** unit tests for the approval endpoint and workflow edge cases,
**so that** error paths are covered and regressions are caught.

**Acceptance Criteria:**
- Test: `POST /api/tasks/{id}/approve` returns 200 for valid waiting task
- Test: `POST /api/tasks/{id}/approve` returns 404 for unknown TaskPacket
- Test: `POST /api/tasks/{id}/approve` returns 409 for task not in `AWAITING_APPROVAL` state
- Test: Double-approve returns 200 (idempotent)
- Test: TaskPacket transitions `VERIFICATION_PASSED -> AWAITING_APPROVAL -> PUBLISHED` verified in DB
- Test: TaskPacket transitions `AWAITING_APPROVAL -> AWAITING_APPROVAL_EXPIRED` verified in DB

**Files to create:** `tests/api/test_approval.py`, `tests/models/test_taskpacket_approval.py`

**Estimate:** S

---

### Story 8: Documentation and Architecture Update

**As a** future developer or AI agent,
**I need** the architecture docs updated to reflect the implemented approval wait state,
**so that** the gap analysis shows C6 as complete.

**Acceptance Criteria:**
- `docs/architecture-vs-implementation-mapping.md` updated: C6 status changed from MISSING to IMPLEMENTED with reference to this epic
- `thestudioarc/15-system-runtime-flow.md` "Human Approval Wait States" section annotated with implementation references
- Pipeline workflow docstring in `src/workflow/pipeline.py` updated to describe the 10th step (approval wait between QA and Publish)
- `WorkflowStep` enum docstring updated

**Files to modify:** `docs/architecture-vs-implementation-mapping.md`, `src/workflow/pipeline.py`

**Estimate:** S

---

## Meridian Review Status

**Round 2: COMMITTABLE**

All Round 1 fixes verified. Full 7-question checklist passes. No red flags.

| # | Question | R1 Status | R2 Status |
|---|----------|-----------|-----------|
| 1 | Are acceptance criteria testable without ambiguity? | Fixed (AC2 spike flexibility, AC3 timestamps, repo_tier clarification) | PASS |
| 2 | Are constraints and non-goals explicit enough to prevent scope creep? | OK | PASS |
| 3 | Do success metrics have concrete targets? | Fixed (timestamps in PipelineOutput) | PASS |
| 4 | Are dependencies and affected systems fully enumerated? | Fixed (Story 1 DB migration) | PASS |
| 5 | Is the story map ordered by risk reduction? | OK (spike-first) | PASS |
| 6 | Can an AI agent implement each story from the description alone? | Fixed (owner placeholders, target sprint) | PASS |
| 7 | Are there red flags? | OK (auth uses existing middleware) | No red flags |

**Minor observations for sprint planning** (not blocking):
- Story 1 migration should follow existing numbering convention (check next available number)
- Consider naming explicit timestamp fields (`wait_entered_at`, `approved_at`) in Story 2
- Spike should verify workflow execution timeout is >= 7 days
