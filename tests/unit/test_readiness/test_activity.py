"""Tests for the readiness gate activity and pipeline integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from src.workflow.activities import (
    AssemblerOutput,
    ContextOutput,
    ImplementOutput,
    IntakeOutput,
    IntentOutput,
    PublishOutput,
    QAOutput,
    ReadinessActivityOutput,
    ReadinessInput,
    VerifyOutput,
    readiness_activity,
)
from src.workflow.pipeline import (
    PipelineInput,
    TheStudioPipelineWorkflow,
    WorkflowStep,
)

# --- Helpers ---


def _default_params(**overrides) -> PipelineInput:
    defaults = {
        "taskpacket_id": "tp-001",
        "correlation_id": "corr-001",
        "labels": ["agent:run"],
        "repo": "acme/widgets",
        "repo_registered": True,
        "repo_paused": False,
        "has_active_workflow": False,
        "event_id": "evt-001",
        "issue_title": "Fix the widget",
        "issue_body": "The widget is broken",
        "repo_path": "/tmp/repo",
        "repo_tier": "observe",
        "readiness_gate_enabled": False,
    }
    defaults.update(overrides)
    return PipelineInput(**defaults)


def _intake_accepted() -> IntakeOutput:
    return IntakeOutput(accepted=True, base_role="developer", overlays=[])


def _context_output(**overrides) -> ContextOutput:
    defaults = {"scope": {}, "risk_flags": {}, "complexity_index": "low", "context_packs": []}
    defaults.update(overrides)
    return ContextOutput(**defaults)


def _readiness_proceed(**overrides) -> ReadinessActivityOutput:
    defaults = {
        "proceed": True,
        "overall_score": 0.85,
        "gate_decision": "pass",
        "clarification_questions": [],
        "missing_dimensions": [],
        "hold_reason": None,
    }
    defaults.update(overrides)
    return ReadinessActivityOutput(**defaults)


def _readiness_hold(**overrides) -> ReadinessActivityOutput:
    defaults = {
        "proceed": False,
        "overall_score": 0.25,
        "gate_decision": "hold",
        "clarification_questions": ["What is the expected behavior?"],
        "missing_dimensions": ["goal_clarity", "acceptance_criteria"],
        "hold_reason": "Readiness score 0.25 below threshold; missing: goal_clarity",
    }
    defaults.update(overrides)
    return ReadinessActivityOutput(**defaults)


def _intent_output() -> IntentOutput:
    return IntentOutput(
        intent_spec_id="int-001", version=1, goal="Fix widget", acceptance_criteria=[]
    )


_ROUTER_OUTPUT = object()


def _assembler_output() -> AssemblerOutput:
    return AssemblerOutput(
        plan_steps=["implement"], qa_handoff=[], provenance={"taskpacket_id": "tp-001"}
    )


def _impl_output() -> ImplementOutput:
    return ImplementOutput(
        taskpacket_id="tp-001", intent_version=1, files_changed=[], agent_summary=""
    )


def _verify_passed() -> VerifyOutput:
    return VerifyOutput(passed=True, checks=[])


def _qa_passed() -> QAOutput:
    return QAOutput(passed=True)


def _publish_output() -> PublishOutput:
    return PublishOutput(pr_number=42, pr_url="https://example.com/42", created=True)


def _happy_path_returns() -> list:
    """9 activity returns for happy path (no readiness gate)."""
    return [
        _intake_accepted(),
        _context_output(),
        _intent_output(),
        _ROUTER_OUTPUT,
        _assembler_output(),
        _impl_output(),
        _verify_passed(),
        _qa_passed(),
        _publish_output(),
    ]


def _happy_path_with_readiness(readiness_output: ReadinessActivityOutput) -> list:
    """10 activity returns for happy path with readiness gate."""
    return [
        _intake_accepted(),
        _context_output(),
        readiness_output,
        _intent_output(),
        _ROUTER_OUTPUT,
        _assembler_output(),
        _impl_output(),
        _verify_passed(),
        _qa_passed(),
        _publish_output(),
    ]


# --- Activity Unit Tests ---


class TestReadinessActivityDirect:
    """Test readiness_activity function directly (without Temporal worker)."""

    async def test_well_formed_issue_proceeds(self) -> None:
        result = await readiness_activity(
            ReadinessInput(
                taskpacket_id="tp-001",
                issue_title="Fix SSO login timeout",
                issue_body=(
                    "## Problem\n\n"
                    "The login page times out after 30 seconds.\n\n"
                    "## Acceptance Criteria\n\n"
                    "- [ ] SSO login completes within 5 seconds\n"
                    "- [ ] Error handling works\n"
                ),
                complexity_index="low",
                trust_tier="observe",
            )
        )
        assert result.proceed is True
        assert result.gate_decision == "pass"
        assert result.overall_score > 0.5

    async def test_empty_issue_at_suggest_holds(self) -> None:
        result = await readiness_activity(
            ReadinessInput(
                taskpacket_id="tp-002",
                issue_title="fix",
                issue_body="",
                complexity_index="medium",
                trust_tier="suggest",
            )
        )
        assert result.proceed is False
        assert result.gate_decision == "hold"
        assert len(result.clarification_questions) > 0
        assert result.hold_reason is not None

    async def test_empty_issue_at_observe_passes(self) -> None:
        result = await readiness_activity(
            ReadinessInput(
                taskpacket_id="tp-003",
                issue_title="",
                issue_body="",
                complexity_index="low",
                trust_tier="observe",
            )
        )
        assert result.proceed is True
        assert result.gate_decision == "pass"

    async def test_missing_dimensions_populated(self) -> None:
        result = await readiness_activity(
            ReadinessInput(
                taskpacket_id="tp-004",
                issue_title="",
                issue_body="",
                complexity_index="low",
                trust_tier="observe",
            )
        )
        assert len(result.missing_dimensions) > 0
        assert "goal_clarity" in result.missing_dimensions

    async def test_unknown_complexity_defaults_to_low(self) -> None:
        result = await readiness_activity(
            ReadinessInput(
                taskpacket_id="tp-005",
                issue_title="Test",
                issue_body="Test body",
                complexity_index="unknown_value",
                trust_tier="observe",
            )
        )
        assert result.proceed is True


# --- Pipeline Integration Tests (mocked activities) ---


class TestPipelineReadinessGate:
    """Test the readiness gate within the full pipeline workflow."""

    async def test_flag_off_skips_readiness(self) -> None:
        """With readiness_gate_enabled=False, pipeline runs 9 activities."""
        returns = _happy_path_returns()
        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params(readiness_gate_enabled=False))
        assert result.success is True
        assert result.step_reached == WorkflowStep.PUBLISH

    async def test_flag_on_proceed_runs_10_activities(self) -> None:
        """With readiness_gate_enabled=True and PASS, pipeline runs 10 activities."""
        returns = _happy_path_with_readiness(_readiness_proceed())
        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(
                _default_params(readiness_gate_enabled=True)
            )
        assert result.success is True
        assert result.step_reached == WorkflowStep.PUBLISH

    async def test_flag_on_hold_stops_at_readiness(self) -> None:
        """With readiness_gate_enabled=True and HOLD, pipeline stops."""
        returns = [
            _intake_accepted(),
            _context_output(),
            _readiness_hold(),
        ]
        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(
                _default_params(readiness_gate_enabled=True)
            )
        assert result.success is False
        assert result.step_reached == WorkflowStep.READINESS
        assert result.rejection_reason is not None
        assert "Readiness score" in result.rejection_reason

    async def test_flag_on_hold_includes_hold_reason(self) -> None:
        """Hold reason from readiness activity is propagated to output."""
        hold = _readiness_hold(
            hold_reason="Readiness score 0.25 below threshold; missing: goal_clarity"
        )
        returns = [_intake_accepted(), _context_output(), hold]
        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(
                _default_params(readiness_gate_enabled=True)
            )
        assert result.rejection_reason == hold.hold_reason

    async def test_flag_off_activity_count_unchanged(self) -> None:
        """Feature flag off should result in exactly 9 activity calls."""
        returns = _happy_path_returns()
        mock = AsyncMock(side_effect=returns)
        with patch("temporalio.workflow.execute_activity", mock):
            wf = TheStudioPipelineWorkflow()
            await wf.run(_default_params(readiness_gate_enabled=False))
        assert mock.call_count == 9

    async def test_flag_on_proceed_activity_count_is_10(self) -> None:
        """Feature flag on with PASS should result in 10 activity calls."""
        returns = _happy_path_with_readiness(_readiness_proceed())
        mock = AsyncMock(side_effect=returns)
        with patch("temporalio.workflow.execute_activity", mock):
            wf = TheStudioPipelineWorkflow()
            await wf.run(_default_params(readiness_gate_enabled=True))
        assert mock.call_count == 10

    async def test_flag_on_hold_activity_count_is_3(self) -> None:
        """Feature flag on with HOLD should result in 3 activity calls."""
        returns = [_intake_accepted(), _context_output(), _readiness_hold()]
        mock = AsyncMock(side_effect=returns)
        with patch("temporalio.workflow.execute_activity", mock):
            wf = TheStudioPipelineWorkflow()
            await wf.run(_default_params(readiness_gate_enabled=True))
        assert mock.call_count == 3
