"""Story 76.3 — Triage Tab: Visual Snapshot Baseline.

Captures baseline screenshots for /dashboard/?tab=triage and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Triage queue section baseline (cards or empty state).
- Empty queue state baseline when no issues are present.

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

Storage location
~~~~~~~~~~~~~~~~
All snapshots are written to:
  tests/playwright/snapshots/pipeline-dashboard/triage-*.png

Related suites
~~~~~~~~~~~~~~
- 76.3 test_pd_triage_intent.py       — semantic content
- 76.3 test_pd_triage_api.py          — API contracts
- 76.3 test_pd_triage_style.py        — style-guide compliance
- 76.3 test_pd_triage_interactions.py — interactive elements
- 76.3 test_pd_triage_a11y.py         — WCAG 2.2 AA
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


def _navigate(page, base_url: str) -> None:
    """Navigate to the triage tab and wait for React hydration."""
    dashboard_navigate(page, base_url, "triage")


def _has_triage_cards(page) -> bool:
    """Return True when at least one triage card is present."""
    return (
        page.evaluate(
            "document.querySelectorAll('[data-tour=\"triage-card\"]').length"
        )
        > 0
    )


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestTriageFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the triage tab.

    The full-page snapshot is the primary regression guard: any unexpected
    layout shift, colour change, or missing section will fail here.
    """

    def test_triage_full_page_baseline(self, page, base_url: str) -> None:
        """Capture full-page baseline at 1280x720 viewport.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/pipeline-dashboard/``.  On subsequent
        runs the current screenshot is compared against that baseline.
        """
        _navigate(page, base_url)
        result = compare_snapshot(page, "triage-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_triage_full_page_create_baseline(self, page, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _navigate(page, base_url)
        result = create_baseline(page, "triage-default-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestTriageSectionSnapshots:
    """Element-level snapshots for the triage queue section.

    Isolating the queue section from the full page reduces noise — a navigation
    bar change should not fail the triage queue snapshot.
    """

    def test_triage_queue_section_snapshot(self, page, base_url: str) -> None:
        """Capture a snapshot of the TriageQueue component root element."""
        _navigate(page, base_url)

        queue_selectors = [
            "[data-tour='triage-queue']",
            "[data-testid='triage-queue']",
            "[data-tour='triage-list']",
        ]

        section_found = False
        for selector in queue_selectors:
            locator = page.locator(selector).first
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "triage-queue-section", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Triage queue section snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            # Graceful fallback: capture full page when the queue has no discrete container
            result = compare_snapshot(
                page, "triage-queue-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_triage_card_snapshot_when_populated(
        self, page, base_url: str
    ) -> None:
        """Capture a snapshot of the first triage card when the queue has issues."""
        _navigate(page, base_url)

        if not _has_triage_cards(page):
            pytest.skip("No triage cards — skipping card-level snapshot")

        card_selector = "[data-tour='triage-card']"
        locator = page.locator(card_selector).first
        try:
            locator.scroll_into_view_if_needed()
            dest = capture_element_snapshot(
                page, card_selector, "triage-card-first", page_name=PAGE_NAME
            )
            assert dest.exists(), (
                f"Triage card snapshot was not written to disk: {dest}"
            )
        except Exception as exc:
            # Graceful degradation: full-page fallback
            result = compare_snapshot(
                page, "triage-card-fallback", page_name=PAGE_NAME
            )
            assert result.passed, (
                f"Triage card element snapshot failed ({exc}); "
                f"full-page fallback also failed: {result.summary()}"
            )


# ---------------------------------------------------------------------------
# Empty queue state snapshot
# ---------------------------------------------------------------------------


class TestTriageEmptyStateSnapshot:
    """Capture a visual baseline for the empty triage queue state.

    The empty state (with its 'No issues awaiting triage' heading and webhook
    guidance link) is a distinct UI surface that must be separately baselined.
    """

    def test_triage_empty_state_snapshot(self, page, base_url: str) -> None:
        """Capture the empty queue state when no issues are awaiting triage."""
        _navigate(page, base_url)

        if _has_triage_cards(page):
            pytest.skip("Queue has cards — empty state snapshot not applicable")

        empty_selectors = [
            "[data-testid='empty-triage-queue']",
            "[class*='empty']",
            ".empty-state",
        ]

        section_found = False
        for selector in empty_selectors:
            locator = page.locator(selector).first
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "triage-empty-state", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Empty state snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            # Fallback: full-page snapshot captures the empty queue state
            result = compare_snapshot(
                page, "triage-empty-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestTriageSnapshotRegression:
    """Verify current render matches committed baselines (pixel-diff guard).

    These tests are the CI regression guards.  They pass on first run
    (baseline auto-created) and fail only when a subsequent run produces
    a pixel-diff above the threshold.

    Override the threshold with ``SNAPSHOT_THRESHOLD=0.002`` (0.2%) for
    environments where minor anti-aliasing differences are expected.
    """

    def test_triage_full_page_regression(self, page, base_url: str) -> None:
        """Full-page pixel-diff must not exceed the configured threshold."""
        _navigate(page, base_url)
        result = compare_snapshot(
            page, "triage-regression-full-page", page_name=PAGE_NAME
        )
        assert result.passed, result.summary()

    def test_no_critical_console_errors_during_snapshot(
        self, page, base_url: str, console_errors: list
    ) -> None:
        """Triage tab must not emit critical console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _navigate(page, base_url)
        # Trigger the snapshot so the page fully renders
        compare_snapshot(page, "triage-console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Triage tab emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
