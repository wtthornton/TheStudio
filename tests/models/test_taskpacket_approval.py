"""Unit tests for TaskPacket approval status transitions (Epic 21, Story 7)."""


from src.models.taskpacket import ALLOWED_TRANSITIONS, TaskPacketStatus


class TestApprovalStatusTransitions:
    """Verify AWAITING_APPROVAL and AWAITING_APPROVAL_EXPIRED transitions."""

    def test_verification_passed_can_transition_to_awaiting_approval(self):
        allowed = ALLOWED_TRANSITIONS[TaskPacketStatus.VERIFICATION_PASSED]
        assert TaskPacketStatus.AWAITING_APPROVAL in allowed

    def test_verification_passed_can_still_transition_to_published(self):
        """Observe tier goes directly to PUBLISHED — transition must remain."""
        allowed = ALLOWED_TRANSITIONS[TaskPacketStatus.VERIFICATION_PASSED]
        assert TaskPacketStatus.PUBLISHED in allowed

    def test_awaiting_approval_can_transition_to_published(self):
        allowed = ALLOWED_TRANSITIONS[TaskPacketStatus.AWAITING_APPROVAL]
        assert TaskPacketStatus.PUBLISHED in allowed

    def test_awaiting_approval_can_transition_to_expired(self):
        allowed = ALLOWED_TRANSITIONS[TaskPacketStatus.AWAITING_APPROVAL]
        assert TaskPacketStatus.AWAITING_APPROVAL_EXPIRED in allowed

    def test_awaiting_approval_can_transition_to_failed(self):
        allowed = ALLOWED_TRANSITIONS[TaskPacketStatus.AWAITING_APPROVAL]
        assert TaskPacketStatus.FAILED in allowed

    def test_awaiting_approval_expired_can_transition_to_failed(self):
        allowed = ALLOWED_TRANSITIONS[TaskPacketStatus.AWAITING_APPROVAL_EXPIRED]
        assert TaskPacketStatus.FAILED in allowed

    def test_awaiting_approval_expired_is_terminal_except_failed(self):
        """AWAITING_APPROVAL_EXPIRED can only go to FAILED."""
        allowed = ALLOWED_TRANSITIONS[TaskPacketStatus.AWAITING_APPROVAL_EXPIRED]
        assert allowed == {TaskPacketStatus.FAILED}

    def test_awaiting_approval_status_values(self):
        assert TaskPacketStatus.AWAITING_APPROVAL.value == "awaiting_approval"
        assert TaskPacketStatus.AWAITING_APPROVAL_EXPIRED.value == "awaiting_approval_expired"

    def test_existing_transitions_unchanged(self):
        """Verify existing transitions are not accidentally broken."""
        # RECEIVED -> ENRICHED, FAILED
        assert ALLOWED_TRANSITIONS[TaskPacketStatus.RECEIVED] == {
            TaskPacketStatus.ENRICHED,
            TaskPacketStatus.FAILED,
        }
        # PUBLISHED -> terminal
        assert ALLOWED_TRANSITIONS[TaskPacketStatus.PUBLISHED] == set()
        # FAILED -> terminal
        assert ALLOWED_TRANSITIONS[TaskPacketStatus.FAILED] == set()

    def test_full_approval_path(self):
        """Verify the full happy path: VERIFICATION_PASSED -> AWAITING_APPROVAL -> PUBLISHED."""
        assert TaskPacketStatus.AWAITING_APPROVAL in ALLOWED_TRANSITIONS[
            TaskPacketStatus.VERIFICATION_PASSED
        ]
        assert TaskPacketStatus.PUBLISHED in ALLOWED_TRANSITIONS[
            TaskPacketStatus.AWAITING_APPROVAL
        ]

    def test_full_timeout_path(self):
        """Verify timeout path: AWAITING_APPROVAL -> AWAITING_APPROVAL_EXPIRED -> FAILED."""
        assert TaskPacketStatus.AWAITING_APPROVAL_EXPIRED in ALLOWED_TRANSITIONS[
            TaskPacketStatus.AWAITING_APPROVAL
        ]
        assert TaskPacketStatus.FAILED in ALLOWED_TRANSITIONS[
            TaskPacketStatus.AWAITING_APPROVAL_EXPIRED
        ]
