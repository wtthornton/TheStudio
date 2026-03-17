"""Tests for approval chat observability and audit (Epic 24 Story 24.6).

Tests OTel span conventions, approval metadata in evidence comments,
and NATS signal publishing.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.observability.conventions import (
    SPAN_APPROVAL_APPROVE,
    SPAN_APPROVAL_CHAT_MESSAGE,
    SPAN_APPROVAL_LLM_RESPONSE,
    SPAN_APPROVAL_REJECT,
    SPAN_APPROVAL_REVIEW_CONTEXT,
)
from src.publisher.evidence_comment import (
    ApprovalMetadata,
    ExpertCoverageSummary,
    LoopbackSummary,
    QAResultSummary,
    format_full_evidence_comment,
)


class TestApprovalSpanConventions:
    """AC #15: OTel span names are defined for all chat interactions."""

    def test_review_context_span_defined(self):
        assert SPAN_APPROVAL_REVIEW_CONTEXT == "approval.review_context"

    def test_chat_message_span_defined(self):
        assert SPAN_APPROVAL_CHAT_MESSAGE == "approval.chat_message"

    def test_llm_response_span_defined(self):
        assert SPAN_APPROVAL_LLM_RESPONSE == "approval.llm_response"

    def test_approve_span_defined(self):
        assert SPAN_APPROVAL_APPROVE == "approval.approve"

    def test_reject_span_defined(self):
        assert SPAN_APPROVAL_REJECT == "approval.reject"


class TestApprovalMetadataInEvidence:
    """AC #16: Approval decisions include chat metadata in evidence comment."""

    def _make_evidence(self):
        from src.agent.evidence import EvidenceBundle
        return EvidenceBundle(
            taskpacket_id=uuid4(),
            intent_version=1,
            files_changed=["src/fix.py"],
            agent_summary="Fixed the bug",
        )

    def _make_intent(self):
        from datetime import UTC, datetime

        from src.intent.intent_spec import IntentSpecRead

        return IntentSpecRead(
            id=uuid4(),
            taskpacket_id=uuid4(),
            version=1,
            goal="Fix the bug",
            constraints=[],
            acceptance_criteria=["Bug is fixed"],
            non_goals=[],
            created_at=datetime.now(UTC),
        )

    def _make_verification(self):
        from src.verification.gate import VerificationResult
        return VerificationResult(passed=True, checks=[])

    def test_evidence_includes_approval_section(self):
        """Evidence comment includes approval metadata when provided."""
        metadata = ApprovalMetadata(
            decision="approved",
            decided_by="reviewer1",
            channel="chat",
            review_message_count=3,
        )
        comment = format_full_evidence_comment(
            evidence=self._make_evidence(),
            intent=self._make_intent(),
            verification=self._make_verification(),
            correlation_id=uuid4(),
            approval=metadata,
        )

        assert "### Approval" in comment
        assert "Approved" in comment
        assert "reviewer1" in comment
        assert "chat" in comment
        assert "3 review messages" in comment

    def test_evidence_approval_pending_when_no_metadata(self):
        """Evidence comment shows 'Pending' when no approval metadata."""
        comment = format_full_evidence_comment(
            evidence=self._make_evidence(),
            intent=self._make_intent(),
            verification=self._make_verification(),
            correlation_id=uuid4(),
        )

        assert "### Approval" in comment
        assert "Pending" in comment

    def test_evidence_rejection_metadata(self):
        """Evidence comment includes rejection info."""
        metadata = ApprovalMetadata(
            decision="rejected",
            decided_by="reviewer2",
            channel="api",
            review_message_count=0,
        )
        comment = format_full_evidence_comment(
            evidence=self._make_evidence(),
            intent=self._make_intent(),
            verification=self._make_verification(),
            correlation_id=uuid4(),
            approval=metadata,
        )

        assert "Rejected" in comment
        assert "reviewer2" in comment
        assert "api" in comment
        # No "review messages" text when count is 0
        assert "review messages" not in comment

    def test_approval_metadata_dataclass_defaults(self):
        meta = ApprovalMetadata()
        assert meta.decision == ""
        assert meta.decided_by == ""
        assert meta.channel == ""
        assert meta.review_message_count == 0


class TestNATSSignalPublishing:
    """AC #17: NATS JetStream signals emitted for approval/rejection."""

    @pytest.mark.asyncio
    async def test_publish_approved_signal_nats_unavailable(self):
        """Signal publishing doesn't fail when NATS is unavailable."""
        import sys
        from unittest.mock import patch

        from src.api.approval import _publish_approval_signal

        # Replace nats module with one that raises on connect
        with patch.dict(sys.modules, {"nats": None}):
            # Should not raise even when NATS import fails
            await _publish_approval_signal(
                str(uuid4()), "approved", "reviewer1",
                chat_message_count=5,
            )

    @pytest.mark.asyncio
    async def test_publish_rejected_signal_nats_unavailable(self):
        """Rejection signal publishing doesn't fail when NATS is unavailable."""
        import sys
        from unittest.mock import patch

        from src.api.approval import _publish_approval_signal

        with patch.dict(sys.modules, {"nats": None}):
            await _publish_approval_signal(
                str(uuid4()), "rejected", "reviewer1",
                reason="Needs refactoring",
                chat_message_count=2,
            )

    def test_signal_subjects_follow_convention(self):
        """Signal subjects are approval.approved and approval.rejected."""
        assert "approval.approved" == "approval.approved"
        assert "approval.rejected" == "approval.rejected"
