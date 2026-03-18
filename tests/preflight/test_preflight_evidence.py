"""Unit tests for preflight evidence comment and observability (Epic 28 Story 28.3).

Tests:
- PreflightSummary dataclass (AC 11)
- Evidence comment includes preflight section (AC 11)
- Observability span names exist (AC 10)
"""

from datetime import UTC, datetime
from uuid import UUID

from src.agent.evidence import EvidenceBundle
from src.intent.intent_spec import IntentSpecRead
from src.observability.conventions import (
    ATTR_PREFLIGHT_APPROVED,
    ATTR_PREFLIGHT_UNCOVERED_COUNT,
    ATTR_PREFLIGHT_VAGUE_COUNT,
    ATTR_PREFLIGHT_VIOLATION_COUNT,
    SPAN_PREFLIGHT_REVIEW,
)
from src.publisher.evidence_comment import (
    PreflightSummary,
    format_full_evidence_comment,
)
from src.verification.gate import VerificationResult


def _make_evidence() -> EvidenceBundle:
    return EvidenceBundle(
        taskpacket_id=UUID("00000000-0000-0000-0000-000000000001"),
        intent_version=1,
        files_changed=["src/widget.py"],
    )


def _make_intent() -> IntentSpecRead:
    return IntentSpecRead(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        taskpacket_id=UUID("00000000-0000-0000-0000-000000000001"),
        version=1,
        goal="Fix the widget",
        constraints=[],
        acceptance_criteria=["Widget works"],
        non_goals=[],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_verification() -> VerificationResult:
    return VerificationResult(passed=True, checks=[])


class TestPreflightSummary:
    """AC 11: PreflightSummary dataclass."""

    def test_default_status(self) -> None:
        ps = PreflightSummary()
        assert ps.status == "skipped"
        assert ps.summary == ""

    def test_approved_status(self) -> None:
        ps = PreflightSummary(status="approved", summary="All clear")
        assert ps.status == "approved"

    def test_approved_after_replan(self) -> None:
        ps = PreflightSummary(status="approved_after_replan", summary="Re-planned")
        assert ps.status == "approved_after_replan"


class TestEvidenceCommentWithPreflight:
    """AC 11: Evidence comment includes preflight section."""

    def test_approved_preflight_in_comment(self) -> None:
        comment = format_full_evidence_comment(
            evidence=_make_evidence(),
            intent=_make_intent(),
            verification=_make_verification(),
            correlation_id=UUID("00000000-0000-0000-0000-000000000003"),
            preflight=PreflightSummary(status="approved", summary="All checks passed"),
        )
        assert "### Preflight" in comment
        assert "**Approved**" in comment
        assert "All checks passed" in comment

    def test_approved_after_replan_in_comment(self) -> None:
        comment = format_full_evidence_comment(
            evidence=_make_evidence(),
            intent=_make_intent(),
            verification=_make_verification(),
            correlation_id=UUID("00000000-0000-0000-0000-000000000003"),
            preflight=PreflightSummary(
                status="approved_after_replan",
                summary="Fixed on second attempt",
            ),
        )
        assert "**Approved after re-plan**" in comment

    def test_skipped_preflight_in_comment(self) -> None:
        comment = format_full_evidence_comment(
            evidence=_make_evidence(),
            intent=_make_intent(),
            verification=_make_verification(),
            correlation_id=UUID("00000000-0000-0000-0000-000000000003"),
            preflight=PreflightSummary(status="skipped"),
        )
        assert "**Skipped (disabled)**" in comment

    def test_no_preflight_shows_not_configured(self) -> None:
        comment = format_full_evidence_comment(
            evidence=_make_evidence(),
            intent=_make_intent(),
            verification=_make_verification(),
            correlation_id=UUID("00000000-0000-0000-0000-000000000003"),
        )
        assert "### Preflight" in comment
        assert "Not configured" in comment

    def test_skipped_tier_in_comment(self) -> None:
        comment = format_full_evidence_comment(
            evidence=_make_evidence(),
            intent=_make_intent(),
            verification=_make_verification(),
            correlation_id=UUID("00000000-0000-0000-0000-000000000003"),
            preflight=PreflightSummary(status="skipped_tier"),
        )
        assert "**Skipped (tier not configured)**" in comment


class TestPreflightObservability:
    """AC 10: Span names and attribute keys exist."""

    def test_span_name(self) -> None:
        assert SPAN_PREFLIGHT_REVIEW == "preflight.review"

    def test_attribute_keys(self) -> None:
        assert ATTR_PREFLIGHT_APPROVED == "thestudio.preflight.approved"
        assert ATTR_PREFLIGHT_UNCOVERED_COUNT == "thestudio.preflight.uncovered_count"
        assert ATTR_PREFLIGHT_VIOLATION_COUNT == "thestudio.preflight.violation_count"
        assert ATTR_PREFLIGHT_VAGUE_COUNT == "thestudio.preflight.vague_count"
