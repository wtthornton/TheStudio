"""Quarantine store — persists and manages quarantined signals for operator review.

Architecture reference: thestudioarc/12-outcome-ingestor.md lines 83-105

Quarantine rules (must quarantine):
- missing correlation_id or TaskPacket id
- unknown TaskPacket
- unknown repo id
- invalid category or severity values
- duplicated event with conflicting payload (idempotency conflict)

Quarantined events can be corrected by an operator and replayed.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.outcome.models import QuarantinedEvent, QuarantineReason

logger = logging.getLogger(__name__)


# In-memory store (replaced by DB in production via repository pattern)
_quarantined: dict[UUID, QuarantinedEvent] = {}


def clear() -> None:
    """Clear all quarantined events (for testing)."""
    _quarantined.clear()


class QuarantineStore:
    """Manages quarantined signal events.

    Provides CRUD operations for quarantined events and replay tracking.
    In production, this is backed by the quarantined_events table.
    """

    def __init__(self) -> None:
        """Initialize the quarantine store."""

    def quarantine(
        self,
        event_payload: dict[str, Any],
        reason: QuarantineReason,
        repo_id: str | None = None,
        category: str | None = None,
    ) -> UUID:
        """Quarantine an event for operator review.

        Args:
            event_payload: The raw event payload that failed validation.
            reason: The QuarantineReason explaining why it was quarantined.
            repo_id: Optional repo_id extracted from the payload (may be None if unknown).
            category: Optional category for filtering (e.g., signal event type).

        Returns:
            The quarantine_id for the quarantined event.
        """
        quarantine_id = uuid4()
        now = datetime.now(UTC)

        event = QuarantinedEvent(
            quarantine_id=quarantine_id,
            event_payload=event_payload,
            reason=reason,
            repo_id=repo_id,
            category=category,
            created_at=now,
        )

        _quarantined[quarantine_id] = event

        logger.info(
            "Quarantined event %s: reason=%s, repo=%s, category=%s",
            quarantine_id, reason.value, repo_id, category,
        )

        return quarantine_id

    def list_quarantined(
        self,
        repo_id: str | None = None,
        category: str | None = None,
        reason: QuarantineReason | None = None,
        include_replayed: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[QuarantinedEvent]:
        """List quarantined events with optional filtering.

        Args:
            repo_id: Filter by repo_id.
            category: Filter by category.
            reason: Filter by quarantine reason.
            include_replayed: If False, exclude events that have been replayed.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of QuarantinedEvent matching the filters.
        """
        results: list[QuarantinedEvent] = []

        for event in _quarantined.values():
            if repo_id is not None and event.repo_id != repo_id:
                continue
            if category is not None and event.category != category:
                continue
            if reason is not None and event.reason != reason:
                continue
            if not include_replayed and event.replayed_at is not None:
                continue
            results.append(event)

        # Sort by created_at descending (newest first)
        results.sort(key=lambda e: e.created_at, reverse=True)

        return results[offset : offset + limit]

    def get_quarantined(self, quarantine_id: UUID) -> QuarantinedEvent | None:
        """Get a quarantined event by ID.

        Args:
            quarantine_id: The UUID of the quarantined event.

        Returns:
            The QuarantinedEvent if found, None otherwise.
        """
        return _quarantined.get(quarantine_id)

    def mark_corrected(
        self,
        quarantine_id: UUID,
        corrected_payload: dict[str, Any],
    ) -> bool:
        """Mark a quarantined event as corrected with a new payload.

        The corrected payload will be used during replay.

        Args:
            quarantine_id: The UUID of the quarantined event.
            corrected_payload: The corrected event payload.

        Returns:
            True if the event was found and updated, False otherwise.
        """
        event = _quarantined.get(quarantine_id)
        if event is None:
            logger.warning("Cannot correct: quarantine_id %s not found", quarantine_id)
            return False

        if event.replayed_at is not None:
            logger.warning("Cannot correct: quarantine_id %s already replayed", quarantine_id)
            return False

        now = datetime.now(UTC)
        updated = event.model_copy(update={
            "corrected_at": now,
            "corrected_payload": corrected_payload,
        })
        _quarantined[quarantine_id] = updated

        logger.info("Marked quarantine_id %s as corrected", quarantine_id)
        return True

    def mark_replayed(self, quarantine_id: UUID) -> bool:
        """Mark a quarantined event as replayed.

        Args:
            quarantine_id: The UUID of the quarantined event.

        Returns:
            True if the event was found and updated, False otherwise.
        """
        event = _quarantined.get(quarantine_id)
        if event is None:
            logger.warning("Cannot mark replayed: quarantine_id %s not found", quarantine_id)
            return False

        now = datetime.now(UTC)
        updated = event.model_copy(update={"replayed_at": now})
        _quarantined[quarantine_id] = updated

        logger.info("Marked quarantine_id %s as replayed", quarantine_id)
        return True

    def count_by_reason(self, repo_id: str | None = None) -> dict[QuarantineReason, int]:
        """Count quarantined events by reason.

        Args:
            repo_id: Optional filter by repo_id.

        Returns:
            Dict mapping QuarantineReason to count.
        """
        counts: dict[QuarantineReason, int] = {}

        for event in _quarantined.values():
            if repo_id is not None and event.repo_id != repo_id:
                continue
            if event.replayed_at is not None:
                continue  # Don't count replayed events

            counts[event.reason] = counts.get(event.reason, 0) + 1

        return counts

    def count_by_category(self, repo_id: str | None = None) -> dict[str, int]:
        """Count quarantined events by category.

        Args:
            repo_id: Optional filter by repo_id.

        Returns:
            Dict mapping category to count.
        """
        counts: dict[str, int] = {}

        for event in _quarantined.values():
            if repo_id is not None and event.repo_id != repo_id:
                continue
            if event.replayed_at is not None:
                continue  # Don't count replayed events

            cat = event.category or "unknown"
            counts[cat] = counts.get(cat, 0) + 1

        return counts

    def delete(self, quarantine_id: UUID) -> bool:
        """Delete a quarantined event.

        Args:
            quarantine_id: The UUID of the quarantined event.

        Returns:
            True if the event was found and deleted, False otherwise.
        """
        if quarantine_id in _quarantined:
            del _quarantined[quarantine_id]
            logger.info("Deleted quarantine_id %s", quarantine_id)
            return True
        return False


# Global store instance
_store: QuarantineStore | None = None


def get_quarantine_store() -> QuarantineStore:
    """Get or create the global QuarantineStore instance."""
    global _store
    if _store is None:
        _store = QuarantineStore()
    return _store
