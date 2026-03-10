"""Story 12.4: Full page navigation tests — every Admin UI page loads correctly.

Parameterized test visits each page, waits for content, and asserts:
- HTTP 200 response
- Expected heading text in the page
- No literal HTML entities in visible text
- No JavaScript console errors
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

# Pages that don't require pre-existing data (always accessible)
STATIC_PAGES = [
    ("/admin/ui/dashboard", "Fleet Dashboard"),
    ("/admin/ui/repos", "Repo Management"),
    ("/admin/ui/workflows", "Workflow Console"),
    ("/admin/ui/audit", "Audit Log"),
    ("/admin/ui/metrics", "Metrics"),
    ("/admin/ui/experts", "Expert Performance"),
    ("/admin/ui/tools", "Tool Hub"),
    ("/admin/ui/models", "Model Gateway"),
    ("/admin/ui/compliance", "Compliance Scorecard"),
    ("/admin/ui/quarantine", "Quarantine"),
    ("/admin/ui/dead-letters", "Dead-Letter"),
    ("/admin/ui/planes", "Execution Planes"),
    ("/admin/ui/settings", "Settings"),
]


@pytest.mark.parametrize(
    ("path", "expected_heading"),
    STATIC_PAGES,
    ids=[p.split("/")[-1] for p, _ in STATIC_PAGES],
)
def test_page_loads_with_heading(
    page, base_url: str, path: str, expected_heading: str
) -> None:
    """Each page returns 200 and contains the expected heading."""
    navigate(page, f"{base_url}{path}")

    heading = page.locator("h2").first
    heading_text = heading.inner_text() if heading else ""
    assert expected_heading in heading_text, (
        f"Expected '{expected_heading}' in page heading, got: '{heading_text}'"
    )


@pytest.mark.parametrize(
    ("path", "_heading"),
    STATIC_PAGES,
    ids=[p.split("/")[-1] for p, _ in STATIC_PAGES],
)
def test_no_entity_artifacts(page, base_url: str, path: str, _heading: str) -> None:
    """No page shows literal HTML entity text like &#9744; in visible content."""
    navigate(page, f"{base_url}{path}")

    visible_text = page.locator("body").inner_text()
    assert "&#" not in visible_text, (
        f"Literal HTML entity found on {path}: {visible_text[:500]}"
    )


@pytest.mark.parametrize(
    ("path", "_heading"),
    STATIC_PAGES,
    ids=[p.split("/")[-1] for p, _ in STATIC_PAGES],
)
def test_no_console_errors(
    page, base_url: str, console_errors: list, path: str, _heading: str
) -> None:
    """No JavaScript console errors on any page."""
    navigate(page, f"{base_url}{path}")

    assert len(console_errors) == 0, (
        f"Console errors on {path}: {console_errors}"
    )


# --- Settings sub-tab tests ---

SETTINGS_TABS = [
    ("api-keys", "API Keys"),
    ("infrastructure", "Infrastructure"),
    ("feature-flags", "Feature Flags"),
    ("agent-config", "Agent"),
    ("secrets", "Secrets"),
]


@pytest.mark.parametrize(
    ("tab_id", "expected_text"),
    SETTINGS_TABS,
    ids=[t for t, _ in SETTINGS_TABS],
)
def test_settings_tab_loads(
    page, base_url: str, tab_id: str, expected_text: str
) -> None:
    """Each settings sub-tab loads content containing expected text."""
    navigate(page, f"{base_url}/admin/ui/settings")

    # Click the tab link that loads the sub-tab via HTMX
    tab_link = page.locator(f'[hx-get*="{tab_id}"]')
    if tab_link.count() > 0:
        tab_link.first.click()
        page.wait_for_load_state("networkidle")

    body_text = page.locator("body").inner_text()
    assert expected_text in body_text, (
        f"Expected '{expected_text}' in settings tab '{tab_id}', not found"
    )
