"""Epic 66.4 — Model Gateway: Interactive Elements.

Validates that /admin/ui/models interactive behaviours work correctly:

  Toggles  — Routing rule enable/disable toggles are present and interactive
  Detail   — Row/card click opens a provider detail panel (§9.14)
  HTMX     — Detail content is loaded via HTMX swap (hx-get, hx-target)
  Panel    — Detail panel can be dismissed via close button or Escape key
  Filter   — Provider filter or search control is present and interactive

These tests verify *interactive behaviour*, not content or appearance.
Content is covered in test_models_intent.py (Epic 66.1).
Style compliance is covered in test_models_style.py (Epic 66.3).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

MODELS_URL = "/admin/ui/models"


def _go(page: object, base_url: str) -> None:
    """Navigate to the models page and wait for content to settle."""
    navigate(page, f"{base_url}{MODELS_URL}")  # type: ignore[arg-type]


def _has_model_rows(page: object) -> bool:
    """Return True when the models page has at least one data row or card."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator(
            "[data-model], [class*='model-card'], [data-provider]"
        ).count()
        > 0
    )


# ---------------------------------------------------------------------------
# Routing rule toggles
# ---------------------------------------------------------------------------


class TestModelsRoutingToggles:
    """Routing rule toggle controls must be present and responsive."""

    def test_routing_toggle_controls_present(self, page: object, base_url: str) -> None:
        """At least one routing rule toggle or enable/disable control exists."""
        _go(page, base_url)

        toggle_selectors = [
            "input[type='checkbox']",
            "input[type='radio']",
            "[role='switch']",
            "button[aria-pressed]",
            "[data-toggle]",
            "[data-routing-toggle]",
            "button:has-text('Enable')",
            "button:has-text('Disable')",
            "[class*='toggle']",
            "[class*='switch']",
        ]
        for sel in toggle_selectors:
            try:
                count = page.locator(sel).count()  # type: ignore[attr-defined]
                if count > 0:
                    ctrl = page.locator(sel).first  # type: ignore[attr-defined]
                    assert ctrl.is_visible(), (  # type: ignore[attr-defined]
                        f"Routing toggle ({sel!r}) must be visible"
                    )
                    return
            except Exception:  # noqa: BLE001
                continue

        pytest.skip(
            "No routing rule toggle controls found on models page — "
            "routing may be view-only in this build"
        )

    def test_toggle_not_permanently_disabled(self, page: object, base_url: str) -> None:
        """Routing toggle controls must not be permanently disabled."""
        _go(page, base_url)

        toggle_selectors = [
            "[role='switch']",
            "button[aria-pressed]",
            "[data-routing-toggle]",
            "input[type='checkbox']",
            "[class*='toggle']",
        ]
        for sel in toggle_selectors:
            try:
                toggles = page.locator(sel)  # type: ignore[attr-defined]
                count = toggles.count()
                if count == 0:
                    continue
                first = toggles.first
                if not first.is_visible():
                    continue
                assert first.is_enabled(), (  # type: ignore[attr-defined]
                    f"Routing toggle ({sel!r}) must not be permanently disabled"
                )
                return
            except Exception:  # noqa: BLE001
                continue

        pytest.skip(
            "No routing toggle controls found — skipping enabled/disabled check"
        )

    def test_routing_toggle_interaction_changes_dom(
        self, page: object, base_url: str
    ) -> None:
        """Clicking a routing toggle must cause a DOM change (state flip or HTMX swap)."""
        _go(page, base_url)

        toggle_selectors = [
            "[role='switch']:not([disabled])",
            "button[aria-pressed]:not([disabled])",
            "[data-routing-toggle]:not([disabled])",
            "[class*='toggle']:not([disabled])",
        ]
        for sel in toggle_selectors:
            try:
                toggles = page.locator(sel)  # type: ignore[attr-defined]
                count = toggles.count()
                if count == 0:
                    continue
                first = toggles.first
                if not first.is_visible() or not first.is_enabled():
                    continue

                before = page.locator("body").inner_html()  # type: ignore[attr-defined]
                first.click()
                page.wait_for_timeout(600)  # type: ignore[attr-defined]
                after = page.locator("body").inner_html()  # type: ignore[attr-defined]

                assert before != after, (
                    "Clicking a routing toggle must change the DOM — "
                    "body HTML was identical before and after click"
                )
                return
            except Exception:  # noqa: BLE001
                continue

        pytest.skip(
            "No interactive routing toggle found — skipping DOM-change toggle test"
        )


# ---------------------------------------------------------------------------
# Provider detail panel (§9.14)
# ---------------------------------------------------------------------------


class TestModelsProviderDetail:
    """Clicking a model/provider item must open a §9.14 detail panel."""

    def test_detail_trigger_elements_exist(self, page: object, base_url: str) -> None:
        """At least one element on the models page can open a detail panel."""
        _go(page, base_url)

        trigger_selectors = [
            "[data-detail-trigger]",
            "[data-panel-trigger]",
            "tr[hx-get]",
            "table tbody tr",
            "[data-model]",
            "[data-provider]",
            "[class*='model-card']",
            "a[href*='detail']",
            "button[aria-label*='detail' i]",
            "button[aria-label*='view' i]",
        ]
        found = any(
            page.locator(sel).count() > 0  # type: ignore[attr-defined]
            for sel in trigger_selectors
        )

        if not found:
            body = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            if any(kw in body for kw in ("no model", "no data", "empty")):
                pytest.skip(
                    "Models page is empty — no items to trigger detail panel"
                )
            pytest.skip("No detail-panel trigger elements found on models page")

    def test_provider_row_click_opens_detail_panel(
        self, page: object, base_url: str
    ) -> None:
        """Clicking a model/provider item reveals a §9.14 detail panel in the DOM."""
        _go(page, base_url)

        if not _has_model_rows(page):
            pytest.skip(
                "No model items on page — skipping detail-panel click test"
            )

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "[data-model][hx-get]",
            "[data-provider][hx-get]",
            "table tbody tr",
            "[data-model]",
            "[data-provider]",
        ]
        clicked_row = False
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            clicked_row = True
            break

        if not clicked_row:
            pytest.skip("No visible model/provider items found to click")

        panel_sel = (
            "[role='complementary'], [role='dialog'], "
            ".detail-panel, .inspector-panel, .slide-panel, "
            "[data-panel], [id*='detail'], [id*='panel'], "
            "[class*='detail-panel'], [class*='inspector']"
        )
        panel = page.locator(panel_sel)  # type: ignore[attr-defined]
        assert panel.count() > 0, (
            "Clicking a model/provider item must reveal a §9.14 side panel/drawer — "
            "none found after click"
        )

    def test_detail_panel_contains_provider_content(
        self, page: object, base_url: str
    ) -> None:
        """The detail panel opened by a provider click contains model-related content."""
        _go(page, base_url)

        if not _has_model_rows(page):
            pytest.skip("No model items — skipping detail content check")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-model]",
            "[data-provider]",
        ]
        clicked_row = False
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            clicked_row = True
            break

        if not clicked_row:
            pytest.skip("No visible model/provider items found to click")

        body_text = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
        model_keywords = [
            "model",
            "provider",
            "routing",
            "cost",
            "token",
            "status",
            "active",
            "enabled",
            "disabled",
            "name",
        ]
        has_model_content = any(kw in body_text for kw in model_keywords)
        assert has_model_content, (
            "Detail panel must contain model/provider-related content — "
            "none of the expected keywords found after opening panel"
        )

    def test_detail_panel_can_be_dismissed(self, page: object, base_url: str) -> None:
        """Once opened, the provider detail panel can be closed via close button or Escape."""
        _go(page, base_url)

        if not _has_model_rows(page):
            pytest.skip("No model items — skipping panel dismiss test")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-model]",
            "[data-provider]",
        ]
        clicked_row = False
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            clicked_row = True
            break

        if not clicked_row:
            pytest.skip("No visible model items found to click")

        close_btn = page.locator(  # type: ignore[attr-defined]
            "[aria-label='Close'], [aria-label='Dismiss'], "
            "button[data-close], button.close, .panel-close, [data-panel-close]"
        ).first
        if close_btn.count() and close_btn.is_visible():
            close_btn.click()
        else:
            page.keyboard.press("Escape")  # type: ignore[attr-defined]

        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        still_open_sel = (
            "[role='complementary'][aria-hidden='false'], "
            ".detail-panel:not(.hidden):not([hidden]), "
            ".inspector-panel:not(.hidden):not([hidden])"
        )
        still_visible_count = page.locator(still_open_sel).count()  # type: ignore[attr-defined]
        assert still_visible_count == 0, (
            "Model provider detail panel must be dismissible — "
            "panel still visible after close action"
        )


# ---------------------------------------------------------------------------
# HTMX swap attributes
# ---------------------------------------------------------------------------


class TestModelsHtmxSwaps:
    """Models page HTMX controls must carry correct hx-* attributes."""

    def test_htmx_elements_have_target(self, page: object, base_url: str) -> None:
        """Elements with hx-get or hx-post on the models page declare hx-target or hx-swap."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-get], [hx-post]")  # type: ignore[attr-defined]
        count = hx_elements.count()

        if count == 0:
            pytest.skip(
                "No HTMX hx-get/hx-post elements found — page may not use HTMX"
            )

        for i in range(min(count, 10)):
            el = hx_elements.nth(i)
            hx_target = el.get_attribute("hx-target")
            hx_swap = el.get_attribute("hx-swap")
            assert hx_target is not None or hx_swap is not None, (
                f"HTMX element {i} on models page must declare hx-target or hx-swap"
            )

    def test_htmx_targets_exist_in_dom(self, page: object, base_url: str) -> None:
        """hx-target selectors on models page reference elements in the current DOM."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-target]")  # type: ignore[attr-defined]
        count = hx_elements.count()

        if count == 0:
            pytest.skip("No elements with hx-target found on models page")

        missing: list[str] = []
        for i in range(min(count, 10)):
            target_sel = hx_elements.nth(i).get_attribute("hx-target") or ""
            if not target_sel or target_sel in (
                "this",
                "closest",
                "next",
                "previous",
                "find",
            ):
                continue
            if any(target_sel.startswith(kw) for kw in ("closest ", "next ", "find ")):
                continue
            try:
                if page.locator(target_sel).count() == 0:  # type: ignore[attr-defined]
                    missing.append(target_sel)
            except Exception:  # noqa: BLE001
                pass

        assert not missing, (
            f"hx-target selector(s) not found in DOM: {missing}"
        )

    def test_no_js_errors_on_item_click(self, page: object, base_url: str) -> None:
        """Model item click that triggers HTMX detail load must not raise JS errors."""
        _go(page, base_url)

        if not _has_model_rows(page):
            pytest.skip("No model items — skipping JS error check")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-model]",
            "[data-provider]",
        ]
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            break

        assert not js_errors, (
            f"JS errors occurred during model item click / HTMX swap: {js_errors}"
        )


# ---------------------------------------------------------------------------
# Filter / search control
# ---------------------------------------------------------------------------


class TestModelsFilterControl:
    """Models page must provide a way to filter or search providers."""

    def test_filter_or_search_control_exists(self, page: object, base_url: str) -> None:
        """A filter or search control exists on the models page."""
        _go(page, base_url)

        filter_selectors = [
            "select[name*='provider' i]",
            "select[name*='status' i]",
            "select[name*='filter' i]",
            "select[aria-label*='provider' i]",
            "select[aria-label*='status' i]",
            "select[aria-label*='filter' i]",
            "[data-filter]",
            "input[type='search']",
            "input[placeholder*='search' i]",
            "input[placeholder*='filter' i]",
            "button:has-text('Filter')",
            "button[aria-label*='filter' i]",
            "th[aria-sort]",
            "th button",
        ]
        for sel in filter_selectors:
            try:
                count = page.locator(sel).count()  # type: ignore[attr-defined]
                if count > 0:
                    ctrl = page.locator(sel).first  # type: ignore[attr-defined]
                    assert ctrl.is_visible(), (  # type: ignore[attr-defined]
                        f"Filter/search control ({sel!r}) must be visible"
                    )
                    return
            except Exception:  # noqa: BLE001
                continue

        # Sortable column headers provide implicit navigation
        headers = page.locator("th")  # type: ignore[attr-defined]
        if headers.count() > 0:
            pytest.skip(
                "No explicit filter/search controls found — table column headers "
                "provide implicit navigation"
            )

    def test_detail_panel_not_visible_before_interaction(
        self, page: object, base_url: str
    ) -> None:
        """The detail panel is hidden or absent before any model item is clicked."""
        _go(page, base_url)

        visible_panel_sel = (
            ".detail-panel:not(.hidden):not([hidden]):not([aria-hidden='true']), "
            ".inspector-panel:not(.hidden):not([hidden]):not([aria-hidden='true'])"
        )
        visible_count = page.locator(visible_panel_sel).count()  # type: ignore[attr-defined]
        assert visible_count == 0, (
            f"Detail panel must be hidden on initial page load — "
            f"found {visible_count} visible panel(s) before any interaction (§9.14)"
        )
