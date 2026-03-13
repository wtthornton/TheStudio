"""EscalationRequest model — signals high-risk conditions to human operators.

Used by Router (Story 20.4) and Assembler (Story 20.5) when pipeline safety
nets detect conditions that require human oversight before proceeding.

Architecture reference: thestudioarc/05-expert-router.md (escalation triggers)
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass(frozen=True)
class EscalationRequest:
    """A request to escalate a pipeline decision to a human operator.

    Produced by Router or Assembler when high-risk conditions are detected
    that exceed the autonomous decision boundary.
    """

    source: str  # "router" or "assembler"
    reason: str
    risk_domain: str  # "security", "compliance", "billing", "partner", "migration", "destructive"
    taskpacket_id: UUID
    correlation_id: UUID
    severity: str  # "high" or "critical"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
