"""Execute Tier Promotion — gate tier promotion on compliance check results.

Architecture reference: thestudioarc/23-admin-control-ui.md
(Execute Tier Compliance Gate, Repo Registration Lifecycle)

Promotion to Execute tier is blocked until compliance checker passes.
All tier transitions are recorded with audit metadata.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from src.compliance.checker import ComplianceChecker, GitHubRepoInfo
from src.compliance.models import ComplianceResult
from src.observability.tracing import get_tracer
from src.repo.repo_profile import RepoTier

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.compliance.promotion")


class PromotionBlockReason(StrEnum):
    """Reasons why promotion may be blocked."""

    INVALID_CURRENT_TIER = "invalid_current_tier"
    COMPLIANCE_FAILED = "compliance_failed"
    ACTIVE_WORKFLOWS = "active_workflows"
    ALREADY_AT_TIER = "already_at_tier"


@dataclass
class EligibilityResult:
    """Result of checking promotion eligibility."""

    eligible: bool
    block_reason: PromotionBlockReason | None = None
    block_details: str | None = None
    compliance_result: ComplianceResult | None = None


@dataclass
class PromotionResult:
    """Result of a tier promotion attempt."""

    success: bool
    repo_id: UUID
    from_tier: RepoTier
    to_tier: RepoTier
    triggered_by: str
    timestamp: datetime
    compliance_score: float | None = None
    compliance_result_id: UUID | None = None
    block_reason: PromotionBlockReason | None = None
    block_details: str | None = None


@dataclass
class DemotionResult:
    """Result of a tier demotion."""

    success: bool
    repo_id: UUID
    from_tier: RepoTier
    to_tier: RepoTier
    reason: str
    triggered_by: str
    timestamp: datetime


@dataclass
class TierTransition:
    """Record of a tier transition for audit trail."""

    id: UUID = field(default_factory=uuid4)
    repo_id: UUID = field(default_factory=uuid4)
    from_tier: RepoTier = RepoTier.OBSERVE
    to_tier: RepoTier = RepoTier.OBSERVE
    triggered_by: str = ""
    compliance_score: float | None = None
    compliance_result_id: UUID | None = None
    reason: str = ""
    transitioned_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# Valid promotion paths
VALID_PROMOTIONS: dict[RepoTier, list[RepoTier]] = {
    RepoTier.OBSERVE: [RepoTier.SUGGEST],
    RepoTier.SUGGEST: [RepoTier.EXECUTE],
    RepoTier.EXECUTE: [],  # No promotion from Execute
}

# Valid demotion paths
VALID_DEMOTIONS: dict[RepoTier, list[RepoTier]] = {
    RepoTier.OBSERVE: [],  # No demotion from Observe
    RepoTier.SUGGEST: [RepoTier.OBSERVE],
    RepoTier.EXECUTE: [RepoTier.SUGGEST, RepoTier.OBSERVE],
}


class PromotionService:
    """Manages tier promotion with compliance gate.

    Usage:
        service = PromotionService(
            compliance_checker=checker,
            repo_profile_getter=get_profile,
            repo_profile_updater=update_tier,
        )
        result = await service.request_promotion(repo_id, RepoTier.EXECUTE, "admin")
    """

    def __init__(
        self,
        compliance_checker: ComplianceChecker | None = None,
        repo_profile_getter: Any | None = None,
        repo_profile_updater: Any | None = None,
        active_workflow_checker: Any | None = None,
        signal_emitter: Any | None = None,
    ) -> None:
        """Initialize promotion service.

        Args:
            compliance_checker: Checker for running compliance checks.
            repo_profile_getter: Callable to get repo profile by ID.
            repo_profile_updater: Callable to update repo tier.
            active_workflow_checker: Callable to check for active workflows.
            signal_emitter: Callable to emit tier_changed signals.
        """
        self._compliance_checker = compliance_checker or ComplianceChecker()
        self._repo_profile_getter = repo_profile_getter
        self._repo_profile_updater = repo_profile_updater
        self._active_workflow_checker = active_workflow_checker
        self._signal_emitter = signal_emitter

    async def check_promotion_eligibility(
        self,
        repo_id: UUID,
        target_tier: RepoTier,
        repo_info: GitHubRepoInfo,
        current_tier: RepoTier,
    ) -> EligibilityResult:
        """Check if a repo is eligible for promotion to target tier.

        Args:
            repo_id: Repository to check.
            target_tier: Target tier for promotion.
            repo_info: GitHub repository information.
            current_tier: Current tier of the repo.

        Returns:
            EligibilityResult with eligibility status and any blocking reasons.
        """
        with tracer.start_as_current_span("promotion.check_eligibility") as span:
            span.set_attribute("thestudio.repo_id", str(repo_id))
            span.set_attribute("thestudio.current_tier", current_tier.value)
            span.set_attribute("thestudio.target_tier", target_tier.value)

            # Check if already at target tier
            if current_tier == target_tier:
                return EligibilityResult(
                    eligible=False,
                    block_reason=PromotionBlockReason.ALREADY_AT_TIER,
                    block_details=f"Repository is already at {target_tier.value} tier",
                )

            # Check if valid promotion path
            valid_targets = VALID_PROMOTIONS.get(current_tier, [])
            if target_tier not in valid_targets:
                return EligibilityResult(
                    eligible=False,
                    block_reason=PromotionBlockReason.INVALID_CURRENT_TIER,
                    block_details=(
                        f"Cannot promote from {current_tier.value} to {target_tier.value}. "
                        f"Valid targets: {[t.value for t in valid_targets]}"
                    ),
                )

            # Check for active workflows (if checker provided)
            if self._active_workflow_checker:
                has_active = await self._active_workflow_checker(repo_id)
                if has_active:
                    return EligibilityResult(
                        eligible=False,
                        block_reason=PromotionBlockReason.ACTIVE_WORKFLOWS,
                        block_details=(
                            "Repository has active workflows. Complete or cancel them first."
                        ),
                    )

            # Run compliance check for Execute tier
            if target_tier == RepoTier.EXECUTE:
                compliance_result = await self._compliance_checker.check_compliance(
                    repo_id=repo_id,
                    repo_info=repo_info,
                    triggered_by="eligibility_check",
                    check_execution_plane=True,
                    target_tier=target_tier.value,
                )

                if not compliance_result.overall_passed:
                    failed_checks = [
                        c.check.value for c in compliance_result.checks if not c.passed
                    ]
                    return EligibilityResult(
                        eligible=False,
                        block_reason=PromotionBlockReason.COMPLIANCE_FAILED,
                        block_details=f"Compliance check failed: {', '.join(failed_checks)}",
                        compliance_result=compliance_result,
                    )

                return EligibilityResult(
                    eligible=True,
                    compliance_result=compliance_result,
                )

            # Suggest tier doesn't require compliance check
            return EligibilityResult(eligible=True)

    async def request_promotion(
        self,
        repo_id: UUID,
        target_tier: RepoTier,
        triggered_by: str,
        repo_info: GitHubRepoInfo,
        current_tier: RepoTier,
    ) -> PromotionResult:
        """Request promotion to a target tier.

        Args:
            repo_id: Repository to promote.
            target_tier: Target tier.
            triggered_by: Who/what triggered the promotion.
            repo_info: GitHub repository information.
            current_tier: Current tier of the repo.

        Returns:
            PromotionResult with success status and audit metadata.
        """
        with tracer.start_as_current_span("promotion.request") as span:
            span.set_attribute("thestudio.repo_id", str(repo_id))
            span.set_attribute("thestudio.target_tier", target_tier.value)
            span.set_attribute("thestudio.triggered_by", triggered_by)

            now = datetime.now(UTC)

            # Check eligibility
            eligibility = await self.check_promotion_eligibility(
                repo_id=repo_id,
                target_tier=target_tier,
                repo_info=repo_info,
                current_tier=current_tier,
            )

            if not eligibility.eligible:
                logger.warning(
                    "Promotion blocked for repo %s: %s - %s",
                    repo_id,
                    eligibility.block_reason,
                    eligibility.block_details,
                )

                # Emit promotion_blocked signal
                if self._signal_emitter:
                    await self._signal_emitter({
                        "event": "promotion_blocked",
                        "repo_id": str(repo_id),
                        "target_tier": target_tier.value,
                        "reason": eligibility.block_reason,
                        "details": eligibility.block_details,
                        "triggered_by": triggered_by,
                        "timestamp": now.isoformat(),
                    })

                return PromotionResult(
                    success=False,
                    repo_id=repo_id,
                    from_tier=current_tier,
                    to_tier=target_tier,
                    triggered_by=triggered_by,
                    timestamp=now,
                    compliance_score=(
                        eligibility.compliance_result.score
                        if eligibility.compliance_result
                        else None
                    ),
                    compliance_result_id=(
                        eligibility.compliance_result.id
                        if eligibility.compliance_result
                        else None
                    ),
                    block_reason=eligibility.block_reason,
                    block_details=eligibility.block_details,
                )

            # Perform promotion (update repo tier)
            if self._repo_profile_updater:
                await self._repo_profile_updater(repo_id, target_tier)

            # Record transition
            transition = TierTransition(
                repo_id=repo_id,
                from_tier=current_tier,
                to_tier=target_tier,
                triggered_by=triggered_by,
                compliance_score=(
                    eligibility.compliance_result.score
                    if eligibility.compliance_result
                    else None
                ),
                compliance_result_id=(
                    eligibility.compliance_result.id
                    if eligibility.compliance_result
                    else None
                ),
                reason=f"Promoted by {triggered_by}",
                transitioned_at=now,
            )
            store_transition(transition)

            # Emit tier_changed signal
            if self._signal_emitter:
                await self._signal_emitter({
                    "event": "tier_changed",
                    "repo_id": str(repo_id),
                    "from_tier": current_tier.value,
                    "to_tier": target_tier.value,
                    "compliance_score": transition.compliance_score,
                    "triggered_by": triggered_by,
                    "timestamp": now.isoformat(),
                })

            logger.info(
                "Repo %s promoted from %s to %s by %s (compliance score: %s)",
                repo_id,
                current_tier.value,
                target_tier.value,
                triggered_by,
                transition.compliance_score,
            )

            return PromotionResult(
                success=True,
                repo_id=repo_id,
                from_tier=current_tier,
                to_tier=target_tier,
                triggered_by=triggered_by,
                timestamp=now,
                compliance_score=transition.compliance_score,
                compliance_result_id=transition.compliance_result_id,
            )

    async def demote_tier(
        self,
        repo_id: UUID,
        target_tier: RepoTier,
        reason: str,
        triggered_by: str,
        current_tier: RepoTier,
    ) -> DemotionResult:
        """Demote a repo to a lower tier.

        Args:
            repo_id: Repository to demote.
            target_tier: Target tier (must be lower than current).
            reason: Reason for demotion.
            triggered_by: Who/what triggered the demotion.
            current_tier: Current tier of the repo.

        Returns:
            DemotionResult with success status.
        """
        with tracer.start_as_current_span("promotion.demote") as span:
            span.set_attribute("thestudio.repo_id", str(repo_id))
            span.set_attribute("thestudio.current_tier", current_tier.value)
            span.set_attribute("thestudio.target_tier", target_tier.value)

            now = datetime.now(UTC)

            # Validate demotion path
            valid_targets = VALID_DEMOTIONS.get(current_tier, [])
            if target_tier not in valid_targets:
                logger.warning(
                    "Invalid demotion path: %s -> %s",
                    current_tier.value,
                    target_tier.value,
                )
                return DemotionResult(
                    success=False,
                    repo_id=repo_id,
                    from_tier=current_tier,
                    to_tier=target_tier,
                    reason=(
                        f"Invalid demotion path. Valid targets: "
                        f"{[t.value for t in valid_targets]}"
                    ),
                    triggered_by=triggered_by,
                    timestamp=now,
                )

            # Perform demotion
            if self._repo_profile_updater:
                await self._repo_profile_updater(repo_id, target_tier)

            # Record transition
            transition = TierTransition(
                repo_id=repo_id,
                from_tier=current_tier,
                to_tier=target_tier,
                triggered_by=triggered_by,
                reason=reason,
                transitioned_at=now,
            )
            store_transition(transition)

            # Emit tier_changed signal
            if self._signal_emitter:
                await self._signal_emitter({
                    "event": "tier_changed",
                    "repo_id": str(repo_id),
                    "from_tier": current_tier.value,
                    "to_tier": target_tier.value,
                    "reason": reason,
                    "triggered_by": triggered_by,
                    "timestamp": now.isoformat(),
                })

            logger.info(
                "Repo %s demoted from %s to %s by %s: %s",
                repo_id,
                current_tier.value,
                target_tier.value,
                triggered_by,
                reason,
            )

            return DemotionResult(
                success=True,
                repo_id=repo_id,
                from_tier=current_tier,
                to_tier=target_tier,
                reason=reason,
                triggered_by=triggered_by,
                timestamp=now,
            )


# In-memory storage for tier transitions (will be replaced with database)
_tier_transitions: list[TierTransition] = []


def store_transition(transition: TierTransition) -> None:
    """Store a tier transition (in-memory stub)."""
    _tier_transitions.append(transition)


def get_transitions(repo_id: UUID) -> list[TierTransition]:
    """Get all transitions for a repo (in-memory stub)."""
    return [t for t in _tier_transitions if t.repo_id == repo_id]


def get_latest_transition(repo_id: UUID) -> TierTransition | None:
    """Get the latest transition for a repo (in-memory stub)."""
    transitions = get_transitions(repo_id)
    return transitions[-1] if transitions else None


def clear() -> None:
    """Clear all stored transitions (for testing)."""
    _tier_transitions.clear()
