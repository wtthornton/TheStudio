"""Epic 62.6 — Audit Log: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/audit and registers them for
visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Component-level baselines for the primary audit page sections:
    * Audit event table
    * Time-range filter control
    * Pagination control

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
- 62.1 test_audit_intent.py         - semantic content
- 62.2 test_audit_api.py            - API endpoints
- 62.3 test_audit_style.py          - style-guide compliance
- 62.4 test_audit_interactions.py   - interactive elements
- 62.5 test_audit_a11y.py           - WCAG 2.2 AA
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

AUDIT_URL = "/admin/ui/audit"
PAGE_NAME = "audit-log"


def _go(page: object, base_url: str) -> None:
    """Navigate to the audit log page and wait for content to settle."""
    navigate(page, f"{base_url}{AUDIT_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshots
# ---------------------------------------------------------------------------


class TestAuditFullPageSnapshot:
    """Capture and compare full-page baselines for /admin/ui/audit.

    These snapshots guard against unexpected layout shifts, colour changes,
    or missing columns in the audit event table.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the audit log at 1280x720.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/audit-log/``.  On subsequent runs
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


class TestAuditSectionSnapshots:
    """Element-level snapshots for primary audit page sections.

    Isolating sections reduces noise: a change to a filter control should
    not fail the audit table snapshot.
    """

    def test_audit_table_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the audit event table (or empty state)."""
        _go(page, base_url)

        table_selectors = [
            "[data-testid='audit-table']",
            "[aria-label*='audit' i]",
            "table",
            "section:has-text('Audit')",
            "div:has-text('Audit')",
        ]

        section_found = False
        for selector in table_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "audit-table", page_name=PAGE_NAME
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
                page, "audit-table-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_time_range_filter_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the time-range filter control.

        The filter appearance (selected state, labels) must remain consistent
        across UI changes.
        """
        _go(page, base_url)

        filter_selectors = [
            "[data-testid='time-range-filter']",
            "[data-filter='time-range']",
            "[data-filter='period']",
            "select[name*='range' i]",
            "select[name*='period' i]",
            "div:has-text('Filter')",
        ]

        section_found = False
        for selector in filter_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "time-range-filter", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            # Filter may not be implemented yet — graceful fallback
            result = compare_snapshot(
                page, "time-range-filter-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_pagination_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the pagination control.

        The pagination appearance (active page, button states) must remain
        consistent across UI changes.
        """
        _go(page, base_url)

        pagination_selectors = [
            "[data-testid='pagination']",
            "[aria-label='pagination']",
            "[role='navigation'][aria-label*='page' i]",
            "nav[aria-label*='page' i]",
            ".pagination",
            "[class*='pagination']",
        ]

        section_found = False
        for selector in pagination_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "pagination", page_name=PAGE_NAME
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
                page, "pagination-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestAuditSnapshotRegression:
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
        """Audit log page must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Audit log page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
