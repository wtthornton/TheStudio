"""TaskPacket status to GitHub Projects v2 field value mapping.

Epic 29 AC 2: Maps TaskPacket statuses to Projects v2 Status field values.
Epic 29 AC 3-4: Maps trust tiers and complexity to Projects v2 fields.

Architecture reference: docs/epics/epic-29-github-projects-v2-meridian-portfolio-review.md
"""

from __future__ import annotations

# TaskPacket status → Projects v2 Status field value
STATUS_MAPPING: dict[str, str] = {
    "RECEIVED": "Queued",
    "ENRICHED": "Queued",
    "INTENT_BUILT": "In Progress",
    "IN_PROGRESS": "In Progress",
    "VERIFICATION_PASSED": "In Progress",
    "AWAITING_APPROVAL": "In Review",
    "CLARIFICATION_REQUESTED": "Blocked",
    "HUMAN_REVIEW_REQUIRED": "Blocked",
    "PUBLISHED": "Done",
    "FAILED": "Done",
    "REJECTED": "Done",
}

# Trust tier → Automation Tier field value (AC 3)
TIER_MAPPING: dict[str, str] = {
    "observe": "Observe",
    "suggest": "Suggest",
    "execute": "Execute",
}

# Complexity index → Risk Tier field value (AC 4)
RISK_TIER_MAPPING: dict[str, str] = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
}

# Required Projects v2 fields for compliance checking (AC 8)
REQUIRED_FIELDS: frozenset[str] = frozenset({
    "Status",
    "Automation Tier",
    "Risk Tier",
    "Priority",
    "Owner",
    "Repo",
})


def map_status(taskpacket_status: str) -> str | None:
    """Map a TaskPacket status to its Projects v2 Status value.

    Returns None if the status is not mapped (unknown status).
    """
    return STATUS_MAPPING.get(taskpacket_status)


def map_tier(trust_tier: str) -> str | None:
    """Map a trust tier to its Automation Tier field value."""
    return TIER_MAPPING.get(trust_tier.lower())


def map_risk(complexity_index: str) -> str | None:
    """Map a complexity index to its Risk Tier field value."""
    return RISK_TIER_MAPPING.get(complexity_index.lower())
