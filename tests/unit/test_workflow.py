"""Unit tests for TheStudio Pipeline Workflow (Story 1.11).

Tests workflow step sequencing, loopback logic, timeout/retry config,
and activity input/output serialization. Activity functions are tested
directly (no Temporal server required).
"""

from datetime import timedelta

import pytest

from src.workflow.activities import (
    ContextInput,
    ContextOutput,
    IntakeInput,
    IntakeOutput,
    IntentOutput,
    PublishOutput,
    QAOutput,
    RouterInput,
    RouterOutput,
    VerifyOutput,
    context_activity,
    intake_activity,
    router_activity,
)
from src.workflow.pipeline import (
    MAX_QA_LOOPBACKS,
    MAX_VERIFICATION_LOOPBACKS,
    STEP_POLICIES,
    PipelineInput,
    PipelineOutput,
    StepPolicy,
    WorkflowStep,
)

# --- Step Policy Configuration Tests ---


class TestStepPolicies:
    def test_all_steps_have_policies(self) -> None:
        """Every workflow step must have a timeout/retry policy."""
        for step in WorkflowStep:
            assert step in STEP_POLICIES, f"Missing policy for {step}"

    def test_intake_timeout(self) -> None:
        assert STEP_POLICIES[WorkflowStep.INTAKE].timeout == timedelta(minutes=2)
        assert STEP_POLICIES[WorkflowStep.INTAKE].max_retries == 2

    def test_context_timeout(self) -> None:
        assert STEP_POLICIES[WorkflowStep.CONTEXT].timeout == timedelta(minutes=10)
        assert STEP_POLICIES[WorkflowStep.CONTEXT].max_retries == 3

    def test_intent_timeout(self) -> None:
        assert STEP_POLICIES[WorkflowStep.INTENT].timeout == timedelta(minutes=10)
        assert STEP_POLICIES[WorkflowStep.INTENT].max_retries == 2

    def test_router_timeout(self) -> None:
        assert STEP_POLICIES[WorkflowStep.ROUTER].timeout == timedelta(minutes=15)
        assert STEP_POLICIES[WorkflowStep.ROUTER].max_retries == 2

    def test_assembler_timeout(self) -> None:
        assert STEP_POLICIES[WorkflowStep.ASSEMBLER].timeout == timedelta(minutes=10)
        assert STEP_POLICIES[WorkflowStep.ASSEMBLER].max_retries == 2

    def test_implement_timeout(self) -> None:
        assert STEP_POLICIES[WorkflowStep.IMPLEMENT].timeout == timedelta(minutes=60)
        assert STEP_POLICIES[WorkflowStep.IMPLEMENT].max_retries == 2

    def test_verify_timeout(self) -> None:
        assert STEP_POLICIES[WorkflowStep.VERIFY].timeout == timedelta(minutes=45)
        assert STEP_POLICIES[WorkflowStep.VERIFY].max_retries == 3

    def test_qa_timeout(self) -> None:
        assert STEP_POLICIES[WorkflowStep.QA].timeout == timedelta(minutes=30)
        assert STEP_POLICIES[WorkflowStep.QA].max_retries == 2

    def test_publish_timeout(self) -> None:
        assert STEP_POLICIES[WorkflowStep.PUBLISH].timeout == timedelta(minutes=5)
        assert STEP_POLICIES[WorkflowStep.PUBLISH].max_retries == 5

    def test_verify_bounded_backoff(self) -> None:
        assert STEP_POLICIES[WorkflowStep.VERIFY].backoff_coefficient == 1.5

    def test_publish_fast_retry(self) -> None:
        assert STEP_POLICIES[WorkflowStep.PUBLISH].initial_interval == timedelta(
            seconds=0.5
        )


class TestStepPolicyRetryConversion:
    def test_retry_policy_attempts(self) -> None:
        """Temporal counts total attempts = max_retries + 1."""
        policy = StepPolicy(timeout=timedelta(minutes=1), max_retries=3)
        rp = policy.to_retry_policy()
        assert rp.maximum_attempts == 4

    def test_default_backoff_coefficient(self) -> None:
        policy = StepPolicy(timeout=timedelta(minutes=1), max_retries=2)
        assert policy.backoff_coefficient == 2.0

    def test_custom_initial_interval(self) -> None:
        policy = StepPolicy(
            timeout=timedelta(minutes=1),
            max_retries=2,
            initial_interval=timedelta(seconds=0.5),
        )
        rp = policy.to_retry_policy()
        assert rp.initial_interval == timedelta(seconds=0.5)


# --- Loopback Cap Tests ---


class TestLoopbackCaps:
    def test_max_verification_loopbacks(self) -> None:
        assert MAX_VERIFICATION_LOOPBACKS == 2

    def test_max_qa_loopbacks(self) -> None:
        assert MAX_QA_LOOPBACKS == 2


# --- Activity Data Model Tests ---


class TestActivityModels:
    def test_intake_output_accepted(self) -> None:
        out = IntakeOutput(accepted=True, base_role="developer", overlays=["security"])
        assert out.accepted is True
        assert out.base_role == "developer"

    def test_intake_output_rejected(self) -> None:
        out = IntakeOutput(accepted=False, rejection_reason="Missing agent:run label")
        assert out.accepted is False
        assert out.rejection_reason == "Missing agent:run label"

    def test_context_output_defaults(self) -> None:
        out = ContextOutput()
        assert out.scope == {}
        assert out.risk_flags == {}
        assert out.complexity_index == "low"

    def test_intent_output(self) -> None:
        out = IntentOutput(
            intent_spec_id="abc",
            version=1,
            goal="Add health endpoint",
            acceptance_criteria=["Returns 200"],
        )
        assert out.goal == "Add health endpoint"
        assert out.version == 1

    def test_router_output(self) -> None:
        out = RouterOutput(rationale="No experts needed")
        assert out.selections == []
        assert out.rationale == "No experts needed"

    def test_verify_output_loopback(self) -> None:
        out = VerifyOutput(passed=False, loopback_triggered=True)
        assert not out.passed
        assert out.loopback_triggered

    def test_qa_output_intent_gap(self) -> None:
        out = QAOutput(passed=False, has_intent_gap=True, defect_count=1)
        assert not out.passed
        assert out.has_intent_gap

    def test_publish_output_ready(self) -> None:
        out = PublishOutput(pr_number=42, pr_url="url", created=True, marked_ready=True)
        assert out.marked_ready


# --- Pipeline Input/Output Tests ---


class TestPipelineModels:
    def test_pipeline_input_defaults(self) -> None:
        inp = PipelineInput(taskpacket_id="abc", correlation_id="def")
        assert inp.repo_tier == "observe"
        assert inp.labels == []
        assert inp.repo_registered is True

    def test_pipeline_output_defaults(self) -> None:
        out = PipelineOutput()
        assert out.success is False
        assert out.step_reached == ""
        assert out.verification_loopbacks == 0
        assert out.qa_loopbacks == 0

    def test_pipeline_output_success(self) -> None:
        out = PipelineOutput(
            success=True,
            step_reached="publish",
            pr_number=42,
            pr_url="https://github.com/acme/widgets/pull/42",
            marked_ready=True,
        )
        assert out.success is True
        assert out.pr_number == 42


# --- Activity Function Tests (direct calls, no Temporal server) ---


class TestIntakeActivity:
    @pytest.mark.asyncio
    async def test_intake_accepts_eligible_issue(self) -> None:
        result = await intake_activity(
            IntakeInput(
                labels=["agent:run", "type:bug"],
                repo="acme/widgets",
                repo_registered=True,
                repo_paused=False,
                has_active_workflow=False,
                event_id="evt-001",
            )
        )
        assert result.accepted is True
        assert result.base_role == "developer"
        assert result.overlays == []

    @pytest.mark.asyncio
    async def test_intake_rejects_missing_label(self) -> None:
        result = await intake_activity(
            IntakeInput(
                labels=["type:bug"],  # Missing agent:run
                repo="acme/widgets",
                repo_registered=True,
                repo_paused=False,
                has_active_workflow=False,
                event_id="evt-002",
            )
        )
        assert result.accepted is False
        assert result.rejection_reason is not None
        assert "agent:run" in result.rejection_reason

    @pytest.mark.asyncio
    async def test_intake_selects_overlays(self) -> None:
        result = await intake_activity(
            IntakeInput(
                labels=["agent:run", "type:feature", "risk:auth"],
                repo="acme/widgets",
                repo_registered=True,
                repo_paused=False,
                has_active_workflow=False,
                event_id="evt-003",
            )
        )
        assert result.accepted is True
        assert "security" in result.overlays

    @pytest.mark.asyncio
    async def test_intake_refactor_selects_architect(self) -> None:
        result = await intake_activity(
            IntakeInput(
                labels=["agent:run", "type:refactor"],
                repo="acme/widgets",
                repo_registered=True,
                repo_paused=False,
                has_active_workflow=False,
                event_id="evt-004",
            )
        )
        assert result.accepted is True
        assert result.base_role == "architect"


class TestContextActivity:
    @pytest.mark.asyncio
    async def test_context_returns_defaults(self) -> None:
        result = await context_activity(
            ContextInput(
                taskpacket_id="tp-001",
                repo="acme/widgets",
                issue_title="Test",
                issue_body="Test body",
                labels=[],
            )
        )
        assert result.complexity_index == "low"
        assert isinstance(result.scope, dict)
        assert isinstance(result.risk_flags, dict)


class TestRouterActivity:
    @pytest.mark.asyncio
    async def test_router_with_no_overlays(self) -> None:
        result = await router_activity(
            RouterInput(
                base_role="developer",
                overlays=[],
                risk_flags={},
            )
        )
        assert result.selections == []
        assert "No expert consultation" in result.rationale

    @pytest.mark.asyncio
    async def test_router_with_security_overlay(self) -> None:
        result = await router_activity(
            RouterInput(
                base_role="developer",
                overlays=["security"],
                risk_flags={"risk_security": True},
            )
        )
        # No experts available, but recruiter requests should be made
        assert len(result.recruiter_requests) > 0
        assert any(
            r.get("expert_class") == "security" for r in result.recruiter_requests
        )


# --- Workflow Step Enum Tests ---


class TestWorkflowStep:
    def test_all_nine_steps(self) -> None:
        """Workflow has exactly 9 steps per the architecture."""
        assert len(WorkflowStep) == 9

    def test_step_order(self) -> None:
        steps = list(WorkflowStep)
        assert steps[0] == WorkflowStep.INTAKE
        assert steps[1] == WorkflowStep.CONTEXT
        assert steps[2] == WorkflowStep.INTENT
        assert steps[3] == WorkflowStep.ROUTER
        assert steps[4] == WorkflowStep.ASSEMBLER
        assert steps[5] == WorkflowStep.IMPLEMENT
        assert steps[6] == WorkflowStep.VERIFY
        assert steps[7] == WorkflowStep.QA
        assert steps[8] == WorkflowStep.PUBLISH
