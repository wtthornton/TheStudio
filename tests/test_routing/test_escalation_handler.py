"""Tests for escalation handler (Story 20.7)."""

import logging
from uuid import uuid4

import pytest

from src.models.escalation import EscalationRequest
from src.routing.escalation import PauseSignal, handle_escalation


class TestEscalationHandler:
    """Test that handle_escalation logs and returns PauseSignal."""

    def test_returns_pause_signal(self) -> None:
        """handle_escalation always returns pause_required=True."""
        escalation = EscalationRequest(
            source="router",
            reason="Low confidence experts with destructive risk",
            risk_domain="destructive",
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            severity="critical",
        )
        result = handle_escalation(escalation)
        assert isinstance(result, PauseSignal)
        assert result.pause_required is True
        assert "router" in result.reason

    def test_logs_escalation_details(self, caplog: pytest.LogCaptureFixture) -> None:
        """handle_escalation logs escalation at WARNING level."""
        escalation = EscalationRequest(
            source="assembler",
            reason="Unresolved security conflict",
            risk_domain="security",
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            severity="high",
        )
        with caplog.at_level(logging.WARNING):
            handle_escalation(escalation)
        assert "escalation.triggered" in caplog.text

    def test_pause_reason_includes_source(self) -> None:
        """PauseSignal reason includes the escalation source."""
        escalation = EscalationRequest(
            source="assembler",
            reason="Billing conflict unresolved",
            risk_domain="billing",
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            severity="high",
        )
        result = handle_escalation(escalation)
        assert "assembler" in result.reason
        assert "Billing conflict unresolved" in result.reason
