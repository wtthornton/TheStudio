"""Escalation handler — processes escalation requests from Router and Assembler.

Logs escalation details and returns a PauseSignal indicating the workflow
should be paused for human review.

Architecture reference: thestudioarc/05-expert-router.md (escalation triggers)
"""

import logging
from dataclasses import dataclass

from src.models.escalation import EscalationRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PauseSignal:
    """Signal indicating whether the workflow should pause for human review."""

    pause_required: bool
    reason: str


def handle_escalation(escalation: EscalationRequest) -> PauseSignal:
    """Log escalation and return pause signal.

    All escalations result in a pause — this is by design. The pipeline
    should not proceed autonomously when high-risk conditions are detected.

    Args:
        escalation: The escalation request from Router or Assembler.

    Returns:
        PauseSignal with pause_required=True.
    """
    logger.warning(
        "escalation.triggered",
        extra={
            "source": escalation.source,
            "reason": escalation.reason,
            "risk_domain": escalation.risk_domain,
            "taskpacket_id": str(escalation.taskpacket_id),
            "correlation_id": str(escalation.correlation_id),
            "severity": escalation.severity,
        },
    )
    return PauseSignal(
        pause_required=True,
        reason=f"Escalation from {escalation.source}: {escalation.reason}",
    )
