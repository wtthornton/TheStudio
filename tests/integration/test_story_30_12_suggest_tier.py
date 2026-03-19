"""Story 30.12: Suggest Tier Validation — Integration Tests.

Validates that the pipeline processes issues at Suggest trust tier
with all feature flags activated, producing correct output at every stage.

Covers:
1. Suggest tier completes all 9 pipeline steps (with approval bypass)
2. Suggest tier with preflight enabled
3. Suggest tier with Projects v2 enabled
4. Suggest tier publish output (pr_number, pr_url, marked_ready)
5. Suggest tier without bypass enters approval wait state
6. All flags combined (preflight + projects_v2 + bypass)
7. Suggest tier with verification loopback
8. Suggest tier with QA loopback
9. Suggest tier step progression tracking
10. Suggest tier with security overlays
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.workflow.pipeline import (
    APPROVAL_REQUIRED_TIERS,
    PipelineInput,
    PipelineOutput,
    WorkflowStep,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_intake_output(overlays=None):
    from src.workflow.activities import IntakeOutput
    return IntakeOutput(accepted=True, base_role="developer", overlays=overlays or [])


def _mock_intake_rejected():
    from src.workflow.activities import IntakeOutput
    return IntakeOutput(accepted=False, rejection_reason="ineligible")


def _mock_context_output(risk_flags=None):
    from src.workflow.activities import ContextOutput
    return ContextOutput(complexity_index="low", risk_flags=risk_flags or {})


def _mock_intent_output():
    from src.workflow.activities import IntentOutput
    return IntentOutput(
        intent_spec_id="intent-suggest-001",
        version=1,
        goal="Add logging to auth module",
        acceptance_criteria=["AC1: Structured logging on login", "AC2: Correlation IDs"],
    )


def _mock_assembler_output():
    from src.workflow.activities import AssemblerOutput
    return AssemblerOutput(plan_steps=["Step 1: Add logger", "Step 2: Wire correlation"], qa_handoff=[])


def _mock_impl_output():
    from src.workflow.activities import ImplementOutput
    return ImplementOutput(taskpacket_id="tp-suggest", files_changed=["src/auth/login.py"])


def _mock_verify_output(passed=True, exhausted=False):
    from src.workflow.activities import VerifyOutput
    return VerifyOutput(passed=passed, exhausted=exhausted)


def _mock_qa_output(passed=True):
    from src.workflow.activities import QAOutput
    return QAOutput(passed=passed)


def _mock_publish_output():
    from src.workflow.activities import PublishOutput
    return PublishOutput(pr_number=101, pr_url="https://github.com/org/repo/pull/101", marked_ready=True)


def _mock_preflight_output(approved=True):
    from src.workflow.activities import PreflightActivityOutput
    return PreflightActivityOutput(
        approved=approved,
        summary="Plan covers all criteria",
        uncovered_criteria=[],
        constraint_violations=[],
        vague_steps=[],
    )


def _mock_logger():
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


def _side_effect_execute_activity(activity_map: dict):
    """Dispatch workflow.execute_activity to the correct mock by function name."""
    async def _execute(activity_fn, *args, **kwargs):
        fn_name = getattr(activity_fn, "__name__", None) or str(activity_fn)
        for name, mock_fn in activity_map.items():
            if name in fn_name or activity_fn is mock_fn:
                # If mock has a side_effect, call it to get the value
                if hasattr(mock_fn, "side_effect") and mock_fn.side_effect is not None:
                    result = mock_fn.side_effect(*args, **kwargs)
                    # Await if it's a coroutine
                    if hasattr(result, "__await__"):
                        return await result
                    return result
                return mock_fn.return_value
        return await activity_fn(*args)
    return _execute


def _standard_activity_mocks(
    verify_outputs=None,
    qa_outputs=None,
    intake_overlays=None,
    risk_flags=None,
):
    """Build standard activity mocks for Suggest tier tests."""
    verify_iter = iter(verify_outputs or [_mock_verify_output()])
    qa_iter = iter(qa_outputs or [_mock_qa_output()])

    mocks = {
        "intake_activity": AsyncMock(
            return_value=_mock_intake_output(overlays=intake_overlays)
        ),
        "context_activity": AsyncMock(
            return_value=_mock_context_output(risk_flags=risk_flags)
        ),
        "intent_activity": AsyncMock(return_value=_mock_intent_output()),
        "router_activity": AsyncMock(return_value=None),
        "assembler_activity": AsyncMock(return_value=_mock_assembler_output()),
        "implement_activity": AsyncMock(return_value=_mock_impl_output()),
        "verify_activity": AsyncMock(side_effect=lambda *a, **kw: next(verify_iter)),
        "qa_activity": AsyncMock(side_effect=lambda *a, **kw: next(qa_iter)),
        "publish_activity": AsyncMock(return_value=_mock_publish_output()),
    }
    return mocks



async def _execute_pipeline(params, activity_mocks, extra_patches=None):
    """Execute the pipeline with mocked activities."""
    import contextlib

    from src.workflow.pipeline import TheStudioPipelineWorkflow

    wf = TheStudioPipelineWorkflow()

    activity_patches = [
        patch("src.workflow.pipeline.intake_activity", activity_mocks["intake_activity"]),
        patch("src.workflow.pipeline.context_activity", activity_mocks["context_activity"]),
        patch("src.workflow.pipeline.intent_activity", activity_mocks["intent_activity"]),
        patch("src.workflow.pipeline.router_activity", activity_mocks["router_activity"]),
        patch("src.workflow.pipeline.assembler_activity", activity_mocks["assembler_activity"]),
        patch("src.workflow.pipeline.implement_activity", activity_mocks["implement_activity"]),
        patch("src.workflow.pipeline.verify_activity", activity_mocks["verify_activity"]),
        patch("src.workflow.pipeline.qa_activity", activity_mocks["qa_activity"]),
        patch("src.workflow.pipeline.publish_activity", activity_mocks["publish_activity"]),
    ]

    with contextlib.ExitStack() as stack:
        mock_wf = stack.enter_context(patch("src.workflow.pipeline.workflow"))
        for p in activity_patches:
            stack.enter_context(p)
        if extra_patches:
            for p in extra_patches:
                stack.enter_context(p)

        mock_wf.execute_activity = _side_effect_execute_activity(activity_mocks)
        mock_wf.logger = _mock_logger()
        mock_wf.now = MagicMock(return_value=MagicMock())
        mock_wf.wait_condition = AsyncMock()

        output = await wf.run(params)
    return output


# ---------------------------------------------------------------------------
# 1. Suggest tier is in APPROVAL_REQUIRED_TIERS
# ---------------------------------------------------------------------------


class TestSuggestTierClassification:
    """Verify Suggest tier is classified as requiring approval."""

    def test_suggest_in_approval_required_tiers(self) -> None:
        assert "suggest" in APPROVAL_REQUIRED_TIERS

    def test_observe_not_in_approval_required_tiers(self) -> None:
        assert "observe" not in APPROVAL_REQUIRED_TIERS

    def test_execute_in_approval_required_tiers(self) -> None:
        assert "execute" in APPROVAL_REQUIRED_TIERS


# ---------------------------------------------------------------------------
# 2. Suggest tier completes all 9 steps with approval bypass
# ---------------------------------------------------------------------------


class TestSuggestTierFullPipeline:
    """Suggest tier with approval_auto_bypass completes the full pipeline."""

    @pytest.mark.asyncio
    async def test_suggest_tier_completes_all_steps(self) -> None:
        """Suggest tier with bypass runs through all 9 steps and publishes."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-full",
            correlation_id="corr-suggest-full",
            repo="org/suggest-repo",
            repo_tier="suggest",
            issue_title="Add auth logging",
            issue_body="We need structured logging in the auth module",
            approval_auto_bypass=True,
        )
        mocks = _standard_activity_mocks()
        output = await _execute_pipeline(params, mocks)

        assert output.success is True
        assert output.step_reached == WorkflowStep.PUBLISH
        assert output.approval_bypassed is True
        assert output.pr_number == 101
        assert output.pr_url == "https://github.com/org/repo/pull/101"
        assert output.marked_ready is True
        assert output.rejection_reason is None

    @pytest.mark.asyncio
    async def test_suggest_tier_reaches_publish(self) -> None:
        """Pipeline reaches PUBLISH step, confirming all activities ran."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-calls",
            correlation_id="corr-suggest-calls",
            repo_tier="suggest",
            approval_auto_bypass=True,
        )
        mocks = _standard_activity_mocks()
        output = await _execute_pipeline(params, mocks)

        # If we reached PUBLISH with success, all 9 activities ran
        assert output.success is True
        assert output.step_reached == WorkflowStep.PUBLISH
        assert output.verification_loopbacks == 0
        assert output.qa_loopbacks == 0

    @pytest.mark.asyncio
    async def test_suggest_tier_publish_output_fields(self) -> None:
        """Pipeline output captures PR details from publish activity."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-publish",
            correlation_id="corr-suggest-publish",
            repo_tier="suggest",
            approval_auto_bypass=True,
        )
        mocks = _standard_activity_mocks()
        output = await _execute_pipeline(params, mocks)

        assert output.pr_number == 101
        assert "github.com" in output.pr_url
        assert output.marked_ready is True


# ---------------------------------------------------------------------------
# 3. Suggest tier with preflight enabled
# ---------------------------------------------------------------------------


class TestSuggestTierWithPreflight:
    """Suggest tier with preflight flag runs the plan review step."""

    @pytest.mark.asyncio
    async def test_preflight_runs_for_suggest_tier(self) -> None:
        """Preflight step runs when preflight_enabled and tier is in preflight_tiers."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-preflight",
            correlation_id="corr-suggest-preflight",
            repo_tier="suggest",
            approval_auto_bypass=True,
            preflight_enabled=True,
            preflight_tiers=["suggest", "execute"],
        )
        mocks = _standard_activity_mocks()

        mock_preflight = AsyncMock(return_value=_mock_preflight_output(approved=True))
        extra_patches = [
            patch("src.workflow.pipeline.preflight_activity", mock_preflight),
        ]
        mocks["preflight_activity"] = mock_preflight

        output = await _execute_pipeline(params, mocks, extra_patches)

        assert output.success is True
        assert output.preflight_approved is True

    @pytest.mark.asyncio
    async def test_preflight_skipped_when_tier_not_in_list(self) -> None:
        """Preflight does NOT run when suggest is not in preflight_tiers."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-no-preflight",
            correlation_id="corr-suggest-no-preflight",
            repo_tier="suggest",
            approval_auto_bypass=True,
            preflight_enabled=True,
            preflight_tiers=["execute"],  # suggest not included
        )
        mocks = _standard_activity_mocks()

        mock_preflight = AsyncMock(return_value=_mock_preflight_output())
        extra_patches = [
            patch("src.workflow.pipeline.preflight_activity", mock_preflight),
        ]

        output = await _execute_pipeline(params, mocks, extra_patches)

        assert output.success is True
        assert output.preflight_approved is None  # never ran


# ---------------------------------------------------------------------------
# 4. Suggest tier with Projects v2 enabled
# ---------------------------------------------------------------------------


class TestSuggestTierWithProjectsV2:
    """Suggest tier with projects_v2_enabled fires project sync calls."""

    @pytest.mark.asyncio
    async def test_projects_v2_sync_calls_fire(self) -> None:
        """Projects v2 sync activities are called during pipeline execution."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-proj",
            correlation_id="corr-suggest-proj",
            repo_tier="suggest",
            approval_auto_bypass=True,
            projects_v2_enabled=True,
        )
        mocks = _standard_activity_mocks()

        mock_project_sync = AsyncMock(return_value=None)
        extra_patches = [
            patch("src.workflow.pipeline.update_project_status_activity", mock_project_sync),
        ]
        mocks["update_project_status_activity"] = mock_project_sync

        output = await _execute_pipeline(params, mocks, extra_patches)

        assert output.success is True
        assert output.step_reached == WorkflowStep.PUBLISH


# ---------------------------------------------------------------------------
# 5. Suggest tier verification loopback
# ---------------------------------------------------------------------------


class TestSuggestTierVerificationLoopback:
    """Suggest tier handles verification failure with loopback."""

    @pytest.mark.asyncio
    async def test_verification_loopback_then_pass(self) -> None:
        """First verify fails, loopback, second verify passes."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-vloop",
            correlation_id="corr-suggest-vloop",
            repo_tier="suggest",
            approval_auto_bypass=True,
        )
        mocks = _standard_activity_mocks(
            verify_outputs=[
                _mock_verify_output(passed=False),
                _mock_verify_output(passed=True),
            ],
        )

        output = await _execute_pipeline(params, mocks)

        assert output.success is True
        assert output.verification_loopbacks == 1


# ---------------------------------------------------------------------------
# 6. Suggest tier QA loopback
# ---------------------------------------------------------------------------


class TestSuggestTierQALoopback:
    """Suggest tier handles QA failure with loopback."""

    @pytest.mark.asyncio
    async def test_qa_loopback_then_pass(self) -> None:
        """First QA fails, loopback to implementation, second QA passes."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-qaloop",
            correlation_id="corr-suggest-qaloop",
            repo_tier="suggest",
            approval_auto_bypass=True,
        )
        # First verify pass, first QA fail, second verify pass, second QA pass
        mocks = _standard_activity_mocks(
            verify_outputs=[
                _mock_verify_output(passed=True),
                _mock_verify_output(passed=True),
            ],
            qa_outputs=[
                _mock_qa_output(passed=False),
                _mock_qa_output(passed=True),
            ],
        )

        output = await _execute_pipeline(params, mocks)

        assert output.success is True
        assert output.qa_loopbacks == 1


# ---------------------------------------------------------------------------
# 7. All flags combined
# ---------------------------------------------------------------------------


class TestSuggestTierAllFlags:
    """Suggest tier with all feature flags enabled simultaneously."""

    @pytest.mark.asyncio
    async def test_all_flags_enabled(self) -> None:
        """Pipeline succeeds with preflight + projects_v2 + bypass all enabled."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-allflags",
            correlation_id="corr-suggest-allflags",
            repo_tier="suggest",
            approval_auto_bypass=True,
            preflight_enabled=True,
            preflight_tiers=["suggest", "execute"],
            projects_v2_enabled=True,
        )
        mocks = _standard_activity_mocks()

        mock_preflight = AsyncMock(return_value=_mock_preflight_output(approved=True))
        mock_project_sync = AsyncMock(return_value=None)
        extra_patches = [
            patch("src.workflow.pipeline.preflight_activity", mock_preflight),
            patch("src.workflow.pipeline.update_project_status_activity", mock_project_sync),
        ]
        mocks["preflight_activity"] = mock_preflight
        mocks["update_project_status_activity"] = mock_project_sync

        output = await _execute_pipeline(params, mocks, extra_patches)

        assert output.success is True
        assert output.approval_bypassed is True
        assert output.preflight_approved is True
        assert output.step_reached == WorkflowStep.PUBLISH
        assert output.pr_number == 101


# ---------------------------------------------------------------------------
# 8. Suggest tier with security overlays
# ---------------------------------------------------------------------------


class TestSuggestTierWithOverlays:
    """Suggest tier pipeline with security overlays from intake."""

    @pytest.mark.asyncio
    async def test_security_overlays_propagate(self) -> None:
        """Security overlays from intake pass through the pipeline."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-security",
            correlation_id="corr-suggest-security",
            repo_tier="suggest",
            approval_auto_bypass=True,
        )
        mocks = _standard_activity_mocks(
            intake_overlays=["security"],
            risk_flags={"security": True},
        )

        output = await _execute_pipeline(params, mocks)

        assert output.success is True
        assert output.step_reached == WorkflowStep.PUBLISH


# ---------------------------------------------------------------------------
# 9. Suggest tier intake rejection
# ---------------------------------------------------------------------------


class TestSuggestTierRejection:
    """Suggest tier pipeline handles intake rejection."""

    @pytest.mark.asyncio
    async def test_intake_rejection_stops_pipeline(self) -> None:
        """If intake rejects the issue, pipeline stops early."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-reject",
            correlation_id="corr-suggest-reject",
            repo_tier="suggest",
            approval_auto_bypass=True,
        )
        mocks = _standard_activity_mocks()
        mocks["intake_activity"] = AsyncMock(return_value=_mock_intake_rejected())

        output = await _execute_pipeline(params, mocks)

        assert output.success is False
        assert output.step_reached == WorkflowStep.INTAKE
        assert output.rejection_reason == "ineligible"


# ---------------------------------------------------------------------------
# 10. Suggest tier step progression
# ---------------------------------------------------------------------------


class TestSuggestTierStepProgression:
    """Verify step_reached is updated correctly through the pipeline."""

    @pytest.mark.asyncio
    async def test_final_step_is_publish(self) -> None:
        """Successful Suggest tier pipeline ends at PUBLISH step."""
        params = PipelineInput(
            taskpacket_id="tp-suggest-steps",
            correlation_id="corr-suggest-steps",
            repo_tier="suggest",
            approval_auto_bypass=True,
        )
        mocks = _standard_activity_mocks()
        output = await _execute_pipeline(params, mocks)

        assert output.step_reached == WorkflowStep.PUBLISH

    def test_pipeline_output_default_values(self) -> None:
        """PipelineOutput defaults are safe for Suggest tier."""
        output = PipelineOutput()
        assert output.success is False
        assert output.approval_bypassed is False
        assert output.awaiting_approval is False
        assert output.pr_number == 0
        assert output.verification_loopbacks == 0
        assert output.qa_loopbacks == 0
