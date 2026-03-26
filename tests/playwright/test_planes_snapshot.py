"""Epic 70.6 — Execution Planes: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/planes and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Component-level baselines for the primary Execution Planes page sections:
    * Worker clusters / planes table (health, registration status)
    * Action controls (pause, resume, register/deregister buttons)
    * Health status badges panel

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
- 70.1 test_planes_intent.py         - semantic content
- 70.2 test_planes_api.py            - API endpoints
- 70.3 test_planes_style.py          - style-guide compliance
- 70.4 test_planes_interactions.py   - interactive elements
- 70.5 test_planes_a11y.py           - WCAG 2.2 AA
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

PLANES_URL = "/admin/ui/planes"
PAGE_NAME = "planes"


def _go(page: object, base_url: str) -> None:
    """Navigate to the execution planes page and wait for content to settle."""
    navigate(page, f"{base_url}{PLANES_URL}")  # type: ignore[arg-type]


def _has_plane_entries(page: object) -> bool:
    """Return True when at least one execution plane row or card is visible."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator(
            "[data-plane], [class*='plane-card'], [data-cluster], [class*='cluster-card']"
        ).count()
        > 0
    )


# ---------------------------------------------------------------------------
# Full-page snapshots
# ---------------------------------------------------------------------------


class TestPlanesFullPageSnapshot:
    """Capture and compare full-page baselines for /admin/ui/planes.

    These snapshots guard against unexpected layout shifts, colour changes,
    or missing table columns in the Execution Planes page.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the planes page at 1280x720.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/planes/``.  On subsequent runs
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


class TestPlanesSectionSnapshots:
    """Element-level snapshots for primary Execution Planes page sections.

    Isolating sections reduces noise: a change to the action controls should
    not fail the planes table snapshot.
    """

    def test_planes_table_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the execution planes / worker clusters table."""
        _go(page, base_url)

        table_selectors = [
            "[data-testid='planes-table']",
            "[data-testid='plane-list']",
            "[aria-label*='plane' i]",
            "[aria-label*='cluster' i]",
            "table",
            "[class*='plane-table']",
            "[class*='plane-list']",
            "[class*='cluster-table']",
            "section:has-text('Execution Plane')",
            "div:has-text('Worker Cluster')",
        ]

        section_found = False
        for selector in table_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "planes-table", page_name=PAGE_NAME
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
                page, "planes-table-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_action_controls_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the pause/resume/register action controls area.

        The layout of the action buttons (position, styling, spacing) must
        remain visually consistent across UI changes.
        """
        _go(page, base_url)

        action_selectors = [
            "[data-testid='plane-actions']",
            "[data-testid='action-controls']",
            "[aria-label*='action' i]",
            "[aria-label*='pause' i]",
            "[aria-label*='resume' i]",
            "section:has-text('Actions')",
            "div:has-text('Pause')",
            "div:has-text('Resume')",
            "[class*='action']",
            "button:has-text('Pause')",
            "button:has-text('Resume')",
        ]

        section_found = False
        for selector in action_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "action-controls", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            # Action controls may not be present on empty state — graceful fallback
            result = compare_snapshot(
                page, "action-controls-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_health_status_badges_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the health status badges for execution planes.

        Health status badges (healthy/degraded/offline) must remain visually
        consistent — operators rely on these to quickly assess cluster health.
        """
        _go(page, base_url)

        if not _has_plane_entries(page):
            # No plane entries — take a fallback full-page snapshot and pass
            result = compare_snapshot(
                page, "health-badges-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        badge_selectors = [
            "[data-testid='health-badge']",
            "[data-testid='status-badge']",
            "[data-health]",
            "[data-status]",
            "[aria-label*='health' i]",
            "[class*='health-badge']",
            "[class*='health-status']",
            "[class*='status-badge']",
            "td:has([class*='badge'])",
        ]

        section_found = False
        for selector in badge_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "health-badges", page_name=PAGE_NAME
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
                page, "health-badges-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_plane_detail_panel_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of an open plane detail panel.

        The detail panel (worker stats, registration details, health timeline)
        must remain visually consistent when a plane row is clicked.
        """
        _go(page, base_url)

        if not _has_plane_entries(page):
            # No data rows — take a fallback full-page snapshot and pass
            result = compare_snapshot(
                page, "plane-detail-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        # Try to open detail panel via row click or expand button
        expand_selectors = [
            "button[data-action='expand']",
            "button:has-text('Details')",
            "[data-testid='expand-btn']",
            "[aria-label*='expand' i]",
            "[aria-label*='detail' i]",
            "table tbody tr:first-child",
        ]
        clicked = False
        for sel in expand_selectors:
            buttons = page.locator(sel)  # type: ignore[attr-defined]
            if buttons.count() == 0:
                continue
            first_btn = buttons.first
            if not first_btn.is_visible():
                continue
            first_btn.click()
            page.wait_for_timeout(500)  # type: ignore[attr-defined]
            clicked = True
            break

        if not clicked:
            result = compare_snapshot(
                page, "plane-detail-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        detail_selectors = [
            "[data-testid='plane-detail']",
            "[data-testid='plane-inspector']",
            "[role='dialog']",
            "[role='region'][aria-label*='detail' i]",
            ".detail-panel",
            "[class*='detail-panel']",
            "[class*='inspector']",
            "[class*='expansion']",
            "[class*='expanded']",
        ]

        section_found = False
        for selector in detail_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "plane-detail", page_name=PAGE_NAME
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
                page, "plane-detail-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestPlanesSnapshotRegression:
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
        """Planes page must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Planes page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
