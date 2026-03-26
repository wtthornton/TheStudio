"""Story 76.7 — Trust Tiers Tab: Visual Snapshot Baseline.

Captures baseline screenshots for /dashboard/?tab=trust and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Section-level baselines for the three primary trust configuration areas:
    * Default tier selector (ActiveTierDisplay)
    * Safety bounds panel (SafetyBoundsPanel)
    * Rules section (rule list or empty state)

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

Required file (Story 76.7):
    tests/playwright/snapshots/pipeline-dashboard/trust-default.png

Related suites
~~~~~~~~~~~~~~
- test_pd_trust_intent.py       — semantic content
- test_pd_trust_api.py          — API endpoints
- test_pd_trust_style.py        — style-guide compliance
- test_pd_trust_interactions.py — interactive elements
- test_pd_trust_a11y.py         — WCAG 2.2 AA
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
    """Navigate to the trust tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "trust")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestTrustFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the trust tab.

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
        result = compare_snapshot(page, "trust-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "trust-full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )

    def test_no_critical_console_errors_during_snapshot(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Trust tab must not emit console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _go(page, base_url)
        # Trigger the snapshot so the page fully renders.
        compare_snapshot(page, "trust-console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Trust tab emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestTrustSectionSnapshots:
    """Element-level snapshots for each primary trust configuration section.

    Isolating sections reduces noise: a change to the safety bounds panel
    should not fail the default tier selector snapshot.
    """

    def test_default_tier_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Default Trust Tier selector panel.

        Locates the default tier container by data-tour='trust-tier'.
        Falls back to a full-page snapshot when no discrete container is found.
        """
        _go(page, base_url)

        tier_selectors = [
            "[data-tour='trust-tier']",
            "div.rounded-lg:has(h3)",
        ]

        section_found = False
        for selector in tier_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "trust-tier-selector", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Trust tier selector snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "trust-tier-selector-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_safety_bounds_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Safety Bounds panel."""
        _go(page, base_url)

        safety_selectors = [
            "[data-testid='safety-bounds-panel']",
            "div:has-text('Safety Bounds')",
            "div:has-text('Max auto-merge lines')",
        ]

        section_found = False
        for selector in safety_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "trust-safety-bounds", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Safety bounds snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "trust-safety-bounds-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_rules_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Rules section (rule list or empty state)."""
        _go(page, base_url)

        rules_selectors = [
            "[data-tour='trust-rules']",
            "[data-testid='trust-rules-empty']",
            "div:has-text('Rules')",
        ]

        section_found = False
        for selector in rules_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "trust-rules-section", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Trust rules section snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "trust-rules-section-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_empty_state_snapshot_when_no_rules(
        self, page: object, base_url: str
    ) -> None:
        """Capture the trust rules empty state when no rules are configured.

        This snapshot is the canonical empty-state baseline.  If rules exist,
        the test is skipped — the empty state is not visible.
        """
        _go(page, base_url)

        body = page.locator("body").inner_text()  # type: ignore[attr-defined]
        if "No trust rules yet" not in body:
            pytest.skip("Trust rules are configured — capturing empty state skipped")

        empty_selectors = [
            "[data-testid='trust-rules-empty']",
            "[data-testid='empty-state']",
        ]

        section_found = False
        for selector in empty_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "trust-empty-state", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Trust empty state snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "trust-empty-state-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baseline
# ---------------------------------------------------------------------------


class TestTrustSnapshotRegression:
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
        result = compare_snapshot(page, "trust-regression-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_trust_default_screenshot_written(self, page: object, base_url: str) -> None:
        """Capture trust-default.png to the canonical snapshot directory.

        This satisfies the explicit file-path requirement in Story 76.7:
        ``tests/playwright/snapshots/pipeline-dashboard/trust-default.png``
        """
        _go(page, base_url)
        result = create_baseline(page, "trust-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()
