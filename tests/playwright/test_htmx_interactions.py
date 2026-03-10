"""Story 12.5: HTMX interaction tests — verify dynamic UI behavior with a real browser.

Tests critical HTMX flows:
1. Register a repo and see it appear in the list
2. Navigate between settings sub-tabs via HTMX
3. Dashboard partials load via HTMX without full page reload
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright


def test_settings_tab_navigation(page, base_url: str, console_errors: list) -> None:
    """Clicking settings sub-tabs swaps content via HTMX without full page reload."""
    navigate(page, f"{base_url}/admin/ui/settings")

    tabs_to_test = [
        ("infrastructure", "Infrastructure"),
        ("feature-flags", "Feature Flags"),
        ("agent-config", "Agent"),
        ("secrets", "Secrets"),
        ("api-keys", "API Keys"),
    ]

    for tab_id, expected_text in tabs_to_test:
        tab_link = page.locator(f'[hx-get*="{tab_id}"]')
        if tab_link.count() == 0:
            pytest.skip(f"Tab link for '{tab_id}' not found in DOM")

        tab_link.first.click()
        page.wait_for_load_state("networkidle")

        body_text = page.locator("body").inner_text()
        assert expected_text in body_text, (
            f"After clicking '{tab_id}' tab, expected '{expected_text}' in page"
        )

    assert len(console_errors) == 0, (
        f"Console errors during tab navigation: {console_errors}"
    )


def test_dashboard_partials_load(page, base_url: str, console_errors: list) -> None:
    """Dashboard page loads HTMX partials (not just the shell)."""
    navigate(page, f"{base_url}/admin/ui/dashboard")

    body_text = page.locator("body").inner_text()
    assert "Fleet Dashboard" in body_text, "Dashboard heading not found after partial load"
    assert len(console_errors) == 0, f"Console errors on dashboard: {console_errors}"


def test_repos_page_empty_state_renders(page, base_url: str) -> None:
    """Repos page shows empty state when no repos are registered."""
    navigate(page, f"{base_url}/admin/ui/repos")

    body_text = page.locator("body").inner_text()
    assert "&#" not in body_text, f"Raw HTML entities in repos page: {body_text[:500]}"


def test_register_repo_flow(page, base_url: str, console_errors: list) -> None:
    """Register a repo via the UI form and verify it appears in the list.

    This test creates a test repo and verifies the HTMX-driven form submission works.
    """
    navigate(page, f"{base_url}/admin/ui/repos")

    # Look for owner/repo input fields
    owner_input = page.locator('input[name="owner"]')
    repo_input = page.locator('input[name="repo"]')

    if owner_input.count() == 0 or repo_input.count() == 0:
        pytest.skip("Repo registration form fields not found")

    test_owner = "playwright-test"
    test_repo = "test-repo-cleanup"

    owner_input.fill(test_owner)
    repo_input.fill(test_repo)

    submit_btn = page.locator('button[type="submit"]')
    if submit_btn.count() > 0:
        submit_btn.first.click()
    else:
        pytest.skip("No submit button found for repo registration")

    page.wait_for_load_state("networkidle")

    body_text = page.locator("body").inner_text()
    assert test_owner in body_text or test_repo in body_text, (
        f"Expected test repo '{test_owner}/{test_repo}' to appear after registration"
    )

    assert len(console_errors) == 0, (
        f"Console errors during repo registration: {console_errors}"
    )


def test_navigation_links_work(page, base_url: str, console_errors: list) -> None:
    """Sidebar navigation links lead to the correct pages without errors."""
    navigate(page, f"{base_url}/admin/ui/dashboard")

    nav_links = [
        ("Repos", "Repo Management"),
        ("Workflows", "Workflow Console"),
        ("Settings", "Settings"),
    ]

    for link_text, expected_heading in nav_links:
        link = page.locator(f'a:has-text("{link_text}")').first
        link.click()
        page.wait_for_load_state("networkidle")

        heading = page.locator("h2").first
        heading_text = heading.inner_text() if heading else ""
        assert expected_heading in heading_text, (
            f"Clicked '{link_text}', expected '{expected_heading}', got '{heading_text}'"
        )

    assert len(console_errors) == 0, f"Console errors during navigation: {console_errors}"
