"""Dead-letter store — persists events that failed parsing/validation after max attempts.

Architecture reference: thestudioarc/12-outcome-ingestor.md lines 94-96

Dead-letter rules:
- events that cannot be parsed or validated after N attempts are moved to dead-letter
- stores raw payload and failure reason for debugging

Dead-letter events are terminal — they cannot be replayed automatically.
Manual investigation is required to understand why they failed.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.outcome.models import DeadLetterEvent

logger = logging.getLogger(__name__)


# Default max attempts before moving to dead-letter
DEFAULT_MAX_ATTEMPTS = 3

# In-memory store (replaced by DB in production via repository pattern)
_dead_letters: dict[UUID, DeadLetterEvent] = {}


def clear() -> None:
    """Clear all dead-letter events (for testing)."""
    _dead_letters.clear()


class DeadLetterStore:
    """Manages dead-letter events for signals that cannot be processed.

    Dead-letter events are signals that failed parsing or validation after
    multiple attempts. They preserve the raw payload and failure reason
    for manual debugging.
    """

    def __init__(self, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> None:
        """Initialize the dead-letter store.

        Args:
            max_attempts: Number of attempts before moving to dead-letter.
        """
        self.max_attempts = max_attempts

    def add_dead_letter(
        self,
        raw_payload: bytes,
        failure_reason: str,
        attempt_count: int,
    ) -> UUID:
        """Add an event to the dead-letter store.

        Args:
            raw_payload: The raw bytes of the event that failed.
            failure_reason: Description of why the event failed.
            attempt_count: Number of processing attempts made.

        Returns:
            The UUID of the dead-letter event.
        """
        event_id = uuid4()
        now = datetime.now(UTC)

        event = DeadLetterEvent(
            id=event_id,
            raw_payload=raw_payload,
            failure_reason=failure_reason,
            attempt_count=attempt_count,
            created_at=now,
        )

        _dead_letters[event_id] = event

        logger.warning(
            "Dead-lettered event %s: reason=%s, attempts=%d",
            event_id, failure_reason, attempt_count,
        )

        return event_id

    def list_dead_letters(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeadLetterEvent]:
        """List dead-letter events.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of DeadLetterEvent sorted by created_at descending.
        """
        results = list(_dead_letters.values())
        results.sort(key=lambda e: e.created_at, reverse=True)
        return results[offset : offset + limit]

    def get_dead_letter(self, event_id: UUID) -> DeadLetterEvent | None:
        """Get a dead-letter event by ID.

        Args:
            event_id: The UUID of the dead-letter event.

        Returns:
            The DeadLetterEvent if found, None otherwise.
        """
        return _dead_letters.get(event_id)

    def count(self) -> int:
        """Count total dead-letter events.

        Returns:
            Number of dead-letter events.
        """
        return len(_dead_letters)

    def delete(self, event_id: UUID) -> bool:
        """Delete a dead-letter event (after manual resolution).

        Args:
            event_id: The UUID of the dead-letter event.

        Returns:
            True if the event was found and deleted, False otherwise.
        """
        if event_id in _dead_letters:
            del _dead_letters[event_id]
            logger.info("Deleted dead-letter event %s", event_id)
            return True
        return False


class FailureTracker:
    """Tracks processing failures for events to determine dead-letter eligibility.

    Each event is identified by a hash of its payload. When an event fails
    processing, the failure count is incremented. When the count reaches
    max_attempts, the event should be moved to dead-letter.
    """

    def __init__(self, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> None:
        """Initialize the failure tracker.

        Args:
            max_attempts: Number of attempts before recommending dead-letter.
        """
        self.max_attempts = max_attempts
        self._failures: dict[str, int] = {}  # payload_hash -> attempt_count

    def record_failure(self, payload_hash: str) -> int:
        """Record a processing failure for an event.

        Args:
            payload_hash: Hash of the event payload for identification.

        Returns:
            The current attempt count after this failure.
        """
        current = self._failures.get(payload_hash, 0)
        self._failures[payload_hash] = current + 1
        return current + 1

    def get_attempt_count(self, payload_hash: str) -> int:
        """Get the current attempt count for an event.

        Args:
            payload_hash: Hash of the event payload.

        Returns:
            The current attempt count (0 if never failed).
        """
        return self._failures.get(payload_hash, 0)

    def should_dead_letter(self, payload_hash: str) -> bool:
        """Check if an event should be moved to dead-letter.

        Args:
            payload_hash: Hash of the event payload.

        Returns:
            True if attempt count >= max_attempts.
        """
        return self._failures.get(payload_hash, 0) >= self.max_attempts

    def clear_failures(self, payload_hash: str) -> None:
        """Clear failure count for an event (e.g., after successful processing).

        Args:
            payload_hash: Hash of the event payload.
        """
        self._failures.pop(payload_hash, None)

    def clear_all(self) -> None:
        """Clear all failure tracking (for testing)."""
        self._failures.clear()


# Global store instance
_store: DeadLetterStore | None = None
_tracker: FailureTracker | None = None


def get_dead_letter_store() -> DeadLetterStore:
    """Get or create the global DeadLetterStore instance."""
    global _store
    if _store is None:
        _store = DeadLetterStore()
    return _store


def get_failure_tracker() -> FailureTracker:
    """Get or create the global FailureTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = FailureTracker()
    return _tracker
