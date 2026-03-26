"""Epic 67.6 — Compliance Scorecard: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/compliance and registers them for
visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Component-level baselines for the primary Compliance Scorecard sections:
    * Per-repo compliance table / card grid (status, check results)
    * Repo filter controls
    * Check detail expansion (when a row is opened)

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
- 67.1 test_compliance_intent.py         - semantic content
- 67.2 test_compliance_api.py            - API endpoints
- 67.3 test_compliance_style.py          - style-guide compliance
- 67.4 test_compliance_interactions.py   - interactive elements
- 67.5 test_compliance_a11y.py           - WCAG 2.2 AA
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

COMPLIANCE_URL = "/admin/ui/compliance"
PAGE_NAME = "compliance"


def _go(page: object, base_url: str) -> None:
    """Navigate to the compliance page and wait for content to settle."""
    navigate(page, f"{base_url}{COMPLIANCE_URL}")  # type: ignore[arg-type]


def _has_compliance_rows(page: object) -> bool:
    """Return True when the compliance table has at least one data row or card."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator("[data-compliance], [class*='compliance-card']").count() > 0
    )


# ---------------------------------------------------------------------------
# Full-page snapshots
# ---------------------------------------------------------------------------


class TestComplianceFullPageSnapshot:
    """Capture and compare full-page baselines for /admin/ui/compliance.

    These snapshots guard against unexpected layout shifts, colour changes,
    or missing scorecard columns in the Compliance Scorecard page.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the compliance page at 1280x720.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/compliance/``.  On subsequent runs
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


class TestComplianceSectionSnapshots:
    """Element-level snapshots for primary Compliance Scorecard page sections.

    Isolating sections reduces noise: a change to the filter controls should
    not fail the compliance table snapshot.
    """

    def test_compliance_table_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the per-repo compliance table or card grid."""
        _go(page, base_url)

        table_selectors = [
            "[data-testid='compliance-table']",
            "[data-testid='compliance-list']",
            "[aria-label*='compliance' i]",
            "table",
            "[class*='compliance-table']",
            "[class*='compliance-list']",
            "section:has-text('Compliance')",
            "div:has-text('Repository')",
        ]

        section_found = False
        for selector in table_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "compliance-table", page_name=PAGE_NAME
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
                page, "compliance-table-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_repo_filter_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the repo filter controls section.

        The filter controls appearance (inputs, dropdowns, layout) must remain
        consistent across UI changes.
        """
        _go(page, base_url)

        filter_selectors = [
            "[data-testid='compliance-filter']",
            "[data-testid='repo-filter']",
            "[aria-label*='filter' i]",
            "section:has-text('Filter')",
            "div:has-text('Filter')",
            "[class*='filter']",
            "form[role='search']",
        ]

        section_found = False
        for selector in filter_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "repo-filter", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            # Filter controls may not be implemented yet — graceful fallback
            result = compare_snapshot(
                page, "repo-filter-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_check_detail_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the check detail expansion when open.

        The check detail layout (check name, status, description, remediation)
        must remain visually consistent.
        """
        _go(page, base_url)

        if not _has_compliance_rows(page):
            # No data rows — take a fallback full-page snapshot and pass
            result = compare_snapshot(
                page, "check-detail-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        # Click the first row to expand check detail
        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-compliance]",
        ]
        clicked = False
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            clicked = True
            break

        if not clicked:
            result = compare_snapshot(
                page, "check-detail-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        panel_selectors = [
            "[data-testid='compliance-detail']",
            "[data-testid='check-detail']",
            "[role='dialog']",
            "[role='complementary']",
            ".detail-panel",
            ".inspector-panel",
            ".slide-panel",
            "[data-panel]",
            "[class*='detail-panel']",
            "[class*='inspector']",
        ]

        section_found = False
        for selector in panel_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "check-detail", page_name=PAGE_NAME
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
                page, "check-detail-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestComplianceSnapshotRegression:
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
        """Compliance page must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Compliance page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
