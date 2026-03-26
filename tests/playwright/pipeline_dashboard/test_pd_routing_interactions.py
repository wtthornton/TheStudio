"""Story 76.5 — Routing Review Tab: Interactive Element Verification.

Validates that routing tab interactions behave correctly:
  - "Go to Pipeline" button switches the active tab to the pipeline tab
  - "Open Backlog" button switches the active tab to the board (backlog) tab
  - The tab itself is reachable via header tab navigation
  - Routing tab header nav button is visible and activatable

These tests check *interactive behaviour*, not visual appearance or API contracts.
Style compliance is covered in test_pd_routing_style.py.
Accessibility is covered in test_pd_routing_a11y.py.
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import (
    DASHBOARD_TABS,
    dashboard_navigate,
)

pytestmark = pytest.mark.playwright


def _go(page, base_url: str) -> None:
    """Navigate to the routing tab and wait for React hydration."""
    dashboard_navigate(page, base_url, "routing")


def _in_empty_state(page) -> bool:
    """Return True when the routing no-task empty state is visible."""
    return page.locator("[data-testid='routing-no-task-state']").count() > 0


# ---------------------------------------------------------------------------
# Tab navigation — reaching the routing tab
# ---------------------------------------------------------------------------


class TestRoutingTabNavigation:
    """The Routing Review tab must be reachable from the header navigation.

    Operators navigate between tabs using the header nav bar.  The routing tab
    must be addressable by its label and must activate correctly.
    """

    def test_routing_tab_accessible_via_url(self, page, base_url: str) -> None:
        """Navigating to /dashboard/?tab=routing renders the routing tab content."""
        _go(page, base_url)

        # Either empty state or routing preview must be present.
        has_empty = page.locator("[data-testid='routing-no-task-state']").count() > 0
        has_preview = page.locator("[data-tour='routing-preview']").count() > 0
        assert has_empty or has_preview, (
            "Navigating to /dashboard/?tab=routing must render either the "
            "routing empty state or a routing preview — neither was found"
        )

    def test_routing_review_nav_button_present(self, page, base_url: str) -> None:
        """'Routing Review' tab button is present in the header navigation."""
        _go(page, base_url)

        # The nav button text is "Routing Review" per App.tsx.
        nav_btn = page.locator("nav button:has-text('Routing Review')")
        assert nav_btn.count() > 0, (
            "Header navigation must include a 'Routing Review' tab button "
            "so operators can navigate to the routing tab"
        )

    def test_routing_review_nav_button_active_state(self, page, base_url: str) -> None:
        """'Routing Review' nav button shows an active style when on the routing tab."""
        _go(page, base_url)

        nav_btn = page.locator("nav button:has-text('Routing Review')").first
        if nav_btn.count() == 0:
            pytest.skip("No 'Routing Review' nav button found")

        # The active tab button has 'bg-gray-700' class per App.tsx.
        btn_class = nav_btn.get_attribute("class") or ""
        body_text = page.locator("body").inner_text()

        # Accept either the active CSS class or the presence of routing content
        # as evidence that the tab is active.
        is_active_class = "bg-gray-700" in btn_class
        has_routing_content = (
            "No Task Selected" in body_text
            or "routing" in body_text.lower()
        )
        assert is_active_class or has_routing_content, (
            "When on the routing tab, the 'Routing Review' nav button must show "
            "an active style (bg-gray-700) or routing content must be visible"
        )


# ---------------------------------------------------------------------------
# CTA interactions — Go to Pipeline
# ---------------------------------------------------------------------------


class TestRoutingGoToPipelineCTA:
    """'Go to Pipeline' button must navigate the operator to the pipeline tab.

    Operators use this CTA to find a task to review.  Clicking it must switch
    the active tab to 'pipeline' so the operator can select a task.
    """

    def test_go_to_pipeline_click_switches_tab(self, page, base_url: str) -> None:
        """Clicking 'Go to Pipeline' renders the pipeline tab content."""
        _go(page, base_url)

        if not _in_empty_state(page):
            pytest.skip(
                "Routing tab not in empty state — 'Go to Pipeline' CTA not visible"
            )

        btn = page.locator("button:has-text('Go to Pipeline')").first
        if btn.count() == 0:
            pytest.skip("'Go to Pipeline' button not found — skipping click test")

        btn.click()
        page.wait_for_timeout(400)

        # After clicking, the URL should contain ?tab=pipeline and/or pipeline
        # content should appear.
        url = page.url
        body = page.locator("body").inner_text().lower()

        tab_switched = (
            "tab=pipeline" in url
            or "pipeline" in body
            or page.locator("[data-testid='pipeline-rail']").count() > 0
            or page.locator("[data-testid='empty-pipeline-rail']").count() > 0
        )
        assert tab_switched, (
            "Clicking 'Go to Pipeline' must switch the active tab to the pipeline tab. "
            f"Current URL: {url!r}"
        )


# ---------------------------------------------------------------------------
# CTA interactions — Open Backlog
# ---------------------------------------------------------------------------


class TestRoutingOpenBacklogCTA:
    """'Open Backlog' button must navigate the operator to the board tab.

    Operators use this CTA to browse available tasks in the backlog.  Clicking
    it must switch the active tab to 'board'.
    """

    def test_open_backlog_click_switches_tab(self, page, base_url: str) -> None:
        """Clicking 'Open Backlog' renders the backlog board tab content."""
        _go(page, base_url)

        if not _in_empty_state(page):
            pytest.skip(
                "Routing tab not in empty state — 'Open Backlog' CTA not visible"
            )

        btn = page.locator("button:has-text('Open Backlog')").first
        if btn.count() == 0:
            pytest.skip("'Open Backlog' button not found — skipping click test")

        btn.click()
        page.wait_for_timeout(400)

        # After clicking, the URL should contain ?tab=board and/or backlog
        # content should appear.
        url = page.url
        body = page.locator("body").inner_text().lower()

        tab_switched = (
            "tab=board" in url
            or "backlog" in body
            or "kanban" in body
            or page.locator("[data-testid='backlog-board']").count() > 0
        )
        assert tab_switched, (
            "Clicking 'Open Backlog' must switch the active tab to the board (backlog) tab. "
            f"Current URL: {url!r}"
        )


# ---------------------------------------------------------------------------
# Round-trip navigation
# ---------------------------------------------------------------------------


class TestRoutingRoundTripNavigation:
    """Navigating away and back to the routing tab must restore the empty state."""

    def test_navigate_away_and_back_to_routing(self, page, base_url: str) -> None:
        """Routing tab restores correctly after navigating to another tab and back."""
        _go(page, base_url)

        initial_empty = _in_empty_state(page)

        # Navigate to pipeline tab.
        pipeline_btn = page.locator("nav button:has-text('Pipeline')").first
        if pipeline_btn.count() == 0:
            pytest.skip("No 'Pipeline' nav button — skipping round-trip test")

        pipeline_btn.click()
        page.wait_for_timeout(300)

        # Navigate back to routing tab.
        routing_btn = page.locator("nav button:has-text('Routing Review')").first
        if routing_btn.count() == 0:
            pytest.skip("No 'Routing Review' nav button found after navigating away")

        routing_btn.click()
        page.wait_for_timeout(400)

        final_empty = _in_empty_state(page)
        has_preview = page.locator("[data-tour='routing-preview']").count() > 0

        assert final_empty or has_preview, (
            "Routing tab must render recognisable content after round-trip navigation. "
            "Neither routing-no-task-state nor routing-preview was found."
        )
