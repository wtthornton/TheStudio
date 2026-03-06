"""Unit tests for Evidence Comment Full Format (Story 1.9).

Architecture reference: thestudioarc/15-system-runtime-flow.md — "Standard Agent Evidence Comment"
"""

from datetime import UTC, datetime
from uuid import uuid4

from src.agent.evidence import EvidenceBundle
from src.intent.intent_spec import IntentSpecRead
from src.publisher.evidence_comment import (
    EVIDENCE_COMMENT_MARKER,
    ExpertCoverageSummary,
    LoopbackSummary,
    QAResultSummary,
    format_full_evidence_comment,
)
from src.verification.gate import VerificationResult
from src.verification.runners.base import CheckResult


def _make_evidence(tp_id=None) -> EvidenceBundle:
    return EvidenceBundle(
        taskpacket_id=tp_id or uuid4(),
        intent_version=2,
        files_changed=["src/auth.py", "tests/test_auth.py"],
        test_results="3 passed",
        lint_results="clean",
        agent_summary="Fixed auth bug",
        loopback_attempt=1,
    )


def _make_intent(tp_id=None) -> IntentSpecRead:
    return IntentSpecRead(
        id=uuid4(),
        taskpacket_id=tp_id or uuid4(),
        version=2,
        goal="Fix the authentication bypass vulnerability",
        constraints=["Must include tests"],
        acceptance_criteria=["Auth enforced on all endpoints", "No credential leaks"],
        non_goals=["No UI changes"],
        created_at=datetime.now(UTC),
    )


def _make_verification(passed: bool = True) -> VerificationResult:
    return VerificationResult(
        passed=passed,
        checks=[
            CheckResult(name="ruff", passed=True, details="clean", duration_ms=100),
            CheckResult(
                name="pytest", passed=passed,
                details="3 passed" if passed else "1 failed",
                duration_ms=500,
            ),
        ],
    )


class TestFullFormatIncludesAllFields:
    """Full format includes all required fields per 15-system-runtime-flow.md."""

    def test_all_required_fields_present(self) -> None:
        tp_id = uuid4()
        corr_id = uuid4()
        evidence = _make_evidence(tp_id)
        intent = _make_intent(tp_id)
        verification = _make_verification()
        qa = QAResultSummary(passed=True)
        expert_cov = ExpertCoverageSummary(
            experts_consulted=[{"name": "SecurityReview", "version": 1}],
            policy_triggers=["risk:auth"],
        )
        loopback = LoopbackSummary(
            verification_loop_count=1,
            verification_failure_categories=["lint"],
        )

        comment = format_full_evidence_comment(
            evidence, intent, verification, corr_id, qa, expert_cov, loopback,
        )

        # All required fields
        assert str(tp_id) in comment
        assert str(corr_id) in comment
        assert "v2" in comment
        assert "Fix the authentication bypass" in comment
        assert "Auth enforced" in comment
        assert "No credential leaks" in comment
        assert "src/auth.py" in comment
        assert "ruff" in comment
        assert "pytest" in comment
        assert "PASSED" in comment
        assert "SecurityReview" in comment
        assert "risk:auth" in comment
        assert "Verification loops: 1" in comment


class TestQAPassedFormat:
    """QA passed is shown correctly."""

    def test_qa_passed(self) -> None:
        comment = format_full_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification(), uuid4(),
            qa_result=QAResultSummary(passed=True),
        )
        assert "**Result:** PASSED" in comment


class TestQADefectFormat:
    """QA defects shown with count and categories."""

    def test_qa_defect_details(self) -> None:
        qa = QAResultSummary(
            passed=False,
            defect_count=2,
            defect_categories=["security", "implementation_bug"],
            has_intent_gap=False,
        )
        comment = format_full_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification(False), uuid4(),
            qa_result=qa,
        )
        assert "**Result:** FAILED" in comment
        assert "Defects: 2" in comment
        assert "security" in comment
        assert "implementation_bug" in comment

    def test_qa_intent_gap_shown(self) -> None:
        qa = QAResultSummary(
            passed=False, defect_count=1,
            defect_categories=["intent_gap"], has_intent_gap=True,
        )
        comment = format_full_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification(False), uuid4(),
            qa_result=qa,
        )
        assert "Intent gap detected" in comment


class TestExpertCoverageSection:
    """Expert coverage shows consulted experts and policy triggers."""

    def test_expert_coverage_listed(self) -> None:
        expert_cov = ExpertCoverageSummary(
            experts_consulted=[
                {"name": "SecurityReview", "version": 1},
                {"name": "QAValidation", "version": 2},
            ],
            policy_triggers=["risk:auth", "risk:billing"],
        )
        comment = format_full_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification(), uuid4(),
            expert_coverage=expert_cov,
        )
        assert "SecurityReview (v1)" in comment
        assert "QAValidation (v2)" in comment
        assert "risk:auth" in comment
        assert "risk:billing" in comment

    def test_no_experts(self) -> None:
        comment = format_full_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification(), uuid4(),
        )
        assert "No experts consulted" in comment


class TestLoopbackSummarySection:
    """Loopback summary shows verification and QA loop counts."""

    def test_loopback_details(self) -> None:
        loopback = LoopbackSummary(
            verification_loop_count=2,
            verification_failure_categories=["lint", "test"],
            qa_loop_count=1,
            qa_defect_categories=["implementation_bug"],
        )
        comment = format_full_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification(), uuid4(),
            loopback=loopback,
        )
        assert "Verification loops: 2" in comment
        assert "lint, test" in comment
        assert "QA loops: 1" in comment
        assert "implementation_bug" in comment


class TestMarkerPresent:
    """Evidence comment marker retained for idempotent updates."""

    def test_marker_in_full_format(self) -> None:
        comment = format_full_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification(), uuid4(),
        )
        assert EVIDENCE_COMMENT_MARKER in comment
