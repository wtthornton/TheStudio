"""Outcome Ingestor — consumes verification + QA signals, normalizes, and produces indicators.

Full implementation (Story 2.2, 2.3) with:
- Normalization by Complexity Index
- Attribution via provenance
- Indicator production for Reputation Engine
- Quarantine + dead-letter + replay (Story 2.3)

Architecture reference: thestudioarc/12-outcome-ingestor.md
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_TASKPACKET_ID,
    SPAN_OUTCOME_INGEST,
)
from src.observability.tracing import get_tracer
from src.outcome.dead_letter import (
    DeadLetterStore,
    FailureTracker,
    get_dead_letter_store,
    get_failure_tracker,
)
from src.outcome.models import (
    DefectCategory,
    DefectSeverity,
    OutcomeSignal,
    OutcomeType,
    QuarantinedEvent,
    QuarantinedSignal,
    QuarantineReason,
    ReputationIndicator,
    SignalEvent,
)
from src.outcome.quarantine import QuarantineStore, get_quarantine_store

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.outcome")


# In-memory stores (stub — replaced by DB in Phase 2)
_signals: list[OutcomeSignal] = []
_quarantined: list[QuarantinedSignal] = []
_indicators: list[ReputationIndicator] = []


def get_signals() -> list[OutcomeSignal]:
    """Return all persisted signals (for analytics queries)."""
    return list(_signals)


def get_quarantined() -> list[QuarantinedSignal]:
    """Return all quarantined signals (for operator review, legacy API)."""
    return list(_quarantined)


def get_quarantined_events() -> list[QuarantinedEvent]:
    """Return all quarantined events from the QuarantineStore."""
    store = get_quarantine_store()
    return store.list_quarantined(include_replayed=True)


def get_indicators() -> list[ReputationIndicator]:
    """Return all produced reputation indicators."""
    return list(_indicators)


def clear() -> None:
    """Clear all stores (for testing)."""
    _signals.clear()
    _quarantined.clear()
    _indicators.clear()

    # Also clear new stores
    from src.outcome.dead_letter import clear as clear_dead_letter
    from src.outcome.quarantine import clear as clear_quarantine

    clear_quarantine()
    clear_dead_letter()


def _compute_payload_hash(payload: dict[str, Any]) -> str:
    """Compute a deterministic hash of a payload for failure tracking."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


# Normalization multipliers by complexity band
# High complexity failures are weighted less negatively; successes more positively
COMPLEXITY_MULTIPLIERS = {
    "low": {"success": 0.8, "failure": 1.2},     # Easy tasks: failures hurt more
    "medium": {"success": 1.0, "failure": 1.0},  # Standard weight
    "high": {"success": 1.2, "failure": 0.8},    # Hard tasks: successes count more
}

# Base weights for outcome types
BASE_WEIGHTS = {
    OutcomeType.SUCCESS: 1.0,
    OutcomeType.FAILURE: -1.0,
    OutcomeType.LOOPBACK: -0.5,
}

# Signal event to outcome type mapping
EVENT_TO_OUTCOME = {
    SignalEvent.VERIFICATION_PASSED: OutcomeType.SUCCESS,
    SignalEvent.VERIFICATION_FAILED: OutcomeType.LOOPBACK,
    SignalEvent.VERIFICATION_EXHAUSTED: OutcomeType.FAILURE,
    SignalEvent.QA_PASSED: OutcomeType.SUCCESS,
    SignalEvent.QA_DEFECT: OutcomeType.FAILURE,
    SignalEvent.QA_REWORK: OutcomeType.LOOPBACK,
}


def _normalize_weight(
    outcome_type: OutcomeType,
    complexity_band: str,
    provenance_complete: bool,
) -> tuple[float, float]:
    """Compute normalized weight from outcome type and complexity.

    Returns (normalized_weight, raw_weight).

    Normalization rules (per docs/architecture/complexity-index-v1.md):
    - High complexity: failures weighted less negatively, successes more positively
    - Low complexity: failures hurt more, successes count less
    - Missing provenance: reduce weight by 50%
    """
    raw_weight = BASE_WEIGHTS[outcome_type]

    multipliers = COMPLEXITY_MULTIPLIERS.get(complexity_band, COMPLEXITY_MULTIPLIERS["medium"])
    multiplier_key = "success" if raw_weight >= 0 else "failure"

    normalized = raw_weight * multipliers[multiplier_key]

    # Reduce weight if provenance is incomplete (per 06-reputation-engine.md)
    if not provenance_complete:
        normalized *= 0.5

    return (round(normalized, 2), raw_weight)


def _build_context_key(repo: str, risk_flags: dict[str, bool], complexity_band: str) -> str:
    """Build context key for reputation storage.

    Format: "{repo}:{risk_class}:{complexity_band}"
    Risk class is the primary active risk flag or "general".
    """
    # Determine primary risk class
    active_risks = [k.replace("risk_", "") for k, v in risk_flags.items() if v]
    risk_class = active_risks[0] if active_risks else "general"

    return f"{repo}:{risk_class}:{complexity_band}"


def _should_attribute_to_expert(
    outcome_type: OutcomeType,
    defect_category: DefectCategory | None,
) -> bool:
    """Determine if this outcome should affect expert reputation.

    Attribution rules (per 06-reputation-engine.md):
    - intent_gap defects do NOT penalize experts (intent quality issue)
    - Success outcomes DO credit experts
    - implementation_bug and regression MAY penalize experts
    """
    if outcome_type == OutcomeType.SUCCESS:
        return True

    if defect_category == DefectCategory.INTENT_GAP:
        return False  # Intent gap is not expert's fault

    return True  # Other failures may be attributed


async def ingest_signal(
    raw_payload: dict[str, Any],
    taskpacket_exists_fn: Any = None,
    get_taskpacket_fn: Any = None,
    get_provenance_fn: Any = None,
    repo_exists_fn: Any = None,
    quarantine_store: QuarantineStore | None = None,
    dead_letter_store: DeadLetterStore | None = None,
    failure_tracker: FailureTracker | None = None,
) -> OutcomeSignal | QuarantinedSignal:
    """Ingest a signal payload from JetStream.

    Validates the payload, correlates to a TaskPacket, normalizes by complexity,
    attributes to experts via provenance, and produces ReputationIndicators.

    Quarantine rules (per thestudioarc/12-outcome-ingestor.md lines 87-93):
    - missing correlation_id or TaskPacket id
    - unknown TaskPacket
    - unknown repo id
    - invalid category or severity values
    - duplicated event with conflicting payload (idempotency conflict)

    Args:
        raw_payload: The raw JSON payload from JetStream.
        taskpacket_exists_fn: Async callable(UUID) -> bool for existence check.
        get_taskpacket_fn: Async callable(UUID) -> TaskPacketRead for full data.
        get_provenance_fn: Async callable(UUID) -> ProvenanceRecord | None.
        repo_exists_fn: Async callable(str) -> bool for repo existence check.
        quarantine_store: Optional QuarantineStore (uses global if not provided).
        dead_letter_store: Optional DeadLetterStore (uses global if not provided).
        failure_tracker: Optional FailureTracker (uses global if not provided).

    Returns:
        OutcomeSignal if valid, QuarantinedSignal if quarantined.
    """
    q_store = quarantine_store or get_quarantine_store()
    dl_store = dead_letter_store or get_dead_letter_store()
    f_tracker = failure_tracker or get_failure_tracker()

    with tracer.start_as_current_span(SPAN_OUTCOME_INGEST) as span:
        now = datetime.now(UTC)

        # Track failures for dead-letter eligibility
        payload_hash = _compute_payload_hash(raw_payload)

        # Extract repo_id for categorization
        repo_id = raw_payload.get("repo_id")
        event_str = raw_payload.get("event", "")

        # Validate correlation_id present
        correlation_id_str = raw_payload.get("correlation_id")
        if not correlation_id_str:
            q_store.quarantine(
                event_payload=raw_payload,
                reason=QuarantineReason.MISSING_CORRELATION_ID,
                repo_id=repo_id,
                category=event_str or "unknown",
            )
            quarantined = QuarantinedSignal(
                raw_payload=raw_payload,
                reason=QuarantineReason.MISSING_CORRELATION_ID,
                timestamp=now,
            )
            _quarantined.append(quarantined)
            logger.warning("Quarantined signal: missing correlation_id")
            return quarantined

        # Parse correlation_id
        try:
            correlation_id = UUID(str(correlation_id_str))
        except ValueError:
            q_store.quarantine(
                event_payload=raw_payload,
                reason=QuarantineReason.MISSING_CORRELATION_ID,
                repo_id=repo_id,
                category=event_str or "unknown",
            )
            quarantined = QuarantinedSignal(
                raw_payload=raw_payload,
                reason=QuarantineReason.MISSING_CORRELATION_ID,
                timestamp=now,
            )
            _quarantined.append(quarantined)
            logger.warning("Quarantined signal: invalid correlation_id format")
            return quarantined

        span.set_attribute(ATTR_CORRELATION_ID, str(correlation_id))

        # Validate event type
        try:
            event = SignalEvent(event_str)
        except ValueError:
            # Check if this should go to dead-letter
            attempt_count = f_tracker.record_failure(payload_hash)
            if f_tracker.should_dead_letter(payload_hash):
                dl_store.add_dead_letter(
                    raw_payload=json.dumps(raw_payload).encode(),
                    failure_reason=f"Invalid event type: {event_str}",
                    attempt_count=attempt_count,
                )
                f_tracker.clear_failures(payload_hash)
                logger.warning(
                    "Dead-lettered signal: invalid event after %d attempts", attempt_count,
                )
            else:
                q_store.quarantine(
                    event_payload=raw_payload,
                    reason=QuarantineReason.INVALID_EVENT,
                    repo_id=repo_id,
                    category=event_str or "unknown",
                )

            quarantined = QuarantinedSignal(
                raw_payload=raw_payload,
                reason=QuarantineReason.INVALID_EVENT,
                timestamp=now,
            )
            _quarantined.append(quarantined)
            logger.warning("Quarantined signal: invalid event type '%s'", event_str)
            return quarantined

        # Parse taskpacket_id
        taskpacket_id_str = raw_payload.get("taskpacket_id")
        if not taskpacket_id_str:
            q_store.quarantine(
                event_payload=raw_payload,
                reason=QuarantineReason.UNKNOWN_TASKPACKET,
                repo_id=repo_id,
                category=event.value,
            )
            quarantined = QuarantinedSignal(
                raw_payload=raw_payload,
                reason=QuarantineReason.UNKNOWN_TASKPACKET,
                timestamp=now,
            )
            _quarantined.append(quarantined)
            logger.warning("Quarantined signal: missing taskpacket_id")
            return quarantined

        try:
            taskpacket_id = UUID(str(taskpacket_id_str))
        except ValueError:
            q_store.quarantine(
                event_payload=raw_payload,
                reason=QuarantineReason.UNKNOWN_TASKPACKET,
                repo_id=repo_id,
                category=event.value,
            )
            quarantined = QuarantinedSignal(
                raw_payload=raw_payload,
                reason=QuarantineReason.UNKNOWN_TASKPACKET,
                timestamp=now,
            )
            _quarantined.append(quarantined)
            logger.warning("Quarantined signal: invalid taskpacket_id format")
            return quarantined

        span.set_attribute(ATTR_TASKPACKET_ID, str(taskpacket_id))

        # Verify TaskPacket exists (if checker provided)
        if taskpacket_exists_fn is not None:
            exists = await taskpacket_exists_fn(taskpacket_id)
            if not exists:
                q_store.quarantine(
                    event_payload=raw_payload,
                    reason=QuarantineReason.UNKNOWN_TASKPACKET,
                    repo_id=repo_id,
                    category=event.value,
                )
                quarantined = QuarantinedSignal(
                    raw_payload=raw_payload,
                    reason=QuarantineReason.UNKNOWN_TASKPACKET,
                    timestamp=now,
                )
                _quarantined.append(quarantined)
                logger.warning(
                    "Quarantined signal: unknown TaskPacket %s", taskpacket_id,
                )
                return quarantined

        # Verify repo_id exists (if checker provided and repo_id present)
        if repo_exists_fn is not None and repo_id is not None:
            repo_exists = await repo_exists_fn(repo_id)
            if not repo_exists:
                q_store.quarantine(
                    event_payload=raw_payload,
                    reason=QuarantineReason.UNKNOWN_REPO,
                    repo_id=repo_id,
                    category=event.value,
                )
                quarantined = QuarantinedSignal(
                    raw_payload=raw_payload,
                    reason=QuarantineReason.UNKNOWN_REPO,
                    timestamp=now,
                )
                _quarantined.append(quarantined)
                logger.warning("Quarantined signal: unknown repo_id %s", repo_id)
                return quarantined

        # Parse timestamp from payload or use now
        timestamp_str = raw_payload.get("timestamp")
        if timestamp_str:
            try:
                signal_ts = datetime.fromisoformat(str(timestamp_str))
            except ValueError:
                signal_ts = now
        else:
            signal_ts = now

        # Idempotency: check for duplicate (same event + taskpacket + timestamp)
        for existing in _signals:
            if (
                existing.event == event
                and existing.taskpacket_id == taskpacket_id
                and existing.timestamp == signal_ts
            ):
                # Check for conflicting payload (idempotency conflict)
                if existing.payload != raw_payload:
                    q_store.quarantine(
                        event_payload=raw_payload,
                        reason=QuarantineReason.IDEMPOTENCY_CONFLICT,
                        repo_id=repo_id,
                        category=event.value,
                    )
                    quarantined = QuarantinedSignal(
                        raw_payload=raw_payload,
                        reason=QuarantineReason.IDEMPOTENCY_CONFLICT,
                        timestamp=now,
                    )
                    _quarantined.append(quarantined)
                    logger.warning(
                        "Quarantined signal: idempotency conflict for %s at %s",
                        event, signal_ts,
                    )
                    return quarantined

                logger.info(
                    "Duplicate signal ignored: %s for %s", event, taskpacket_id,
                )
                return existing

        # Parse defect category and severity for QA signals
        defect_category: DefectCategory | None = None
        defect_severity: DefectSeverity | None = None

        if event in (SignalEvent.QA_DEFECT, SignalEvent.QA_REWORK):
            category_str = raw_payload.get("defect_category")
            severity_str = raw_payload.get("defect_severity")

            if category_str:
                try:
                    defect_category = DefectCategory(category_str)
                except ValueError:
                    q_store.quarantine(
                        event_payload=raw_payload,
                        reason=QuarantineReason.INVALID_CATEGORY_SEVERITY,
                        repo_id=repo_id,
                        category=event.value,
                    )
                    quarantined = QuarantinedSignal(
                        raw_payload=raw_payload,
                        reason=QuarantineReason.INVALID_CATEGORY_SEVERITY,
                        timestamp=now,
                    )
                    _quarantined.append(quarantined)
                    logger.warning("Quarantined signal: invalid defect_category '%s'", category_str)
                    return quarantined

            if severity_str:
                try:
                    defect_severity = DefectSeverity(severity_str)
                except ValueError:
                    q_store.quarantine(
                        event_payload=raw_payload,
                        reason=QuarantineReason.INVALID_CATEGORY_SEVERITY,
                        repo_id=repo_id,
                        category=event.value,
                    )
                    quarantined = QuarantinedSignal(
                        raw_payload=raw_payload,
                        reason=QuarantineReason.INVALID_CATEGORY_SEVERITY,
                        timestamp=now,
                    )
                    _quarantined.append(quarantined)
                    logger.warning("Quarantined signal: invalid defect_severity '%s'", severity_str)
                    return quarantined

        # Clear failure tracker on successful processing
        f_tracker.clear_failures(payload_hash)

        # Persist signal
        signal = OutcomeSignal(
            event=event,
            taskpacket_id=taskpacket_id,
            correlation_id=correlation_id,
            timestamp=signal_ts,
            payload=raw_payload,
        )
        _signals.append(signal)

        logger.info(
            "Ingested signal %s for TaskPacket %s (correlation=%s)",
            event,
            taskpacket_id,
            correlation_id,
        )

        # Produce reputation indicators if we have the necessary data
        if get_taskpacket_fn and get_provenance_fn:
            await _produce_indicators(
                signal=signal,
                defect_category=defect_category,
                defect_severity=defect_severity,
                get_taskpacket_fn=get_taskpacket_fn,
                get_provenance_fn=get_provenance_fn,
            )

        return signal


async def _produce_indicators(
    signal: OutcomeSignal,
    defect_category: DefectCategory | None,
    defect_severity: DefectSeverity | None,
    get_taskpacket_fn: Any,
    get_provenance_fn: Any,
) -> list[ReputationIndicator]:
    """Produce ReputationIndicators for all attributed experts.

    Normalizes by complexity and applies attribution rules.
    """
    indicators: list[ReputationIndicator] = []

    # Get TaskPacket for complexity and repo info
    taskpacket = await get_taskpacket_fn(signal.taskpacket_id)
    if taskpacket is None:
        logger.warning("Cannot produce indicators: TaskPacket %s not found", signal.taskpacket_id)
        return indicators

    # Extract complexity info
    complexity_data = taskpacket.complexity_index or {}
    complexity_band = complexity_data.get("band", "medium")

    # Get provenance for expert attribution
    provenance = await get_provenance_fn(signal.taskpacket_id)
    provenance_complete = provenance is not None and bool(provenance.experts_consulted)

    # Determine outcome type
    outcome_type = EVENT_TO_OUTCOME.get(signal.event, OutcomeType.FAILURE)

    # Check attribution rules
    if not _should_attribute_to_expert(outcome_type, defect_category):
        logger.info(
            "Outcome not attributed to experts: %s with category %s",
            outcome_type, defect_category,
        )
        return indicators

    # Build context key
    risk_flags = taskpacket.risk_flags or {}
    context_key = _build_context_key(taskpacket.repo, risk_flags, complexity_band)

    # Compute normalized weight
    normalized_weight, raw_weight = _normalize_weight(
        outcome_type, complexity_band, provenance_complete,
    )

    # Create indicator for each expert in provenance
    if provenance and provenance.experts_consulted:
        for expert_data in provenance.experts_consulted:
            expert_id = UUID(str(expert_data.get("id", "00000000-0000-0000-0000-000000000000")))
            expert_version = int(expert_data.get("version", 1))

            indicator = ReputationIndicator(
                expert_id=expert_id,
                expert_version=expert_version,
                context_key=context_key,
                outcome_type=outcome_type,
                defect_category=defect_category,
                defect_severity=defect_severity,
                normalized_weight=normalized_weight,
                raw_weight=raw_weight,
                complexity_band=complexity_band,
                provenance_complete=True,
                taskpacket_id=signal.taskpacket_id,
                correlation_id=signal.correlation_id,
                timestamp=signal.timestamp,
            )
            indicators.append(indicator)
            _indicators.append(indicator)

            logger.info(
                "Produced indicator for expert %s: outcome=%s, weight=%.2f (normalized from %.2f)",
                expert_id, outcome_type, normalized_weight, raw_weight,
            )
    else:
        # No provenance — create a single indicator with reduced weight
        indicator = ReputationIndicator(
            expert_id=UUID("00000000-0000-0000-0000-000000000000"),  # Unknown expert
            expert_version=0,
            context_key=context_key,
            outcome_type=outcome_type,
            defect_category=defect_category,
            defect_severity=defect_severity,
            normalized_weight=normalized_weight,
            raw_weight=raw_weight,
            complexity_band=complexity_band,
            provenance_complete=False,
            taskpacket_id=signal.taskpacket_id,
            correlation_id=signal.correlation_id,
            timestamp=signal.timestamp,
        )
        indicators.append(indicator)
        _indicators.append(indicator)

        logger.info(
            "Produced indicator without provenance: outcome=%s, weight=%.2f",
            outcome_type, normalized_weight,
        )

    return indicators
