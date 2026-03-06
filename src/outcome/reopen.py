"""Reopen Event Processor — ingests and classifies reopen events.

Architecture reference: thestudioarc/12-outcome-ingestor.md lines 110-127

Reopen events are high-signal quality outcomes:
- Issue reopened after merge
- New issue referencing the PR for a regression
- Rollback PR linked to the original task

Classification:
- intent_gap: reopen within 7 days + same acceptance criteria failing
- implementation_bug: reopen within 7 days + new failure mode
- regression: reopen after 7 days + related feature broken
- governance_failure: reopen + compliance/review bypass detected
"""

import enum
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.outcome.models import OutcomeType, ReputationIndicator

logger = logging.getLogger(__name__)


class ReopenSource(enum.StrEnum):
    """Source types for reopen events."""

    ISSUE_REOPENED = "issue_reopened"
    REGRESSION_ISSUE = "regression_issue"
    ROLLBACK_PR = "rollback_pr"


class ReopenClassification(enum.StrEnum):
    """Classification of reopen events.

    Per thestudioarc/12-outcome-ingestor.md lines 120-122:
    - intent_gap: original AC was wrong/incomplete
    - implementation_bug: AC was correct but implementation was wrong
    - regression: previously working feature broke
    - governance_failure: compliance/review bypass detected
    """

    INTENT_GAP = "intent_gap"
    IMPLEMENTATION_BUG = "implementation_bug"
    REGRESSION = "regression"
    GOVERNANCE_FAILURE = "governance_failure"


class ReopenEvent(BaseModel):
    """Incoming reopen event from GitHub webhook."""

    event_id: UUID = Field(default_factory=uuid4)
    source: ReopenSource
    repo_id: str
    issue_number: int | None = None
    pr_number: int | None = None
    original_pr_number: int | None = None
    original_taskpacket_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    labels: list[str] = Field(default_factory=list)
    title: str = ""
    body: str = ""
    original_merge_timestamp: datetime | None = None
    has_compliance_bypass: bool = False
    ac_failing: list[str] = Field(default_factory=list)


class ReopenOutcome(BaseModel):
    """Result of processing a reopen event."""

    event_id: UUID
    source: ReopenSource
    classification: ReopenClassification
    taskpacket_id: UUID | None = None
    repo_id: str
    days_since_merge: float | None = None
    confidence: float = 1.0
    reason: str = ""
    indicator_produced: bool = False


# In-memory stores (replaced by DB in production)
_reopen_events: list[ReopenEvent] = []
_reopen_outcomes: list[ReopenOutcome] = []
_reopen_metrics: dict[str, dict[str, float]] = {}  # repo_id -> {metric: value}
_indicators_produced: list[ReputationIndicator] = []


def clear() -> None:
    """Clear all stores (for testing)."""
    _reopen_events.clear()
    _reopen_outcomes.clear()
    _reopen_metrics.clear()
    _indicators_produced.clear()


def get_reopen_events() -> list[ReopenEvent]:
    """Return all reopen events."""
    return list(_reopen_events)


def get_reopen_outcomes() -> list[ReopenOutcome]:
    """Return all reopen outcomes."""
    return list(_reopen_outcomes)


def get_reopen_indicators() -> list[ReputationIndicator]:
    """Return all reopen indicators produced."""
    return list(_indicators_produced)


# Configuration
RECENT_REOPEN_DAYS = 7  # Days threshold for "recent" vs "late" reopen
REOPEN_METRIC_WINDOW_DAYS = 30  # Rolling window for reopen rate


class ReopenEventProcessor:
    """Processes reopen events and produces reputation indicators.

    Per thestudioarc/12-outcome-ingestor.md lines 110-127:
    - Links reopen to original TaskPacket via issue/PR reference
    - Classifies reopen as intent_gap, implementation_bug, regression, governance_failure
    - Updates reopen rate metrics per repo, role+overlays, expert set
    """

    def __init__(
        self,
        get_taskpacket_by_pr_fn: Any = None,
        get_provenance_fn: Any = None,
        get_effective_role_fn: Any = None,
    ) -> None:
        """Initialize the processor.

        Args:
            get_taskpacket_by_pr_fn: Async callable(repo_id, pr_number) -> TaskPacket | None.
            get_provenance_fn: Async callable(taskpacket_id) -> ProvenanceRecord | None.
            get_effective_role_fn: Async callable(taskpacket_id) -> EffectiveRolePolicy | None.
        """
        self.get_taskpacket_by_pr_fn = get_taskpacket_by_pr_fn
        self.get_provenance_fn = get_provenance_fn
        self.get_effective_role_fn = get_effective_role_fn

    async def process_reopen(self, event: ReopenEvent) -> ReopenOutcome:
        """Process a reopen event and produce an outcome.

        Args:
            event: The ReopenEvent to process.

        Returns:
            ReopenOutcome with classification and attribution info.
        """
        _reopen_events.append(event)

        # Try to link to original TaskPacket
        taskpacket_id = event.original_taskpacket_id
        if taskpacket_id is None and self.get_taskpacket_by_pr_fn is not None:
            pr_num = event.original_pr_number or event.pr_number
            if pr_num is not None:
                taskpacket = await self.get_taskpacket_by_pr_fn(event.repo_id, pr_num)
                if taskpacket is not None:
                    taskpacket_id = taskpacket.id

        # Compute days since merge
        days_since_merge: float | None = None
        if event.original_merge_timestamp is not None:
            delta = event.timestamp - event.original_merge_timestamp
            days_since_merge = delta.total_seconds() / 86400

        # Classify the reopen
        classification, reason = self._classify(event, days_since_merge)

        outcome = ReopenOutcome(
            event_id=event.event_id,
            source=event.source,
            classification=classification,
            taskpacket_id=taskpacket_id,
            repo_id=event.repo_id,
            days_since_merge=days_since_merge,
            reason=reason,
        )

        _reopen_outcomes.append(outcome)

        # Update metrics
        self._update_metrics(event.repo_id, classification)

        # Produce indicator if we have TaskPacket linkage
        if taskpacket_id is not None:
            await self._produce_indicator(event, outcome)
            outcome = outcome.model_copy(update={"indicator_produced": True})

        logger.info(
            "Processed reopen event %s: source=%s, classification=%s, taskpacket=%s",
            event.event_id, event.source.value, classification.value, taskpacket_id,
        )

        return outcome

    def _classify(
        self,
        event: ReopenEvent,
        days_since_merge: float | None,
    ) -> tuple[ReopenClassification, str]:
        """Classify a reopen event.

        Classification logic per DoD:
        - Reopen within 7 days + same AC failing -> intent_gap
        - Reopen within 7 days + new failure mode -> implementation_bug
        - Reopen after 7 days + related feature broken -> regression
        - Reopen + compliance/review bypass detected -> governance_failure
        """
        # Governance failure takes precedence
        if event.has_compliance_bypass:
            return (
                ReopenClassification.GOVERNANCE_FAILURE,
                "Compliance or review bypass detected",
            )

        # Rollback PR is always a regression
        if event.source == ReopenSource.ROLLBACK_PR:
            return (
                ReopenClassification.REGRESSION,
                "Rollback PR indicates regression",
            )

        # New issue with regression label
        if event.source == ReopenSource.REGRESSION_ISSUE:
            if "regression" in [label.lower() for label in event.labels]:
                return (
                    ReopenClassification.REGRESSION,
                    "Issue labeled as regression",
                )

        # Time-based classification
        is_recent = (
            days_since_merge is not None and days_since_merge <= RECENT_REOPEN_DAYS
        )

        if is_recent:
            # Recent reopen — check AC
            if event.ac_failing:
                return (
                    ReopenClassification.INTENT_GAP,
                    f"Reopen within {RECENT_REOPEN_DAYS} days with AC failing: {event.ac_failing}",
                )
            else:
                return (
                    ReopenClassification.IMPLEMENTATION_BUG,
                    f"Reopen within {RECENT_REOPEN_DAYS} days with new failure mode",
                )
        else:
            # Late reopen — assume regression
            return (
                ReopenClassification.REGRESSION,
                f"Reopen after {RECENT_REOPEN_DAYS} days indicates regression",
            )

    def _update_metrics(self, repo_id: str, classification: ReopenClassification) -> None:
        """Update reopen rate metrics for a repo.

        Tracks reopen rate per repo (rolling 30-day window).
        """
        if repo_id not in _reopen_metrics:
            _reopen_metrics[repo_id] = {
                "total_reopens": 0,
                "intent_gap_count": 0,
                "implementation_bug_count": 0,
                "regression_count": 0,
                "governance_failure_count": 0,
            }

        metrics = _reopen_metrics[repo_id]
        metrics["total_reopens"] += 1
        metrics[f"{classification.value}_count"] += 1

    async def _produce_indicator(
        self,
        event: ReopenEvent,
        outcome: ReopenOutcome,
    ) -> None:
        """Produce a ReputationIndicator for a reopen event.

        Per thestudioarc/12-outcome-ingestor.md lines 124-127:
        - intent_gap reopen impacts intent quality metrics (not expert weights)
        - regression reopen impacts execution and expert guidance per provenance
        """
        if outcome.taskpacket_id is None:
            return

        # Get provenance for attribution
        provenance = None
        if self.get_provenance_fn is not None:
            provenance = await self.get_provenance_fn(outcome.taskpacket_id)

        # Determine if this should affect expert weights
        should_attribute = outcome.classification != ReopenClassification.INTENT_GAP

        # Get effective role for context key
        role_key = "general"
        if self.get_effective_role_fn is not None:
            role_policy = await self.get_effective_role_fn(outcome.taskpacket_id)
            if role_policy is not None:
                role_key = getattr(role_policy, "base_role", "general")

        # Build context key
        context_key = f"{event.repo_id}:{role_key}:reopen"

        # Weight based on classification
        weight_map = {
            ReopenClassification.INTENT_GAP: 0.0,  # Does not affect experts
            ReopenClassification.IMPLEMENTATION_BUG: -0.8,
            ReopenClassification.REGRESSION: -1.0,
            ReopenClassification.GOVERNANCE_FAILURE: -1.0,
        }
        raw_weight = weight_map[outcome.classification]

        # Create indicators for each expert if provenance available and should attribute
        experts_consulted: list[dict[str, Any]] = []
        if provenance is not None and hasattr(provenance, "experts_consulted"):
            experts_consulted = provenance.experts_consulted or []

        if should_attribute and experts_consulted:
            for expert_data in experts_consulted:
                expert_id = UUID(str(expert_data.get("id", "00000000-0000-0000-0000-000000000000")))
                expert_version = int(expert_data.get("version", 1))

                indicator = ReputationIndicator(
                    expert_id=expert_id,
                    expert_version=expert_version,
                    context_key=context_key,
                    outcome_type=OutcomeType.FAILURE,  # Reopen is always a failure
                    defect_category=None,
                    defect_severity=None,
                    normalized_weight=raw_weight,
                    raw_weight=raw_weight,
                    complexity_band="medium",  # Reopens don't have complexity context
                    provenance_complete=True,
                    taskpacket_id=outcome.taskpacket_id,
                    correlation_id=event.event_id,
                    timestamp=event.timestamp,
                )
                _indicators_produced.append(indicator)
                logger.info(
                    "Produced reopen indicator for expert %s: classification=%s, weight=%.2f",
                    expert_id, outcome.classification.value, raw_weight,
                )
        else:
            # No attribution or intent_gap — still log the event
            indicator = ReputationIndicator(
                expert_id=UUID("00000000-0000-0000-0000-000000000000"),
                expert_version=0,
                context_key=context_key,
                outcome_type=OutcomeType.FAILURE,
                defect_category=None,
                defect_severity=None,
                normalized_weight=0.0,  # No weight impact
                raw_weight=raw_weight,
                complexity_band="medium",
                provenance_complete=False,
                taskpacket_id=outcome.taskpacket_id,
                correlation_id=event.event_id,
                timestamp=event.timestamp,
            )
            _indicators_produced.append(indicator)
            logger.info(
                "Produced reopen indicator (no attribution): classification=%s",
                outcome.classification.value,
            )

    def get_reopen_rate(self, repo_id: str) -> float:
        """Get the reopen rate for a repo (total reopens / window).

        This is a simplified metric — production would compute against
        total merged PRs in the window.
        """
        metrics = _reopen_metrics.get(repo_id)
        if metrics is None:
            return 0.0
        return metrics.get("total_reopens", 0)

    def get_metrics_by_repo(self, repo_id: str) -> dict[str, float]:
        """Get all reopen metrics for a repo."""
        return _reopen_metrics.get(repo_id, {})

    def get_metrics_summary(self) -> dict[str, dict[str, float]]:
        """Get metrics summary for all repos."""
        return dict(_reopen_metrics)


# Global processor instance
_processor: ReopenEventProcessor | None = None


def get_reopen_processor() -> ReopenEventProcessor:
    """Get or create the global ReopenEventProcessor instance."""
    global _processor
    if _processor is None:
        _processor = ReopenEventProcessor()
    return _processor
