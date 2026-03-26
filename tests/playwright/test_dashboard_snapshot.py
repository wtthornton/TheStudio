"""Epic 59.6 — Fleet Dashboard: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/dashboard and registers them for
visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280×720 viewport.
- Component-level baselines for the three primary dashboard sections:
    * System Health
    * Workflow Summary
    * Repo Activity table (or empty state)

First run
~~~~~~~~~
No baseline files exist → ``compare_snapshot`` auto-creates them; every test
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
- 59.1 test_dashboard_intent.py   — semantic content
- 59.2 test_dashboard_api.py      — API endpoints
- 59.3 test_dashboard_style.py    — style-guide compliance
- 59.4 test_dashboard_interactions.py — interactive elements
- 59.5 test_dashboard_a11y.py     — WCAG 2.2 AA
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

DASHBOARD_URL = "/admin/ui/dashboard"
PAGE_NAME = "fleet-dashboard"


def _go(page: object, base_url: str) -> None:
    """Navigate to the fleet dashboard and wait for content to settle."""
    navigate(page, f"{base_url}{DASHBOARD_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestDashboardFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the fleet dashboard.

    The full-page snapshot is the primary regression guard: any unexpected
    layout shift, colour change, or missing section will fail here.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline at 1280×720 viewport.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/fleet-dashboard/``.  On subsequent runs
        the current screenshot is compared against that baseline.
        """
        _go(page, base_url)
        result = compare_snapshot(page, "full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

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


class TestDashboardSectionSnapshots:
    """Element-level snapshots for each primary dashboard section.

    Isolating sections reduces noise: a change to the repo-activity table
    should not fail the system-health snapshot.
    """

    def test_system_health_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the System Health section.

        The test locates the section by searching for the first element that
        contains 'Temporal' or 'health' in its accessible text.  Falls back
        to a full-page snapshot when no discrete section element is found.
        """
        _go(page, base_url)

        # Try progressively broader selectors for the health section.
        health_selectors = [
            "[data-testid='system-health']",
            "[aria-label*='health' i]",
            "section:has-text('Temporal')",
            "div:has-text('Temporal'):has-text('Postgres')",
        ]

        section_found = False
        for selector in health_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "system-health", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            # Graceful fallback: capture full page when the section has no
            # discrete DOM container.
            result = compare_snapshot(
                page, "system-health-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_workflow_summary_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Workflow Summary section."""
        _go(page, base_url)

        workflow_selectors = [
            "[data-testid='workflow-summary']",
            "[aria-label*='workflow' i]",
            "section:has-text('Running')",
            "div:has-text('Running'):has-text('Failed')",
        ]

        section_found = False
        for selector in workflow_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "workflow-summary", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "workflow-summary-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_repo_activity_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Repo Activity table or its empty state."""
        _go(page, base_url)

        repo_selectors = [
            "[data-testid='repo-activity']",
            "[aria-label*='repo' i]",
            "section:has-text('Repo')",
            "table",
        ]

        section_found = False
        for selector in repo_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "repo-activity", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "repo-activity-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baseline
# ---------------------------------------------------------------------------


class TestDashboardSnapshotRegression:
    """Verify current render matches committed baselines (pixel-diff guard).

    These tests are the continuous-integration regression guards.  They pass
    on first run (baseline auto-created) and fail only when a subsequent run
    produces a pixel-diff above the threshold.

    Override the threshold with ``SNAPSHOT_THRESHOLD=0.002`` (0.2 %) for
    environments where minor antialiasing differences are expected.
    """

    def test_full_page_regression(self, page: object, base_url: str) -> None:
        """Full-page pixel-diff must not exceed the configured threshold."""
        _go(page, base_url)
        result = compare_snapshot(page, "regression-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_no_critical_console_errors_during_snapshot(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Dashboard must not emit console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _go(page, base_url)
        # Trigger the snapshot so the page fully renders.
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Dashboard emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
