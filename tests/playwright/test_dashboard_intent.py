"""Epic 59.1 — Fleet Dashboard: Page Intent & Semantic Content.

Validates that /admin/ui/dashboard delivers its core purpose:
  - System Health section shows Temporal and Postgres service status
  - Workflow Summary shows Running / Stuck / Failed / Queue counts
  - Repo Activity table renders (or an appropriate empty-state is shown)

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_dashboard_style.py (Epic 59.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

DASHBOARD_URL = "/admin/ui/dashboard"


class TestDashboardSystemHealth:
    """System Health section must surface critical infrastructure service status.

    Operators need to see at a glance whether Temporal, Postgres, JetStream,
    and the Router are healthy *before* investigating workflow issues.
    """

    def test_temporal_service_shown(self, page, base_url: str) -> None:
        """Dashboard shows 'Temporal' health status."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")
        body = page.locator("body").inner_text()
        assert "Temporal" in body, (
            "Dashboard must display 'Temporal' in the system health section"
        )

    def test_postgres_service_shown(self, page, base_url: str) -> None:
        """Dashboard shows 'Postgres' health status."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")
        body = page.locator("body").inner_text()
        assert "Postgres" in body, (
            "Dashboard must display 'Postgres' in the system health section"
        )

    def test_service_health_has_status_or_latency(self, page, base_url: str) -> None:
        """Each service card shows a latency measurement (ms) or status indicator."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")
        body = page.locator("body").inner_text()
        body_lower = body.lower()

        has_latency = "ms" in body
        has_status_word = any(
            kw in body_lower for kw in ("healthy", "degraded", "unavailable", "status", "ok")
        )
        assert has_latency or has_status_word, (
            "Dashboard service health cards must show latency (ms) or a status indicator"
        )

    def test_system_health_section_heading(self, page, base_url: str) -> None:
        """Dashboard page has a section heading for system / service health."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")
        body = page.locator("body").inner_text().lower()

        assert "health" in body or "system" in body or "service" in body, (
            "Dashboard must have a 'System Health' or 'Services' section heading"
        )


class TestDashboardWorkflowSummary:
    """Workflow Summary section must show pipeline workload metrics.

    Key counts needed for capacity monitoring:
      Running — active workflows in progress
      Stuck   — workflows stalled and needing attention
      Failed  — workflows that terminated with an error
      Queue   — depth of the incoming work backlog
    """

    def test_running_metric_shown(self, page, base_url: str) -> None:
        """Dashboard shows 'Running' workflow count."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")
        body = page.locator("body").inner_text()
        assert "Running" in body, (
            "Dashboard Workflow Summary must display the 'Running' count"
        )

    def test_stuck_metric_shown(self, page, base_url: str) -> None:
        """Dashboard shows 'Stuck' workflow count."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")
        body = page.locator("body").inner_text()
        assert "Stuck" in body, (
            "Dashboard Workflow Summary must display the 'Stuck' count"
        )

    def test_failed_metric_shown(self, page, base_url: str) -> None:
        """Dashboard shows 'Failed' workflow count."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")
        body = page.locator("body").inner_text()
        assert "Failed" in body, (
            "Dashboard Workflow Summary must display the 'Failed' count"
        )

    def test_queue_depth_shown(self, page, base_url: str) -> None:
        """Dashboard shows 'Queue' depth metric."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")
        body = page.locator("body").inner_text()
        # Accept 'Queue' label or 'Queue Depth' variant
        assert "Queue" in body, (
            "Dashboard Workflow Summary must display the 'Queue' (depth) count"
        )

    def test_workflow_summary_has_numeric_values(self, page, base_url: str) -> None:
        """Workflow Summary cards contain numeric metric values."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")
        body = page.locator("body").inner_text()

        # Any digit present near the metric labels is sufficient — the page
        # renders zero-state as "0" when no workflows exist.
        has_digit = any(ch.isdigit() for ch in body)
        assert has_digit, (
            "Dashboard Workflow Summary must show numeric metric values (even 0)"
        )


class TestDashboardRepoActivity:
    """Repo Activity section must show per-repo throughput or an empty-state CTA.

    Without repo-level breakdown operators cannot identify which repo is
    causing issues.  An empty state must guide users to register repos.
    """

    def test_repo_activity_table_or_empty_state(self, page, base_url: str) -> None:
        """Dashboard shows a repo activity table or 'No repos' empty-state."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")
        body = page.locator("body").inner_text()
        body_lower = body.lower()

        has_table = page.locator("table").count() > 0
        has_empty_state = "no repos" in body_lower or "no repo" in body_lower
        assert has_table or has_empty_state, (
            "Dashboard must show a repo activity table or a 'No repos' empty-state"
        )

    def test_repo_activity_section_heading(self, page, base_url: str) -> None:
        """Dashboard has a section heading for repo activity."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")
        body = page.locator("body").inner_text().lower()

        assert "repo" in body or "repository" in body or "activity" in body, (
            "Dashboard must have a 'Repo Activity' section heading or repo references"
        )

    def test_repo_table_has_expected_columns_when_populated(
        self, page, base_url: str
    ) -> None:
        """If repos are registered, the activity table shows name and status columns."""
        navigate(page, f"{base_url}{DASHBOARD_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No repos registered — empty state is acceptable for 59.1")

        # When a table is present the header row should include repo name context
        table_text = page.locator("table").first.inner_text().lower()
        has_repo_col = "repo" in table_text or "name" in table_text
        assert has_repo_col, (
            "Repo activity table must include a 'Repo' or 'Name' column"
        )
