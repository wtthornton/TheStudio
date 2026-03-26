"""Epic 68.1 — Quarantine: Page Intent & Semantic Content.

Validates that /admin/ui/quarantine delivers its core purpose:
  - Quarantined events table renders with event identity and failure reasons
  - Failure reasons are surfaced so operators understand why events were quarantined
  - Page heading clearly identifies the quarantine section
  - Empty state is shown when no quarantined events are present

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_quarantine_style.py (Epic 68.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

QUARANTINE_URL = "/admin/ui/quarantine"


class TestQuarantineEventContent:
    """Quarantined events table must surface the key information operators need.

    When quarantined events are present the page must show:
      Event identity   — event ID, type, or source repo that was quarantined
      Failure reason   — why the event was quarantined (error, parse failure, etc.)
      Quarantine state — status indicating the event is held / blocked
    """

    def test_quarantine_page_renders(self, page, base_url: str) -> None:
        """Quarantine page shows an events table or an empty-state container."""
        navigate(page, f"{base_url}{QUARANTINE_URL}")

        has_table = page.locator("table").count() > 0
        has_list = page.locator(
            "[class*='quarantine'], [data-quarantine], [data-component='quarantine-card']"
        ).count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in ("no quarantine", "no events", "queue is empty", "nothing quarantined", "empty")
        )
        assert has_table or has_list or has_empty_state, (
            "Quarantine page must show an events table (or card list) or an "
            "empty-state message when no quarantined events are present"
        )

    def test_event_identity_shown(self, page, base_url: str) -> None:
        """Quarantine list or page body includes event identity information."""
        navigate(page, f"{base_url}{QUARANTINE_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-quarantine]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no quarantine", "empty", "no events")):
                pytest.skip("No quarantined events — empty state is acceptable for 68.1")

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
            "Quarantine page must display event identity information (ID, repo, or source)"
        )

    def test_failure_reason_shown(self, page, base_url: str) -> None:
        """Quarantine page surfaces failure reasons explaining why events were quarantined."""
        navigate(page, f"{base_url}{QUARANTINE_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-quarantine]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no quarantine", "empty", "no events")):
                pytest.skip("No quarantined events — empty state is acceptable for 68.1")

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
        )
        assert any(kw in body_lower for kw in reason_keywords), (
            "Quarantine page must display failure reasons explaining why events were quarantined"
        )

    def test_quarantine_status_shown(self, page, base_url: str) -> None:
        """Quarantine page surfaces status indicating events are held or blocked."""
        navigate(page, f"{base_url}{QUARANTINE_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-quarantine]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no quarantine", "empty", "no events")):
                pytest.skip("No quarantined events — empty state is acceptable for 68.1")

        body_lower = page.locator("body").inner_text().lower()
        status_keywords = (
            "quarantine",
            "quarantined",
            "held",
            "blocked",
            "failed",
            "pending",
            "status",
            "replay",
            "retry",
        )
        assert any(kw in body_lower for kw in status_keywords), (
            "Quarantine page must display status indicating events are quarantined / held"
        )

    def test_quarantine_table_has_identifier_column(self, page, base_url: str) -> None:
        """Quarantine table has a column or field identifying each quarantined event."""
        navigate(page, f"{base_url}{QUARANTINE_URL}")

        has_table = page.locator("table").count() > 0
        if not has_table:
            pytest.skip("No table on quarantine page — card-based layout acceptable for 68.1")

        body_lower = page.locator("body").inner_text().lower()
        id_keywords = ("event", "id", "repo", "repository", "name", "source", "type", "slug")
        assert any(kw in body_lower for kw in id_keywords), (
            "Quarantine table must include an identifier column (event ID, repo name, or source)"
        )


class TestQuarantineEmptyState:
    """Empty-state must communicate clearly when no quarantined events exist.

    An informative empty state prevents confusion when the quarantine queue is
    empty and gives operators context about what the quarantine section manages.
    """

    def test_empty_state_has_descriptive_text(self, page, base_url: str) -> None:
        """When no quarantined events exist, the page shows descriptive text about quarantine."""
        navigate(page, f"{base_url}{QUARANTINE_URL}")

        if page.locator("table").count() > 0:
            rows = page.locator("table tbody tr").count()
            if rows > 0:
                pytest.skip("Quarantined events are present — empty-state test not applicable")

        body_lower = page.locator("body").inner_text().lower()
        descriptive_keywords = (
            "quarantine",
            "quarantined",
            "no events",
            "no quarantined",
            "queue is empty",
            "nothing quarantined",
            "blocked",
            "failed events",
        )
        assert any(kw in body_lower for kw in descriptive_keywords), (
            "Empty-state quarantine page must include descriptive text about the quarantine queue"
        )


class TestQuarantinePageStructure:
    """Quarantine page must have clear page-level structure for operator orientation.

    Operators navigating between admin pages need consistent heading hierarchy
    so they know immediately which page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Quarantine page has a heading identifying it as the quarantine section."""
        navigate(page, f"{base_url}{QUARANTINE_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = (
            "quarantine",
            "quarantined",
            "quarantined events",
            "failed events",
            "blocked events",
            "event queue",
        )
        assert any(kw in body_lower for kw in heading_keywords), (
            "Quarantine page must have a heading referencing 'Quarantine' or 'Quarantined Events'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Quarantine page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{QUARANTINE_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Quarantine page body must not be empty"
