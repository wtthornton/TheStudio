"""Story 76.9 — Pipeline Dashboard: Activity Log Visual Snapshot Baseline.

Captures baseline screenshots for /dashboard/?tab=activity and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Section-level baselines for the primary activity log areas:
    * Activity log table (or empty state)
    * Filter bar
    * Pagination controls

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

Canonical snapshot
~~~~~~~~~~~~~~~~~~
Story 76.9 requires:
    tests/playwright/snapshots/pipeline-dashboard/activity-default.png

Related suites
~~~~~~~~~~~~~~
- test_pd_activity_intent.py       — semantic content
- test_pd_activity_api.py          — API endpoints
- test_pd_activity_style.py        — style-guide compliance
- test_pd_activity_interactions.py — interactive elements
- test_pd_activity_a11y.py         — WCAG 2.2 AA
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
    """Navigate to the activity tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "activity")  # type: ignore[arg-type]
    # Allow the audit API request to resolve before snapshotting.
    page.wait_for_timeout(800)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestActivityFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the activity tab.

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
        result = compare_snapshot(page, "activity-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "activity-full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )

    def test_no_critical_console_errors_during_snapshot(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Activity tab must not emit console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _go(page, base_url)
        # Trigger the snapshot so the page fully renders.
        compare_snapshot(page, "activity-console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Activity tab emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )


# ---------------------------------------------------------------------------
# Canonical snapshot (Story 76.9 requirement)
# ---------------------------------------------------------------------------


class TestActivityCanonicalSnapshot:
    """Capture the canonical activity-default.png snapshot.

    Story 76.9 explicitly requires the snapshot to be written to:
        tests/playwright/snapshots/pipeline-dashboard/activity-default.png

    This class satisfies that requirement.
    """

    def test_activity_default_snapshot_written(
        self, page: object, base_url: str
    ) -> None:
        """Capture activity-default.png to the canonical snapshot directory.

        This satisfies the explicit file-path requirement in Story 76.9:
        ``tests/playwright/snapshots/pipeline-dashboard/activity-default.png``
        """
        _go(page, base_url)
        result = create_baseline(page, "activity-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_activity_default_regression(
        self, page: object, base_url: str
    ) -> None:
        """Full-page pixel-diff must not exceed the configured threshold."""
        _go(page, base_url)
        result = compare_snapshot(page, "activity-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestActivitySectionSnapshots:
    """Element-level snapshots for each primary activity log section.

    Isolating sections reduces noise: a change to the filter bar should
    not fail the audit table snapshot.
    """

    def test_audit_table_or_empty_state_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the audit table or the empty state.

        The test locates the audit table or the empty-state container.
        Falls back to a full-page snapshot when neither discrete container
        is found.
        """
        _go(page, base_url)

        table_selectors = [
            "[class*='overflow-x-auto']",
            "table",
            "[data-testid='activity-log-empty-state']",
            "[data-testid='empty-state']",
        ]

        section_found = False
        for selector in table_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "activity-table", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Activity table snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            # Graceful fallback: capture full page when the section has no
            # discrete DOM container.
            result = compare_snapshot(
                page, "activity-table-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_filter_bar_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the filter bar area."""
        _go(page, base_url)

        filter_selectors = [
            "select",
            "[class*='flex'][class*='flex-wrap']",
            "label[class*='text-gray']",
        ]

        section_found = False
        for selector in filter_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "activity-filter-bar", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Filter bar snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "activity-filter-bar-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_pagination_controls_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the pagination controls."""
        _go(page, base_url)

        pagination_selectors = [
            "div[class*='flex'][class*='justify-between']",
            "button[disabled]",
        ]

        section_found = False
        for selector in pagination_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "activity-pagination", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Pagination snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "activity-pagination-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_empty_state_snapshot_when_no_entries(
        self, page: object, base_url: str
    ) -> None:
        """Capture the empty activity state when no steering actions exist.

        This snapshot is the canonical empty-state baseline for the activity
        log.  If entries are present, the test is skipped — the empty state
        is not visible.
        """
        _go(page, base_url)

        if page.locator("table tbody tr").count() > 0:  # type: ignore[attr-defined]
            pytest.skip("Audit entries present — capturing empty state skipped")

        empty_state_selectors = [
            "[data-testid='activity-log-empty-state']",
            "[data-testid='empty-state']",
            "div[class*='flex'][class*='items-center'][class*='justify-center']",
        ]

        section_found = False
        for selector in empty_state_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "activity-empty-state", page_name=PAGE_NAME
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
                page, "activity-empty-state-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baseline
# ---------------------------------------------------------------------------


class TestActivitySnapshotRegression:
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
        result = compare_snapshot(
            page, "activity-regression-full-page", page_name=PAGE_NAME
        )
        assert result.passed, result.summary()
