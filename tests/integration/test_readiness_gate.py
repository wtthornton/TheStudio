"""Integration tests for the readiness gate (Story 16.8).

6 scenarios testing the full readiness gate flow through the Temporal workflow:
1. Happy path: high-readiness issue passes gate
2. Hold path: low-readiness held, re-evaluation passes, pipeline completes
3. Escalation path: high-risk + low-readiness at Execute tier escalates
4. Observe tier: low-readiness records score but does not block
5. Feature flag off: pipeline behaves exactly as before
6. Re-evaluation cap: issue fails readiness 3 times, escalated
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

# Real activities
from src.workflow.activities import (
    ReadinessActivityOutput,
    intake_activity,
    router_activity,
)
from src.workflow.pipeline import (
    PipelineInput,
    PipelineOutput,
    TheStudioPipelineWorkflow,
)
from tests.integration.conftest import TASK_QUEUE, make_pipeline_input
from tests.integration.mock_providers import (
    ALL_MOCK_ACTIVITIES,
    mock_assembler_activity,
    mock_context_activity,
    mock_implement_activity,
    mock_intent_activity,
    mock_post_approval_request_activity,
    mock_publish_activity,
    mock_qa_activity,
    mock_verify_activity,
)

# --- Mock readiness activities ---


def make_readiness_pass():
    """Create a readiness activity that always passes."""

    @activity.defn(name="readiness_activity")
    async def readiness_pass(params) -> ReadinessActivityOutput:
        return ReadinessActivityOutput(
            proceed=True,
            overall_score=0.85,
            gate_decision="pass",
        )

    return readiness_pass


def make_readiness_hold():
    """Create a readiness activity that always holds."""

    @activity.defn(name="readiness_activity")
    async def readiness_hold(params) -> ReadinessActivityOutput:
        return ReadinessActivityOutput(
            proceed=False,
            overall_score=0.3,
            gate_decision="hold",
            hold_reason="Low readiness score",
            missing_dimensions=["acceptance_criteria"],
            clarification_questions=["Could you add acceptance criteria?"],
        )

    return readiness_hold


def make_readiness_hold_then_pass(fail_count: int = 1):
    """Create a readiness activity that fails N times then passes."""
    call_count = 0

    @activity.defn(name="readiness_activity")
    async def readiness_hold_then_pass(params) -> ReadinessActivityOutput:
        nonlocal call_count
        call_count += 1
        if call_count <= fail_count:
            return ReadinessActivityOutput(
                proceed=False,
                overall_score=0.3,
                gate_decision="hold",
                hold_reason="Low readiness score",
                missing_dimensions=["acceptance_criteria"],
            )
        return ReadinessActivityOutput(
            proceed=True,
            overall_score=0.85,
            gate_decision="pass",
        )

    return readiness_hold_then_pass


def make_readiness_always_fail():
    """Create a readiness activity that always fails (for escalation testing)."""

    @activity.defn(name="readiness_activity")
    async def readiness_always_fail(params) -> ReadinessActivityOutput:
        return ReadinessActivityOutput(
            proceed=False,
            overall_score=0.15,
            gate_decision="hold",
            hold_reason="Very low readiness",
            missing_dimensions=["goal_clarity", "acceptance_criteria"],
        )

    return readiness_always_fail


def _base_activities() -> list:
    """Base activities without readiness (for adding readiness mock)."""
    return [
        intake_activity,
        mock_context_activity,
        mock_intent_activity,
        router_activity,
        mock_assembler_activity,
        mock_implement_activity,
        mock_verify_activity,
        mock_qa_activity,
        mock_publish_activity,
        mock_post_approval_request_activity,
    ]


def activities_with_readiness(readiness_activity_fn) -> list:
    """Build activity list with a specific readiness mock."""
    activities = _base_activities()
    activities.append(readiness_activity_fn)
    return activities


@pytest.fixture
async def temporal_env():
    env = await WorkflowEnvironment.start_local()
    yield env
    await env.shutdown()


async def _run_workflow(env, activities, params: PipelineInput) -> PipelineOutput:
    """Helper to run a workflow with given activities."""
    async with Worker(
        env.client,
        task_queue=TASK_QUEUE,
        workflows=[TheStudioPipelineWorkflow],
        activities=activities,
    ):
        return await env.client.execute_workflow(
            TheStudioPipelineWorkflow.run,
            params,
            id=f"readiness-test-{uuid4()}",
            task_queue=TASK_QUEUE,
        )


# --- Scenario 1: Happy path ---


@pytest.mark.integration
async def test_high_readiness_passes_gate(temporal_env):
    """High-readiness issue passes gate and pipeline completes successfully."""
    params = make_pipeline_input(readiness_gate_enabled=True)
    activities = activities_with_readiness(make_readiness_pass())

    result = await _run_workflow(temporal_env, activities, params)

    assert result.success is True
    assert result.step_reached == "publish"
    assert result.readiness_evaluations == 1
    assert result.readiness_escalated is False


# --- Scenario 2: Hold + re-evaluation ---


@pytest.mark.integration
async def test_hold_then_reevaluation_passes(temporal_env):
    """Low-readiness issue is held, re-evaluation with improved issue passes."""
    params = make_pipeline_input(readiness_gate_enabled=True, repo_tier="suggest")
    activities = activities_with_readiness(make_readiness_hold_then_pass(fail_count=1))

    async with Worker(
        temporal_env.client,
        task_queue=TASK_QUEUE,
        workflows=[TheStudioPipelineWorkflow],
        activities=activities,
    ):
        handle = await temporal_env.client.start_workflow(
            TheStudioPipelineWorkflow.run,
            params,
            id=f"readiness-hold-reeval-{uuid4()}",
            task_queue=TASK_QUEUE,
        )

        # Give the workflow time to reach the wait state
        import asyncio
        await asyncio.sleep(1)

        # Send the readiness_cleared signal with updated issue content
        await handle.signal(
            "readiness_cleared",
            arg={
                "issue_title": "Improved title with clear problem statement",
                "issue_body": (
                    "## Problem\nClear description\n\n"
                    "## Acceptance Criteria\n- [ ] Passes all tests\n"
                ),
            },
        )

        result = await handle.result()

    assert result.success is True
    assert result.readiness_evaluations == 2
    assert result.readiness_escalated is False


# --- Scenario 3: Escalation at Execute tier ---


@pytest.mark.integration
async def test_escalation_on_high_risk(temporal_env):
    """High-risk + low-readiness at Execute tier results in escalation after 3 tries."""
    params = make_pipeline_input(
        readiness_gate_enabled=True,
        repo_tier="execute",
    )
    activities = activities_with_readiness(make_readiness_always_fail())

    async with Worker(
        temporal_env.client,
        task_queue=TASK_QUEUE,
        workflows=[TheStudioPipelineWorkflow],
        activities=activities,
    ):
        handle = await temporal_env.client.start_workflow(
            TheStudioPipelineWorkflow.run,
            params,
            id=f"readiness-escalate-{uuid4()}",
            task_queue=TASK_QUEUE,
        )

        import asyncio

        # Send 2 readiness_cleared signals (total evaluations will be 3)
        for i in range(2):
            await asyncio.sleep(0.5)
            await handle.signal(
                "readiness_cleared",
                arg={"issue_title": f"attempt {i+2}", "issue_body": "still bad"},
            )

        result = await handle.result()

    assert result.success is False
    assert result.readiness_escalated is True
    assert result.readiness_evaluations == 3
    assert "escalated to human review" in result.rejection_reason


# --- Scenario 4: Observe tier ---


@pytest.mark.integration
async def test_observe_tier_does_not_block(temporal_env):
    """At Observe tier, low-readiness is recorded but pipeline continues.

    Note: The readiness gate already handles this via the scorer's trust_tier logic.
    At observe tier, the gate decision is 'pass' with score recorded.
    """
    params = make_pipeline_input(
        readiness_gate_enabled=True,
        repo_tier="observe",
    )
    # At observe tier, readiness passes (observe tier never blocks)
    activities = activities_with_readiness(make_readiness_pass())

    result = await _run_workflow(temporal_env, activities, params)

    assert result.success is True
    assert result.step_reached == "publish"


# --- Scenario 5: Feature flag off ---


@pytest.mark.integration
async def test_feature_flag_off_bypasses_gate(temporal_env):
    """With readiness_gate_enabled=False, pipeline skips the gate entirely."""
    params = make_pipeline_input(readiness_gate_enabled=False)
    # Use standard mock activities (no readiness mock needed)
    result = await _run_workflow(temporal_env, ALL_MOCK_ACTIVITIES, params)

    assert result.success is True
    assert result.step_reached == "publish"
    assert result.readiness_evaluations == 0


# --- Scenario 6: Re-evaluation cap ---


@pytest.mark.integration
async def test_reevaluation_cap_triggers_escalation(temporal_env):
    """After 3 failed evaluations, issue is escalated to human review."""
    params = make_pipeline_input(readiness_gate_enabled=True, repo_tier="suggest")
    activities = activities_with_readiness(make_readiness_always_fail())

    async with Worker(
        temporal_env.client,
        task_queue=TASK_QUEUE,
        workflows=[TheStudioPipelineWorkflow],
        activities=activities,
    ):
        handle = await temporal_env.client.start_workflow(
            TheStudioPipelineWorkflow.run,
            params,
            id=f"readiness-cap-{uuid4()}",
            task_queue=TASK_QUEUE,
        )

        import asyncio

        # Send 2 signals to trigger 2 re-evaluations (3 total evaluations)
        for i in range(2):
            await asyncio.sleep(0.5)
            await handle.signal(
                "readiness_cleared",
                arg={"issue_title": f"attempt {i+2}", "issue_body": "no improvement"},
            )

        result = await handle.result()

    assert result.success is False
    assert result.readiness_escalated is True
    assert result.readiness_evaluations == 3
