"""Integration tests for the approval wait state (Epic 21, Story 6).

Uses Temporal's time-skipping test environment to validate the 7-day timeout
and approval signal behavior without waiting in real time.
"""

import asyncio

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from src.workflow.activities import (
    assembler_activity,
    context_activity,
    escalate_timeout_activity,
    implement_activity,
    intake_activity,
    intent_activity,
    post_approval_request_activity,
    publish_activity,
    qa_activity,
    router_activity,
    verify_activity,
)
from src.workflow.pipeline import (
    PipelineInput,
    TheStudioPipelineWorkflow,
)

TASK_QUEUE = "test-approval-queue"


def _make_input(repo_tier: str = "observe") -> PipelineInput:
    """Create a minimal PipelineInput for testing."""
    return PipelineInput(
        taskpacket_id="test-tp-001",
        correlation_id="test-corr-001",
        repo="owner/repo",
        repo_registered=True,
        repo_tier=repo_tier,
        event_id="evt-001",
        issue_title="Test issue",
        issue_body="Test body",
    )


ALL_ACTIVITIES = [
    intake_activity,
    context_activity,
    intent_activity,
    router_activity,
    assembler_activity,
    implement_activity,
    verify_activity,
    qa_activity,
    publish_activity,
    post_approval_request_activity,
    escalate_timeout_activity,
]


@pytest.mark.asyncio
async def test_observe_tier_skips_approval_wait():
    """Observe tier completes without entering the approval wait state."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=ALL_ACTIVITIES,
        ):
            result = await env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="observe"),
                id="test-observe-skip",
                task_queue=TASK_QUEUE,
            )

            assert result.success is True
            assert result.step_reached == "publish"
            assert result.awaiting_approval is False
            assert result.approved_by is None


@pytest.mark.asyncio
async def test_suggest_tier_timeout_no_approval():
    """Suggest tier times out after 7 days without approval signal."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=ALL_ACTIVITIES,
        ):
            result = await env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-suggest-timeout",
                task_queue=TASK_QUEUE,
            )

            assert result.success is False
            assert result.rejection_reason == "approval_timeout"
            assert result.step_reached == "awaiting_approval"
            assert result.awaiting_approval is True
            assert result.approved_by is None


@pytest.mark.asyncio
async def test_suggest_tier_approved():
    """Suggest tier proceeds to publish after receiving approval signal."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=ALL_ACTIVITIES,
        ):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-suggest-approved",
                task_queue=TASK_QUEUE,
            )

            # Brief pause to let workflow reach the wait state
            await asyncio.sleep(2)

            # Send approval signal
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is True
            assert result.step_reached == "publish"
            assert result.awaiting_approval is True
            assert result.approved_by == "admin@example.com"


@pytest.mark.asyncio
async def test_execute_tier_approved():
    """Execute tier also enters wait state and proceeds on approval."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=ALL_ACTIVITIES,
        ):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="execute"),
                id="test-execute-approved",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["ops@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is True
            assert result.approved_by == "ops@example.com"


@pytest.mark.asyncio
async def test_double_approve_is_idempotent():
    """Sending approval signal twice does not cause errors."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=ALL_ACTIVITIES,
        ):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                _make_input(repo_tier="suggest"),
                id="test-double-approve",
                task_queue=TASK_QUEUE,
            )

            await asyncio.sleep(2)

            # Send approval twice
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()

            assert result.success is True
            assert result.approved_by == "admin@example.com"
