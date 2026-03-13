"""Tests for EscalationRequest model (Story 20.1)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.models.escalation import EscalationRequest


class TestEscalationRequestConstruction:
    """Test EscalationRequest dataclass construction and defaults."""

    def test_basic_construction(self) -> None:
        """EscalationRequest can be constructed with all required fields."""
        tp_id = uuid4()
        corr_id = uuid4()
        req = EscalationRequest(
            source="router",
            reason="Budget exhausted with high-risk flags",
            risk_domain="security",
            taskpacket_id=tp_id,
            correlation_id=corr_id,
            severity="critical",
        )
        assert req.source == "router"
        assert req.reason == "Budget exhausted with high-risk flags"
        assert req.risk_domain == "security"
        assert req.taskpacket_id == tp_id
        assert req.correlation_id == corr_id
        assert req.severity == "critical"

    def test_timestamp_defaults_to_now(self) -> None:
        """Timestamp defaults to current UTC time."""
        before = datetime.now(UTC)
        req = EscalationRequest(
            source="assembler",
            reason="Unresolved security conflict",
            risk_domain="compliance",
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            severity="high",
        )
        after = datetime.now(UTC)
        assert before <= req.timestamp <= after

    def test_frozen_immutability(self) -> None:
        """EscalationRequest is frozen — fields cannot be modified."""
        req = EscalationRequest(
            source="router",
            reason="test",
            risk_domain="security",
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            severity="high",
        )
        try:
            req.source = "assembler"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected: frozen dataclass

    def test_all_risk_domains(self) -> None:
        """All documented risk domains can be used."""
        for domain in ("security", "compliance", "billing", "partner", "migration", "destructive"):
            req = EscalationRequest(
                source="router",
                reason="test",
                risk_domain=domain,
                taskpacket_id=UUID(int=0),
                correlation_id=UUID(int=0),
                severity="high",
            )
            assert req.risk_domain == domain
