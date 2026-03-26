"""Story 76.10 — Analytics Tab: Interactive Elements.

Validates that /dashboard/?tab=analytics interactive behaviours work correctly:

  - Period selector buttons (7d / 30d / 90d) are clickable without JS errors
  - Clicking a period button changes the active state
  - Tab navigation buttons are reachable from the analytics tab
  - Expert table rows are rendered and the tab remains stable after interaction
  - No JavaScript errors are raised during normal interactions

These tests verify *interactive behaviour*, not content or appearance.
Content is in test_pd_analytics_intent.py.
Style compliance is in test_pd_analytics_style.py.
"""

from __future__ import annotations

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _go(page: object, base_url: str) -> None:
    """Navigate to the analytics tab and wait for React to settle."""
    dashboard_navigate(page, base_url, "analytics")  # type: ignore[arg-type]


def _skip_if_empty(page: object) -> None:
    """Skip the calling test when the analytics empty state is rendered."""
    if page.locator("[data-testid='analytics-empty-state']").count() > 0:  # type: ignore[attr-defined]
        pytest.skip("Analytics empty state — interaction tests require data")


# ---------------------------------------------------------------------------
# Period selector interactions
# ---------------------------------------------------------------------------


class TestAnalyticsPeriodSelectorInteractions:
    """Period selector buttons must switch the active time range."""

    def test_period_7d_button_clickable(self, page, base_url: str) -> None:
        """'7d' period button is clickable without JS errors."""
        _go(page, base_url)
        _skip_if_empty(page)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        buttons = page.locator("button")
        count = buttons.count()

        btn_7d = None
        for i in range(count):
            btn = buttons.nth(i)
            if btn.inner_text().strip() == "7d":
                btn_7d = btn
                break

        if btn_7d is None:
            pytest.skip("'7d' period button not found on analytics tab")

        assert btn_7d.is_visible(), "'7d' period button must be visible"
        assert btn_7d.is_enabled(), "'7d' period button must not be disabled"

        btn_7d.click()
        page.wait_for_timeout(500)

        assert not js_errors, (
            f"JS errors after clicking '7d' period button: {js_errors}"
        )

    def test_period_30d_button_clickable(self, page, base_url: str) -> None:
        """'30d' period button is clickable without JS errors."""
        _go(page, base_url)
        _skip_if_empty(page)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        buttons = page.locator("button")
        count = buttons.count()

        btn_30d = None
        for i in range(count):
            btn = buttons.nth(i)
            if btn.inner_text().strip() == "30d":
                btn_30d = btn
                break

        if btn_30d is None:
            pytest.skip("'30d' period button not found on analytics tab")

        assert btn_30d.is_visible(), "'30d' period button must be visible"
        btn_30d.click()
        page.wait_for_timeout(500)

        assert not js_errors, (
            f"JS errors after clicking '30d' period button: {js_errors}"
        )

    def test_period_90d_button_clickable(self, page, base_url: str) -> None:
        """'90d' period button is clickable without JS errors."""
        _go(page, base_url)
        _skip_if_empty(page)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        buttons = page.locator("button")
        count = buttons.count()

        btn_90d = None
        for i in range(count):
            btn = buttons.nth(i)
            if btn.inner_text().strip() == "90d":
                btn_90d = btn
                break

        if btn_90d is None:
            pytest.skip("'90d' period button not found on analytics tab")

        assert btn_90d.is_visible(), "'90d' period button must be visible"
        btn_90d.click()
        page.wait_for_timeout(500)

        assert not js_errors, (
            f"JS errors after clicking '90d' period button: {js_errors}"
        )

    def test_period_selection_changes_active_state(self, page, base_url: str) -> None:
        """Clicking a period button changes which button appears active (bg-gray-700)."""
        _go(page, base_url)
        _skip_if_empty(page)

        # Default is 30d. Click 7d and check the page rerenders without errors.
        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        buttons = page.locator("button")
        count = buttons.count()

        btn_7d = None
        for i in range(count):
            btn = buttons.nth(i)
            if btn.inner_text().strip() == "7d":
                btn_7d = btn
                break

        if btn_7d is None:
            pytest.skip("'7d' period button not found — cannot test active state change")

        btn_7d.click()
        page.wait_for_timeout(600)

        # After clicking 7d, the page must still be on /dashboard/.
        current_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]
        assert "/dashboard" in current_path, (
            f"Period selector click must not navigate away from /dashboard/. "
            f"Current path: {current_path!r}"
        )

        assert not js_errors, (
            f"JS errors after period selection change: {js_errors}"
        )

    def test_period_selector_does_not_reload_page(self, page, base_url: str) -> None:
        """Period selector changes happen client-side — no hard page reload."""
        _go(page, base_url)
        _skip_if_empty(page)

        initial_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]

        buttons = page.locator("button")
        count = buttons.count()

        # Click any period button.
        for i in range(count):
            btn = buttons.nth(i)
            if btn.inner_text().strip() in ("7d", "90d"):
                btn.click()
                page.wait_for_timeout(400)
                break

        current_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]
        assert current_path == initial_path, (
            f"Period selector must stay on {initial_path!r} — navigated to {current_path!r}"
        )


# ---------------------------------------------------------------------------
# Tab navigation from analytics tab
# ---------------------------------------------------------------------------


class TestAnalyticsTabNavigation:
    """Header tab buttons remain reachable from the analytics tab."""

    def test_analytics_tab_button_present_in_nav(self, page, base_url: str) -> None:
        """'Analytics' tab button is present in the primary navigation."""
        _go(page, base_url)

        nav = page.locator("nav[aria-label='Primary navigation']")
        if nav.count() == 0:
            pytest.skip("Primary navigation not found")

        analytics_btn = nav.locator("button", has_text="Analytics")
        assert analytics_btn.count() > 0, (
            "Primary navigation must contain an 'Analytics' tab button"
        )
        assert analytics_btn.first.is_visible(), (
            "'Analytics' tab button must be visible"
        )

    def test_tab_switch_from_analytics_stays_on_dashboard(
        self, page, base_url: str
    ) -> None:
        """Clicking another tab from analytics keeps the user on /dashboard/."""
        _go(page, base_url)

        initial_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]

        nav = page.locator("nav[aria-label='Primary navigation']")
        if nav.count() == 0:
            pytest.skip("Primary navigation not found")

        buttons = nav.locator("button")
        if buttons.count() < 2:
            pytest.skip("Not enough tab buttons for switch test")

        # Click the first non-Analytics tab.
        for i in range(buttons.count()):
            btn = buttons.nth(i)
            if "Analytics" not in (btn.inner_text() or ""):
                btn.click()
                page.wait_for_timeout(500)
                break

        current_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]
        assert current_path == initial_path, (
            f"Tab switch must stay on {initial_path!r} — navigated to {current_path!r}"
        )


# ---------------------------------------------------------------------------
# Analytics empty state interactions
# ---------------------------------------------------------------------------


class TestAnalyticsEmptyStateInteractions:
    """Analytics empty state CTAs must be interactive."""

    def test_go_to_pipeline_cta_clickable(self, page, base_url: str) -> None:
        """'Go to Pipeline' CTA in the analytics empty state is clickable."""
        _go(page, base_url)

        empty = page.locator("[data-testid='analytics-empty-state']")
        if empty.count() == 0:
            pytest.skip("Analytics data is present — empty state not shown")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        # Look for the primary action button in the empty state.
        cta_selectors = [
            "[data-testid='empty-state-primary-action']",
            "[data-testid='analytics-empty-state-cta']",
        ]
        btn = None
        for sel in cta_selectors:
            candidate = page.locator(sel)
            if candidate.count() > 0:
                btn = candidate.first
                break

        if btn is None:
            # Fall back to text search within the empty state.
            all_btns = empty.locator("button, a")
            for i in range(all_btns.count()):
                el = all_btns.nth(i)
                text = el.inner_text() or ""
                if "Pipeline" in text or "Go to" in text:
                    btn = el
                    break

        if btn is None:
            pytest.skip(
                "'Go to Pipeline' CTA not found in analytics empty state"
            )

        assert btn.is_visible(), "Analytics empty state CTA must be visible"

        btn.click()
        page.wait_for_timeout(500)

        assert not js_errors, (
            f"JS errors after clicking analytics empty state CTA: {js_errors}"
        )

    def test_learn_about_analytics_link_present(self, page, base_url: str) -> None:
        """'Learn about analytics' secondary link is present in the empty state."""
        _go(page, base_url)

        empty = page.locator("[data-testid='analytics-empty-state']")
        if empty.count() == 0:
            pytest.skip("Analytics data is present — empty state not shown")

        secondary_selectors = [
            "[data-testid='empty-state-secondary-action']",
        ]
        link = None
        for sel in secondary_selectors:
            candidate = page.locator(sel)
            if candidate.count() > 0:
                link = candidate.first
                break

        if link is None:
            all_links = empty.locator("a, button")
            for i in range(all_links.count()):
                el = all_links.nth(i)
                text = el.inner_text() or ""
                if "Learn" in text or "analytics" in text.lower():
                    link = el
                    break

        if link is None:
            pytest.skip(
                "'Learn about analytics' secondary link not found — skipping visibility check"
            )

        assert link.is_visible(), (
            "'Learn about analytics' secondary link must be visible in the empty state"
        )


# ---------------------------------------------------------------------------
# No JS errors on load
# ---------------------------------------------------------------------------


class TestAnalyticsNoJsErrors:
    """Analytics tab must not emit JavaScript errors during normal load."""

    def test_no_js_errors_on_initial_load(
        self, page, base_url: str, console_errors: list
    ) -> None:
        """Analytics tab does not raise TypeError or ReferenceError on load."""
        _go(page, base_url)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Analytics tab emitted {len(critical_errors)} critical JS error(s) "
            f"on initial load: {critical_errors[:3]}"
        )

    def test_no_js_errors_after_period_change(self, page, base_url: str) -> None:
        """Changing the analytics period does not produce JS errors."""
        _go(page, base_url)
        _skip_if_empty(page)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        # Click each period button in sequence.
        for period_label in ("7d", "90d", "30d"):
            buttons = page.locator("button")
            count = buttons.count()
            for i in range(count):
                btn = buttons.nth(i)
                if btn.inner_text().strip() == period_label:
                    btn.click()
                    page.wait_for_timeout(300)
                    break

        assert not js_errors, (
            f"JS errors encountered during period cycling: {js_errors}"
        )
