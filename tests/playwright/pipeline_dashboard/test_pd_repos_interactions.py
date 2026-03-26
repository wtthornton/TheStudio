"""Story 76.12 — Pipeline Dashboard: Repos Tab — Interactive Elements.

Validates that /dashboard/?tab=repos interactive behaviours work correctly:

  - Repo card (table row) click loads the config editor for that repo
  - Save/edit form in the config editor is interactive (inputs, buttons)
  - Refresh button reloads repository data without a page reload
  - Tour beacon ([data-tour]) is present and reachable
  - Tab navigation buttons switch views without JS errors
  - No JavaScript errors are raised during normal interactions

These tests verify *interactive behaviour*, not content or appearance.
Content is in test_pd_repos_intent.py.
Style compliance is in test_pd_repos_style.py.
"""

from __future__ import annotations

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _go(page: object, base_url: str) -> None:
    """Navigate to the repos tab and wait for React to settle."""
    dashboard_navigate(page, base_url, "repos")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tab navigation
# ---------------------------------------------------------------------------


class TestReposTabNavigation:
    """Header tab buttons must switch views without a full page reload."""

    def test_repos_tab_button_present_in_nav(self, page, base_url: str) -> None:
        """'Repos' tab button is present and visible in the primary navigation."""
        _go(page, base_url)

        nav = page.locator("nav[aria-label='Primary navigation']")
        assert nav.count() > 0, "Primary navigation landmark must be present"

        repos_btn = nav.locator("button", has_text="Repos")
        assert repos_btn.count() > 0, (
            "Header nav must contain a 'Repos' tab button"
        )
        assert repos_btn.first.is_visible(), (
            "'Repos' tab button must be visible"
        )

    def test_tab_switch_does_not_navigate_away(self, page, base_url: str) -> None:
        """Clicking a tab button keeps the user on /dashboard/ (no hard navigate)."""
        _go(page, base_url)

        initial_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]

        nav = page.locator("nav[aria-label='Primary navigation']")
        buttons = nav.locator("button")
        if buttons.count() < 2:
            pytest.skip("Not enough tab buttons for switch test")

        # Click the first tab button.
        buttons.nth(0).click()
        page.wait_for_timeout(500)

        current_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]
        assert current_path == initial_path, (
            f"Tab switch must stay on {initial_path!r} — navigated to {current_path!r}"
        )

    def test_tab_switch_no_js_errors(self, page, base_url: str) -> None:
        """Clicking another tab does not emit critical JS errors."""
        _go(page, base_url)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        nav = page.locator("nav[aria-label='Primary navigation']")
        pipeline_btn = nav.locator("button", has_text="Pipeline")

        if pipeline_btn.count() == 0:
            pytest.skip("No 'Pipeline' tab button found in navigation")

        pipeline_btn.first.click()
        page.wait_for_timeout(600)

        assert not js_errors, (
            f"JS errors after clicking Pipeline tab from Repos: {js_errors}"
        )


# ---------------------------------------------------------------------------
# Repo row click → config editor
# ---------------------------------------------------------------------------


class TestRepoRowClick:
    """Clicking a repo row must open the config editor for that repo."""

    def test_repo_row_click_shows_config_panel(self, page, base_url: str) -> None:
        """Clicking the first repo row displays the Repo Configuration panel."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No repo table — empty state shown, no rows to click")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            pytest.skip("No repo rows in table — nothing to click")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        # Click the first data row.
        rows.first.click()
        page.wait_for_timeout(700)

        assert not js_errors, (
            f"JS errors after clicking repo row: {js_errors}"
        )

        # Config panel should now be visible.
        config_panel = page.locator("[data-tour='repo-config']")
        assert config_panel.count() > 0, (
            "Clicking a repo row must display the Repo Configuration panel "
            "(data-tour='repo-config')"
        )

    def test_repo_row_click_shows_config_heading(self, page, base_url: str) -> None:
        """After clicking a repo row the 'Repo Configuration' heading appears."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No repo table — empty state shown")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            pytest.skip("No repo rows in table")

        rows.first.click()
        page.wait_for_timeout(700)

        body = page.locator("body").inner_text()
        assert "Repo Configuration" in body or "Repository Configuration" in body, (
            "After clicking a repo row, 'Repo Configuration' heading must appear "
            "in the config panel"
        )

    def test_second_row_click_switches_config(self, page, base_url: str) -> None:
        """Clicking a second repo row switches the config editor to that repo."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No repo table — empty state shown")

        rows = page.locator("table tbody tr")
        if rows.count() < 2:
            pytest.skip("Only one repo row — cannot test row switching")

        rows.first.click()
        page.wait_for_timeout(500)

        rows.nth(1).click()
        page.wait_for_timeout(700)

        # Config panel must still be visible after the switch.
        config_panel = page.locator("[data-tour='repo-config']")
        assert config_panel.count() > 0, (
            "Clicking a second repo row must keep the config panel open "
            "(switching the selected repo)"
        )

    def test_repo_row_click_same_row_deselects(self, page, base_url: str) -> None:
        """Clicking the same repo row a second time closes the config panel."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No repo table — empty state shown")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            pytest.skip("No repo rows in table")

        rows.first.click()
        page.wait_for_timeout(500)

        # Click again to deselect.
        rows.first.click()
        page.wait_for_timeout(500)

        config_panel = page.locator("[data-tour='repo-config']")
        assert config_panel.count() == 0, (
            "Clicking the same repo row a second time must deselect it and "
            "hide the config panel"
        )


# ---------------------------------------------------------------------------
# Refresh button
# ---------------------------------------------------------------------------


class TestReposRefreshButton:
    """Refresh button must reload fleet health data without a page reload."""

    def test_refresh_button_click_no_js_errors(self, page, base_url: str) -> None:
        """Clicking 'Refresh' does not emit critical JS errors."""
        _go(page, base_url)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        buttons = page.locator("button")  # type: ignore[attr-defined]
        refresh_btn = None
        count = buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            label = btn.inner_text() or ""
            if "Refresh" in label or "↺" in label:
                refresh_btn = btn
                break

        if refresh_btn is None:
            pytest.skip("No 'Refresh' button found on repos tab")

        refresh_btn.click()
        page.wait_for_timeout(800)

        assert not js_errors, (
            f"JS errors after clicking Refresh: {js_errors}"
        )

    def test_refresh_button_stays_on_same_path(self, page, base_url: str) -> None:
        """Clicking 'Refresh' keeps the user on /dashboard/ (no navigation)."""
        _go(page, base_url)

        initial_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]

        buttons = page.locator("button")  # type: ignore[attr-defined]
        refresh_btn = None
        count = buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            label = btn.inner_text() or ""
            if "Refresh" in label or "↺" in label:
                refresh_btn = btn
                break

        if refresh_btn is None:
            pytest.skip("No 'Refresh' button found on repos tab")

        refresh_btn.click()
        page.wait_for_timeout(800)

        current_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]
        assert current_path == initial_path, (
            f"Refresh must not navigate away from {initial_path!r}"
        )


# ---------------------------------------------------------------------------
# Tour beacon
# ---------------------------------------------------------------------------


class TestReposTourBeacon:
    """Product tour beacon must be reachable on the repos tab.

    The [data-tour='repo-selector'] attribute on the fleet health panel
    is the anchor for the guided tour.
    """

    def test_tour_beacon_present(self, page, base_url: str) -> None:
        """data-tour='repo-selector' beacon is present on the fleet health panel."""
        _go(page, base_url)

        beacon = page.locator("[data-tour='repo-selector']")  # type: ignore[attr-defined]
        assert beacon.count() > 0, (
            "Repos tab must include a [data-tour='repo-selector'] beacon "
            "on the fleet health panel for the guided tour"
        )

    def test_tour_beacon_visible(self, page, base_url: str) -> None:
        """data-tour='repo-selector' beacon element is visible in the viewport."""
        _go(page, base_url)

        beacon = page.locator("[data-tour='repo-selector']").first  # type: ignore[attr-defined]
        if beacon.count() == 0:
            pytest.skip("Tour beacon not found on repos tab")

        assert beacon.is_visible(), (
            "[data-tour='repo-selector'] element must be visible "
            "so the product tour can anchor to it"
        )


# ---------------------------------------------------------------------------
# Config form interactivity
# ---------------------------------------------------------------------------


class TestReposConfigFormInteractivity:
    """Config form inputs and save button must be interactive after row selection."""

    def test_config_form_has_inputs_after_row_click(
        self, page, base_url: str
    ) -> None:
        """After clicking a repo row the config form shows at least one input."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No repo table — empty state shown")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            pytest.skip("No repo rows in table")

        rows.first.click()
        page.wait_for_timeout(700)

        config_panel = page.locator("[data-tour='repo-config']")
        if config_panel.count() == 0:
            pytest.skip("Config panel did not appear after row click")

        inputs = config_panel.locator("input, select, textarea")
        assert inputs.count() > 0, (
            "Repo Configuration panel must include at least one form input "
            "after a repo row is selected"
        )

    def test_config_form_save_button_present(self, page, base_url: str) -> None:
        """Config form shows a save/submit button after repo row is selected."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No repo table — empty state shown")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            pytest.skip("No repo rows in table")

        rows.first.click()
        page.wait_for_timeout(700)

        config_panel = page.locator("[data-tour='repo-config']")
        if config_panel.count() == 0:
            pytest.skip("Config panel did not appear after row click")

        # Accept any submit/save button inside the config panel.
        save_btn = config_panel.locator(
            "button[type='submit'], button:has-text('Save'), button:has-text('Update')"
        )
        assert save_btn.count() > 0, (
            "Repo Configuration form must include a Save / Update submit button"
        )

    def test_config_form_inputs_are_enabled(self, page, base_url: str) -> None:
        """Form inputs inside the config panel are enabled (not disabled)."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No repo table — empty state shown")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            pytest.skip("No repo rows in table")

        rows.first.click()
        page.wait_for_timeout(700)

        config_panel = page.locator("[data-tour='repo-config']")
        if config_panel.count() == 0:
            pytest.skip("Config panel did not appear after row click")

        inputs = config_panel.locator("input:not([type='hidden'])")
        if inputs.count() == 0:
            pytest.skip("No visible inputs found in config panel")

        disabled_count = sum(
            1
            for i in range(inputs.count())
            if not inputs.nth(i).is_enabled()
        )
        assert disabled_count == 0, (
            f"{disabled_count} form input(s) in the config panel are disabled — "
            "all editable inputs must be enabled on load"
        )
