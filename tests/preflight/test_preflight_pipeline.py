"""Integration tests for preflight in the pipeline workflow (Epic 28 Story 28.2).

Tests:
- Preflight skipped when disabled (AC 8)
- Preflight runs when enabled for matching tier (AC 9)
- Preflight approval lets pipeline continue (AC 6)
- Preflight rejection triggers one Assembler loopback (AC 7)
- Preflight double-failure proceeds with warning (AC 7)
- WorkflowStep.PREFLIGHT enum exists (AC 6)
- STEP_POLICIES has preflight entry (AC 6)
"""

from unittest.mock import AsyncMock, patch

from src.workflow.activities import (
    AssemblerOutput,
    ContextOutput,
    ImplementOutput,
    IntakeOutput,
    IntentOutput,
    PreflightActivityOutput,
    PublishOutput,
    QAOutput,
    VerifyOutput,
)
from src.workflow.pipeline import (
    STEP_POLICIES,
    PipelineInput,
    PipelineOutput,
    TheStudioPipelineWorkflow,
    WorkflowStep,
)

# --- Helpers ---

_ROUTER_OUTPUT = object()


def _intent(**overrides) -> IntentOutput:
    defaults = {
        "intent_spec_id": "i-1",
        "version": 1,
        "goal": "Fix it",
        "acceptance_criteria": ["Works"],
    }
    defaults.update(overrides)
    return IntentOutput(**defaults)


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
        "preflight_enabled": False,
    }
    defaults.update(overrides)
    return PipelineInput(**defaults)


def _happy_path_returns():
    """Activity returns for a normal pipeline run (no preflight)."""
    return [
        IntakeOutput(accepted=True, base_role="developer", overlays=[]),
        ContextOutput(),
        IntentOutput(intent_spec_id="i-1", version=1, goal="Fix it", acceptance_criteria=["Works"]),
        _ROUTER_OUTPUT,
        AssemblerOutput(plan_steps=["implement_changes"]),
        ImplementOutput(taskpacket_id="tp-001"),
        VerifyOutput(passed=True),
        QAOutput(passed=True),
        PublishOutput(pr_number=42, created=True),
    ]


class TestPreflightEnum:
    """AC 6: WorkflowStep.PREFLIGHT exists."""

    def test_preflight_in_enum(self) -> None:
        assert WorkflowStep.PREFLIGHT == "preflight"

    def test_preflight_between_assembler_and_implement(self) -> None:
        steps = list(WorkflowStep)
        assembler_idx = steps.index(WorkflowStep.ASSEMBLER)
        preflight_idx = steps.index(WorkflowStep.PREFLIGHT)
        implement_idx = steps.index(WorkflowStep.IMPLEMENT)
        assert assembler_idx < preflight_idx < implement_idx

    def test_step_policy_exists(self) -> None:
        assert WorkflowStep.PREFLIGHT in STEP_POLICIES
        policy = STEP_POLICIES[WorkflowStep.PREFLIGHT]
        assert policy.timeout.total_seconds() == 120  # 2 minutes
        assert policy.max_retries == 1


class TestPreflightSkippedWhenDisabled:
    """AC 8: Preflight is feature-flagged, off by default."""

    async def test_pipeline_succeeds_without_preflight(self) -> None:
        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=_happy_path_returns(),
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is True
        assert result.preflight_approved is None
        assert result.preflight_summary == ""


class TestPreflightApproved:
    """AC 6: Preflight approved lets pipeline continue.

    Uses repo_tier="observe" with preflight_tiers=["observe"] to avoid
    triggering the approval wait state (which requires Temporal runtime).
    """

    async def test_preflight_approved_continues_to_implement(self) -> None:
        returns = [
            IntakeOutput(accepted=True, base_role="developer", overlays=[]),
            ContextOutput(),
            _intent(),
            _ROUTER_OUTPUT,
            AssemblerOutput(plan_steps=["implement_changes"]),
            # Preflight approved
            PreflightActivityOutput(approved=True, summary="All clear"),
            # Continue normally
            ImplementOutput(taskpacket_id="tp-001"),
            VerifyOutput(passed=True),
            QAOutput(passed=True),
            PublishOutput(pr_number=42, created=True),
        ]

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(
                _default_params(
                    preflight_enabled=True,
                    repo_tier="observe",
                    preflight_tiers=["observe"],
                )
            )

        assert result.success is True
        assert result.preflight_approved is True
        assert result.preflight_summary == "All clear"


class TestPreflightRejectionLoopback:
    """AC 7: Preflight failure triggers one Assembler loopback."""

    async def test_rejection_triggers_replan_then_approve(self) -> None:
        returns = [
            IntakeOutput(accepted=True, base_role="developer", overlays=[]),
            ContextOutput(),
            _intent(),
            _ROUTER_OUTPUT,
            AssemblerOutput(plan_steps=["vague step"]),
            # First preflight: rejected
            PreflightActivityOutput(
                approved=False,
                vague_steps=["vague step"],
                summary="1 vague step",
            ),
            # Assembler re-plan
            AssemblerOutput(plan_steps=["concrete step: add validation"]),
            # Second preflight: approved
            PreflightActivityOutput(approved=True, summary="Approved after re-plan"),
            # Continue normally
            ImplementOutput(taskpacket_id="tp-001"),
            VerifyOutput(passed=True),
            QAOutput(passed=True),
            PublishOutput(pr_number=42, created=True),
        ]

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(
                _default_params(
                    preflight_enabled=True,
                    repo_tier="observe",
                    preflight_tiers=["observe"],
                )
            )

        assert result.success is True
        assert result.preflight_approved is True

    async def test_double_rejection_proceeds_with_warning(self) -> None:
        """If both plans fail preflight, proceed anyway (AC 7)."""
        returns = [
            IntakeOutput(accepted=True, base_role="developer", overlays=[]),
            ContextOutput(),
            _intent(),
            _ROUTER_OUTPUT,
            AssemblerOutput(plan_steps=["bad plan"]),
            # First preflight: rejected
            PreflightActivityOutput(approved=False, summary="Bad plan"),
            # Assembler re-plan
            AssemblerOutput(plan_steps=["still bad plan"]),
            # Second preflight: still rejected
            PreflightActivityOutput(approved=False, summary="Still bad"),
            # Pipeline continues anyway
            ImplementOutput(taskpacket_id="tp-001"),
            VerifyOutput(passed=True),
            QAOutput(passed=True),
            PublishOutput(pr_number=42, created=True),
        ]

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=returns,
        ), patch(
            "temporalio.workflow.logger",
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(
                _default_params(
                    preflight_enabled=True,
                    repo_tier="observe",
                    preflight_tiers=["observe"],
                )
            )

        assert result.success is True
        assert result.preflight_approved is False
        assert result.preflight_summary == "Still bad"


class TestPreflightTierFiltering:
    """AC 9: Preflight only runs for configured tiers."""

    async def test_non_matching_tier_skips_preflight(self) -> None:
        """When repo_tier is not in preflight_tiers, preflight is skipped."""
        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=_happy_path_returns(),
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(
                _default_params(
                    preflight_enabled=True,
                    repo_tier="observe",
                    preflight_tiers=["execute"],  # observe not in list
                )
            )

        assert result.success is True
        assert result.preflight_approved is None


class TestPipelineOutputFields:
    """PipelineOutput has preflight tracking fields."""

    def test_default_preflight_fields(self) -> None:
        output = PipelineOutput()
        assert output.preflight_approved is None
        assert output.preflight_summary == ""
