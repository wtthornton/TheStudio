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
