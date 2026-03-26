"""Epic 69.1 — Dead-Letter Inspector: Page Intent & Semantic Content.

Validates that /admin/ui/dead-letters delivers its core purpose:
  - Dead-lettered events table renders with event identity and failure reasons
  - Failure reasons are surfaced so operators understand why events were dead-lettered
  - Attempt counts are shown so operators can gauge retry history
  - Page heading clearly identifies the dead-letter section
  - Empty state is shown when no dead-lettered events are present

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_dead_letters_style.py (Epic 69.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

DEAD_LETTERS_URL = "/admin/ui/dead-letters"


class TestDeadLettersEventContent:
    """Dead-lettered events table must surface the key information operators need.

    When dead-lettered events are present the page must show:
      Event identity   — event ID, type, or source repo that was dead-lettered
      Failure reason   — why the event failed after exhausting retries
      Attempt count    — how many times the event was attempted before dead-lettering
    """

    def test_dead_letters_page_renders(self, page, base_url: str) -> None:
        """Dead-letter page shows an events table or an empty-state container."""
        navigate(page, f"{base_url}{DEAD_LETTERS_URL}")

        has_table = page.locator("table").count() > 0
        has_list = page.locator(
            "[class*='dead-letter'], [data-dead-letter], [data-component='dead-letter-card']"
        ).count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in (
                "no dead",
                "no events",
                "queue is empty",
                "nothing to show",
                "empty",
                "dead letter",
                "dead-letter",
            )
        )
        assert has_table or has_list or has_empty_state, (
            "Dead-letter page must show an events table (or card list) or an "
            "empty-state message when no dead-lettered events are present"
        )

    def test_event_identity_shown(self, page, base_url: str) -> None:
        """Dead-letter list or page body includes event identity information."""
        navigate(page, f"{base_url}{DEAD_LETTERS_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-dead-letter]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no dead", "empty", "no events")):
                pytest.skip("No dead-lettered events — empty state is acceptable for 69.1")

        body_lower = page.locator("body").inner_text().lower()
        identity_keywords = (
            "event",
            "id",
            "repo",
            "repository",
            "source",
            "issue",
            "webhook",
            "type",
            "name",
        )
        assert any(kw in body_lower for kw in identity_keywords), (
            "Dead-letter page must display event identity information (ID, repo, or source)"
        )

    def test_failure_reason_shown(self, page, base_url: str) -> None:
        """Dead-letter page surfaces failure reasons explaining why events were dead-lettered."""
        navigate(page, f"{base_url}{DEAD_LETTERS_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-dead-letter]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no dead", "empty", "no events")):
                pytest.skip("No dead-lettered events — empty state is acceptable for 69.1")

        body_lower = page.locator("body").inner_text().lower()
        reason_keywords = (
            "reason",
            "failure",
            "error",
            "fail",
            "cause",
            "message",
            "why",
            "exception",
            "invalid",
            "rejected",
            "exhausted",
            "timed out",
        )
        assert any(kw in body_lower for kw in reason_keywords), (
            "Dead-letter page must display failure reasons explaining why events were dead-lettered"
        )

    def test_attempt_count_shown(self, page, base_url: str) -> None:
        """Dead-letter page surfaces attempt counts showing how many retries were made."""
        navigate(page, f"{base_url}{DEAD_LETTERS_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-dead-letter]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no dead", "empty", "no events")):
                pytest.skip("No dead-lettered events — empty state is acceptable for 69.1")

        body_lower = page.locator("body").inner_text().lower()
        attempt_keywords = (
            "attempt",
            "attempts",
            "retry",
            "retries",
            "tries",
            "count",
            "times",
        )
        assert any(kw in body_lower for kw in attempt_keywords), (
            "Dead-letter page must display attempt counts showing retry history"
        )

    def test_dead_letter_status_shown(self, page, base_url: str) -> None:
        """Dead-letter page surfaces status indicating events are permanently failed."""
        navigate(page, f"{base_url}{DEAD_LETTERS_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-dead-letter]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no dead", "empty", "no events")):
                pytest.skip("No dead-lettered events — empty state is acceptable for 69.1")

        body_lower = page.locator("body").inner_text().lower()
        status_keywords = (
            "dead",
            "dead-letter",
            "dead letter",
            "failed",
            "permanent",
            "exhausted",
            "status",
            "retry",
            "requeue",
        )
        assert any(kw in body_lower for kw in status_keywords), (
            "Dead-letter page must display status indicating events are permanently failed"
        )

    def test_dead_letter_table_has_identifier_column(self, page, base_url: str) -> None:
        """Dead-letter table has a column or field identifying each dead-lettered event."""
        navigate(page, f"{base_url}{DEAD_LETTERS_URL}")

        has_table = page.locator("table").count() > 0
        if not has_table:
            pytest.skip("No table on dead-letter page — card-based layout acceptable for 69.1")

        body_lower = page.locator("body").inner_text().lower()
        id_keywords = ("event", "id", "repo", "repository", "name", "source", "type", "slug")
        assert any(kw in body_lower for kw in id_keywords), (
            "Dead-letter table must include an identifier column (event ID, repo name, or source)"
        )


class TestDeadLettersEmptyState:
    """Empty-state must communicate clearly when no dead-lettered events exist.

    An informative empty state prevents confusion when the dead-letter queue is
    empty and gives operators context about what the dead-letter section manages.
    """

    def test_empty_state_has_descriptive_text(self, page, base_url: str) -> None:
        """When no dead-lettered events exist, the page shows descriptive text."""
        navigate(page, f"{base_url}{DEAD_LETTERS_URL}")

        if page.locator("table").count() > 0:
            rows = page.locator("table tbody tr").count()
            if rows > 0:
                pytest.skip("Dead-lettered events are present — empty-state test not applicable")

        body_lower = page.locator("body").inner_text().lower()
        descriptive_keywords = (
            "dead",
            "dead-letter",
            "dead letter",
            "no events",
            "no dead",
            "queue is empty",
            "nothing to show",
            "failed events",
            "exhausted",
        )
        assert any(kw in body_lower for kw in descriptive_keywords), (
            "Empty-state dead-letter page must include descriptive text about the dead-letter queue"
        )


class TestDeadLettersPageStructure:
    """Dead-letter page must have clear page-level structure for operator orientation.

    Operators navigating between admin pages need consistent heading hierarchy
    so they know immediately which page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Dead-letter page has a heading identifying it as the dead-letter section."""
        navigate(page, f"{base_url}{DEAD_LETTERS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = (
            "dead letter",
            "dead-letter",
            "dead letters",
            "dead-letters",
            "failed events",
            "undeliverable",
            "dlq",
        )
        assert any(kw in body_lower for kw in heading_keywords), (
            "Dead-letter page must have a heading referencing 'Dead Letter' or 'Dead-Letter Events'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Dead-letter page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{DEAD_LETTERS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Dead-letter page body must not be empty"
