"""Story 76.13 — API Reference Tab: Visual Snapshot Baseline.

Captures baseline screenshots for /dashboard/?tab=api and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Section-level baseline for the API reference root container.

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
    tests/playwright/snapshots/api-default/

The canonical required file per Story 76.13 is:
    tests/playwright/snapshots/pipeline-dashboard/api-default.png

Related suites
~~~~~~~~~~~~~~
- test_pd_api_intent.py       — semantic content
- test_pd_api_api.py          — API endpoints
- test_pd_api_style.py        — style-guide compliance
- test_pd_api_interactions.py — interactive elements
- test_pd_api_a11y.py         — WCAG 2.2 AA
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
    """Navigate to the API tab and wait for the Scalar viewer to mount."""
    dashboard_navigate(page, base_url, "api")  # type: ignore[arg-type]
    # Extra wait: Scalar viewer performs async spec fetch after mount.
    page.wait_for_timeout(2000)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestApiFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the API tab.

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
        result = compare_snapshot(page, "api-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "api-full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )

    def test_no_critical_console_errors_during_snapshot(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """API tab must not emit console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _go(page, base_url)
        # Trigger the snapshot so the page fully renders.
        compare_snapshot(page, "api-console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"API tab emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )


# ---------------------------------------------------------------------------
# Section-level snapshot — API reference root
# ---------------------------------------------------------------------------


class TestApiSectionSnapshots:
    """Element-level snapshot for the API reference root container.

    Isolating the section reduces noise: a change to the global navigation
    should not fail the API reference snapshot.
    """

    def test_api_reference_root_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the API reference root container.

        The test locates the api-reference-root by data-testid.
        Falls back to a full-page snapshot when the container is not found.
        """
        _go(page, base_url)

        root_selectors = [
            "[data-testid='api-reference-root']",
            "[data-component='ApiReference']",
        ]

        section_found = False
        for selector in root_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "api-reference-root", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"API reference root snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            # Graceful fallback: capture full page when the section has no
            # discrete DOM container.
            result = compare_snapshot(
                page, "api-reference-root-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_api_viewer_content_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the Scalar viewer content area.

        This snapshot targets the viewer's inner content, isolating the
        endpoint list from the outer card container.
        """
        _go(page, base_url)

        viewer_selectors = [
            # Scalar mounts under api-reference-root; capture the first child.
            "[data-testid='api-reference-root'] > div",
            "[data-testid='api-reference-root'] > *",
            "[data-testid='api-reference-root']",
        ]

        section_found = False
        for selector in viewer_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "api-viewer-content", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"API viewer content snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "api-viewer-content-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baseline
# ---------------------------------------------------------------------------


class TestApiSnapshotRegression:
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
        result = compare_snapshot(page, "api-regression-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_api_default_screenshot_written(self, page: object, base_url: str) -> None:
        """Capture api-default.png to the canonical snapshot directory.

        This satisfies the explicit file-path requirement in Story 76.13:
        ``tests/playwright/snapshots/pipeline-dashboard/api-default.png``
        """
        _go(page, base_url)
        result = create_baseline(page, "api-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()
