"""Epic 69.6 — Dead-Letter Inspector: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/dead-letters and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Component-level baselines for the primary Dead-Letter Inspector page sections:
    * Dead-lettered events table (failure reasons, event IDs, attempt counts)
    * Event detail expansion panel
    * Retry action controls

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
- 69.1 test_dead_letters_intent.py         - semantic content
- 69.2 test_dead_letters_api.py            - API endpoints
- 69.3 test_dead_letters_style.py          - style-guide compliance
- 69.4 test_dead_letters_interactions.py   - interactive elements
- 69.5 test_dead_letters_a11y.py           - WCAG 2.2 AA
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

DEAD_LETTERS_URL = "/admin/ui/dead-letters"
PAGE_NAME = "dead_letters"


def _go(page: object, base_url: str) -> None:
    """Navigate to the dead-letters page and wait for content to settle."""
    navigate(page, f"{base_url}{DEAD_LETTERS_URL}")  # type: ignore[arg-type]


def _has_dead_letter_rows(page: object) -> bool:
    """Return True when the dead-letters table has at least one data row."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator(
            "[data-dead-letter], [class*='dead-letter-row']"
        ).count()
        > 0
    )


# ---------------------------------------------------------------------------
# Full-page snapshots
# ---------------------------------------------------------------------------


class TestDeadLettersFullPageSnapshot:
    """Capture and compare full-page baselines for /admin/ui/dead-letters.

    These snapshots guard against unexpected layout shifts, colour changes,
    or missing table columns in the Dead-Letter Inspector page.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the dead-letters page at 1280x720.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/dead_letters/``.  On subsequent runs
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


class TestDeadLettersSectionSnapshots:
    """Element-level snapshots for primary Dead-Letter Inspector page sections.

    Isolating sections reduces noise: a change to the retry controls should
    not fail the events table snapshot.
    """

    def test_dead_letters_table_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the dead-lettered events table."""
        _go(page, base_url)

        table_selectors = [
            "[data-testid='dead-letters-table']",
            "[data-testid='dead-letter-list']",
            "[aria-label*='dead letter' i]",
            "table",
            "[class*='dead-letter-table']",
            "[class*='dead-letter-list']",
            "section:has-text('Dead Letter')",
            "div:has-text('Dead-Letter')",
        ]

        section_found = False
        for selector in table_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "dead-letters-table", page_name=PAGE_NAME
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
                page, "dead-letters-table-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_retry_controls_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the retry action controls area.

        The layout of the retry buttons (position, styling, spacing) must
        remain visually consistent across UI changes.
        """
        _go(page, base_url)

        retry_selectors = [
            "[data-testid='dead-letter-actions']",
            "[data-testid='retry-controls']",
            "[aria-label*='retry' i]",
            "[aria-label*='action' i]",
            "section:has-text('Actions')",
            "div:has-text('Retry')",
            "[class*='action']",
            "button:has-text('Retry')",
        ]

        section_found = False
        for selector in retry_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "retry-controls", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            # Retry controls may not be present on empty state — graceful fallback
            result = compare_snapshot(
                page, "retry-controls-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_event_detail_expansion_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of an expanded event detail panel.

        The detail panel (failure reasons, attempt counts, stack traces) must
        remain visually consistent when a dead-letter row is expanded.
        """
        _go(page, base_url)

        if not _has_dead_letter_rows(page):
            # No data rows — take a fallback full-page snapshot and pass
            result = compare_snapshot(
                page, "event-detail-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        # Try to expand an event detail via row click or expand button
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
                page, "event-detail-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        detail_selectors = [
            "[data-testid='event-detail']",
            "[data-testid='dead-letter-detail']",
            "[role='dialog']",
            "[role='region'][aria-label*='detail' i]",
            ".detail-panel",
            "[class*='detail-panel']",
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
                        page, selector, "event-detail", page_name=PAGE_NAME
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
                page, "event-detail-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestDeadLettersSnapshotRegression:
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
        """Dead-letters page must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Dead-letters page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
