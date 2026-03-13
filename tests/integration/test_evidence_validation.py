"""Integration test: Evidence comment format validation.

Validates that the evidence comment produced by the Publisher contains
all required sections (TaskPacket ID, Intent Summary, Verification
Result) in the correct markdown format.
"""

from datetime import UTC, datetime
from uuid import uuid4

from src.agent.evidence import EvidenceBundle
from src.intent.intent_spec import IntentSpecRead
from src.publisher.evidence_comment import (
    EVIDENCE_COMMENT_MARKER,
    format_evidence_comment,
)
from src.verification.gate import VerificationResult
from src.verification.runners.base import CheckResult


def _make_evidence(
    taskpacket_id=None, loopback_attempt=0, files=None
) -> EvidenceBundle:
    return EvidenceBundle(
        taskpacket_id=taskpacket_id or uuid4(),
        intent_version=1,
        files_changed=files or ["src/app.py", "tests/test_app.py"],
        test_results="24 passed",
        lint_results="All checks passed",
        agent_summary="Added health endpoint",
        loopback_attempt=loopback_attempt,
    )


def _make_intent(taskpacket_id=None) -> IntentSpecRead:
    return IntentSpecRead(
        id=uuid4(),
        taskpacket_id=taskpacket_id or uuid4(),
        version=1,
        goal="Add /health endpoint returning HTTP 200",
        constraints=["must include tests"],
        acceptance_criteria=[
            "GET /health returns 200",
            "Response body contains status: ok",
        ],
        non_goals=["performance optimization"],
        created_at=datetime.now(UTC),
    )


def _make_verification(passed=True) -> VerificationResult:
    checks = [
        CheckResult(
            name="ruff",
            passed=passed,
            details="" if passed else "E501 line too long",
        ),
        CheckResult(name="pytest", passed=True, details="24/24 passed"),
    ]
    return VerificationResult(passed=passed, checks=checks)


class TestEvidenceCommentFormat:
    """Validate evidence comment structure matches the spec."""

    def test_contains_evidence_marker(self) -> None:
        """Evidence comment must start with the idempotency marker."""
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification()
        )
        assert EVIDENCE_COMMENT_MARKER in comment

    def test_contains_taskpacket_id(self) -> None:
        """Evidence comment must contain TaskPacket ID."""
        tp_id = uuid4()
        comment = format_evidence_comment(
            _make_evidence(taskpacket_id=tp_id), _make_intent(), _make_verification()
        )
        assert str(tp_id) in comment

    def test_contains_intent_goal(self) -> None:
        """Evidence comment must contain the intent goal."""
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification()
        )
        assert "Add /health endpoint" in comment

    def test_contains_acceptance_criteria(self) -> None:
        """Evidence comment must list acceptance criteria."""
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification()
        )
        assert "GET /health returns 200" in comment
        assert "Response body contains status: ok" in comment

    def test_contains_verification_checks(self) -> None:
        """Evidence comment must list verification check results."""
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification()
        )
        assert "ruff" in comment
        assert "pytest" in comment
        assert "PASSED" in comment

    def test_contains_loopback_count(self) -> None:
        """Evidence comment must show loopback attempt count."""
        comment = format_evidence_comment(
            _make_evidence(loopback_attempt=2), _make_intent(), _make_verification()
        )
        assert "2" in comment

    def test_contains_files_changed(self) -> None:
        """Evidence comment must list changed files."""
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification()
        )
        assert "src/app.py" in comment
        assert "tests/test_app.py" in comment

    def test_is_valid_markdown(self) -> None:
        """Evidence comment must be valid markdown with headers."""
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification()
        )
        assert "## TheStudio Evidence" in comment
        assert "### Intent Summary" in comment
        assert "### Verification Results" in comment
        # Must not contain raw HTML entities (Epic 12 bug)
        assert "&#" not in comment

    def test_failed_verification_shows_details(self) -> None:
        """When verification fails, comment must show failure details."""
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification(passed=False)
        )
        assert "FAILED" in comment
        assert "E501" in comment


# --- Story 15.4: Full Evidence Comment Validation ---


class TestFullEvidenceComment:
    """Validate format_full_evidence_comment with pipeline-shaped data."""

    def _make_full_comment(self) -> str:
        """Build a full evidence comment with realistic pipeline data."""
        from src.publisher.evidence_comment import (
            ExpertCoverageSummary,
            LoopbackSummary,
            QAResultSummary,
            format_full_evidence_comment,
        )

        tp_id = uuid4()
        corr_id = uuid4()

        evidence = EvidenceBundle(
            taskpacket_id=tp_id,
            intent_version=1,
            files_changed=[
                "src/auth/sso_client.py",
                "src/auth/connection_pool.py",
                "tests/test_sso_client.py",
            ],
            test_results="42 passed, 0 failed",
            lint_results="All checks passed",
            agent_summary="Fixed SSO timeout",
            loopback_attempt=0,
        )

        intent = IntentSpecRead(
            id=uuid4(),
            taskpacket_id=tp_id,
            version=1,
            goal="Fix SSO login timeout by reducing pool wait",
            constraints=["must not break existing auth"],
            acceptance_criteria=[
                "SSO login completes within 5 seconds",
                "Error message shown on timeout",
            ],
            non_goals=["performance optimization"],
            created_at=datetime.now(UTC),
        )

        verification = VerificationResult(
            passed=True,
            checks=[
                CheckResult(name="ruff", passed=True, details="OK"),
                CheckResult(
                    name="pytest", passed=True, details="42/42 passed",
                ),
            ],
        )

        qa = QAResultSummary(
            passed=True, defect_count=0, defect_categories=[],
        )

        experts = ExpertCoverageSummary(
            experts_consulted=[
                {"name": "SecurityExpert", "version": "2"},
                {"name": "AuthExpert", "version": "1"},
            ],
            policy_triggers=["security_overlay"],
        )

        loopback = LoopbackSummary(
            verification_loop_count=0,
            verification_failure_categories=[],
            qa_loop_count=0,
            qa_defect_categories=[],
        )

        return format_full_evidence_comment(
            evidence=evidence,
            intent=intent,
            verification=verification,
            correlation_id=corr_id,
            qa_result=qa,
            expert_coverage=experts,
            loopback=loopback,
        )

    def test_contains_evidence_marker(self) -> None:
        comment = self._make_full_comment()
        assert EVIDENCE_COMMENT_MARKER in comment

    def test_contains_header(self) -> None:
        comment = self._make_full_comment()
        assert "## TheStudio Evidence" in comment

    def test_contains_correlation_id_field(self) -> None:
        comment = self._make_full_comment()
        assert "Correlation ID" in comment

    def test_contains_intent_summary(self) -> None:
        comment = self._make_full_comment()
        assert "### Intent Summary" in comment
        assert "Fix SSO login timeout" in comment

    def test_contains_acceptance_criteria(self) -> None:
        comment = self._make_full_comment()
        assert "### Acceptance Criteria" in comment
        assert "SSO login completes within 5 seconds" in comment

    def test_contains_what_changed(self) -> None:
        comment = self._make_full_comment()
        assert "### What Changed" in comment
        assert "src/auth/sso_client.py" in comment

    def test_contains_verification_results(self) -> None:
        comment = self._make_full_comment()
        assert "### Verification Results" in comment
        assert "ruff" in comment
        assert "PASSED" in comment

    def test_contains_qa_result(self) -> None:
        comment = self._make_full_comment()
        assert "### QA Result" in comment

    def test_contains_expert_coverage(self) -> None:
        comment = self._make_full_comment()
        assert "### Expert Coverage" in comment
        assert "SecurityExpert" in comment

    def test_contains_loopback_summary(self) -> None:
        comment = self._make_full_comment()
        assert "### Loopback Summary" in comment

    def test_contains_footer(self) -> None:
        comment = self._make_full_comment()
        assert "Generated by TheStudio" in comment

    def test_all_seven_sections_present(self) -> None:
        """All 7 required sections exist in the full evidence comment."""
        comment = self._make_full_comment()
        sections = [
            EVIDENCE_COMMENT_MARKER,
            "## TheStudio Evidence",
            "### Intent Summary",
            "### Acceptance Criteria",
            "### What Changed",
            "### Verification Results",
            "Generated by TheStudio",
        ]
        for section in sections:
            assert section in comment, f"Missing section: {section}"
