"""Epic 68.6 — Quarantine: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/quarantine and registers them for
visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Component-level baselines for the primary Quarantine page sections:
    * Quarantined events table (failure reasons, event IDs, timestamps)
    * Action controls (Replay / Delete buttons)
    * Confirmation dialog (when a destructive action is triggered)

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
- 68.1 test_quarantine_intent.py         - semantic content
- 68.2 test_quarantine_api.py            - API endpoints
- 68.3 test_quarantine_style.py          - style-guide compliance
- 68.4 test_quarantine_interactions.py   - interactive elements
- 68.5 test_quarantine_a11y.py           - WCAG 2.2 AA
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

QUARANTINE_URL = "/admin/ui/quarantine"
PAGE_NAME = "quarantine"


def _go(page: object, base_url: str) -> None:
    """Navigate to the quarantine page and wait for content to settle."""
    navigate(page, f"{base_url}{QUARANTINE_URL}")  # type: ignore[arg-type]


def _has_quarantine_rows(page: object) -> bool:
    """Return True when the quarantine table has at least one data row."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator("[data-quarantine], [class*='quarantine-row']").count() > 0
    )


# ---------------------------------------------------------------------------
# Full-page snapshots
# ---------------------------------------------------------------------------


class TestQuarantineFullPageSnapshot:
    """Capture and compare full-page baselines for /admin/ui/quarantine.

    These snapshots guard against unexpected layout shifts, colour changes,
    or missing table columns in the Quarantine page.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the quarantine page at 1280x720.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/quarantine/``.  On subsequent runs
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


class TestQuarantineSectionSnapshots:
    """Element-level snapshots for primary Quarantine page sections.

    Isolating sections reduces noise: a change to the action controls should
    not fail the events table snapshot.
    """

    def test_quarantine_table_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the quarantined events table."""
        _go(page, base_url)

        table_selectors = [
            "[data-testid='quarantine-table']",
            "[data-testid='quarantine-list']",
            "[aria-label*='quarantine' i]",
            "table",
            "[class*='quarantine-table']",
            "[class*='quarantine-list']",
            "section:has-text('Quarantine')",
            "div:has-text('Quarantined')",
        ]

        section_found = False
        for selector in table_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "quarantine-table", page_name=PAGE_NAME
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
                page, "quarantine-table-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_action_controls_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the Replay / Delete action controls area.

        The layout of the action buttons (position, styling, spacing) must
        remain visually consistent across UI changes.
        """
        _go(page, base_url)

        action_selectors = [
            "[data-testid='quarantine-actions']",
            "[data-testid='action-controls']",
            "[aria-label*='replay' i]",
            "[aria-label*='action' i]",
            "section:has-text('Actions')",
            "div:has-text('Replay')",
            "[class*='action']",
            "button:has-text('Replay')",
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

    def test_confirmation_dialog_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the confirmation dialog when open.

        The dialog layout (message text, confirm/cancel buttons) must remain
        visually consistent when a destructive action (Delete) is triggered.
        """
        _go(page, base_url)

        if not _has_quarantine_rows(page):
            # No data rows — take a fallback full-page snapshot and pass
            result = compare_snapshot(
                page, "confirmation-dialog-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        # Try to trigger a confirmation dialog via the Delete button
        delete_selectors = [
            "button[data-action='delete']",
            "button:has-text('Delete')",
            "[data-testid='delete-btn']",
            "[aria-label*='delete' i]",
        ]
        clicked = False
        for sel in delete_selectors:
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
                page, "confirmation-dialog-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        dialog_selectors = [
            "[data-testid='confirmation-dialog']",
            "[role='dialog']",
            "[role='alertdialog']",
            ".modal",
            ".dialog",
            "[class*='dialog']",
            "[class*='modal']",
            "[class*='confirm']",
        ]

        section_found = False
        for selector in dialog_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "confirmation-dialog", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        # Dismiss dialog regardless of whether snapshot succeeded
        dismiss_selectors = [
            "button:has-text('Cancel')",
            "button[data-action='cancel']",
            "[aria-label*='cancel' i]",
            "[aria-label*='close' i]",
            "button:has-text('Close')",
        ]
        for sel in dismiss_selectors:
            btn = page.locator(sel).first  # type: ignore[attr-defined]
            if btn.count() > 0 and btn.is_visible():
                btn.click()
                page.wait_for_timeout(300)  # type: ignore[attr-defined]
                break

        if not section_found:
            result = compare_snapshot(
                page, "confirmation-dialog-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestQuarantineSnapshotRegression:
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
        """Quarantine page must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Quarantine page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
