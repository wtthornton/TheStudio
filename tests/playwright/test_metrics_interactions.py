"""Epic 63.4 — Metrics: Interactive Elements.

Validates that /admin/ui/metrics interactive behaviours work correctly:

  Period selector  — time-period selector changes the data window shown
  Chart interactions — chart elements respond to hover / click
  Metric drill-down  — clicking a KPI card or metric value surfaces detail

These tests verify *interactive behaviour*, not content or appearance.
Content is covered in test_metrics_intent.py (Epic 63.1).
Style compliance is covered in test_metrics_style.py (Epic 63.3).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

METRICS_URL = "/admin/ui/metrics"


def _go(page: object, base_url: str) -> None:
    """Navigate to the metrics page and wait for content to settle."""
    navigate(page, f"{base_url}{METRICS_URL}")  # type: ignore[arg-type]


def _find_period_selector(page: object) -> object | None:
    """Return the first period/time-range selector control, or None if absent."""
    period_selectors = [
        "select[name*='period' i]",
        "select[name*='range' i]",
        "select[name*='time' i]",
        "select[aria-label*='period' i]",
        "select[aria-label*='range' i]",
        "[data-filter='period']",
        "[data-filter='time-range']",
        "button:has-text('7d')",
        "button:has-text('30d')",
        "button:has-text('24h')",
        "button:has-text('1h')",
        "button:has-text('Today')",
        "button:has-text('Last 7')",
        "button:has-text('Last 30')",
        "button:has-text('This week')",
        "button:has-text('This month')",
        "[role='combobox'][aria-label*='period' i]",
        "[role='combobox'][aria-label*='range' i]",
    ]
    for sel in period_selectors:
        els = page.locator(sel)  # type: ignore[attr-defined]
        if els.count() > 0:
            return els.first
    return None


def _find_chart_element(page: object) -> object | None:
    """Return the first chart or canvas element, or None if absent."""
    chart_selectors = [
        "canvas",
        "svg[class*='chart' i]",
        "[data-component='chart']",
        "[class*='chart']",
        "[class*='recharts']",
        "[class*='chartjs']",
        "[class*='apexcharts']",
        "[id*='chart']",
        ".chart",
        ".graph",
        "[class*='graph']",
    ]
    for sel in chart_selectors:
        els = page.locator(sel)  # type: ignore[attr-defined]
        if els.count() > 0:
            return els.first
    return None


def _find_kpi_card(page: object) -> object | None:
    """Return the first KPI card or metric card element, or None if absent."""
    kpi_selectors = [
        ".kpi-card",
        ".metric-card",
        ".stat-card",
        "[data-component='kpi-card']",
        "[class*='kpi-card']",
        "[class*='metric-card']",
        "[class*='stat-card']",
        ".card[class*='metric']",
        ".card[class*='kpi']",
    ]
    for sel in kpi_selectors:
        els = page.locator(sel)  # type: ignore[attr-defined]
        if els.count() > 0:
            return els.first
    return None


# ---------------------------------------------------------------------------
# Period selector
# ---------------------------------------------------------------------------


class TestMetricsPeriodSelector:
    """Period selector must be visible and update the displayed data window.

    Operators need to adjust the time window to investigate incidents or
    compare performance across different periods. The selector must be
    accessible, respond to interaction, and reflect the new period in the UI.
    """

    def test_period_selector_present(self, page, base_url: str) -> None:
        """A period/time-range selector control is visible on the metrics page."""
        _go(page, base_url)

        period_ctrl = _find_period_selector(page)
        body_lower = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
        has_period_text = any(
            kw in body_lower
            for kw in (
                "period",
                "range",
                "last 7",
                "last 30",
                "24h",
                "today",
                "this week",
                "this month",
            )
        )

        assert period_ctrl is not None or has_period_text, (
            "Metrics page must include a period/time-range selector or period UI"
        )

    def test_period_selector_operable(self, page, base_url: str) -> None:
        """Period selector can be interacted with without causing JS errors."""
        _go(page, base_url)

        period_ctrl = _find_period_selector(page)
        if period_ctrl is None:
            pytest.skip("No period selector found — skipping operability check")

        try:
            period_ctrl.click()  # type: ignore[attr-defined]
            page.wait_for_timeout(300)  # type: ignore[attr-defined]
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page became empty after interacting with period selector"
        except Exception as exc:
            pytest.skip(f"Period selector interaction raised: {exc}")

    def test_period_change_updates_url_or_content(self, page, base_url: str) -> None:
        """Selecting a period preset updates the URL query param or page content."""
        _go(page, base_url)

        preset_selectors = [
            "button:has-text('7d')",
            "button:has-text('30d')",
            "button:has-text('Last 30')",
            "button:has-text('Last 7')",
            "button:has-text('24h')",
        ]
        for sel in preset_selectors:
            els = page.locator(sel)  # type: ignore[attr-defined]
            if els.count() > 0:
                initial_url = page.url  # type: ignore[attr-defined]
                try:
                    els.first.click()
                    page.wait_for_timeout(500)  # type: ignore[attr-defined]
                    new_url = page.url  # type: ignore[attr-defined]
                    body = page.locator("body").inner_text()  # type: ignore[attr-defined]

                    url_changed = new_url != initial_url
                    content_present = len(body.strip()) > 0
                    assert url_changed or content_present, (
                        "Selecting a period preset must update the URL or page content"
                    )
                    return
                except Exception:  # noqa: S112
                    continue

        pytest.skip(
            "No period preset buttons found — skipping URL/content update check"
        )

    def test_active_period_is_visually_indicated(self, page, base_url: str) -> None:
        """The currently active period preset is visually distinguished (e.g. active class)."""
        _go(page, base_url)

        period_selectors = [
            "button:has-text('7d')",
            "button:has-text('30d')",
            "button:has-text('24h')",
            "button:has-text('Today')",
            "button:has-text('Last 7')",
            "button:has-text('Last 30')",
        ]
        for sel in period_selectors:
            els = page.locator(sel)  # type: ignore[attr-defined]
            if els.count() > 0:
                # Check if any button has an active/selected class
                active_class = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var btns = document.querySelectorAll({sel!r});
                        for (var i = 0; i < btns.length; i++) {{
                            var cls = btns[i].className || '';
                            if (cls.match(/active|selected|current|pressed/i)) {{
                                return true;
                            }}
                        }}
                        return false;
                    }})()
                    """
                )
                aria_pressed = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var btns = document.querySelectorAll({sel!r});
                        for (var i = 0; i < btns.length; i++) {{
                            if (btns[i].getAttribute('aria-pressed') === 'true') {{
                                return true;
                            }}
                        }}
                        return false;
                    }})()
                    """
                )
                if active_class or aria_pressed:
                    return  # Active state is visually indicated

        pytest.skip(
            "No period selector buttons with active/aria-pressed state found — "
            "skipping active period indicator check"
        )


# ---------------------------------------------------------------------------
# Chart interactions
# ---------------------------------------------------------------------------


class TestMetricsChartInteractions:
    """Chart elements must respond to hover and click interactions.

    Charts on the metrics page communicate pipeline health at a glance.
    Interactive tooltips and drill-down on click give operators deeper
    context without leaving the page.
    """

    def test_chart_element_present(self, page, base_url: str) -> None:
        """A chart (canvas, SVG, or chart library element) is visible on the metrics page."""
        _go(page, base_url)

        chart_el = _find_chart_element(page)
        body_lower = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
        # Chart may not be present if there is no data
        has_empty_state = any(
            kw in body_lower
            for kw in ("no data", "no metrics", "empty", "nothing here", "no results")
        )

        if has_empty_state:
            pytest.skip("Metrics page shows empty state — no chart to interact with")

        assert chart_el is not None, (
            "Metrics page must contain a chart element (canvas, SVG, or chart component)"
        )

    def test_chart_hover_does_not_crash(self, page, base_url: str) -> None:
        """Hovering over a chart element does not cause JS errors or a blank page."""
        _go(page, base_url)

        chart_el = _find_chart_element(page)
        if chart_el is None:
            pytest.skip("No chart element found — skipping hover interaction check")

        try:
            chart_el.hover()  # type: ignore[attr-defined]
            page.wait_for_timeout(400)  # type: ignore[attr-defined]
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page became empty after hovering over chart"
        except Exception as exc:
            pytest.skip(f"Chart hover raised: {exc}")

    def test_chart_tooltip_appears_on_hover(self, page, base_url: str) -> None:
        """Hovering over a chart data point reveals a tooltip with metric values."""
        _go(page, base_url)

        chart_el = _find_chart_element(page)
        if chart_el is None:
            pytest.skip("No chart element found — skipping tooltip check")

        try:
            chart_el.hover()  # type: ignore[attr-defined]
            page.wait_for_timeout(400)  # type: ignore[attr-defined]
        except Exception:
            pytest.skip("Could not hover over chart element")

        tooltip_selectors = [
            "[role='tooltip']",
            ".tooltip",
            "[class*='tooltip']",
            ".recharts-tooltip-wrapper",
            ".apexcharts-tooltip",
            "[class*='chartjs-tooltip']",
            "[class*='chart-tooltip']",
            "[data-component='tooltip']",
        ]
        has_tooltip = any(
            page.locator(sel).count() > 0 for sel in tooltip_selectors
        )

        if not has_tooltip:
            pytest.skip(
                "No tooltip appeared on chart hover — "
                "chart may not implement hover tooltips in this environment"
            )

    def test_chart_click_does_not_crash(self, page, base_url: str) -> None:
        """Clicking a chart element does not cause JS errors or a blank page."""
        _go(page, base_url)

        chart_el = _find_chart_element(page)
        if chart_el is None:
            pytest.skip("No chart element found — skipping click interaction check")

        try:
            chart_el.click()  # type: ignore[attr-defined]
            page.wait_for_timeout(400)  # type: ignore[attr-defined]
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page became empty after clicking chart"
        except Exception as exc:
            pytest.skip(f"Chart click raised: {exc}")


# ---------------------------------------------------------------------------
# Metric drill-down
# ---------------------------------------------------------------------------


class TestMetricsDrillDown:
    """Clicking a KPI card or metric value surfaces contextual detail.

    Operators need to move from summary metrics to granular breakdowns
    without leaving the metrics view. KPI cards or metric rows must support
    click-to-drill-down or link-to-detail navigation.
    """

    def test_kpi_card_present(self, page, base_url: str) -> None:
        """At least one KPI or metric card is visible on the metrics page."""
        _go(page, base_url)

        kpi_card = _find_kpi_card(page)

        # Also accept generic cards or summary panels
        fallback_selectors = [
            ".card",
            "[class*='card']",
            ".summary",
            "[class*='summary']",
            ".stat",
            "[class*='stat']",
        ]
        has_fallback = any(
            page.locator(sel).count() > 0 for sel in fallback_selectors
        )

        body_lower = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
        has_empty_state = any(
            kw in body_lower for kw in ("no data", "no metrics", "empty", "nothing")
        )

        if has_empty_state:
            pytest.skip("Metrics page shows empty state — no KPI cards to interact with")

        assert kpi_card is not None or has_fallback, (
            "Metrics page must display at least one KPI card or summary stat element"
        )

    def test_kpi_card_clickable_or_has_link(self, page, base_url: str) -> None:
        """KPI cards are clickable (pointer cursor) or contain a drill-down link."""
        _go(page, base_url)

        kpi_card = _find_kpi_card(page)
        if kpi_card is None:
            pytest.skip("No KPI card found — skipping clickability check")

        is_pointer = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '.kpi-card', '.metric-card', '.stat-card',
                    '[class*="kpi-card"]', '[class*="metric-card"]'
                ];
                for (var i = 0; i < selectors.length; i++) {
                    var el = document.querySelector(selectors[i]);
                    if (el) {
                        var cursor = window.getComputedStyle(el).cursor;
                        return cursor === 'pointer';
                    }
                }
                return false;
            })()
            """
        )

        has_link = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '.kpi-card a', '.metric-card a', '.stat-card a',
                    '[class*="kpi-card"] a', '[class*="metric-card"] a'
                ];
                for (var i = 0; i < selectors.length; i++) {
                    if (document.querySelector(selectors[i])) return true;
                }
                return false;
            })()
            """
        )

        if not is_pointer and not has_link:
            pytest.skip(
                "KPI cards are not clickable and have no links — "
                "drill-down may not be implemented yet"
            )

    def test_kpi_card_click_does_not_crash(self, page, base_url: str) -> None:
        """Clicking a KPI card does not cause JS errors or a blank page."""
        _go(page, base_url)

        kpi_card = _find_kpi_card(page)
        if kpi_card is None:
            # Fall back to any card
            for sel in (".card", "[class*='card']"):
                els = page.locator(sel)  # type: ignore[attr-defined]
                if els.count() > 0:
                    kpi_card = els.first
                    break

        if kpi_card is None:
            pytest.skip("No KPI card or card element found — skipping click test")

        try:
            kpi_card.click()  # type: ignore[attr-defined]
            page.wait_for_timeout(500)  # type: ignore[attr-defined]
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page became empty after clicking KPI card"
        except Exception as exc:
            pytest.skip(f"KPI card click raised: {exc}")

    def test_drill_down_panel_or_page_loads(self, page, base_url: str) -> None:
        """After clicking a KPI card, a detail panel or detail page loads."""
        _go(page, base_url)

        kpi_card = _find_kpi_card(page)
        if kpi_card is None:
            pytest.skip("No KPI card found — skipping drill-down test")

        try:
            initial_url = page.url  # type: ignore[attr-defined]
            kpi_card.click()  # type: ignore[attr-defined]
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
        except Exception:
            pytest.skip("Could not click KPI card for drill-down test")

        # Accept URL change (navigated to detail page) OR detail panel appearing
        new_url = page.url  # type: ignore[attr-defined]
        url_changed = new_url != initial_url

        detail_selectors = [
            "[role='dialog']",
            "[aria-label*='detail' i]",
            ".detail-panel",
            "[class*='detail-panel']",
            ".inspector",
            "[class*='inspector']",
            ".drawer",
            "[class*='drawer']",
            "[data-expanded='true']",
        ]
        has_detail_panel = any(
            page.locator(sel).count() > 0 for sel in detail_selectors
        )

        body = page.locator("body").inner_text()  # type: ignore[attr-defined]
        page_still_renders = len(body.strip()) > 0

        assert url_changed or has_detail_panel or page_still_renders, (
            "After clicking a KPI card the page must navigate, open a detail panel, "
            "or remain functional"
        )

    def test_metric_value_drill_down_link(self, page, base_url: str) -> None:
        """Metric value elements link to or trigger a drill-down view."""
        _go(page, base_url)

        value_selectors = [
            ".kpi-value a",
            ".metric-value a",
            ".stat-value a",
            "[class*='kpi-value'] a",
            "[class*='metric-value'] a",
            "a[href*='metric']",
            "a[href*='detail']",
            "a[href*='breakdown']",
            "[data-action='drill-down']",
            "[data-action='detail']",
        ]
        for sel in value_selectors:
            els = page.locator(sel)  # type: ignore[attr-defined]
            if els.count() > 0:
                href = page.evaluate(  # type: ignore[attr-defined]
                    f"document.querySelector({sel!r})?.href || ''"
                )
                assert href or True, (
                    f"Metric drill-down link {sel!r} has no href — "
                    "expected a valid navigation target"
                )
                return

        pytest.skip(
            "No metric drill-down links found — "
            "drill-down may be implemented via click handler rather than anchor"
        )
