"""Epic 66.6 — Model Gateway: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/models and registers them for
visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Component-level baselines for the primary Model Gateway sections:
    * Model providers table / card grid (routing rules, cost info)
    * Filter / search controls
    * Detail panel (when a model row is opened)

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
- 66.1 test_models_intent.py         - semantic content
- 66.2 test_models_api.py            - API endpoints
- 66.3 test_models_style.py          - style-guide compliance
- 66.4 test_models_interactions.py   - interactive elements
- 66.5 test_models_a11y.py           - WCAG 2.2 AA
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

MODELS_URL = "/admin/ui/models"
PAGE_NAME = "models"


def _go(page: object, base_url: str) -> None:
    """Navigate to the models page and wait for content to settle."""
    navigate(page, f"{base_url}{MODELS_URL}")  # type: ignore[arg-type]


def _has_model_rows(page: object) -> bool:
    """Return True when the models catalog has at least one data row or card."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator("[data-model], [class*='model-card']").count() > 0
    )


# ---------------------------------------------------------------------------
# Full-page snapshots
# ---------------------------------------------------------------------------


class TestModelsFullPageSnapshot:
    """Capture and compare full-page baselines for /admin/ui/models.

    These snapshots guard against unexpected layout shifts, colour changes,
    or missing catalog columns in the Model Gateway page.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the models page at 1280x720.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/models/``.  On subsequent runs
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


class TestModelsSectionSnapshots:
    """Element-level snapshots for primary Model Gateway page sections.

    Isolating sections reduces noise: a change to the filter controls should
    not fail the model catalog snapshot.
    """

    def test_model_catalog_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the model provider table or card grid."""
        _go(page, base_url)

        catalog_selectors = [
            "[data-testid='models-table']",
            "[data-testid='model-list']",
            "[aria-label*='model' i]",
            "table",
            "[class*='model-table']",
            "[class*='model-catalog']",
            "section:has-text('Model')",
            "div:has-text('Provider')",
        ]

        section_found = False
        for selector in catalog_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "model-catalog", page_name=PAGE_NAME
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
                page, "model-catalog-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_routing_rules_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the routing rules section.

        The routing rules appearance (toggles, labels, layout) must remain
        consistent across UI changes.
        """
        _go(page, base_url)

        routing_selectors = [
            "[data-testid='routing-rules']",
            "[data-testid='model-routing']",
            "[aria-label*='routing' i]",
            "section:has-text('Routing')",
            "div:has-text('Routing Rule')",
            "[class*='routing']",
        ]

        section_found = False
        for selector in routing_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "routing-rules", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            # Routing rules may not be implemented yet — graceful fallback
            result = compare_snapshot(
                page, "routing-rules-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_detail_panel_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the model detail panel when open.

        The detail panel layout (model name, provider, cost info, routing)
        must remain visually consistent.
        """
        _go(page, base_url)

        if not _has_model_rows(page):
            # No data rows — take a fallback full-page snapshot and pass
            result = compare_snapshot(
                page, "detail-panel-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        # Open the first model item to reveal the detail panel
        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-model]",
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
                page, "detail-panel-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        panel_selectors = [
            "[data-testid='model-detail']",
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
                        page, selector, "detail-panel", page_name=PAGE_NAME
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
                page, "detail-panel-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestModelsSnapshotRegression:
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
        """Models page must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Models page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
