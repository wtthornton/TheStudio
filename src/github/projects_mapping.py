"""TaskPacket status to GitHub Projects v2 field value mapping.

Epic 29 AC 2: Maps TaskPacket statuses to Projects v2 Status field values.
Epic 29 AC 3-4: Maps trust tiers and complexity to Projects v2 fields.
Epic 38.14: Adds Cost (number) and Complexity (single-select) field mappings.

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

# Complexity index → Complexity single-select field value (Epic 38.14)
COMPLEXITY_MAPPING: dict[str, str] = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
}

# Field names for custom fields added by Epic 38.14
COST_FIELD_NAME = "Cost"
COMPLEXITY_FIELD_NAME = "Complexity"

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


def map_cost(cost_usd: float) -> str:
    """Format a cost in USD as a string suitable for a number field.

    Epic 38.14: Cost field stores the float value formatted to 4 decimal places.
    """
    return f"{cost_usd:.4f}"


def map_complexity(complexity_index: str) -> str | None:
    """Map a complexity index to its Complexity single-select value.

    Epic 38.14: Separate from Risk Tier — this drives the custom Complexity
    field that is auto-created on first sync.
    """
    return COMPLEXITY_MAPPING.get(complexity_index.lower())
