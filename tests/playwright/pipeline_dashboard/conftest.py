"""Playwright fixtures and helpers for the React Pipeline Dashboard SPA.

The dashboard is a single-page application served from /dashboard/. Tab content
renders client-side via React Router query params — the catch-all route always
returns HTTP 200 regardless of ?tab=... value.
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

# ---------------------------------------------------------------------------
# URL / tab registry
# ---------------------------------------------------------------------------

DASHBOARD_URL = "/dashboard/"

DASHBOARD_TABS = {
    "pipeline": {"label": "Pipeline", "query": "?tab=pipeline"},
    "triage": {"label": "Triage", "query": "?tab=triage"},
    "intent": {"label": "Intent Review", "query": "?tab=intent"},
    "routing": {"label": "Routing Review", "query": "?tab=routing"},
    "board": {"label": "Backlog", "query": "?tab=board"},
    "trust": {"label": "Trust Tiers", "query": "?tab=trust"},
    "budget": {"label": "Budget", "query": "?tab=budget"},
    "activity": {"label": "Activity Log", "query": "?tab=activity"},
    "analytics": {"label": "Analytics", "query": "?tab=analytics"},
    "reputation": {"label": "Reputation", "query": "?tab=reputation"},
    "repos": {"label": "Repos", "query": "?tab=repos"},
    "api": {"label": "API", "query": "?tab=api"},
}

ALL_TAB_IDS: list[str] = list(DASHBOARD_TABS.keys())

# ---------------------------------------------------------------------------
# Navigation helper
# ---------------------------------------------------------------------------


def dashboard_navigate(page, base_url: str, tab: str) -> None:
    """Navigate the Playwright page to a specific dashboard tab.

    Args:
        page: Playwright Page object.
        base_url: Root URL of the running app (e.g. "http://localhost:9080").
            Must not have a trailing slash — matches the base_url fixture.
        tab: Key from DASHBOARD_TABS (e.g. "pipeline", "triage").

    Raises:
        KeyError: If *tab* is not a recognised key in DASHBOARD_TABS.
    """
    if tab not in DASHBOARD_TABS:
        valid = ", ".join(sorted(DASHBOARD_TABS))
        raise KeyError(
            f"Unknown dashboard tab {tab!r}. Valid tabs: {valid}"
        )

    query = DASHBOARD_TABS[tab]["query"]
    url = f"{base_url}{DASHBOARD_URL}{query}"

    navigate(page, url)

    # Allow React to hydrate and render the tab content before assertions.
    # Increase this value if tests prove flaky on slower CI machines.
    page.wait_for_timeout(500)
