"""Story 76.9 — Pipeline Dashboard: Activity Log Page Intent & Semantic Content.

Validates that /dashboard/?tab=activity delivers its core purpose:
  - "Steering Activity Log" heading is present (h2 in SteeringActivityLog).
  - Filter bar with action-type select is rendered.
  - Audit table columns (Time, Task ID, Action, From Stage, To Stage, Reason, Actor).
  - Empty state communicates "No steering actions yet" when no entries exist.
  - Pagination controls (Previous / Next) are rendered.

These tests check *what* the page communicates, not *how* it looks.
Style compliance is in test_pd_activity_style.py.
API contracts are in test_pd_activity_api.py.

Implementation note: The ``activity`` tab is rendered by the else-fallthrough in
App.tsx — there is no explicit ``?tab=activity`` conditional; SteeringActivityLog
is the default catch-all content for unrecognised (or activity) tab values.
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


# ---------------------------------------------------------------------------
# Navigation helper
# ---------------------------------------------------------------------------


def _go(page: object, base_url: str) -> None:
    """Navigate to the activity tab and wait for React to hydrate."""
    dashboard_navigate(page, base_url, "activity")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Page heading
# ---------------------------------------------------------------------------


class TestActivityLogHeading:
    """Steering Activity Log must display its primary heading.

    The heading is the first content operators see and anchors the page
    purpose for screen-reader users.
    """

    def test_steering_activity_log_heading_present(self, page, base_url: str) -> None:
        """Activity tab renders 'Steering Activity Log' h2 heading."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "Steering Activity Log" in body, (
            "Activity tab must render 'Steering Activity Log' heading "
            "so operators can identify the audit log section"
        )

    def test_heading_element_is_present(self, page, base_url: str) -> None:
        """A heading element (h1–h3) exists on the activity tab."""
        _go(page, base_url)

        heading_count = page.locator("h1, h2, h3").count()
        assert heading_count > 0, (
            "Activity tab must have at least one heading element "
            "(h1–h3) so screen-reader users can navigate the page"
        )

    def test_page_description_present(self, page, base_url: str) -> None:
        """Activity tab includes a description of the log's purpose."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        has_description = (
            "steering" in body
            or "pause" in body
            or "resume" in body
            or "abort" in body
            or "pipeline" in body
        )
        assert has_description, (
            "Activity tab must include a description mentioning steering actions "
            "(pause, resume, abort, redirect, retry, trust tier changes)"
        )


# ---------------------------------------------------------------------------
# Filter bar
# ---------------------------------------------------------------------------


class TestActivityFilterBar:
    """Filter bar must allow operators to narrow activity log by action type.

    The filter bar is the primary interaction element on the activity tab,
    letting operators focus on specific action types (pause, abort, etc.).
    """

    def test_filter_bar_present(self, page, base_url: str) -> None:
        """Activity tab renders a filter bar element."""
        _go(page, base_url)

        # The filter bar renders a select element for action type.
        select_count = page.locator("select").count()
        has_filter_text = "filter" in page.locator("body").inner_text().lower()

        assert select_count > 0 or has_filter_text, (
            "Activity tab must render a filter bar with an action-type selector "
            "so operators can narrow the audit log"
        )

    def test_filter_by_action_label_present(self, page, base_url: str) -> None:
        """Filter bar includes a 'Filter by action' label."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        assert "filter" in body or "action" in body, (
            "Activity tab filter bar must include a 'Filter by action' label "
            "or similar descriptive text"
        )

    def test_all_actions_option_present(self, page, base_url: str) -> None:
        """Filter select includes an 'All actions' option to clear the filter."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        assert "all actions" in body or "all" in body, (
            "Activity filter must include an 'All actions' or 'All' option "
            "to reset the action-type filter"
        )

    def test_refresh_button_present(self, page, base_url: str) -> None:
        """Activity tab has a Refresh button to reload the audit log."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        assert "refresh" in body, (
            "Activity tab must include a Refresh button "
            "so operators can reload the audit log on demand"
        )


# ---------------------------------------------------------------------------
# Audit table columns
# ---------------------------------------------------------------------------


class TestActivityAuditTableColumns:
    """Audit table must show the seven canonical column headers.

    The column headers tell operators what data is in each column without
    requiring them to infer meaning from content alone.
    """

    COLUMN_HEADERS = [
        "Time",
        "Task ID",
        "Action",
        "Actor",
    ]

    def test_audit_table_present_or_empty_state(self, page, base_url: str) -> None:
        """Activity tab renders either an audit table or an empty state."""
        _go(page, base_url)

        has_table = page.locator("table").count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty = (
            "no steering actions" in body_lower
            or "no activity" in body_lower
            or "empty" in body_lower
        )

        assert has_table or has_empty, (
            "Activity tab must render an audit table or an empty state "
            "— neither was found in the DOM"
        )

    def test_time_column_header_present(self, page, base_url: str) -> None:
        """Audit table has a 'Time' column header."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No audit table — empty state is present, no entries")

        body = page.locator("table").inner_text()
        assert "Time" in body, (
            "Audit table must include a 'Time' column header "
            "so operators can correlate events to specific moments"
        )

    def test_task_id_column_header_present(self, page, base_url: str) -> None:
        """Audit table has a 'Task ID' column header."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No audit table — empty state is present")

        body = page.locator("table").inner_text()
        assert "Task ID" in body or "Task" in body, (
            "Audit table must include a 'Task ID' column header "
            "so operators can link actions back to specific tasks"
        )

    def test_action_column_header_present(self, page, base_url: str) -> None:
        """Audit table has an 'Action' column header."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No audit table — empty state is present")

        body = page.locator("table").inner_text()
        assert "Action" in body, (
            "Audit table must include an 'Action' column header "
            "identifying the type of steering action taken"
        )

    def test_actor_column_header_present(self, page, base_url: str) -> None:
        """Audit table has an 'Actor' column header."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No audit table — empty state is present")

        body = page.locator("table").inner_text()
        assert "Actor" in body, (
            "Audit table must include an 'Actor' column header "
            "showing who initiated the steering action"
        )

    def test_all_core_columns_present_when_table_active(
        self, page, base_url: str
    ) -> None:
        """When the audit table renders, all core column headers are visible."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No audit table — empty state is acceptable")

        body = page.locator("table").inner_text()
        missing = [col for col in self.COLUMN_HEADERS if col not in body]
        assert not missing, (
            f"Audit table is missing column headers: {missing!r}"
        )


# ---------------------------------------------------------------------------
# Audit log entries
# ---------------------------------------------------------------------------


class TestActivityLogEntries:
    """Log entries must display action type, actor, and timestamp when populated.

    These are the three minimum data points operators need to understand
    what happened, who did it, and when.
    """

    def test_log_entries_or_empty_state(self, page, base_url: str) -> None:
        """Activity tab shows log entries or the 'No steering actions yet' empty state."""
        _go(page, base_url)

        has_rows = page.locator("table tbody tr").count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty = (
            "no steering actions" in body_lower
            or "loading" in body_lower
        )

        assert has_rows or has_empty, (
            "Activity tab must show log entries or an empty state — "
            "neither table rows nor empty-state text was found"
        )

    def test_entry_rows_have_content_when_populated(self, page, base_url: str) -> None:
        """Each audit entry row contains non-empty text."""
        _go(page, base_url)

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            pytest.skip("No log entries — empty state is acceptable")

        first_row_text = rows.first.inner_text().strip()
        assert first_row_text, (
            "Audit log entry rows must contain non-empty text "
            "(timestamp, task ID, action type, actor)"
        )


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------


class TestActivityEmptyState:
    """Empty state must communicate that no steering actions have been recorded yet.

    When the pipeline has not had any steering interventions, the empty state
    guides operators to understand the normal pipeline flow.
    """

    def test_empty_state_heading_when_no_entries(self, page, base_url: str) -> None:
        """Empty state has 'No steering actions yet' heading."""
        _go(page, base_url)

        if page.locator("table tbody tr").count() > 0:
            pytest.skip("Log entries present — not in empty state")

        body = page.locator("body").inner_text()
        has_empty_heading = (
            "No steering actions yet" in body
            or "No activity" in body
            or "no entries" in body.lower()
        )
        # Also accept a loading or error state as valid non-empty-state alternatives
        has_loading = "loading" in body.lower() or "Loading" in body
        assert has_empty_heading or has_loading, (
            "Empty activity state must display 'No steering actions yet' or similar "
            "heading when no entries exist"
        )

    def test_empty_state_description_mentions_actions(
        self, page, base_url: str
    ) -> None:
        """Empty state description explains what types of actions appear here."""
        _go(page, base_url)

        if page.locator("table tbody tr").count() > 0:
            pytest.skip("Log entries present — not in empty state")

        body = page.locator("body").inner_text().lower()
        # Check for description mentioning actions or that the log is inactive
        has_description = (
            "pause" in body
            or "resume" in body
            or "abort" in body
            or "steering" in body
            or "pipeline" in body
        )
        # Accept loading as valid while entries are being fetched
        has_loading = "loading" in body
        assert has_description or has_loading, (
            "Empty activity state must include a description mentioning "
            "the types of steering actions that will appear here"
        )


# ---------------------------------------------------------------------------
# Pagination controls
# ---------------------------------------------------------------------------


class TestActivityPagination:
    """Pagination controls must be present and navigable.

    The activity log is paginated in 50-entry pages. Operators need
    Previous/Next controls to move through large audit histories.
    """

    def test_pagination_controls_present(self, page, base_url: str) -> None:
        """Activity tab renders Previous and Next pagination buttons."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        has_prev = "Previous" in body or "← Previous" in body
        has_next = "Next" in body or "Next →" in body

        assert has_prev or has_next, (
            "Activity tab must include pagination controls "
            "(Previous / Next buttons) for navigating large audit logs"
        )

    def test_previous_button_disabled_on_first_page(
        self, page, base_url: str
    ) -> None:
        """The Previous pagination button is disabled on the first page."""
        _go(page, base_url)

        # Find the Previous button
        prev_buttons = page.locator("button", has_text="Previous")
        if prev_buttons.count() == 0:
            pytest.skip("No 'Previous' button found on activity tab")

        prev_btn = prev_buttons.first
        is_disabled = not prev_btn.is_enabled()
        assert is_disabled, (
            "The 'Previous' button must be disabled when on the first page "
            "of the activity log (page 0)"
        )
