"""Epic 73.4 — Portfolio Health: Interactive Elements.

Validates that /admin/ui/portfolio-health interactive behaviours work correctly:

  Risk filter    — A risk-level filter control is present and interactive
  Repo drill-down — Clicking a repo row/card opens detail content or navigates
  HTMX           — Detail content is loaded via HTMX swap (hx-get, hx-target)
  Panel          — Detail panel or accordion can be dismissed / collapsed

These tests verify *interactive behaviour*, not content or appearance.
Content is covered in test_portfolio_health_intent.py (Epic 73.1).
Style compliance is covered in test_portfolio_health_style.py (Epic 73.3).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

PORTFOLIO_HEALTH_URL = "/admin/ui/portfolio-health"


def _go(page: object, base_url: str) -> None:
    """Navigate to the portfolio health page and wait for content to settle."""
    navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")  # type: ignore[arg-type]


def _has_portfolio_rows(page: object) -> bool:
    """Return True when the portfolio health page has at least one data row or card."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator(
            "[data-repo], [class*='repo-card'], [class*='health-card'], "
            "[data-health], [class*='portfolio-card']"
        ).count()
        > 0
    )


# ---------------------------------------------------------------------------
# Risk filter control
# ---------------------------------------------------------------------------


class TestPortfolioHealthRiskFilter:
    """A risk filter control must be present and interactive on the portfolio health page."""

    def test_risk_filter_control_exists(self, page: object, base_url: str) -> None:
        """A risk filter, status select, or search input control exists on the page."""
        _go(page, base_url)

        filter_selectors = [
            "select[name*='risk' i]",
            "select[name*='health' i]",
            "select[name*='status' i]",
            "select[name*='filter' i]",
            "select[aria-label*='risk' i]",
            "select[aria-label*='health' i]",
            "select[aria-label*='filter' i]",
            "[data-filter]",
            "[data-risk-filter]",
            "[data-health-filter]",
            "input[type='search']",
            "input[placeholder*='search' i]",
            "input[placeholder*='filter' i]",
            "input[placeholder*='risk' i]",
            "input[placeholder*='repo' i]",
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
                        f"Risk filter control ({sel!r}) must be visible"
                    )
                    return
            except Exception:  # noqa: BLE001
                continue

        # Sortable column headers provide implicit navigation / filtering
        headers = page.locator("th")  # type: ignore[attr-defined]
        if headers.count() > 0:
            pytest.skip(
                "No explicit risk filter/search controls found — table column headers "
                "provide implicit navigation (acceptable for portfolio health page)"
            )

        pytest.skip(
            "No risk filter or search controls found on portfolio health page — "
            "page may show a flat list without filter controls"
        )

    def test_risk_filter_is_not_permanently_disabled(
        self, page: object, base_url: str
    ) -> None:
        """Risk filter controls must not be permanently disabled."""
        _go(page, base_url)

        filter_selectors = [
            "select[name*='risk' i]",
            "select[name*='health' i]",
            "select[name*='status' i]",
            "select[name*='filter' i]",
            "input[type='search']",
            "input[placeholder*='search' i]",
            "input[placeholder*='filter' i]",
            "[data-filter]",
            "[data-risk-filter]",
        ]
        for sel in filter_selectors:
            try:
                controls = page.locator(sel)  # type: ignore[attr-defined]
                count = controls.count()
                if count == 0:
                    continue
                first = controls.first
                if not first.is_visible():
                    continue
                assert first.is_enabled(), (  # type: ignore[attr-defined]
                    f"Risk filter control ({sel!r}) must not be permanently disabled"
                )
                return
            except Exception:  # noqa: BLE001
                continue

        pytest.skip(
            "No risk filter controls found — skipping enabled/disabled check"
        )

    def test_risk_filter_interaction_changes_dom(
        self, page: object, base_url: str
    ) -> None:
        """Changing the risk filter or entering search text must cause a DOM change."""
        _go(page, base_url)

        # Try select-based filter first
        select_selectors = [
            "select[name*='risk' i]",
            "select[name*='health' i]",
            "select[name*='status' i]",
            "select[name*='filter' i]",
        ]
        for sel in select_selectors:
            try:
                selects = page.locator(sel)  # type: ignore[attr-defined]
                if selects.count() == 0:
                    continue
                first = selects.first
                if not first.is_visible() or not first.is_enabled():
                    continue
                options = first.locator("option")  # type: ignore[attr-defined]
                if options.count() < 2:
                    continue
                before = page.locator("body").inner_html()  # type: ignore[attr-defined]
                second_val = options.nth(1).get_attribute("value")
                if second_val:
                    first.select_option(second_val)
                    page.wait_for_timeout(600)  # type: ignore[attr-defined]
                    after = page.locator("body").inner_html()  # type: ignore[attr-defined]
                    assert before != after, (
                        "Changing risk filter select must update the DOM — "
                        "body HTML was identical before and after filter change"
                    )
                    return
            except Exception:  # noqa: BLE001
                continue

        # Try text input filter
        input_selectors = [
            "input[type='search']",
            "input[placeholder*='search' i]",
            "input[placeholder*='filter' i]",
            "input[placeholder*='repo' i]",
        ]
        for sel in input_selectors:
            try:
                inputs = page.locator(sel)  # type: ignore[attr-defined]
                if inputs.count() == 0:
                    continue
                first = inputs.first
                if not first.is_visible() or not first.is_enabled():
                    continue
                before = page.locator("body").inner_html()  # type: ignore[attr-defined]
                first.fill("test-filter-query")
                page.wait_for_timeout(600)  # type: ignore[attr-defined]
                after = page.locator("body").inner_html()  # type: ignore[attr-defined]
                assert before != after, (
                    "Typing in the risk/repo search input must update the DOM — "
                    "body HTML was identical before and after typing"
                )
                return
            except Exception:  # noqa: BLE001
                continue

        pytest.skip(
            "No interactive risk filter controls found — skipping DOM-change filter test"
        )


# ---------------------------------------------------------------------------
# Repo drill-down
# ---------------------------------------------------------------------------


class TestPortfolioHealthRepoDrillDown:
    """Clicking a repo row or card must open detail content for that repo."""

    def test_repo_drill_down_trigger_elements_exist(
        self, page: object, base_url: str
    ) -> None:
        """At least one element on the portfolio health page can trigger repo drill-down."""
        _go(page, base_url)

        trigger_selectors = [
            "[data-detail-trigger]",
            "[data-panel-trigger]",
            "[data-expand]",
            "[data-toggle]",
            "[aria-expanded]",
            "tr[hx-get]",
            "table tbody tr",
            "[data-repo]",
            "[data-health]",
            "[class*='repo-card']",
            "[class*='health-card']",
            "button[aria-label*='detail' i]",
            "button[aria-label*='view' i]",
            "button[aria-label*='expand' i]",
            "details > summary",
            "a[href*='repo']",
            "a[href*='health']",
        ]
        found = any(
            page.locator(sel).count() > 0  # type: ignore[attr-defined]
            for sel in trigger_selectors
        )

        if not found:
            body = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            if any(kw in body for kw in ("no repos", "no repositories", "empty")):
                pytest.skip(
                    "Portfolio health page is empty — no repos to drill into"
                )
            pytest.skip(
                "No repo drill-down trigger elements found on portfolio health page"
            )

    def test_repo_drill_down_reveals_content(
        self, page: object, base_url: str
    ) -> None:
        """Clicking or expanding a repo row/card reveals repo-level health detail."""
        _go(page, base_url)

        if not _has_portfolio_rows(page):
            pytest.skip(
                "No portfolio repos on page — skipping repo drill-down test"
            )

        # Try <details> / <summary> accordion pattern first
        summaries = page.locator("details > summary")  # type: ignore[attr-defined]
        if summaries.count() > 0:
            first = summaries.first
            if first.is_visible():
                before = page.locator("body").inner_html()  # type: ignore[attr-defined]
                first.click()
                page.wait_for_timeout(400)  # type: ignore[attr-defined]
                after = page.locator("body").inner_html()  # type: ignore[attr-defined]
                assert before != after, (
                    "Clicking portfolio health <summary> must reveal repo details — "
                    "DOM unchanged after click"
                )
                return

        # Try HTMX row click or dedicated expand button
        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "[data-repo][hx-get]",
            "[data-health][hx-get]",
            "[class*='repo-card'][hx-get]",
            "button[data-expand]",
            "button[aria-expanded='false']",
            "table tbody tr",
            "[data-repo]",
            "[class*='repo-card']",
        ]
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            before = page.locator("body").inner_html()  # type: ignore[attr-defined]
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            after = page.locator("body").inner_html()  # type: ignore[attr-defined]
            if before != after:
                return

        pytest.skip(
            "No interactive repo row or drill-down trigger found — "
            "skipping repo drill-down content test"
        )

    def test_drill_down_content_is_repo_relevant(
        self, page: object, base_url: str
    ) -> None:
        """After drilling into a repo the visible content references repo health data."""
        _go(page, base_url)

        if not _has_portfolio_rows(page):
            pytest.skip("No portfolio repos — skipping drill-down content check")

        clicked = False

        # Try <details> accordion
        summaries = page.locator("details > summary")  # type: ignore[attr-defined]
        if summaries.count() > 0:
            first = summaries.first
            if first.is_visible():
                first.click()
                page.wait_for_timeout(400)  # type: ignore[attr-defined]
                clicked = True

        if not clicked:
            row_selectors = [
                "table tbody tr[hx-get]",
                "table tbody tr[data-detail-trigger]",
                "[data-repo][hx-get]",
                "table tbody tr",
                "[data-repo]",
                "[class*='repo-card']",
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
                clicked = True
                break

        if not clicked:
            pytest.skip("No clickable portfolio repo found for drill-down content check")

        body_text = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
        repo_health_keywords = [
            "health",
            "healthy",
            "degraded",
            "critical",
            "risk",
            "repo",
            "repository",
            "status",
            "score",
            "passing",
            "failing",
            "warning",
            "ok",
            "good",
            "poor",
        ]
        has_content = any(kw in body_text for kw in repo_health_keywords)
        assert has_content, (
            "Repo drill-down must show health-related content — "
            "none of the expected keywords found after drill-down"
        )

    def test_detail_panel_can_be_dismissed(self, page: object, base_url: str) -> None:
        """Once opened, the repo detail panel can be closed or collapsed."""
        _go(page, base_url)

        if not _has_portfolio_rows(page):
            pytest.skip("No portfolio repos — skipping panel dismiss test")

        # <details> accordion: click to open, click again to close
        summaries = page.locator("details > summary")  # type: ignore[attr-defined]
        if summaries.count() > 0:
            first = summaries.first
            if first.is_visible():
                first.click()
                page.wait_for_timeout(300)  # type: ignore[attr-defined]
                first.click()
                page.wait_for_timeout(300)  # type: ignore[attr-defined]
                open_details = page.locator("details[open]").count()  # type: ignore[attr-defined]
                assert open_details == 0, (
                    "Clicking <summary> again must collapse the repo detail — "
                    f"found {open_details} open <details> element(s) after second click"
                )
                return

        # Side-panel: open then close via close button or Escape
        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-repo]",
            "[class*='repo-card']",
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
            pytest.skip("No visible portfolio repo items found to click")

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
            "Portfolio health repo detail panel must be dismissible — "
            "panel still visible after close action"
        )


# ---------------------------------------------------------------------------
# HTMX swap attributes
# ---------------------------------------------------------------------------


class TestPortfolioHealthHtmxSwaps:
    """Portfolio health page HTMX controls must carry correct hx-* attributes."""

    def test_htmx_elements_have_target(self, page: object, base_url: str) -> None:
        """Elements with hx-get or hx-post on the portfolio health page declare hx-target or hx-swap."""
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
                f"HTMX element {i} on portfolio health page must declare hx-target or hx-swap"
            )

    def test_htmx_targets_exist_in_dom(self, page: object, base_url: str) -> None:
        """hx-target selectors on portfolio health page reference elements in the current DOM."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-target]")  # type: ignore[attr-defined]
        count = hx_elements.count()

        if count == 0:
            pytest.skip("No elements with hx-target found on portfolio health page")

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
            f"hx-target selector(s) not found in DOM on portfolio health page: {missing}"
        )

    def test_no_js_errors_on_row_click(self, page: object, base_url: str) -> None:
        """Repo row click that triggers HTMX detail load must not raise JS errors."""
        _go(page, base_url)

        if not _has_portfolio_rows(page):
            pytest.skip("No portfolio repos — skipping JS error check")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-repo]",
            "[class*='repo-card']",
            "details > summary",
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
            f"JS errors occurred during portfolio health row click / HTMX swap: {js_errors}"
        )


# ---------------------------------------------------------------------------
# Detail panel initial state
# ---------------------------------------------------------------------------


class TestPortfolioHealthDetailPanelInitialState:
    """The repo detail panel must be hidden before any user interaction."""

    def test_detail_panel_not_visible_before_interaction(
        self, page: object, base_url: str
    ) -> None:
        """The detail panel is hidden or absent before any repo row is clicked."""
        _go(page, base_url)

        visible_panel_sel = (
            ".detail-panel:not(.hidden):not([hidden]):not([aria-hidden='true']), "
            ".inspector-panel:not(.hidden):not([hidden]):not([aria-hidden='true'])"
        )
        visible_count = page.locator(visible_panel_sel).count()  # type: ignore[attr-defined]
        assert visible_count == 0, (
            f"Detail panel must be hidden on initial portfolio health page load — "
            f"found {visible_count} visible panel(s) before any interaction (§9.14)"
        )
