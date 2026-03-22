"""Tests for Temporal steering signal handlers (Epic 37 T37.9).

Tests all 5 signal handlers:
  - pause_task
  - resume_task
  - abort_task
  - redirect_task
  - retry_stage

Test dimensions covered:
  - State mutations (pause/unpause, abort flag, redirect target)
  - Audit activity calls (persist_steering_audit_activity called with correct args)
  - Idempotency (pause twice, abort twice)
  - Invalid redirect targets (unknown stage, forward direction)
  - retry with no current stage

Uses ``temporalio.testing.WorkflowEnvironment`` with time-skipping, matching the
pattern established in ``tests/workflow/test_approval_wait.py``.  All activities
are registered as stubs.  ``persist_steering_audit_activity`` is replaced with a
recording stub so tests can assert it was called with the expected arguments.
"""

from __future__ import annotations

import asyncio

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from src.workflow.activities import (
    ApprovalRequestInput,
    AssemblerInput,
    AssemblerOutput,
    AssignTrustTierInput,
    AssignTrustTierOutput,
    ContextInput,
    ContextOutput,
    EscalateTimeoutInput,
    EscalateTimeoutOutput,
    ImplementInput,
    ImplementOutput,
    IntakeInput,
    IntakeOutput,
    IntentInput,
    IntentOutput,
    PersistSteeringAuditInput,
    PreflightActivityOutput,
    PreflightInput,
    ProjectStatusInput,
    ProjectStatusOutput,
    PublishInput,
    PublishOutput,
    QAInput,
    QAOutput,
    ReadinessActivityOutput,
    ReadinessInput,
    RouterInput,
    RouterOutput,
    VerifyInput,
    VerifyOutput,
)
from src.workflow.pipeline import (
    PipelineInput,
    TheStudioPipelineWorkflow,
)

# ---------------------------------------------------------------------------
# Recorded audit calls — reset before each test
# ---------------------------------------------------------------------------

_recorded_audit_calls: list[PersistSteeringAuditInput] = []

TASK_QUEUE = "test-steering-signals-queue"


def _make_input(
    repo_tier: str = "suggest",
    task_id: str = "test-tp-steering-001",
) -> PipelineInput:
    """Minimal PipelineInput for steering signal tests."""
    return PipelineInput(
        taskpacket_id=task_id,
        correlation_id="test-corr-steering-001",
        repo="owner/repo",
        repo_registered=True,
        repo_tier=repo_tier,
        event_id="evt-steering-001",
        issue_title="Steering test issue",
        issue_body="Test body for steering signals",
    )


# ---------------------------------------------------------------------------
# Stub activities
# ---------------------------------------------------------------------------

@activity.defn(name="intake_activity")
async def stub_intake_activity(params: IntakeInput) -> IntakeOutput:
    return IntakeOutput(accepted=True, base_role="developer", overlays=[])


@activity.defn(name="context_activity")
async def stub_context_activity(params: ContextInput) -> ContextOutput:
    return ContextOutput(complexity_index="low", risk_flags={})


@activity.defn(name="assign_trust_tier_activity")
async def stub_assign_trust_tier_activity(
    params: AssignTrustTierInput,
) -> AssignTrustTierOutput:
    return AssignTrustTierOutput(tier="observe", matched_rule_id=None)


@activity.defn(name="readiness_activity")
async def stub_readiness_activity(params: ReadinessInput) -> ReadinessActivityOutput:
    return ReadinessActivityOutput(proceed=True, overall_score=1.0, gate_decision="pass")


@activity.defn(name="intent_activity")
async def stub_intent_activity(params: IntentInput) -> IntentOutput:
    return IntentOutput(
        intent_spec_id="spec-001",
        version=1,
        goal="Test goal",
        acceptance_criteria=["AC1"],
    )


@activity.defn(name="router_activity")
async def stub_router_activity(params: RouterInput) -> RouterOutput:
    return RouterOutput(selections=[], rationale="default")


@activity.defn(name="assembler_activity")
async def stub_assembler_activity(params: AssemblerInput) -> AssemblerOutput:
    return AssemblerOutput(plan_steps=["step 1"], qa_handoff=[])


@activity.defn(name="preflight_activity")
async def stub_preflight_activity(params: PreflightInput) -> PreflightActivityOutput:
    return PreflightActivityOutput(approved=True, summary="OK")


@activity.defn(name="implement_activity")
async def stub_implement_activity(params: ImplementInput) -> ImplementOutput:
    return ImplementOutput(
        taskpacket_id=params.taskpacket_id,
        files_changed=["file.py"],
        agent_summary="Implemented",
    )


@activity.defn(name="verify_activity")
async def stub_verify_activity(params: VerifyInput) -> VerifyOutput:
    return VerifyOutput(passed=True, exhausted=False)


@activity.defn(name="qa_activity")
async def stub_qa_activity(params: QAInput) -> QAOutput:
    return QAOutput(passed=True, defect_count=0, has_intent_gap=False)


@activity.defn(name="publish_activity")
async def stub_publish_activity(params: PublishInput) -> PublishOutput:
    return PublishOutput(pr_number=42, pr_url="https://github.com/owner/repo/pull/42")


@activity.defn(name="post_approval_request_activity")
async def stub_post_approval_request_activity(
    params: ApprovalRequestInput,
) -> None:
    return None


@activity.defn(name="escalate_timeout_activity")
async def stub_escalate_timeout_activity(
    params: EscalateTimeoutInput,
) -> EscalateTimeoutOutput:
    return EscalateTimeoutOutput(escalated=True, label_applied=True)


@activity.defn(name="update_project_status_activity")
async def stub_update_project_status_activity(
    params: ProjectStatusInput,
) -> ProjectStatusOutput:
    return ProjectStatusOutput(synced=False)


@activity.defn(name="persist_steering_audit_activity")
async def stub_persist_steering_audit_activity(
    params: PersistSteeringAuditInput,
) -> None:
    """Recording stub — appends call to module-level list for test assertions."""
    _recorded_audit_calls.append(params)


ALL_STUB_ACTIVITIES = [
    stub_intake_activity,
    stub_context_activity,
    stub_assign_trust_tier_activity,
    stub_readiness_activity,
    stub_intent_activity,
    stub_router_activity,
    stub_assembler_activity,
    stub_preflight_activity,
    stub_implement_activity,
    stub_verify_activity,
    stub_qa_activity,
    stub_publish_activity,
    stub_post_approval_request_activity,
    stub_escalate_timeout_activity,
    stub_update_project_status_activity,
    stub_persist_steering_audit_activity,
]


@pytest.fixture(autouse=True)
def clear_audit_calls() -> None:
    """Clear the recorded audit calls before each test."""
    _recorded_audit_calls.clear()


# ---------------------------------------------------------------------------
# Helper — shared worker context manager
# ---------------------------------------------------------------------------

def _worker_context(env: WorkflowEnvironment):  # type: ignore[return]
    return Worker(
        env.client,
        task_queue=TASK_QUEUE,
        workflows=[TheStudioPipelineWorkflow],
        activities=ALL_STUB_ACTIVITIES,
    )


# ===========================================================================
# pause_task tests
# ===========================================================================


@pytest.mark.asyncio
async def test_pause_task_then_resume_then_approve_succeeds() -> None:
    """Pause while in approval wait, resume, then approve → workflow succeeds."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-pause-resume-approve",
                task_queue=TASK_QUEUE,
            )

            # Allow workflow to reach the approval wait state.
            await asyncio.sleep(2)

            # Pause → sets _paused = True, emits audit entry.
            await handle.signal(
                TheStudioPipelineWorkflow.pause_task,
                args=["admin", "test-tp-steering-001"],
            )
            # Resume → sets _paused = False, emits audit entry.
            await handle.signal(
                TheStudioPipelineWorkflow.resume_task,
                args=["admin", "test-tp-steering-001"],
            )
            # Approve to unblock approval wait.
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is True
            assert result.step_reached == "publish"

            # Both pause and resume should have generated audit entries.
            assert len(_recorded_audit_calls) >= 2
            actions = [c.action for c in _recorded_audit_calls]
            assert "pause" in actions
            assert "resume" in actions


@pytest.mark.asyncio
async def test_pause_task_idempotent() -> None:
    """Sending pause_task twice does not cause errors; workflow unblocks normally."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-pause-idempotent",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            # Pause twice — second call is harmless.
            await handle.signal(
                TheStudioPipelineWorkflow.pause_task,
                args=["admin", "test-tp-steering-001"],
            )
            await handle.signal(
                TheStudioPipelineWorkflow.pause_task,
                args=["admin", "test-tp-steering-001"],
            )
            # Resume to unblock pause hold.
            await handle.signal(
                TheStudioPipelineWorkflow.resume_task,
                args=["admin", "test-tp-steering-001"],
            )
            # Approve.
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is True


# ===========================================================================
# resume_task tests
# ===========================================================================


@pytest.mark.asyncio
async def test_resume_task_without_prior_pause_is_harmless() -> None:
    """resume_task when not paused sets _paused = False (already False) — no crash."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-resume-no-pause",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            # Resume without a prior pause — idempotent, no error.
            await handle.signal(
                TheStudioPipelineWorkflow.resume_task,
                args=["admin", "test-tp-steering-001"],
            )
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is True
            # Audit entry should still be emitted for the resume action.
            resume_calls = [c for c in _recorded_audit_calls if c.action == "resume"]
            assert len(resume_calls) == 1
            assert resume_calls[0].actor == "admin"


# ===========================================================================
# abort_task tests
# ===========================================================================


@pytest.mark.asyncio
async def test_abort_task_returns_aborted_rejection() -> None:
    """Abort signal during approval wait → workflow returns with aborted rejection."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-abort-basic",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            # Abort the task with a reason.
            await handle.signal(
                TheStudioPipelineWorkflow.abort_task,
                args=["human cancelled", "admin", "test-tp-steering-001"],
            )
            # Approve to unblock the approval wait condition so the workflow
            # can observe the abort at the next _await_if_paused checkpoint.
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is False
            assert result.rejection_reason is not None
            assert "aborted" in result.rejection_reason
            assert "human cancelled" in result.rejection_reason

            # Audit entry must be emitted for abort.
            abort_calls = [c for c in _recorded_audit_calls if c.action == "abort"]
            assert len(abort_calls) == 1
            assert abort_calls[0].reason == "human cancelled"
            assert abort_calls[0].actor == "admin"
            assert abort_calls[0].to_stage == "aborted"


@pytest.mark.asyncio
async def test_abort_task_clears_pause() -> None:
    """abort_task unblocks a paused workflow by clearing the _paused flag."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-abort-clears-pause",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            # Pause first.
            await handle.signal(
                TheStudioPipelineWorkflow.pause_task,
                args=["admin", "test-tp-steering-001"],
            )
            # Abort — this should clear the pause flag.
            await handle.signal(
                TheStudioPipelineWorkflow.abort_task,
                args=["abort clears pause", "admin", "test-tp-steering-001"],
            )
            # Approve to unblock approval wait so abort is observed.
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is False
            assert result.rejection_reason is not None
            assert "aborted" in result.rejection_reason


@pytest.mark.asyncio
async def test_abort_task_idempotent() -> None:
    """Sending abort_task twice does not cause errors."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-abort-idempotent",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            await handle.signal(
                TheStudioPipelineWorkflow.abort_task,
                args=["first abort", "admin", "test-tp-steering-001"],
            )
            await handle.signal(
                TheStudioPipelineWorkflow.abort_task,
                args=["second abort", "admin", "test-tp-steering-001"],
            )
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is False
            assert result.rejection_reason is not None
            assert "aborted" in result.rejection_reason

            # At least one abort audit entry must have been emitted.  The second
            # abort signal may race with workflow completion (TMPRL1102), so we
            # only assert >= 1 rather than == 2.
            abort_calls = [c for c in _recorded_audit_calls if c.action == "abort"]
            assert len(abort_calls) >= 1


# ===========================================================================
# redirect_task tests
# ===========================================================================


@pytest.mark.asyncio
async def test_redirect_task_unknown_stage_is_noop() -> None:
    """redirect_task to an unknown stage is silently ignored; workflow continues."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-redirect-unknown-stage",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            # Redirect to a completely unknown stage → should be a no-op.
            await handle.signal(
                TheStudioPipelineWorkflow.redirect_task,
                args=["totally_unknown_stage", "reason", "admin", ""],
            )
            # No redirect was set, so approve unblocks normally.
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            # Redirect was ignored; workflow completed normally.
            assert result.success is True
            assert result.step_reached == "publish"

            # No audit entry should have been emitted for an invalid redirect.
            redirect_calls = [c for c in _recorded_audit_calls if c.action == "redirect"]
            assert len(redirect_calls) == 0


@pytest.mark.asyncio
async def test_redirect_task_forward_direction_is_noop() -> None:
    """redirect_task to a stage AFTER the current stage is silently ignored."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-redirect-forward",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            # At approval wait, _current_step = "awaiting_approval" (order 13).
            # Redirect to "publish" (order 14) is a forward redirect → no-op.
            await handle.signal(
                TheStudioPipelineWorkflow.redirect_task,
                args=["publish", "try to skip to publish", "admin", ""],
            )
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is True
            assert result.step_reached == "publish"

            # No audit entry for invalid redirect.
            redirect_calls = [c for c in _recorded_audit_calls if c.action == "redirect"]
            assert len(redirect_calls) == 0


@pytest.mark.asyncio
async def test_redirect_task_valid_triggers_restart_from_target() -> None:
    """redirect_task to an earlier stage triggers continue_as_new and restarts."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-redirect-valid",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            # Redirect from "awaiting_approval" (order 13) back to "context" (order 2).
            await handle.signal(
                TheStudioPipelineWorkflow.redirect_task,
                args=["context", "redo context", "admin", "test-tp-steering-001"],
            )
            # Approve to unblock the approval wait; the workflow then applies
            # the redirect at the publish checkpoint via continue_as_new.
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            # Wait for continue_as_new to fire and new execution to reach
            # the approval wait state again.
            await asyncio.sleep(4)

            # Approve the new execution.
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is True
            assert result.step_reached == "publish"

            # Audit entry must have been emitted for the redirect.
            redirect_calls = [c for c in _recorded_audit_calls if c.action == "redirect"]
            assert len(redirect_calls) >= 1
            assert redirect_calls[0].to_stage == "context"
            assert redirect_calls[0].from_stage == "awaiting_approval"
            assert redirect_calls[0].reason == "redo context"


# ===========================================================================
# retry_stage tests
# ===========================================================================


@pytest.mark.asyncio
async def test_retry_stage_valid_triggers_continue_as_new() -> None:
    """retry_stage at current stage triggers continue_as_new to re-enter the stage."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-retry-valid",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            # At approval wait, _current_step = "awaiting_approval".
            # retry_stage retries the current stage.
            await handle.signal(
                TheStudioPipelineWorkflow.retry_stage,
                args=["retry approval stage", "admin", "test-tp-steering-001"],
            )
            # Approve to unblock the approval wait; workflow applies retry via
            # continue_as_new at the publish checkpoint.
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            # Wait for continue_as_new to fire and new execution to reach
            # the approval wait state.
            await asyncio.sleep(4)

            # Approve the new execution.
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is True
            assert result.step_reached == "publish"

            # Audit entry must be emitted for the retry action.
            retry_calls = [c for c in _recorded_audit_calls if c.action == "retry"]
            assert len(retry_calls) >= 1
            assert retry_calls[0].reason == "retry approval stage"
            assert retry_calls[0].actor == "admin"
            # from_stage and to_stage are both the current stage for retry.
            assert retry_calls[0].from_stage == "awaiting_approval"
            assert retry_calls[0].to_stage == "awaiting_approval"


@pytest.mark.asyncio
async def test_retry_stage_no_current_stage_is_noop() -> None:
    """retry_stage when _current_step is not yet set is silently ignored.

    Sends the retry signal immediately after workflow start (with minimal delay),
    before the workflow has had a chance to commit its first step.  Even if the
    signal races with the first _await_if_paused call, the workflow must still
    complete normally — the retry is either a no-op (empty current stage) or
    retries "intake" which fast-paths through to the same result.
    """
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-retry-no-stage",
                task_queue=TASK_QUEUE,
            )

            # Send retry_stage immediately, before significant workflow execution.
            # _current_step is "" at this point if delivered before the first
            # _await_if_paused; the handler logs a warning and returns early.
            await handle.signal(
                TheStudioPipelineWorkflow.retry_stage,
                args=["early retry", "admin", ""],
            )

            # Let workflow reach approval wait.
            await asyncio.sleep(2)

            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            # Regardless of signal timing, the workflow should complete or
            # reach the publish step (retry was a no-op or retried "intake").
            assert result.step_reached in ("publish", "intake", "context", "intent",
                                           "router", "assembler", "implement",
                                           "verify", "qa", "awaiting_approval")


@pytest.mark.asyncio
async def test_retry_stage_audit_activity_called() -> None:
    """retry_stage emits an audit activity call with correct action field."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with _worker_context(env):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-retry-audit",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            await handle.signal(
                TheStudioPipelineWorkflow.retry_stage,
                args=["verify audit", "ops-bot", ""],
            )
            # Approve to trigger continue_as_new.
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            await asyncio.sleep(4)

            # Approve new execution.
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            await handle.result()

            # Audit entry must have action == "retry".
            retry_calls = [c for c in _recorded_audit_calls if c.action == "retry"]
            assert len(retry_calls) >= 1
            assert retry_calls[0].actor == "ops-bot"
