"""Unit tests for TheStudioPipelineWorkflow.run() orchestration logic.

Tests the full 9-step pipeline flow, loopback logic for verification
and QA gates, rejection handling, and step_reached tracking.
All Temporal activity calls are mocked — no Temporal server required.
"""

from unittest.mock import AsyncMock, patch

from src.workflow.activities import (
    ApprovalRequestOutput,
    AssemblerOutput,
    ContextOutput,
    ImplementOutput,
    IntakeOutput,
    IntentOutput,
    PublishOutput,
    QAOutput,
    VerifyOutput,
)
from src.workflow.pipeline import (
    MAX_QA_LOOPBACKS,
    MAX_VERIFICATION_LOOPBACKS,
    PipelineInput,
    TheStudioPipelineWorkflow,
    WorkflowStep,
)

# --- Helpers ---


def _default_params(**overrides) -> PipelineInput:
    """Build a PipelineInput with sensible defaults, accepting overrides."""
    defaults = dict(
        taskpacket_id="tp-001",
        correlation_id="corr-001",
        labels=["agent:run"],
        repo="acme/widgets",
        repo_registered=True,
        repo_paused=False,
        has_active_workflow=False,
        event_id="evt-001",
        issue_title="Fix the widget",
        issue_body="The widget is broken",
        repo_path="/tmp/repo",
        repo_tier="observe",
    )
    defaults.update(overrides)
    return PipelineInput(**defaults)


def _intake_accepted(**overrides) -> IntakeOutput:
    defaults = dict(accepted=True, base_role="developer", overlays=[])
    defaults.update(overrides)
    return IntakeOutput(**defaults)


def _intake_rejected(reason: str = "Not eligible") -> IntakeOutput:
    return IntakeOutput(accepted=False, rejection_reason=reason)


def _context_output(**overrides) -> ContextOutput:
    defaults = dict(scope={}, risk_flags={}, complexity_index="low", context_packs=[])
    defaults.update(overrides)
    return ContextOutput(**defaults)


def _intent_output(**overrides) -> IntentOutput:
    defaults = dict(
        intent_spec_id="int-001",
        version=1,
        goal="Fix the widget",
        acceptance_criteria=["Widget works"],
    )
    defaults.update(overrides)
    return IntentOutput(**defaults)


# Router returns are not captured by the workflow, so we use None sentinel
_ROUTER_OUTPUT = object()


def _assembler_output(**overrides) -> AssemblerOutput:
    defaults = dict(
        plan_steps=["implement_changes"],
        qa_handoff=[{"check": "widget_works"}],
        provenance={"taskpacket_id": "tp-001"},
    )
    defaults.update(overrides)
    return AssemblerOutput(**defaults)


def _impl_output(**overrides) -> ImplementOutput:
    defaults = dict(
        taskpacket_id="tp-001",
        intent_version=1,
        files_changed=["src/widget.py"],
        agent_summary="Fixed widget",
    )
    defaults.update(overrides)
    return ImplementOutput(**defaults)


def _verify_passed() -> VerifyOutput:
    return VerifyOutput(passed=True, checks=[])


def _verify_failed(exhausted: bool = False) -> VerifyOutput:
    return VerifyOutput(passed=False, loopback_triggered=True, exhausted=exhausted)


def _qa_passed() -> QAOutput:
    return QAOutput(passed=True)


def _qa_failed() -> QAOutput:
    return QAOutput(passed=False, has_intent_gap=True, defect_count=1)


def _publish_output(**overrides) -> PublishOutput:
    defaults = dict(
        pr_number=42,
        pr_url="https://github.com/acme/widgets/pull/42",
        created=True,
        marked_ready=True,
    )
    defaults.update(overrides)
    return PublishOutput(**defaults)


# --- Tests ---


class TestHappyPath:
    """Full pipeline completes successfully with no loopbacks."""

    async def test_full_pipeline_success(self) -> None:
        """All 9 steps succeed on first attempt — PR is published."""
        activity_returns = [
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

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is True
        assert result.step_reached == WorkflowStep.PUBLISH
        assert result.pr_number == 42
        assert result.pr_url == "https://github.com/acme/widgets/pull/42"
        assert result.marked_ready is True
        assert result.verification_loopbacks == 0
        assert result.qa_loopbacks == 0
        assert result.rejection_reason is None

    async def test_publish_output_fields_propagated(self) -> None:
        """PR fields from publish activity are propagated to pipeline output."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            _impl_output(),
            _verify_passed(),
            _qa_passed(),
            _publish_output(pr_number=99, pr_url="https://example.com/pr/99", marked_ready=False),
        ]

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.pr_number == 99
        assert result.pr_url == "https://example.com/pr/99"
        assert result.marked_ready is False


class TestIntakeRejection:
    """Intake rejects the issue — pipeline exits early."""

    async def test_rejected_returns_reason(self) -> None:
        """Rejected intake sets rejection_reason and exits."""
        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            return_value=_intake_rejected("Missing agent:run label"),
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is False
        assert result.step_reached == WorkflowStep.INTAKE
        assert result.rejection_reason == "Missing agent:run label"
        assert result.pr_number == 0

    async def test_rejected_no_further_steps(self) -> None:
        """Only intake activity is called when issue is rejected."""
        mock_exec = AsyncMock(return_value=_intake_rejected("paused"))

        with patch("temporalio.workflow.execute_activity", mock_exec):
            wf = TheStudioPipelineWorkflow()
            await wf.run(_default_params())

        # Only one activity call (intake)
        assert mock_exec.call_count == 1

    async def test_base_role_defaults_to_developer(self) -> None:
        """When intake returns base_role=None, pipeline defaults to 'developer'."""
        activity_returns = [
            _intake_accepted(base_role=None),  # None base_role
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            _impl_output(),
            _verify_passed(),
            _qa_passed(),
            _publish_output(),
        ]

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is True


class TestVerificationLoopback:
    """Verification gate can trigger loopback to implementation."""

    async def test_verify_fails_then_passes(self) -> None:
        """One verification loopback: impl -> verify(fail) -> impl -> verify(pass) -> QA -> publish."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            # First loop: impl -> verify fails
            _impl_output(),
            _verify_failed(),
            # Second loop: impl -> verify passes
            _impl_output(),
            _verify_passed(),
            _qa_passed(),
            _publish_output(),
        ]

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is True
        assert result.verification_loopbacks == 1
        assert result.qa_loopbacks == 0

    async def test_verify_exhausts_max_loopbacks(self) -> None:
        """Verification fails MAX_VERIFICATION_LOOPBACKS+1 times — pipeline fails closed."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
        ]
        # Add MAX_VERIFICATION_LOOPBACKS + 1 impl/verify pairs (all fail)
        for _ in range(MAX_VERIFICATION_LOOPBACKS + 1):
            activity_returns.extend([_impl_output(), _verify_failed()])

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is False
        assert result.step_reached == WorkflowStep.VERIFY
        assert result.verification_loopbacks == MAX_VERIFICATION_LOOPBACKS

    async def test_verify_exhausted_flag_fails_immediately(self) -> None:
        """Verification with exhausted=True fails immediately without loopback."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            _impl_output(),
            _verify_failed(exhausted=True),
        ]

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is False
        assert result.step_reached == WorkflowStep.VERIFY
        assert result.verification_loopbacks == 0

    async def test_two_verify_loopbacks_then_pass(self) -> None:
        """Two verification loopbacks followed by a pass — near the cap."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            # Fail twice
            _impl_output(), _verify_failed(),
            _impl_output(), _verify_failed(),
            # Third attempt passes
            _impl_output(), _verify_passed(),
            _qa_passed(),
            _publish_output(),
        ]

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is True
        assert result.verification_loopbacks == 2


class TestQALoopback:
    """QA gate can trigger loopback to implementation."""

    async def test_qa_fails_then_passes(self) -> None:
        """One QA loopback: impl -> verify(pass) -> QA(fail) -> impl -> verify(pass) -> QA(pass)."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            # First loop: passes verification, fails QA
            _impl_output(),
            _verify_passed(),
            _qa_failed(),
            # Second loop: passes both
            _impl_output(),
            _verify_passed(),
            _qa_passed(),
            _publish_output(),
        ]

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is True
        assert result.qa_loopbacks == 1
        assert result.verification_loopbacks == 0

    async def test_qa_exhausts_max_loopbacks(self) -> None:
        """QA fails MAX_QA_LOOPBACKS+1 times — pipeline fails closed."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
        ]
        # Each QA loop: impl -> verify(pass) -> QA(fail)
        for _ in range(MAX_QA_LOOPBACKS + 1):
            activity_returns.extend([
                _impl_output(),
                _verify_passed(),
                _qa_failed(),
            ])

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is False
        assert result.step_reached == WorkflowStep.QA
        assert result.qa_loopbacks == MAX_QA_LOOPBACKS

    async def test_two_qa_loopbacks_then_pass(self) -> None:
        """Two QA loopbacks followed by a pass."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            # Fail QA twice
            _impl_output(), _verify_passed(), _qa_failed(),
            _impl_output(), _verify_passed(), _qa_failed(),
            # Third attempt passes
            _impl_output(), _verify_passed(), _qa_passed(),
            _publish_output(),
        ]

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is True
        assert result.qa_loopbacks == 2


class TestMixedLoopbacks:
    """Combined verification and QA loopbacks."""

    async def test_verify_loopback_then_qa_loopback(self) -> None:
        """One verify loopback + one QA loopback — both counters tracked."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            # First loop: verify fails
            _impl_output(), _verify_failed(),
            # Second loop: verify passes, QA fails
            _impl_output(), _verify_passed(), _qa_failed(),
            # Third loop: both pass
            _impl_output(), _verify_passed(), _qa_passed(),
            _publish_output(),
        ]

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is True
        assert result.verification_loopbacks == 1
        assert result.qa_loopbacks == 1


class TestStepReachedTracking:
    """step_reached is updated as the workflow progresses."""

    async def test_step_reached_on_intake_rejection(self) -> None:
        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            return_value=_intake_rejected("no"),
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())
        assert result.step_reached == WorkflowStep.INTAKE

    async def test_step_reached_on_verify_failure(self) -> None:
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            _impl_output(),
            _verify_failed(exhausted=True),
        ]
        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())
        assert result.step_reached == WorkflowStep.VERIFY

    async def test_step_reached_on_qa_failure(self) -> None:
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
        ]
        for _ in range(MAX_QA_LOOPBACKS + 1):
            activity_returns.extend([_impl_output(), _verify_passed(), _qa_failed()])

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())
        assert result.step_reached == WorkflowStep.QA


class TestActivityCallArguments:
    """Verify correct arguments are passed to each activity."""

    async def test_intake_receives_correct_input(self) -> None:
        """Intake activity receives labels, repo, and gate fields from pipeline input."""
        mock_exec = AsyncMock(return_value=_intake_rejected("no"))

        with patch("temporalio.workflow.execute_activity", mock_exec):
            wf = TheStudioPipelineWorkflow()
            params = _default_params(labels=["agent:run", "type:bug"], repo="org/repo")
            await wf.run(params)

        call_args = mock_exec.call_args_list[0]
        intake_input = call_args[0][1]  # second positional arg (activity fn, input)
        assert intake_input.labels == ["agent:run", "type:bug"]
        assert intake_input.repo == "org/repo"
        assert intake_input.repo_registered is True

    async def test_context_receives_taskpacket_and_issue(self) -> None:
        """Context activity receives taskpacket_id and issue metadata."""
        activity_returns = [
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
        mock_exec = AsyncMock(side_effect=activity_returns)

        with patch("temporalio.workflow.execute_activity", mock_exec):
            wf = TheStudioPipelineWorkflow()
            params = _default_params(
                taskpacket_id="tp-xyz",
                issue_title="My Title",
                issue_body="My Body",
            )
            await wf.run(params)

        # Context is the 2nd call (index 1)
        context_input = mock_exec.call_args_list[1][0][1]
        assert context_input.taskpacket_id == "tp-xyz"
        assert context_input.issue_title == "My Title"
        assert context_input.issue_body == "My Body"

    async def test_publish_receives_repo_tier_and_qa_passed(self) -> None:
        """Publish activity receives repo_tier from pipeline and qa_passed=True."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            _impl_output(),
            _verify_passed(),
            _qa_passed(),
            # approval request activity (triggered by execute tier)
            ApprovalRequestOutput(comment_posted=True),
            _publish_output(),
        ]
        mock_exec = AsyncMock(side_effect=activity_returns)

        from datetime import datetime, timezone

        wf = TheStudioPipelineWorkflow()

        async def mock_wait_condition(fn, *, timeout=None):
            """Simulate immediate approval."""
            wf._approved = True
            wf._approved_by = "test-user"

        with (
            patch("temporalio.workflow.execute_activity", mock_exec),
            patch("temporalio.workflow.wait_condition", mock_wait_condition),
            patch("temporalio.workflow.now", return_value=datetime.now(timezone.utc)),
            patch("temporalio.workflow.logger") as mock_logger,
        ):
            params = _default_params(repo_tier="execute")
            await wf.run(params)

        # Publish is the last call
        publish_input = mock_exec.call_args_list[-1][0][1]
        assert publish_input.repo_tier == "execute"
        assert publish_input.qa_passed is True

    async def test_implement_receives_loopback_attempt(self) -> None:
        """Implementation activity receives combined loopback count."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            # First loop: verify fails (loopback_attempt=0)
            _impl_output(), _verify_failed(),
            # Second loop: passes verification, QA fails (loopback_attempt=1)
            _impl_output(), _verify_passed(), _qa_failed(),
            # Third loop: all pass (loopback_attempt=2)
            _impl_output(), _verify_passed(), _qa_passed(),
            _publish_output(),
        ]
        mock_exec = AsyncMock(side_effect=activity_returns)

        with patch("temporalio.workflow.execute_activity", mock_exec):
            wf = TheStudioPipelineWorkflow()
            await wf.run(_default_params())

        # Find implement calls — ImplementInput has loopback_attempt attr
        impl_calls = [
            c for c in mock_exec.call_args_list
            if hasattr(c[0][1], "loopback_attempt")
        ]
        assert len(impl_calls) == 3
        assert impl_calls[0][0][1].loopback_attempt == 0
        assert impl_calls[1][0][1].loopback_attempt == 1
        assert impl_calls[2][0][1].loopback_attempt == 2


class TestPipelineOutputDefaults:
    """Pipeline output has correct defaults for partial runs."""

    async def test_rejected_output_has_zero_pr(self) -> None:
        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            return_value=_intake_rejected("no"),
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.pr_number == 0
        assert result.pr_url == ""
        assert result.marked_ready is False

    async def test_verify_failure_output_has_zero_qa_loopbacks(self) -> None:
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            _impl_output(),
            _verify_failed(exhausted=True),
        ]
        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.qa_loopbacks == 0
        assert result.verification_loopbacks == 0


class TestActivityCallCount:
    """Verify the correct number of activity calls for various scenarios."""

    async def test_happy_path_has_nine_calls(self) -> None:
        """Full success path calls exactly 9 activities."""
        activity_returns = [
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
        mock_exec = AsyncMock(side_effect=activity_returns)

        with patch("temporalio.workflow.execute_activity", mock_exec):
            wf = TheStudioPipelineWorkflow()
            await wf.run(_default_params())

        assert mock_exec.call_count == 9

    async def test_one_verify_loopback_has_eleven_calls(self) -> None:
        """One verification loopback adds 2 calls (impl + verify)."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            _impl_output(), _verify_failed(),
            _impl_output(), _verify_passed(),
            _qa_passed(),
            _publish_output(),
        ]
        mock_exec = AsyncMock(side_effect=activity_returns)

        with patch("temporalio.workflow.execute_activity", mock_exec):
            wf = TheStudioPipelineWorkflow()
            await wf.run(_default_params())

        assert mock_exec.call_count == 11

    async def test_one_qa_loopback_has_twelve_calls(self) -> None:
        """One QA loopback adds 3 calls (impl + verify + QA)."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
            _ROUTER_OUTPUT,
            _assembler_output(),
            _impl_output(), _verify_passed(), _qa_failed(),
            _impl_output(), _verify_passed(), _qa_passed(),
            _publish_output(),
        ]
        mock_exec = AsyncMock(side_effect=activity_returns)

        with patch("temporalio.workflow.execute_activity", mock_exec):
            wf = TheStudioPipelineWorkflow()
            await wf.run(_default_params())

        assert mock_exec.call_count == 12


class TestIntentReviewWaitPoint:
    """Step 3.5: Intent review wait point (Story 36.8)."""

    async def test_intent_review_disabled_by_default(self) -> None:
        """When intent_review_enabled=False (default), workflow skips wait point."""
        activity_returns = [
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

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=activity_returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(_default_params())

        assert result.success is True
        assert result.intent_approved_by is None

    async def test_intent_review_approve_continues_to_router(self) -> None:
        """Approve signal resumes workflow to Router and beyond."""
        activity_returns = [
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
        mock_exec = AsyncMock(side_effect=activity_returns)

        wf = TheStudioPipelineWorkflow()

        async def mock_wait_condition(fn, *, timeout=None):
            """Simulate immediate intent approval."""
            wf._intent_approved = True
            wf._intent_approved_by = "developer-user"

        with (
            patch("temporalio.workflow.execute_activity", mock_exec),
            patch("temporalio.workflow.wait_condition", mock_wait_condition),
        ):
            result = await wf.run(
                _default_params(intent_review_enabled=True),
            )

        assert result.success is True
        assert result.intent_approved_by == "developer-user"
        assert result.step_reached == WorkflowStep.PUBLISH

    async def test_intent_review_reject_terminates(self) -> None:
        """Reject signal terminates workflow with reason."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
        ]
        mock_exec = AsyncMock(side_effect=activity_returns)

        wf = TheStudioPipelineWorkflow()

        async def mock_wait_condition(fn, *, timeout=None):
            """Simulate intent rejection."""
            wf._intent_rejected = True
            wf._intent_rejected_by = "developer-user"
            wf._intent_rejection_reason = "Goal is too vague"

        with (
            patch("temporalio.workflow.execute_activity", mock_exec),
            patch("temporalio.workflow.wait_condition", mock_wait_condition),
        ):
            result = await wf.run(
                _default_params(intent_review_enabled=True),
            )

        assert result.success is False
        assert "Intent rejected" in result.rejection_reason
        assert "Goal is too vague" in result.rejection_reason

    async def test_intent_review_timeout_escalates(self) -> None:
        """30-day timeout terminates workflow without auto-approve."""
        activity_returns = [
            _intake_accepted(),
            _context_output(),
            _intent_output(),
        ]
        mock_exec = AsyncMock(side_effect=activity_returns)

        async def mock_wait_condition(fn, *, timeout=None):
            raise TimeoutError("30-day timeout")

        with (
            patch("temporalio.workflow.execute_activity", mock_exec),
            patch("temporalio.workflow.wait_condition", mock_wait_condition),
            patch("temporalio.workflow.logger"),
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(
                _default_params(intent_review_enabled=True),
            )

        assert result.success is False
        assert result.rejection_reason == "intent_review_timeout"

    async def test_approve_signal_idempotent(self) -> None:
        """Calling approve_intent twice is harmless."""
        wf = TheStudioPipelineWorkflow()
        await wf.approve_intent("user-1")
        await wf.approve_intent("user-2")
        assert wf._intent_approved is True
        # Second call overwrites approver (idempotent, not an error)
        assert wf._intent_approved_by == "user-2"

    async def test_reject_signal_idempotent(self) -> None:
        """Calling reject_intent twice is harmless."""
        wf = TheStudioPipelineWorkflow()
        await wf.reject_intent("user-1", "reason-1")
        await wf.reject_intent("user-2", "reason-2")
        assert wf._intent_rejected is True
