"""Smoke tests: healthz, admin dashboard load, no console errors."""

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
