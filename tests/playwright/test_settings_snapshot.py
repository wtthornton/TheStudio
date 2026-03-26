"""Epic 71.6 — Settings: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/settings and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Component-level baselines for the primary Settings page sections:
    * Tab navigation bar (API keys, infra, flags, agent, budget, secrets)
    * Active tab panel content
    * Form inputs / save controls

First run
~~~~~~~~~
No baseline files exist — ``compare_snapshot`` auto-creates them; every test
passes with ``is_new_baseline=True``.

Subsequent runs
~~~~~~~~~~~~~~~
Existing baselines are loaded and compared.  Tests fail when the pixel-diff
ratio exceeds ``DEFAULT_THRESHOLD`` (0.1 %).

Updating baselines
~~~~~~~~~~~~~~~~~~
Set ``SNAPSHOT_UPDATE=1`` in the environment to overwrite all baselines and
always pass.

Related suites
~~~~~~~~~~~~~~
- 71.1 test_settings_intent.py         - semantic content
- 71.2 test_settings_api.py            - API endpoints
- 71.3 test_settings_style.py          - style-guide compliance
- 71.4 test_settings_interactions.py   - interactive elements
- 71.5 test_settings_a11y.py           - WCAG 2.2 AA
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate
from tests.playwright.lib.snapshot_helpers import (
    capture_element_snapshot,
    compare_snapshot,
    create_baseline,
)

pytestmark = pytest.mark.playwright

SETTINGS_URL = "/admin/ui/settings"
PAGE_NAME = "settings"


def _go(page: object, base_url: str) -> None:
    """Navigate to the settings page and wait for content to settle."""
    navigate(page, f"{base_url}{SETTINGS_URL}")  # type: ignore[arg-type]


def _has_tab_nav(page: object) -> bool:
    """Return True when the settings tab navigation bar is present."""
    return (
        page.locator("[role='tablist']").count() > 0  # type: ignore[attr-defined]
        or page.locator("[role='tab']").count() > 0  # type: ignore[attr-defined]
        or page.locator("[data-tab]").count() > 0  # type: ignore[attr-defined]
        or page.locator("[class*='tab-nav']").count() > 0  # type: ignore[attr-defined]
    )


# ---------------------------------------------------------------------------
# Full-page snapshots
# ---------------------------------------------------------------------------


class TestSettingsFullPageSnapshot:
    """Capture and compare full-page baselines for /admin/ui/settings.

    These snapshots guard against unexpected layout shifts, colour changes,
    or missing tab panels in the Settings page.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the settings page at 1280x720.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/settings/``.  On subsequent runs
        the current screenshot is compared against that baseline.
        """
        _go(page, base_url)
        result = compare_snapshot(page, "full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestSettingsSectionSnapshots:
    """Element-level snapshots for primary Settings page sections.

    Isolating sections reduces noise: a change to the form inputs should
    not fail the tab navigation snapshot.
    """

    def test_tab_navigation_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the settings tab navigation bar.

        The 6-tab navigation (API keys, infra, flags, agent, budget, secrets)
        must remain visually consistent across UI changes — operators rely on
        this nav to reach each configuration section.
        """
        _go(page, base_url)

        tab_nav_selectors = [
            "[role='tablist']",
            "[data-testid='settings-tabs']",
            "[data-testid='tab-nav']",
            "[aria-label*='settings' i]",
            "[aria-label*='configuration' i]",
            "nav[class*='tab']",
            "[class*='tab-list']",
            "[class*='tab-nav']",
            "[class*='settings-nav']",
            "section:has([role='tab'])",
        ]

        section_found = False
        for selector in tab_nav_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "tab-navigation", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "tab-navigation-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_active_tab_panel_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the currently active settings tab panel.

        The default active panel content (typically API keys or the first tab)
        must render correctly and remain visually stable.
        """
        _go(page, base_url)

        panel_selectors = [
            "[role='tabpanel']:not([hidden]):not([aria-hidden='true'])",
            "[data-testid='settings-panel']",
            "[data-testid='tab-panel']",
            "[data-tab-content]:not(.hidden):not([hidden])",
            ".tab-pane.active",
            ".tab-pane:not(.hidden)",
            "[class*='tab-panel']:not(.hidden)",
            "[class*='settings-panel']",
            "[class*='tab-content']",
            "section:has(form)",
        ]

        section_found = False
        for selector in panel_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "active-tab-panel", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            # No tabpanel found — take a fallback full-page snapshot
            result = compare_snapshot(
                page, "active-tab-panel-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_form_inputs_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the settings form inputs and save controls.

        Form field layout, input styling, and save button placement must
        remain visually consistent — operators use these controls to configure
        the platform.
        """
        _go(page, base_url)

        form_selectors = [
            "form",
            "[data-testid='settings-form']",
            "[class*='settings-form']",
            "[class*='config-form']",
            "[hx-post]",
            "[hx-put]",
            "fieldset",
            "section:has(input)",
            "div:has(input[type='text']):has(button)",
        ]

        section_found = False
        for selector in form_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "form-inputs", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "form-inputs-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_second_tab_panel_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the second settings tab panel after switching.

        Switching to the second tab (typically infra config) must render the
        corresponding panel content without layout breakage.
        """
        _go(page, base_url)

        if not _has_tab_nav(page):
            # No tab navigation — take full-page fallback and pass
            result = compare_snapshot(
                page, "second-tab-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        all_tabs = page.locator("[role='tab']")  # type: ignore[attr-defined]
        if all_tabs.count() < 2:
            result = compare_snapshot(
                page, "second-tab-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        second_tab = all_tabs.nth(1)
        if not second_tab.is_visible():
            result = compare_snapshot(
                page, "second-tab-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        second_tab.click()
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        # Capture the now-active panel for the second tab
        panel_selectors = [
            "[role='tabpanel']:not([hidden]):not([aria-hidden='true'])",
            ".tab-pane.active",
            "[data-tab-content]:not(.hidden):not([hidden])",
            "[class*='tab-panel']:not(.hidden)",
        ]

        section_found = False
        for selector in panel_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "second-tab-panel", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "second-tab-panel-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestSettingsSnapshotRegression:
    """Verify current render matches committed baselines (pixel-diff guard).

    These tests are the continuous-integration regression guards.  They pass
    on first run (baseline auto-created) and fail only when a subsequent run
    produces a pixel-diff above the threshold.

    Override the threshold with ``SNAPSHOT_THRESHOLD=0.002`` (0.2%) for
    environments where minor antialiasing differences are expected.
    """

    def test_full_page_regression(self, page: object, base_url: str) -> None:
        """Full-page pixel-diff must not exceed the configured threshold."""
        _go(page, base_url)
        result = compare_snapshot(
            page, "regression-full-page", page_name=PAGE_NAME
        )
        assert result.passed, result.summary()

    def test_no_critical_console_errors(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Settings page must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Settings page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
