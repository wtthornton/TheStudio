"""Integration tests for the full TheStudio pipeline workflow.

Stories 9.1-9.4 (Epic 9): Prove the full 9-step Temporal workflow executes
end-to-end using the Temporal test environment with mock adapters.

Tests run without external services (no real Temporal server, GitHub, or LLM).
"""

from uuid import uuid4

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from src.workflow.activities import (
    QAOutput,
    VerifyOutput,
    assembler_activity,
    context_activity,
    implement_activity,
    intake_activity,
    intent_activity,
    publish_activity,
    qa_activity,
    router_activity,
    verify_activity,
)
from src.workflow.pipeline import PipelineInput, PipelineOutput, TheStudioPipelineWorkflow
from tests.integration.mock_providers import (
    ALL_MOCK_ACTIVITIES,
    activities_with_verify_loopback,
)

TASK_QUEUE = "test-pipeline"

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
]


def _eligible_input(**overrides) -> PipelineInput:
    """Build an eligible PipelineInput with fresh UUIDs."""
    defaults = {
        "taskpacket_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "labels": ["agent:run", "type:feature"],
        "repo": "acme/widgets",
        "repo_registered": True,
        "repo_paused": False,
        "has_active_workflow": False,
        "event_id": "evt-test-001",
        "issue_title": "Add /health endpoint returning HTTP 200",
        "issue_body": "Need a health check.\n## Acceptance Criteria\n- GET /health returns 200",
        "repo_path": "/tmp/acme-widgets",
        "repo_tier": "suggest",
    }
    defaults.update(overrides)
    return PipelineInput(**defaults)


@pytest.fixture
async def temporal_env():
    """Temporal test environment (function-scoped for pytest-asyncio loop scope)."""
    env = await WorkflowEnvironment.start_local()
    yield env
    await env.shutdown()


# --- Story 9.1: Happy Path (AC1) ---


class TestPipelineHappyPath:
    """Story 9.1: Full pipeline — happy path."""

    async def test_full_pipeline_succeeds(self, temporal_env):
        """Pipeline runs all 9 steps and produces success output."""
        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=ALL_ACTIVITIES,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                _eligible_input(),
                id=f"test-happy-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

            assert result.success is True
            assert result.step_reached == "publish"
            assert result.verification_loopbacks == 0
            assert result.qa_loopbacks == 0

    async def test_pipeline_rejection_for_ineligible(self, temporal_env):
        """Pipeline correctly rejects issue without agent:run label."""
        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=ALL_ACTIVITIES,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                _eligible_input(labels=["type:feature"]),  # Missing agent:run
                id=f"test-reject-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

            assert result.success is False
            assert result.step_reached == "intake"
            assert result.rejection_reason is not None
            assert "agent:run" in result.rejection_reason.lower()


# --- Story 9.2: Verification Loopback (AC2) ---


class TestVerificationLoopback:
    """Story 9.2: Verification fails once, then passes on retry."""

    async def test_verification_loopback_then_pass(self, temporal_env):
        """Verification fails once, then passes. Pipeline succeeds with loopback_count=1."""
        call_count = 0

        from temporalio import activity

        @activity.defn(name="verify_activity")
        async def verify_with_loopback(params):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return VerifyOutput(passed=False, loopback_triggered=True)
            return VerifyOutput(passed=True, checks=[])

        loopback_activities = [
            intake_activity, context_activity, intent_activity, router_activity,
            assembler_activity, implement_activity, verify_with_loopback,
            qa_activity, publish_activity,
        ]

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=loopback_activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                _eligible_input(),
                id=f"test-verify-loop-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

            assert result.success is True
            assert result.verification_loopbacks == 1


# --- Story 9.3: QA Loopback (AC3) ---


class TestQALoopback:
    """Story 9.3: QA fails once, then passes on retry."""

    async def test_qa_loopback_then_pass(self, temporal_env):
        """QA fails once, then passes. Pipeline succeeds with qa_loopbacks=1."""
        qa_call_count = 0

        from temporalio import activity

        @activity.defn(name="qa_activity")
        async def qa_with_loopback(params):
            nonlocal qa_call_count
            qa_call_count += 1
            if qa_call_count == 1:
                return QAOutput(passed=False, needs_loopback=True, defect_count=1)
            return QAOutput(passed=True)

        qa_loop_activities = [
            intake_activity, context_activity, intent_activity, router_activity,
            assembler_activity, implement_activity, verify_activity,
            qa_with_loopback, publish_activity,
        ]

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=qa_loop_activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                _eligible_input(),
                id=f"test-qa-loop-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

            assert result.success is True
            assert result.qa_loopbacks == 1


# --- Story 9.4: Gate Exhaustion (AC4) ---


class TestGateExhaustion:
    """Story 9.4: Gate exhaustion fails closed without crash."""

    async def test_verification_exhaustion_fails_closed(self, temporal_env):
        """Verification fails every time until cap. Pipeline fails, doesn't hang."""
        from temporalio import activity

        @activity.defn(name="verify_activity")
        async def verify_always_fails(params):
            return VerifyOutput(passed=False, loopback_triggered=True)

        exhaust_activities = [
            intake_activity, context_activity, intent_activity, router_activity,
            assembler_activity, implement_activity, verify_always_fails,
            qa_activity, publish_activity,
        ]

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=exhaust_activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                _eligible_input(),
                id=f"test-exhaust-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

            assert result.success is False
            assert result.verification_loopbacks >= 1
            assert result.step_reached == "verify"

    async def test_qa_exhaustion_fails_closed(self, temporal_env):
        """QA fails every time until cap. Pipeline fails, doesn't hang."""
        from temporalio import activity

        @activity.defn(name="qa_activity")
        async def qa_always_fails(params):
            return QAOutput(passed=False, needs_loopback=True, defect_count=1)

        qa_exhaust_activities = [
            intake_activity, context_activity, intent_activity, router_activity,
            assembler_activity, implement_activity, verify_activity,
            qa_always_fails, publish_activity,
        ]

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=qa_exhaust_activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                _eligible_input(),
                id=f"test-qa-exhaust-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

            assert result.success is False
            assert result.qa_loopbacks >= 1
            assert result.step_reached == "qa"


# --- Story 15.5: Temporal Data-Fidelity with Realistic Providers ---


REALISTIC_QUEUE = "realistic-test"


class TestRealisticPipeline:
    """Data-fidelity tests using mock providers with realistic data."""

    async def test_realistic_happy_path(self, temporal_env):
        """Pipeline with mock providers produces valid, non-empty output."""
        async with Worker(
            temporal_env.client,
            task_queue=REALISTIC_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=ALL_MOCK_ACTIVITIES,
        ):
            result: PipelineOutput = (
                await temporal_env.client.execute_workflow(
                    TheStudioPipelineWorkflow.run,
                    _eligible_input(),
                    id=f"test-realistic-{uuid4()}",
                    task_queue=REALISTIC_QUEUE,
                )
            )

        assert result.success is True
        assert result.step_reached == "publish"
        assert result.pr_number == 42
        assert result.pr_url != ""
        assert result.verification_loopbacks == 0
        assert result.qa_loopbacks == 0

    async def test_realistic_loopback(self, temporal_env):
        """Verify loopback with realistic data tracks count."""
        loopback_activities = activities_with_verify_loopback(
            fail_count=1,
        )
        async with Worker(
            temporal_env.client,
            task_queue=REALISTIC_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=loopback_activities,
        ):
            result: PipelineOutput = (
                await temporal_env.client.execute_workflow(
                    TheStudioPipelineWorkflow.run,
                    _eligible_input(),
                    id=f"test-realistic-loop-{uuid4()}",
                    task_queue=REALISTIC_QUEUE,
                )
            )

        assert result.success is True
        assert result.verification_loopbacks == 1
        assert result.step_reached == "publish"
