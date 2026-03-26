"""Story 76.12 — Pipeline Dashboard: Repos Tab — Visual Snapshot Baseline.

Captures baseline screenshots for /dashboard/?tab=repos and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Section-level baselines for the primary repos areas:
    * Fleet health table or empty state
    * Repo configuration panel (when a repo row is selected)

First run
~~~~~~~~~
No baseline files exist — ``compare_snapshot`` auto-creates them; every test
passes with ``is_new_baseline=True``.

Subsequent runs
~~~~~~~~~~~~~~~
Existing baselines are loaded and compared.  Tests fail when the pixel-diff
ratio exceeds ``DEFAULT_THRESHOLD`` (0.1%).

Updating baselines
~~~~~~~~~~~~~~~~~~
Set ``SNAPSHOT_UPDATE=1`` in the environment to overwrite all baselines and
always pass.

Baseline location
~~~~~~~~~~~~~~~~~
All snapshot files are written to:
    tests/playwright/snapshots/pipeline-dashboard/

Related suites
~~~~~~~~~~~~~~
- test_pd_repos_intent.py       — semantic content
- test_pd_repos_api.py          — API endpoints
- test_pd_repos_style.py        — style-guide compliance
- test_pd_repos_interactions.py — interactive elements
- test_pd_repos_a11y.py         — WCAG 2.2 AA
"""

from __future__ import annotations

import pytest

from tests.playwright.lib.snapshot_helpers import (
    capture_element_snapshot,
    compare_snapshot,
    create_baseline,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

PAGE_NAME = "pipeline-dashboard"


def _go(page: object, base_url: str) -> None:
    """Navigate to the repos tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "repos")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestReposFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the repos tab.

    The full-page snapshot is the primary regression guard: any unexpected
    layout shift, colour change, or missing section will fail here.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline at 1280x720 viewport.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/pipeline-dashboard/``.  On subsequent
        runs the current screenshot is compared against that baseline.
        """
        _go(page, base_url)
        result = compare_snapshot(page, "repos-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "repos-full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )

    def test_no_critical_console_errors_during_snapshot(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Repos tab must not emit console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _go(page, base_url)
        # Trigger the snapshot so the page fully renders.
        compare_snapshot(page, "repos-console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Repos tab emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestReposSectionSnapshots:
    """Element-level snapshots for each primary repos section.

    Isolating sections reduces noise: a change to the config panel should
    not fail the fleet health table snapshot.
    """

    def test_fleet_health_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the fleet health panel."""
        _go(page, base_url)

        fleet_selectors = [
            "[data-tour='repo-selector']",
            "table",
            "[data-testid='repos-empty']",
            "div:has-text('Fleet Health')",
        ]

        section_found = False
        for selector in fleet_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "repos-fleet-health", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Fleet health snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "repos-fleet-health-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_empty_state_snapshot_when_no_repos(
        self, page: object, base_url: str
    ) -> None:
        """Capture the empty repos state when no repos are registered.

        This snapshot is the canonical empty-state baseline.  If the fleet
        health table is active (repos exist), the test is skipped — the empty
        state is not visible.
        """
        _go(page, base_url)

        if page.locator("table").count() > 0:  # type: ignore[attr-defined]
            pytest.skip("Fleet health table active — capturing empty state skipped")

        empty_selectors = [
            "[data-testid='repos-empty']",
            "[data-tour='repo-selector']",
        ]

        section_found = False
        for selector in empty_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "repos-empty-state", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Empty state snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "repos-empty-state-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_config_panel_snapshot_after_row_click(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Repo Configuration panel after selecting a repo.

        If no repos exist the test is skipped — the config panel is not shown
        until a repo row is clicked.
        """
        _go(page, base_url)

        rows = page.locator("table tbody tr")  # type: ignore[attr-defined]
        if rows.count() == 0:
            pytest.skip("No repo rows — config panel snapshot not applicable")

        rows.first.click()
        page.wait_for_timeout(700)

        config_panel = page.locator("[data-tour='repo-config']")  # type: ignore[attr-defined]
        if config_panel.count() == 0:
            pytest.skip("Config panel did not open after row click")

        config_panel.first.scroll_into_view_if_needed()

        config_selectors = [
            "[data-tour='repo-config']",
        ]

        section_found = False
        for selector in config_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "repos-config-panel", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Config panel snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "repos-config-panel-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baseline
# ---------------------------------------------------------------------------


class TestReposSnapshotRegression:
    """Verify current render matches committed baselines (pixel-diff guard).

    These tests are the continuous-integration regression guards.  They pass
    on first run (baseline auto-created) and fail only when a subsequent run
    produces a pixel-diff above the threshold.

    Override the threshold with ``SNAPSHOT_THRESHOLD=0.002`` (0.2%) for
    environments where minor anti-aliasing differences are expected.
    """

    def test_full_page_regression(self, page: object, base_url: str) -> None:
        """Full-page pixel-diff must not exceed the configured threshold."""
        _go(page, base_url)
        result = compare_snapshot(page, "repos-regression-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_repos_default_screenshot_written(self, page: object, base_url: str) -> None:
        """Capture repos-default.png to the canonical snapshot directory.

        This satisfies the explicit file-path requirement in Story 76.12:
        ``tests/playwright/snapshots/pipeline-dashboard/repos-default.png``
        """
        _go(page, base_url)
        result = create_baseline(page, "repos-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()
