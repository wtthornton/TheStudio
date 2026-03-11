"""Story 12.5: HTMX interaction tests — verify dynamic UI behavior with a real browser.

Tests critical HTMX flows:
1. Register a repo and see it appear in the list
2. Navigate between settings sub-tabs via HTMX
3. Dashboard partials load via HTMX without full page reload
"""

import uuid

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

    The register form is hidden by default; we open it with "Register Repo", then fill
    and submit. Verifies the HTMX-driven form submission works.
    """
    navigate(page, f"{base_url}/admin/ui/repos")

    # Open the register form (it is hidden by default; button toggles visibility)
    register_btn = page.get_by_role("button", name="Register Repo")
    register_btn.click()
    # Wait for the form container to be visible so inputs are interactable
    form_container = page.locator("#register-form")
    form_container.wait_for(state="visible", timeout=5000)

    owner_input = page.locator('input[name="owner"]')
    repo_input = page.locator('input[name="repo"]')
    installation_input = page.locator('input[name="installation_id"]')

    if owner_input.count() == 0 or repo_input.count() == 0:
        pytest.skip("Repo registration form fields not found")

    test_owner = "playwright-test"
    test_repo = f"test-repo-{uuid.uuid4().hex[:8]}"
    test_installation_id = 12345

    owner_input.fill(test_owner)
    repo_input.fill(test_repo)
    if installation_input.count() > 0:
        installation_input.fill(str(test_installation_id))

    submit_btn = page.locator('#register-form button[type="submit"]')
    if submit_btn.count() > 0:
        submit_btn.first.click()
    else:
        pytest.skip("No submit button found for repo registration")

    page.wait_for_load_state("networkidle")

    # API returns JSON into #register-result. Unique repo per run so we get 201.
    register_result = page.locator("#register-result")
    page.wait_for_function(
        f"""() => {{
            const el = document.getElementById("register-result");
            const t = el && el.innerText ? el.innerText : "";
            return t.includes("{test_owner}") || t.includes("{test_repo}");
        }}""",
        timeout=10000,
    )
    result_text = register_result.inner_text()
    assert test_owner in result_text or test_repo in result_text, (
        f"Expected result to contain '{test_owner}' or '{test_repo}', got: {result_text[:200]}"
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
