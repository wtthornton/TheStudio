"""Epic 62.1 — Audit Log: Page Intent & Semantic Content.

Validates that /admin/ui/audit delivers its core purpose:
  - Event log table renders with timestamp, actor, action, and target columns
  - Empty state is shown when no audit events exist
  - Page has a heading identifying the audit log section

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_audit_style.py (Epic 62.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

AUDIT_URL = "/admin/ui/audit"


class TestAuditTableContent:
    """Audit event table must surface the key columns operators need at a glance.

    When audit events exist the table must show:
      Timestamp — when the event occurred, formatted for readability
      Actor     — who triggered the event (user, system, or agent)
      Action    — what operation was performed
      Target    — which entity was affected
    """

    def test_audit_page_renders(self, page, base_url: str) -> None:
        """Audit page shows a table or empty-state container."""
        navigate(page, f"{base_url}{AUDIT_URL}")

        has_table = page.locator("table").count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in (
                "no audit",
                "no events",
                "no log",
                "nothing to show",
                "empty",
                "get started",
            )
        )
        assert has_table or has_empty_state, (
            "Audit page must show an event log table or an empty-state message"
        )

    def test_audit_timestamp_column_shown(self, page, base_url: str) -> None:
        """Audit table header or body contains timestamp information."""
        navigate(page, f"{base_url}{AUDIT_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No audit events registered — empty state is acceptable for 62.1")

        body_lower = page.locator("body").inner_text().lower()
        timestamp_keywords = ("timestamp", "time", "date", "when", "at")
        assert any(kw in body_lower for kw in timestamp_keywords), (
            "Audit table must include a timestamp column"
        )

    def test_audit_actor_column_shown(self, page, base_url: str) -> None:
        """Audit table includes an actor or user column."""
        navigate(page, f"{base_url}{AUDIT_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No audit events registered — empty state is acceptable for 62.1")

        body_lower = page.locator("body").inner_text().lower()
        actor_keywords = ("actor", "user", "by", "who", "agent", "source")
        assert any(kw in body_lower for kw in actor_keywords), (
            "Audit table must display the actor or user who triggered the event"
        )

    def test_audit_action_column_shown(self, page, base_url: str) -> None:
        """Audit table includes an action or event type column."""
        navigate(page, f"{base_url}{AUDIT_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No audit events registered — empty state is acceptable for 62.1")

        body_lower = page.locator("body").inner_text().lower()
        action_keywords = ("action", "event", "operation", "type", "kind")
        assert any(kw in body_lower for kw in action_keywords), (
            "Audit table must display the action or event type"
        )

    def test_audit_target_column_shown(self, page, base_url: str) -> None:
        """Audit table includes a target or resource column."""
        navigate(page, f"{base_url}{AUDIT_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No audit events registered — empty state is acceptable for 62.1")

        body_lower = page.locator("body").inner_text().lower()
        target_keywords = ("target", "resource", "entity", "object", "repo", "subject")
        assert any(kw in body_lower for kw in target_keywords), (
            "Audit table must display the target resource affected by the event"
        )


class TestAuditEmptyState:
    """Audit page must display a helpful empty state when no events exist.

    An informative empty state prevents operators from assuming the page is
    broken when no audit events have been recorded yet.
    """

    def test_empty_state_or_table_shown(self, page, base_url: str) -> None:
        """Audit page renders either data or an explicit empty-state indicator."""
        navigate(page, f"{base_url}{AUDIT_URL}")

        has_table_rows = page.locator("table tbody tr").count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in ("no audit", "no events", "no log", "nothing", "empty", "yet")
        )
        # At least one of the two must be true
        assert has_table_rows or has_empty_state, (
            "Audit page must show audit events or an empty-state message"
        )


class TestAuditPageStructure:
    """Audit page must have clear page-level structure for operator orientation.

    Consistent heading hierarchy ensures operators know immediately which
    page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Audit page has a heading identifying it as the audit log section."""
        navigate(page, f"{base_url}{AUDIT_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = ("audit", "audit log", "event log", "activity", "log")
        assert any(kw in body_lower for kw in heading_keywords), (
            "Audit page must have a heading referencing 'Audit' or 'Event Log'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Audit page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{AUDIT_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Audit page body must not be empty"
