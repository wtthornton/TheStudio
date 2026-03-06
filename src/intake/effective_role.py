"""EffectiveRolePolicy — computed runtime policy for a workflow.

Architecture reference: thestudioarc/08-agent-roles.md
The EffectiveRolePolicy is computed from base role + overlays + risk flags
and drives enforcement across Router, tools, Verification, QA, and Publisher.
"""

import enum
from dataclasses import dataclass

from src.experts.expert import ExpertClass


class BaseRole(enum.StrEnum):
    """Base roles for the Primary Agent."""

    DEVELOPER = "developer"
    ARCHITECT = "architect"
    PLANNER = "planner"


class Overlay(enum.StrEnum):
    """Overlays modify base role behavior without creating new role identities."""

    SECURITY = "security"
    COMPLIANCE = "compliance"
    BILLING = "billing"
    MIGRATION = "migration"
    PARTNER_API = "partner_api"
    INFRA = "infra"
    HOTFIX = "hotfix"
    HIGH_RISK = "high_risk"


# Maps risk labels to overlays (per 08-agent-roles.md overlay catalog)
RISK_LABEL_TO_OVERLAY: dict[str, Overlay] = {
    "risk:auth": Overlay.SECURITY,
    "risk:compliance": Overlay.COMPLIANCE,
    "risk:billing": Overlay.BILLING,
    "risk:migration": Overlay.MIGRATION,
    "risk:partner-api": Overlay.PARTNER_API,
    "risk:infra": Overlay.INFRA,
}

# Maps overlays to mandatory expert classes (per 08-agent-roles.md)
OVERLAY_MANDATORY_EXPERTS: dict[Overlay, list[ExpertClass]] = {
    Overlay.SECURITY: [ExpertClass.SECURITY],
    Overlay.COMPLIANCE: [ExpertClass.COMPLIANCE],
    Overlay.BILLING: [ExpertClass.BUSINESS],
    Overlay.PARTNER_API: [ExpertClass.PARTNER],
    Overlay.INFRA: [ExpertClass.TECHNICAL],
}

# Overlays that require human review escalation
ESCALATION_OVERLAYS: frozenset[Overlay] = frozenset({
    Overlay.SECURITY,
    Overlay.COMPLIANCE,
    Overlay.BILLING,
    Overlay.MIGRATION,
})


@dataclass(frozen=True)
class EffectiveRolePolicy:
    """Computed runtime policy applied to the workflow.

    Drives enforcement at Router, tools, Verification, QA, and Publisher.
    """

    base_role: BaseRole
    overlays: tuple[Overlay, ...] = ()
    mandatory_expert_classes: tuple[ExpertClass, ...] = ()
    requires_human_review: bool = False

    @staticmethod
    def compute(
        base_role: BaseRole,
        overlays: list[Overlay],
    ) -> "EffectiveRolePolicy":
        """Compute the EffectiveRolePolicy from base role and overlays.

        Overlay merge order: governance → change-type → operational.
        If overlays conflict, the more restrictive behavior wins.
        """
        # Deduplicate and sort by overlay enum value for determinism
        unique_overlays = tuple(sorted(set(overlays), key=lambda o: o.value))

        # Collect mandatory expert classes from overlays
        mandatory: set[ExpertClass] = set()
        for overlay in unique_overlays:
            mandatory.update(OVERLAY_MANDATORY_EXPERTS.get(overlay, []))

        # If any risk overlay is present, QA validation is always required
        if unique_overlays:
            mandatory.add(ExpertClass.QA_VALIDATION)

        # Determine if human review is required
        requires_human = any(o in ESCALATION_OVERLAYS for o in unique_overlays)

        return EffectiveRolePolicy(
            base_role=base_role,
            overlays=unique_overlays,
            mandatory_expert_classes=tuple(sorted(mandatory, key=lambda c: c.value)),
            requires_human_review=requires_human,
        )
