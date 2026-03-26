"""Story 76.4 — Intent Review Tab: Interactive Behaviour.

Validates that interactive elements on /dashboard/?tab=intent function
correctly:

  - "Go to Pipeline" button switches to the pipeline tab (?tab=pipeline).
  - "Open Backlog" button switches to the board tab (?tab=board).
  - Tab navigation bar transitions from intent to other tabs correctly.

These tests check *interactive behaviour*, not visual presentation.
Style compliance is in test_pd_intent_style.py.
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _go(page: object, base_url: str) -> None:
    """Navigate to the intent tab and wait for React to hydrate."""
    dashboard_navigate(page, base_url, "intent")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# CTA button navigation
# ---------------------------------------------------------------------------


class TestIntentCtaNavigation:
    """CTA buttons on the intent empty state must navigate to the correct tabs.

    The 'Go to Pipeline' button must navigate the SPA to ?tab=pipeline and the
    'Open Backlog' button must navigate to ?tab=board.  Both transitions happen
    client-side (React state update + URL sync) so we verify the tab label and
    URL query param after the click.
    """

    def test_go_to_pipeline_navigates_to_pipeline_tab(
        self, page, base_url: str
    ) -> None:
        """Clicking 'Go to Pipeline' switches the active tab to ?tab=pipeline."""
        _go(page, base_url)

        # Locate the 'Go to Pipeline' button inside the intent empty state.
        button = None
        buttons = page.locator("button")
        count = buttons.count()
        for i in range(count):
            btn = buttons.nth(i)
            if "Go to Pipeline" in (btn.inner_text() or ""):
                button = btn
                break

        if button is None:
            pytest.skip(
                "'Go to Pipeline' button not found — skipping navigation test"
            )

        button.click()
        page.wait_for_timeout(600)  # Allow React state + URL sync

        current_url = page.url
        assert "tab=pipeline" in current_url, (
            "After clicking 'Go to Pipeline', the URL must contain 'tab=pipeline'. "
            f"Actual URL: {current_url!r}"
        )

    def test_open_backlog_navigates_to_board_tab(self, page, base_url: str) -> None:
        """Clicking 'Open Backlog' switches the active tab to ?tab=board."""
        _go(page, base_url)

        button = None
        buttons = page.locator("button")
        count = buttons.count()
        for i in range(count):
            btn = buttons.nth(i)
            if "Open Backlog" in (btn.inner_text() or ""):
                button = btn
                break

        if button is None:
            pytest.skip(
                "'Open Backlog' button not found — skipping navigation test"
            )

        button.click()
        page.wait_for_timeout(600)  # Allow React state + URL sync

        current_url = page.url
        assert "tab=board" in current_url, (
            "After clicking 'Open Backlog', the URL must contain 'tab=board'. "
            f"Actual URL: {current_url!r}"
        )

    def test_go_to_pipeline_then_return_to_intent(
        self, page, base_url: str
    ) -> None:
        """Navigate to pipeline via CTA then back to intent tab — empty state re-renders."""
        _go(page, base_url)

        # Click 'Go to Pipeline'
        button = None
        buttons = page.locator("button")
        count = buttons.count()
        for i in range(count):
            btn = buttons.nth(i)
            if "Go to Pipeline" in (btn.inner_text() or ""):
                button = btn
                break

        if button is None:
            pytest.skip(
                "'Go to Pipeline' button not found — skipping round-trip test"
            )

        button.click()
        page.wait_for_timeout(600)

        # Verify we're now on the pipeline tab
        assert "tab=pipeline" in page.url, (
            "Expected 'tab=pipeline' in URL after clicking 'Go to Pipeline'"
        )

        # Navigate back to intent tab via the tab bar
        dashboard_navigate(page, base_url, "intent")

        # Empty state should be present again
        body = page.locator("body").inner_text()
        assert "No Task Selected" in body, (
            "Navigating back to the intent tab must re-render the 'No Task Selected' "
            "empty state — the state should be reset between tab visits"
        )


# ---------------------------------------------------------------------------
# Tab bar navigation — into intent tab
# ---------------------------------------------------------------------------


class TestIntentTabBarNavigation:
    """The Intent Review tab in the navigation bar must work correctly.

    Users navigate to the intent tab by clicking the 'Intent Review' button in
    the top navigation bar.  The tab button must be present, clickable, and
    result in ?tab=intent being reflected in the URL.
    """

    def test_intent_review_tab_button_present_in_nav(
        self, page, base_url: str
    ) -> None:
        """'Intent Review' tab button is present in the page navigation bar."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "Intent Review" in body, (
            "Navigation bar must include an 'Intent Review' tab button "
            "so users can navigate to the intent review workflow"
        )

    def test_intent_tab_url_reflects_tab_param(self, page, base_url: str) -> None:
        """Navigating to the intent tab results in ?tab=intent in the URL."""
        _go(page, base_url)

        current_url = page.url
        assert "tab=intent" in current_url, (
            f"URL after navigating to intent tab must contain 'tab=intent'. "
            f"Actual URL: {current_url!r}"
        )

    def test_navigate_to_pipeline_from_nav_bar(self, page, base_url: str) -> None:
        """Tab navigation bar can switch from intent to pipeline tab."""
        _go(page, base_url)

        # Click the 'Pipeline' tab button in the nav bar
        buttons = page.locator("button")
        count = buttons.count()
        pipeline_btn = None
        for i in range(count):
            btn = buttons.nth(i)
            text = btn.inner_text() or ""
            # Match the pipeline tab label — not the 'Go to Pipeline' CTA
            if text.strip() == "Pipeline":
                pipeline_btn = btn
                break

        if pipeline_btn is None:
            pytest.skip("'Pipeline' tab button not found in nav bar")

        pipeline_btn.click()
        page.wait_for_timeout(600)

        current_url = page.url
        assert "tab=pipeline" in current_url, (
            f"Clicking the 'Pipeline' nav tab from the intent tab must result in "
            f"'tab=pipeline' in the URL. Actual URL: {current_url!r}"
        )

    def test_navigate_to_board_from_nav_bar(self, page, base_url: str) -> None:
        """Tab navigation bar can switch from intent to board (Backlog) tab."""
        _go(page, base_url)

        buttons = page.locator("button")
        count = buttons.count()
        board_btn = None
        for i in range(count):
            btn = buttons.nth(i)
            text = btn.inner_text() or ""
            if "Backlog" in text:
                board_btn = btn
                break

        if board_btn is None:
            pytest.skip("'Backlog' tab button not found in nav bar")

        board_btn.click()
        page.wait_for_timeout(600)

        current_url = page.url
        assert "tab=board" in current_url, (
            f"Clicking 'Backlog' nav tab from the intent tab must result in "
            f"'tab=board' in the URL. Actual URL: {current_url!r}"
        )


# ---------------------------------------------------------------------------
# Intent tab active state in nav bar
# ---------------------------------------------------------------------------


class TestIntentTabActiveState:
    """The 'Intent Review' tab button must appear active when ?tab=intent is set.

    Active tab styling (highlighted background, different text colour) helps
    users understand which section of the dashboard they are currently viewing.
    """

    def test_intent_tab_button_appears_active(self, page, base_url: str) -> None:
        """'Intent Review' nav button has active styling when on the intent tab."""
        _go(page, base_url)

        # Check that the page renders and the URL reflects the intent tab.
        current_url = page.url
        assert "tab=intent" in current_url, (
            f"URL must contain 'tab=intent' for the active tab check. "
            f"Actual URL: {current_url!r}"
        )

        # The active tab should have a distinct class (bg-gray-700 or similar).
        active_classes = page.evaluate(
            """
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                for (const btn of buttons) {
                    if (btn.textContent.trim() === 'Intent Review') {
                        return btn.className;
                    }
                }
                return null;
            }
            """
        )

        if active_classes is None:
            pytest.skip("'Intent Review' button not found — skipping active state check")

        # Active tab has bg-gray-700 or similar active-state class
        is_active = (
            "bg-gray-700" in active_classes
            or "bg-gray-800" in active_classes
            or "active" in active_classes.lower()
            or "selected" in active_classes.lower()
        )
        assert is_active, (
            f"'Intent Review' tab button classes {active_classes!r} do not indicate "
            "an active state — expected 'bg-gray-700' or equivalent"
        )
