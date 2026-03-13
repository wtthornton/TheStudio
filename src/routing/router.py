"""Expert Router — selects expert subsets from intent + risk flags.

Architecture reference: thestudioarc/05-expert-router.md

The Router is the single entry point for expert consultation. It:
1. Determines required expert classes from EffectiveRolePolicy + risk flags
2. Queries Expert Library by class + capability tags
3. Queries Reputation Engine for weights and confidence
4. Ranks candidates by selection score (trust_tier * reputation-adjusted)
5. Enforces budget limits
6. Produces a ConsultPlan with rationale
7. Emits Recruiter callback when no eligible expert exists
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from src.experts.expert import ExpertClass, ExpertRead, TrustTier
from src.intake.effective_role import EffectiveRolePolicy
from src.models.escalation import EscalationRequest
from src.reputation.models import WeightQueryResult


@dataclass(frozen=True)
class ExpertSelection:
    """A single expert selected for consultation."""

    expert_id: UUID
    expert_version: int
    expert_class: ExpertClass
    pattern: str  # "parallel" or "staged"
    reputation_weight: float  # From Reputation Engine (0.0-1.0, default 0.5)
    reputation_confidence: float  # From Reputation Engine (0.0-1.0, default 0.0)
    selection_score: float  # Computed: trust_tier_score * (1 + weight * confidence)


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
    escalations: tuple[EscalationRequest, ...] = ()


# Signals emitted by the Router
SIGNAL_ROUTING_DECISION_MADE = "routing_decision_made"
SIGNAL_MANDATORY_COVERAGE_TRIGGERED = "mandatory_coverage_triggered"
SIGNAL_EXPERT_GAP_TRIGGERED = "expert_gap_triggered"

# Trust tier base scores for selection algorithm
TRUST_TIER_SCORES: dict[TrustTier, float] = {
    TrustTier.TRUSTED: 3.0,
    TrustTier.PROBATION: 2.0,
    TrustTier.SHADOW: 1.0,  # Not auto-selected, but included for completeness
}

# Threshold below which confidence is flagged as "probationary selection"
LOW_CONFIDENCE_THRESHOLD = 0.3

# Default reputation values for experts with no history
DEFAULT_REPUTATION_WEIGHT = 0.5
DEFAULT_REPUTATION_CONFIDENCE = 0.0


def _compute_selection_score(
    trust_tier: TrustTier,
    reputation_weight: float,
    reputation_confidence: float,
) -> float:
    """Compute selection score for ranking experts.

    Formula: trust_tier_score * (1 + reputation_weight * confidence)

    This means:
    - Trust tier is the base factor
    - Reputation weight adjusts within the tier (scaled by confidence)
    - High confidence amplifies reputation; low confidence dampens it
    """
    base_score = TRUST_TIER_SCORES.get(trust_tier, 1.0)
    reputation_adjustment = 1.0 + (reputation_weight * reputation_confidence)
    return base_score * reputation_adjustment


# Type alias for reputation lookup function (injected for testability)
ReputationLookupFn = Callable[[UUID, str | None], WeightQueryResult | None]


# Default capability tags to search for each expert class
CLASS_DEFAULT_TAGS: dict[ExpertClass, list[str]] = {
    ExpertClass.SECURITY: ["auth", "secrets", "crypto", "injection"],
    ExpertClass.COMPLIANCE: ["retention", "export", "residency", "audit"],
    ExpertClass.BUSINESS: ["pricing", "billing", "payments"],
    ExpertClass.PARTNER: ["partner_api", "integration", "contract"],
    ExpertClass.TECHNICAL: ["architecture", "infra", "performance"],
    ExpertClass.QA_VALIDATION: [
        "intent_validation",
        "acceptance_criteria",
        "defect_classification",
    ],
}


@dataclass(frozen=True)
class ScoredCandidate:
    """Intermediate structure for ranking candidates."""

    expert: ExpertRead
    reputation_weight: float
    reputation_confidence: float
    selection_score: float


def _get_reputation_for_expert(
    expert: ExpertRead,
    repo: str | None,
    reputation_lookup: ReputationLookupFn | None,
) -> tuple[float, float]:
    """Get reputation weight and confidence for an expert.

    Returns (weight, confidence), defaulting to (0.5, 0.0) if no data.
    """
    if reputation_lookup is None:
        return DEFAULT_REPUTATION_WEIGHT, DEFAULT_REPUTATION_CONFIDENCE

    result = reputation_lookup(expert.id, repo)
    if result is None:
        return DEFAULT_REPUTATION_WEIGHT, DEFAULT_REPUTATION_CONFIDENCE

    return result.weight, result.confidence


def _score_and_rank_candidates(
    candidates: list[ExpertRead],
    repo: str | None,
    reputation_lookup: ReputationLookupFn | None,
) -> list[ScoredCandidate]:
    """Score candidates using reputation and rank by selection score."""
    scored: list[ScoredCandidate] = []

    for expert in candidates:
        weight, confidence = _get_reputation_for_expert(expert, repo, reputation_lookup)
        score = _compute_selection_score(expert.trust_tier, weight, confidence)
        scored.append(
            ScoredCandidate(
                expert=expert,
                reputation_weight=weight,
                reputation_confidence=confidence,
                selection_score=score,
            )
        )

    # Sort by selection_score descending
    scored.sort(key=lambda c: c.selection_score, reverse=True)
    return scored


def route(
    effective_role: EffectiveRolePolicy,
    risk_flags: dict[str, bool] | None,
    available_experts: list[ExpertRead],
    max_experts_per_consult: int | None = None,
    reputation_lookup: ReputationLookupFn | None = None,
    repo: str | None = None,
) -> ConsultPlan:
    """Select expert subset and produce a ConsultPlan.

    Args:
        effective_role: Computed role policy with mandatory expert classes.
        risk_flags: Risk flags from TaskPacket context enrichment.
        available_experts: All active experts from Expert Library.
        max_experts_per_consult: Budget limit on total experts.
            If None, uses the policy's max_experts_per_consult.
        reputation_lookup: Optional function to query Reputation Engine.
            Signature: (expert_id, repo) -> WeightQueryResult | None.
            If None, defaults are used (weight=0.5, confidence=0.0).
        repo: Optional repo identifier for context-specific reputation lookup.

    Returns:
        ConsultPlan with selections, recruiter requests, and rationale.
    """
    # Use policy budget if not explicitly overridden
    if max_experts_per_consult is None:
        max_experts_per_consult = effective_role.max_experts_per_consult

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
            rationale_parts.append(f"Budget exhausted — skipped {required_class.value} coverage")
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

        # Score and rank candidates using reputation
        scored_candidates = _score_and_rank_candidates(candidates, repo, reputation_lookup)
        best = scored_candidates[0]

        # Build rationale with reputation info
        rationale_suffix = ""
        if best.reputation_confidence < LOW_CONFIDENCE_THRESHOLD:
            rationale_suffix = " [probationary selection — low confidence]"
        reputation_info = (
            f"reputation weight {best.reputation_weight:.2f} "
            f"(confidence {best.reputation_confidence:.2f})"
        )

        selections.append(
            ExpertSelection(
                expert_id=best.expert.id,
                expert_version=best.expert.current_version,
                expert_class=best.expert.expert_class,
                pattern="parallel",  # Default: parallel consult for independent domains
                reputation_weight=best.reputation_weight,
                reputation_confidence=best.reputation_confidence,
                selection_score=best.selection_score,
            )
        )
        budget -= 1
        rationale_parts.append(
            f"Selected {best.expert.name} (v{best.expert.current_version}, "
            f"{best.expert.trust_tier.value}) for {required_class.value} coverage — "
            f"{reputation_info}{rationale_suffix}"
        )

    rationale = "; ".join(rationale_parts) if rationale_parts else "Empty consult plan"

    # Detect escalation conditions
    escalations: list[EscalationRequest] = []
    high_risk_flags = {"risk_privileged_access", "risk_destructive"}
    active_high_risk = (
        {k for k, v in risk_flags.items() if v} & high_risk_flags if risk_flags else set()
    )

    if active_high_risk:
        # Condition 1: Budget exhausted before all mandatory classes covered
        covered_classes = {s.expert_class for s in selections}
        uncovered = required_classes - covered_classes
        if uncovered and budget <= 0:
            escalations.append(
                EscalationRequest(
                    source="router",
                    reason=(
                        f"Budget exhausted with uncovered mandatory classes "
                        f"({', '.join(c.value for c in uncovered)}) "
                        f"and high-risk flags ({', '.join(sorted(active_high_risk))})"
                    ),
                    risk_domain=(
                        "destructive" if "risk_destructive" in active_high_risk else "security"
                    ),
                    taskpacket_id=UUID(int=0),
                    correlation_id=UUID(int=0),
                    severity="critical",
                )
            )

        # Condition 2: Low confidence on selected experts with high-risk flags
        low_confidence_selections = [s for s in selections if s.reputation_confidence < 0.7]
        if low_confidence_selections:
            escalations.append(
                EscalationRequest(
                    source="router",
                    reason=(
                        "Low confidence experts selected for high-risk task: "
                        + ", ".join(
                            f"{s.expert_class.value} (conf={s.reputation_confidence:.2f})"
                            for s in low_confidence_selections
                        )
                    ),
                    risk_domain=(
                        "destructive" if "risk_destructive" in active_high_risk else "security"
                    ),
                    taskpacket_id=UUID(int=0),
                    correlation_id=UUID(int=0),
                    severity="high",
                )
            )

    return ConsultPlan(
        selections=tuple(selections),
        recruiter_requests=tuple(recruiter_requests),
        rationale=rationale,
        budget_remaining=budget,
        escalations=tuple(escalations),
    )
