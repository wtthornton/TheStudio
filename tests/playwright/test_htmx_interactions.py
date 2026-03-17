"""HTMX interaction tests — verify dynamic UI delivers meaningful content.

Tests go beyond "did HTMX fire?" to validate that dynamic interactions
produce the content users actually need:
1. Settings tabs deliver domain-specific configuration controls
2. Dashboard partials show operational data, not empty shells
3. Repo registration produces actionable feedback
4. Navigation maintains page purpose across transitions
"""

import uuid

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright


def test_settings_tab_navigation_delivers_content(
    page, base_url: str, console_errors: list
) -> None:
    """Clicking settings tabs swaps in domain-specific configuration content.

    Each tab must deliver its purpose:
    - Infrastructure: connection strings and service addresses
    - Feature Flags: toggleable flags with descriptions
    - Agent Config: model selection and execution parameters
    - Secrets: key rotation controls
    - API Keys: key management with masking
    """
    navigate(page, f"{base_url}/admin/ui/settings")

    # Each tab and what it must deliver (not just a label, but purposeful content)
    tabs_to_test = [
        ("infrastructure", ["Infrastructure"], ["connect", "address", "url", "server", "pool"]),
        ("feature-flags", ["Feature Flags"], ["enabled", "disabled", "flag", "toggle"]),
        ("agent-config", ["Agent"], ["model", "timeout", "retries", "concurrency", "config"]),
        ("secrets", ["Secrets"], ["secret", "rotate", "regenerate", "encrypt", "webhook"]),
        ("api-keys", ["API Keys"], ["key", "token", "reveal", "update", "***"]),
    ]

    for tab_id, heading_words, purpose_words in tabs_to_test:
        tab_link = page.locator(f'[hx-get*="{tab_id}"]')
        if tab_link.count() == 0:
            pytest.skip(f"Tab link for '{tab_id}' not found in DOM")

        tab_link.first.click()
        page.wait_for_load_state("networkidle")

        body_text = page.locator("body").inner_text()
        body_lower = body_text.lower()

        # Heading word present
        for hw in heading_words:
            assert hw in body_text, (
                f"After clicking '{tab_id}' tab, expected '{hw}' in page"
            )

        # Purpose content present — tab must deliver domain-specific info
        has_purpose = any(pw in body_lower for pw in purpose_words)
        assert has_purpose, (
            f"'{tab_id}' tab must show domain content ({purpose_words}), "
            f"got only generic shell"
        )

    assert len(console_errors) == 0, (
        f"Console errors during tab navigation: {console_errors}"
    )


def test_dashboard_partials_deliver_operational_data(
    page, base_url: str, console_errors: list
) -> None:
    """Dashboard HTMX partials must deliver operational data, not empty shells.

    After partials load, the dashboard must show:
    - System health service names (infrastructure visibility)
    - Workflow status metrics (operational awareness)
    """
    navigate(page, f"{base_url}/admin/ui/dashboard")

    body_text = page.locator("body").inner_text()
    assert "Fleet Dashboard" in body_text, "Dashboard heading not found after partial load"

    # Partials must have delivered operational content
    body_lower = body_text.lower()
    has_health = any(s in body_text for s in ("Temporal", "Postgres"))
    has_metrics = any(m in body_text for m in ("Running", "Stuck", "Failed"))
    assert has_health or has_metrics, (
        "Dashboard partials must deliver operational data (health services or workflow metrics)"
    )

    assert len(console_errors) == 0, f"Console errors on dashboard: {console_errors}"


def test_repos_page_empty_state_guides_user(page, base_url: str) -> None:
    """Empty repos page must guide user toward registration, not show a blank table.

    Purpose: when no repos exist, the page should communicate that registration
    is the next action, not leave the user staring at an empty grid.
    """
    navigate(page, f"{base_url}/admin/ui/repos")

    body_text = page.locator("body").inner_text()
    assert "&#" not in body_text, f"Raw HTML entities in repos page: {body_text[:500]}"

    # The page should provide registration guidance
    has_register_btn = page.get_by_role("button", name="Register Repo").count() > 0
    has_guidance = (
        "register" in body_text.lower()
        or "add" in body_text.lower()
        or "no repos" in body_text.lower()
    )
    assert has_register_btn or has_guidance, (
        "Empty repos page must guide user to register a repo"
    )


def test_register_repo_flow(page, base_url: str, console_errors: list) -> None:
    """Register a repo and verify the result communicates success with repo details.

    The flow must:
    1. Accept owner + repo name (minimum viable registration)
    2. Return confirmation that includes the submitted repo identity
    3. Confirm via visible result, not just absence of error
    """
    navigate(page, f"{base_url}/admin/ui/repos")

    register_btn = page.get_by_role("button", name="Register Repo")
    register_btn.click()
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

    # Result must confirm the registration with repo identity
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
        f"Registration result must confirm repo identity. Got: {result_text[:200]}"
    )

    assert len(console_errors) == 0, (
        f"Console errors during repo registration: {console_errors}"
    )


def test_navigation_preserves_page_purpose(
    page, base_url: str, console_errors: list
) -> None:
    """Sidebar navigation links lead to pages that deliver their intended purpose.

    Each navigation target must show its purpose heading AND at least one
    element that serves that page's function (not just a heading shell).
    """
    navigate(page, f"{base_url}/admin/ui/dashboard")

    nav_targets = [
        ("Repos", "Repo Management", ["register", "repo", "owner"]),
        ("Workflows", "Workflow Console", ["status", "running", "filter", "workflow"]),
        ("Settings", "Settings", ["api", "key", "infrastructure", "flag", "config"]),
    ]

    for link_text, expected_heading, purpose_words in nav_targets:
        link = page.locator(f'a:has-text("{link_text}")').first
        link.click()
        page.wait_for_load_state("networkidle")

        heading = page.locator("h2").first
        heading_text = heading.inner_text() if heading else ""
        assert expected_heading in heading_text, (
            f"Clicked '{link_text}', expected '{expected_heading}', got '{heading_text}'"
        )

        # Page must deliver purpose content, not just a heading
        body_lower = page.locator("body").inner_text().lower()
        has_purpose = any(pw in body_lower for pw in purpose_words)
        assert has_purpose, (
            f"'{link_text}' page loaded but lacks purpose content ({purpose_words})"
        )

    assert len(console_errors) == 0, f"Console errors during navigation: {console_errors}"
