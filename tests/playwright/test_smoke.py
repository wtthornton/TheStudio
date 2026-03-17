"""Smoke tests: healthz, admin dashboard loads with operational content.

These are the first tests to run — they validate that the app is alive and
the primary dashboard delivers its core purpose: fleet health visibility.
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright


def test_healthz_returns_ok(page, base_url: str) -> None:
    """Navigate to /healthz and assert 'ok' appears in the response."""
    navigate(page, f"{base_url}/healthz")
    content = page.content()
    assert "ok" in content, f"Expected 'ok' in response body, got: {content[:200]}"


def test_admin_dashboard_loads(page, base_url: str) -> None:
    """Navigate to admin dashboard and assert page title."""
    navigate(page, f"{base_url}/admin/ui/dashboard")
    title = page.title()
    assert "Dashboard" in title, f"Expected 'Dashboard' in title, got: {title}"


def test_no_console_errors_on_dashboard(page, base_url: str, console_errors: list) -> None:
    """Load dashboard and assert no JavaScript console errors."""
    navigate(page, f"{base_url}/admin/ui/dashboard")
    assert len(console_errors) == 0, f"Expected no console errors, got: {console_errors}"


def test_empty_repos_page_no_entity_artifacts(page, base_url: str) -> None:
    """Empty Repos page must not show literal HTML entity text (e.g. &#9744;)."""
    navigate(page, f"{base_url}/admin/ui/repos")
    visible_text = page.locator("body").inner_text()
    assert "&#" not in visible_text, (
        f"Visible content must not contain literal HTML entities; found in: {visible_text[:500]}"
    )


# ---------------------------------------------------------------------------
# Dashboard purpose validation — the dashboard exists to give operators
# a single-screen view of fleet health, workflow throughput, and hot alerts.
# ---------------------------------------------------------------------------


def test_dashboard_shows_system_health_section(page, base_url: str) -> None:
    """Dashboard must display system health for critical infrastructure services.

    Operators need to see at a glance whether Temporal, Postgres, JetStream,
    and the Router are healthy before investigating workflow issues.
    """
    navigate(page, f"{base_url}/admin/ui/dashboard")
    body = page.locator("body").inner_text()

    for service in ("Temporal", "Postgres"):
        assert service in body, (
            f"Dashboard must show '{service}' health — operators need infrastructure status"
        )


def test_dashboard_shows_workflow_throughput(page, base_url: str) -> None:
    """Dashboard must show workflow counts so operators can assess pipeline load.

    Key metrics: Running (active work), Stuck (needs attention), Failed (broken),
    Queue Depth (backlog pressure). Without these, the dashboard is just a logo.
    """
    navigate(page, f"{base_url}/admin/ui/dashboard")
    body = page.locator("body").inner_text()

    for metric in ("Running", "Stuck", "Failed"):
        assert metric in body, (
            f"Dashboard must show '{metric}' workflow count for capacity monitoring"
        )


def test_dashboard_shows_repo_activity_or_empty_guidance(page, base_url: str) -> None:
    """Dashboard must show per-repo activity table or guide user to register repos.

    Without repo-level breakdown, operators cannot identify which repo is
    causing issues. Empty state should direct users to register repos.
    """
    navigate(page, f"{base_url}/admin/ui/dashboard")
    body = page.locator("body").inner_text()

    has_table = page.locator("table").count() > 0
    has_empty_state = "No repos" in body or "no repos" in body.lower()
    assert has_table or has_empty_state, (
        "Dashboard must show repo activity table or 'No repos' empty-state guidance"
    )
