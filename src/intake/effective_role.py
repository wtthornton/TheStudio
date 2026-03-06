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


class VerificationStrictness(enum.StrEnum):
    """How strict verification checks should be."""

    STANDARD = "standard"
    STRICT = "strict"


class QAStrictness(enum.StrEnum):
    """How strict QA validation should be."""

    STANDARD = "standard"
    STRICT = "strict"


class PublishingPosture(enum.StrEnum):
    """Controls whether Publisher can mark PRs ready-for-review."""

    DRAFT_ONLY = "draft_only"  # Observe tier or governance overlay
    READY_AFTER_GATE = "ready_after_gate"  # Suggest tier, V+QA must pass


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

# Overlays that force strict verification
STRICT_VERIFICATION_OVERLAYS: frozenset[Overlay] = frozenset({
    Overlay.SECURITY,
    Overlay.COMPLIANCE,
    Overlay.MIGRATION,
    Overlay.INFRA,
})

# Overlays that force strict QA
STRICT_QA_OVERLAYS: frozenset[Overlay] = frozenset({
    Overlay.SECURITY,
    Overlay.COMPLIANCE,
    Overlay.BILLING,
    Overlay.PARTNER_API,
    Overlay.HIGH_RISK,
})

# Overlays that force draft-only publishing posture
DRAFT_ONLY_OVERLAYS: frozenset[Overlay] = frozenset({
    Overlay.SECURITY,
    Overlay.COMPLIANCE,
    Overlay.INFRA,
})

# Default tool allowlists per base role (per 08-agent-roles.md)
ROLE_TOOL_ALLOWLISTS: dict[BaseRole, tuple[str, ...]] = {
    BaseRole.DEVELOPER: ("Read", "Write", "Edit", "Glob", "Grep", "Bash"),
    BaseRole.ARCHITECT: ("Read", "Write", "Edit", "Glob", "Grep", "Bash"),
    BaseRole.PLANNER: ("Read", "Glob", "Grep"),  # read-only, no repo write tools
}

# Default max experts per consult by base role
ROLE_MAX_EXPERTS: dict[BaseRole, int] = {
    BaseRole.DEVELOPER: 3,
    BaseRole.ARCHITECT: 5,  # higher consult budget for complex boundary work
    BaseRole.PLANNER: 2,    # small consult budgets
}


@dataclass(frozen=True)
class EffectiveRolePolicy:
    """Computed runtime policy applied to the workflow.

    Drives enforcement at Router, tools, Verification, QA, and Publisher.
    """

    base_role: BaseRole
    overlays: tuple[Overlay, ...] = ()
    mandatory_expert_classes: tuple[ExpertClass, ...] = ()
    requires_human_review: bool = False
    tool_allowlist: tuple[str, ...] = ()
    verification_strictness: VerificationStrictness = VerificationStrictness.STANDARD
    qa_strictness: QAStrictness = QAStrictness.STANDARD
    publishing_posture: PublishingPosture = PublishingPosture.DRAFT_ONLY
    max_experts_per_consult: int = 3

    @staticmethod
    def compute(
        base_role: BaseRole,
        overlays: list[Overlay],
    ) -> "EffectiveRolePolicy":
        """Compute the EffectiveRolePolicy from base role and overlays.

        Overlay merge order: governance -> change-type -> operational.
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

        # Tool allowlist from base role
        tool_allowlist = ROLE_TOOL_ALLOWLISTS.get(
            base_role, ROLE_TOOL_ALLOWLISTS[BaseRole.DEVELOPER]
        )

        # Verification strictness: strict if any strict-verification overlay present
        verification_strictness = (
            VerificationStrictness.STRICT
            if any(o in STRICT_VERIFICATION_OVERLAYS for o in unique_overlays)
            else VerificationStrictness.STANDARD
        )

        # QA strictness: strict if any strict-QA overlay present
        qa_strictness = (
            QAStrictness.STRICT
            if any(o in STRICT_QA_OVERLAYS for o in unique_overlays)
            else QAStrictness.STANDARD
        )

        # Publishing posture: draft-only if draft-only overlays or escalation required
        publishing_posture = (
            PublishingPosture.DRAFT_ONLY
            if (
                requires_human
                or any(o in DRAFT_ONLY_OVERLAYS for o in unique_overlays)
            )
            else PublishingPosture.READY_AFTER_GATE
        )

        # Max experts from base role
        max_experts = ROLE_MAX_EXPERTS.get(base_role, 3)

        return EffectiveRolePolicy(
            base_role=base_role,
            overlays=unique_overlays,
            mandatory_expert_classes=tuple(sorted(mandatory, key=lambda c: c.value)),
            requires_human_review=requires_human,
            tool_allowlist=tool_allowlist,
            verification_strictness=verification_strictness,
            qa_strictness=qa_strictness,
            publishing_posture=publishing_posture,
            max_experts_per_consult=max_experts,
        )
