"""Expert Router — selects expert subsets from intent + risk flags.

Architecture reference: thestudioarc/05-expert-router.md

The Router is the single entry point for expert consultation. It:
1. Determines required expert classes from EffectiveRolePolicy + risk flags
2. Queries Expert Library by class + capability tags
3. Ranks candidates by trust_tier (trusted > probation; shadow excluded)
4. Enforces budget limits
5. Produces a ConsultPlan with rationale
6. Emits Recruiter callback when no eligible expert exists
"""

from dataclasses import dataclass
from uuid import UUID

from src.experts.expert import ExpertClass, ExpertRead, TrustTier
from src.intake.effective_role import EffectiveRolePolicy


@dataclass(frozen=True)
class ExpertSelection:
    """A single expert selected for consultation."""

    expert_id: UUID
    expert_version: int
    expert_class: ExpertClass
    pattern: str  # "parallel" or "staged"


@dataclass(frozen=True)
class RecruiterRequest:
    """Request to Recruiter when no eligible expert exists for a required class."""

    expert_class: ExpertClass
    capability_tags: list[str]
    reason: str


@dataclass(frozen=True)
class ConsultPlan:
    """Output of the Router: selected experts + rationale + gaps."""

    selections: tuple[ExpertSelection, ...]
    recruiter_requests: tuple[RecruiterRequest, ...]
    rationale: str
    budget_remaining: int


# Signals emitted by the Router
SIGNAL_ROUTING_DECISION_MADE = "routing_decision_made"
SIGNAL_MANDATORY_COVERAGE_TRIGGERED = "mandatory_coverage_triggered"
SIGNAL_EXPERT_GAP_TRIGGERED = "expert_gap_triggered"


# Default capability tags to search for each expert class
CLASS_DEFAULT_TAGS: dict[ExpertClass, list[str]] = {
    ExpertClass.SECURITY: ["auth", "secrets", "crypto", "injection"],
    ExpertClass.COMPLIANCE: ["retention", "export", "residency", "audit"],
    ExpertClass.BUSINESS: ["pricing", "billing", "payments"],
    ExpertClass.PARTNER: ["partner_api", "integration", "contract"],
    ExpertClass.TECHNICAL: ["architecture", "infra", "performance"],
    ExpertClass.QA_VALIDATION: [
        "intent_validation", "acceptance_criteria", "defect_classification",
    ],
}


def route(
    effective_role: EffectiveRolePolicy,
    risk_flags: dict[str, bool] | None,
    available_experts: list[ExpertRead],
    max_experts_per_consult: int = 3,
) -> ConsultPlan:
    """Select expert subset and produce a ConsultPlan.

    Args:
        effective_role: Computed role policy with mandatory expert classes.
        risk_flags: Risk flags from TaskPacket context enrichment.
        available_experts: All active experts from Expert Library.
        max_experts_per_consult: Budget limit on total experts.

    Returns:
        ConsultPlan with selections, recruiter requests, and rationale.
    """
    # Determine required classes from EffectiveRolePolicy
    required_classes = set(effective_role.mandatory_expert_classes)

    # Add QA validation if any risk flags are present
    if risk_flags and any(risk_flags.values()):
        required_classes.add(ExpertClass.QA_VALIDATION)

    # If no required classes, return empty plan
    if not required_classes:
        return ConsultPlan(
            selections=(),
            recruiter_requests=(),
            rationale="No expert consultation required (no risk flags or mandatory coverage)",
            budget_remaining=max_experts_per_consult,
        )

    # Build index of available experts by class (excluding shadow and non-active)
    experts_by_class: dict[ExpertClass, list[ExpertRead]] = {}
    for expert in available_experts:
        if expert.trust_tier == TrustTier.SHADOW:
            continue  # Shadow experts excluded from auto-selection
        if expert.expert_class not in experts_by_class:
            experts_by_class[expert.expert_class] = []
        experts_by_class[expert.expert_class].append(expert)

    selections: list[ExpertSelection] = []
    recruiter_requests: list[RecruiterRequest] = []
    rationale_parts: list[str] = []
    budget = max_experts_per_consult

    for required_class in sorted(required_classes, key=lambda c: c.value):
        if budget <= 0:
            rationale_parts.append(
                f"Budget exhausted — skipped {required_class.value} coverage"
            )
            break

        candidates = experts_by_class.get(required_class, [])

        if not candidates:
            # No eligible expert — emit Recruiter callback
            tags = CLASS_DEFAULT_TAGS.get(required_class, [])
            recruiter_requests.append(
                RecruiterRequest(
                    expert_class=required_class,
                    capability_tags=tags,
                    reason=f"No eligible {required_class.value} expert found",
                )
            )
            rationale_parts.append(
                f"No eligible {required_class.value} expert — Recruiter callback requested"
            )
            continue

        # Select the best candidate (already ranked by trust_tier from search)
        best = candidates[0]
        selections.append(
            ExpertSelection(
                expert_id=best.id,
                expert_version=best.current_version,
                expert_class=best.expert_class,
                pattern="parallel",  # Default: parallel consult for independent domains
            )
        )
        budget -= 1
        rationale_parts.append(
            f"Selected {best.name} (v{best.current_version}, {best.trust_tier.value}) "
            f"for {required_class.value} coverage"
        )

    rationale = "; ".join(rationale_parts) if rationale_parts else "Empty consult plan"

    return ConsultPlan(
        selections=tuple(selections),
        recruiter_requests=tuple(recruiter_requests),
        rationale=rationale,
        budget_remaining=budget,
    )
