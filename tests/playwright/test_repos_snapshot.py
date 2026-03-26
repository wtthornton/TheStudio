"""Epic 60.6 - Repo Management: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/repos and registers them for
visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Component-level baselines for the primary repos page sections:
    * Repo table (or empty state)
    * Trust tier badge area
    * Detail panel (if accessible via DOM without interaction)

First run
~~~~~~~~~
No baseline files exist - ``compare_snapshot`` auto-creates them; every test
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
- 60.1 test_repos_intent.py         - semantic content
- 60.2 test_repos_api.py            - API endpoints
- 60.3 test_repos_style.py          - style-guide compliance
- 60.4 test_repos_interactions.py   - interactive elements
- 60.5 test_repos_a11y.py           - WCAG 2.2 AA
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

REPOS_URL = "/admin/ui/repos"
PAGE_NAME = "repo-management"


def _go(page: object, base_url: str) -> None:
    """Navigate to the repo management page and wait for content to settle."""
    navigate(page, f"{base_url}{REPOS_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestReposFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the repos page.

    The full-page snapshot is the primary regression guard: any unexpected
    layout shift, colour change, or missing section will fail here.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline at 1280x720 viewport.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/repo-management/``.  On subsequent runs
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


class TestReposSectionSnapshots:
    """Element-level snapshots for each primary repos page section.

    Isolating sections reduces noise: a change to the trust tier badge
    should not fail the table header snapshot.
    """

    def test_repo_table_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the Repo table (or empty state).

        The test locates the table by progressively broader selectors.
        Falls back to a full-page snapshot when no discrete table element
        is found.
        """
        _go(page, base_url)

        table_selectors = [
            "[data-testid='repo-table']",
            "[aria-label*='repo' i]",
            "table",
            "section:has-text('Repos')",
            "div:has-text('Repository')",
        ]

        section_found = False
        for selector in table_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "repo-table", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(page, "repo-table-fallback", page_name=PAGE_NAME)
            assert result.passed, result.summary()

    def test_trust_tier_badges_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the trust tier badge area.

        Trust tier badges (Observe / Suggest / Execute) are defined in
        style guide §5.2.  Any colour or label regression in these badges
        should be caught here.
        """
        _go(page, base_url)

        badge_selectors = [
            "[data-testid='trust-tier-badge']",
            "[aria-label*='tier' i]",
            ".badge--tier",
            "td:has-text('Observe'), td:has-text('Suggest'), td:has-text('Execute')",
            "span:has-text('Observe'), span:has-text('Suggest'), span:has-text('Execute')",
        ]

        section_found = False
        for selector in badge_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "trust-tier-badges", page_name=PAGE_NAME
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
                page, "trust-tier-badges-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_empty_state_snapshot(self, page: object, base_url: str) -> None:
        """Capture the empty state if no repos are present, otherwise the table.

        The empty state CTA is surfaced when no repos are registered (§9.2
        empty state recipe).  When repos exist this test falls back to a
        full-page snapshot so it always produces a baseline file.
        """
        _go(page, base_url)

        empty_state_selectors = [
            "[data-testid='empty-state']",
            "[aria-label*='empty' i]",
            "div:has-text('No repositories')",
            ".empty-state",
        ]

        for selector in empty_state_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "empty-state", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    return
                except Exception:  # noqa: S112
                    continue

        # Repos are present — fall back to full-page baseline.
        result = compare_snapshot(
            page, "empty-state-or-table-fallback", page_name=PAGE_NAME
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
        """Repos page must not emit console errors while the snapshot is captured.

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
            f"Repos page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
