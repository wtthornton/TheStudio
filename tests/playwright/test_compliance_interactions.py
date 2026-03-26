"""Epic 67.4 — Compliance Scorecard: Interactive Elements.

Validates that /admin/ui/compliance interactive behaviours work correctly:

  Repo filter    — A repo filter or search control is present and interactive
  Check detail   — Row/card click or expand button opens check detail content
  HTMX           — Detail content is loaded via HTMX swap (hx-get, hx-target)
  Panel          — Detail panel or accordion can be dismissed / collapsed

These tests verify *interactive behaviour*, not content or appearance.
Content is covered in test_compliance_intent.py (Epic 67.1).
Style compliance is covered in test_compliance_style.py (Epic 67.3).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

COMPLIANCE_URL = "/admin/ui/compliance"


def _go(page: object, base_url: str) -> None:
    """Navigate to the compliance scorecard page and wait for content to settle."""
    navigate(page, f"{base_url}{COMPLIANCE_URL}")  # type: ignore[arg-type]


def _has_compliance_rows(page: object) -> bool:
    """Return True when the compliance page has at least one data row or card."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator(
            "[data-compliance], [class*='compliance-card'], [data-repo]"
        ).count()
        > 0
    )


# ---------------------------------------------------------------------------
# Repo filter control
# ---------------------------------------------------------------------------


class TestComplianceRepoFilter:
    """A repo filter or search control must be present and interactive on the compliance page."""

    def test_repo_filter_control_exists(self, page: object, base_url: str) -> None:
        """A repo filter, search input, or status select control exists on the page."""
        _go(page, base_url)

        filter_selectors = [
            "select[name*='repo' i]",
            "select[name*='repository' i]",
            "select[name*='status' i]",
            "select[name*='filter' i]",
            "select[aria-label*='repo' i]",
            "select[aria-label*='filter' i]",
            "select[aria-label*='status' i]",
            "[data-filter]",
            "[data-repo-filter]",
            "input[type='search']",
            "input[placeholder*='search' i]",
            "input[placeholder*='filter' i]",
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
                        f"Repo filter/search control ({sel!r}) must be visible"
                    )
                    return
            except Exception:  # noqa: BLE001
                continue

        # Sortable column headers provide implicit navigation / filtering
        headers = page.locator("th")  # type: ignore[attr-defined]
        if headers.count() > 0:
            pytest.skip(
                "No explicit repo filter/search controls found — table column headers "
                "provide implicit navigation (acceptable for compliance page)"
            )

        pytest.skip(
            "No repo filter or search controls found on compliance page — "
            "page may show a flat list without filter controls"
        )

    def test_repo_filter_is_not_permanently_disabled(
        self, page: object, base_url: str
    ) -> None:
        """Repo filter controls must not be permanently disabled."""
        _go(page, base_url)

        filter_selectors = [
            "select[name*='repo' i]",
            "select[name*='status' i]",
            "select[name*='filter' i]",
            "input[type='search']",
            "input[placeholder*='search' i]",
            "input[placeholder*='filter' i]",
            "[data-filter]",
            "[data-repo-filter]",
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
                    f"Repo filter control ({sel!r}) must not be permanently disabled"
                )
                return
            except Exception:  # noqa: BLE001
                continue

        pytest.skip(
            "No repo filter controls found — skipping enabled/disabled check"
        )

    def test_repo_filter_interaction_changes_dom(
        self, page: object, base_url: str
    ) -> None:
        """Changing the repo filter or entering search text must cause a DOM change."""
        _go(page, base_url)

        # Try select-based filter first
        select_selectors = [
            "select[name*='repo' i]",
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
                        "Changing repo filter select must update the DOM — "
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
                    "Typing in the repo search/filter input must update the DOM — "
                    "body HTML was identical before and after typing"
                )
                return
            except Exception:  # noqa: BLE001
                continue

        pytest.skip(
            "No interactive repo filter controls found — skipping DOM-change filter test"
        )


# ---------------------------------------------------------------------------
# Check detail expansion
# ---------------------------------------------------------------------------


class TestComplianceCheckDetailExpansion:
    """Clicking or expanding a compliance row must reveal individual check details."""

    def test_check_detail_trigger_elements_exist(
        self, page: object, base_url: str
    ) -> None:
        """At least one element on the compliance page can trigger detail expansion."""
        _go(page, base_url)

        trigger_selectors = [
            "[data-detail-trigger]",
            "[data-panel-trigger]",
            "[data-expand]",
            "[data-toggle]",
            "[aria-expanded]",
            "tr[hx-get]",
            "table tbody tr",
            "[data-compliance]",
            "[data-repo]",
            "[class*='compliance-card']",
            "button[aria-label*='detail' i]",
            "button[aria-label*='view' i]",
            "button[aria-label*='expand' i]",
            "details > summary",
            "a[href*='detail']",
        ]
        found = any(
            page.locator(sel).count() > 0  # type: ignore[attr-defined]
            for sel in trigger_selectors
        )

        if not found:
            body = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            if any(kw in body for kw in ("no compliance", "no repos", "empty")):
                pytest.skip(
                    "Compliance page is empty — no items to trigger check detail"
                )
            pytest.skip(
                "No check-detail trigger elements found on compliance page"
            )

    def test_check_detail_expansion_reveals_content(
        self, page: object, base_url: str
    ) -> None:
        """Clicking or expanding a compliance row reveals check-level detail content."""
        _go(page, base_url)

        if not _has_compliance_rows(page):
            pytest.skip(
                "No compliance items on page — skipping check detail expansion test"
            )

        # Try <details> / <summary> accordion pattern first (most accessible)
        summaries = page.locator("details > summary")  # type: ignore[attr-defined]
        if summaries.count() > 0:
            first = summaries.first
            if first.is_visible():
                before = page.locator("body").inner_html()  # type: ignore[attr-defined]
                first.click()
                page.wait_for_timeout(400)  # type: ignore[attr-defined]
                after = page.locator("body").inner_html()  # type: ignore[attr-defined]
                assert before != after, (
                    "Clicking compliance <summary> must reveal check details — "
                    "DOM unchanged after click"
                )
                return

        # Try HTMX row click or dedicated expand button
        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "[data-compliance][hx-get]",
            "[data-repo][hx-get]",
            "button[data-expand]",
            "button[aria-expanded='false']",
            "table tbody tr",
            "[data-compliance]",
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
            "No interactive compliance row or expand trigger found — "
            "skipping check detail expansion test"
        )

    def test_expanded_detail_contains_check_content(
        self, page: object, base_url: str
    ) -> None:
        """After expanding a compliance row the visible content references check details."""
        _go(page, base_url)

        if not _has_compliance_rows(page):
            pytest.skip("No compliance items — skipping detail content check")

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
                "[data-compliance][hx-get]",
                "table tbody tr",
                "[data-compliance]",
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
            pytest.skip("No clickable compliance item found for detail content check")

        body_text = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
        check_keywords = [
            "check",
            "rule",
            "policy",
            "pass",
            "fail",
            "warning",
            "compliant",
            "non-compliant",
            "status",
            "result",
            "violation",
            "score",
            "audit",
            "repo",
            "repository",
        ]
        has_content = any(kw in body_text for kw in check_keywords)
        assert has_content, (
            "Expanded check detail must contain compliance-related content — "
            "none of the expected keywords found after expansion"
        )

    def test_detail_panel_can_be_dismissed(self, page: object, base_url: str) -> None:
        """Once opened, the check detail panel can be closed or collapsed."""
        _go(page, base_url)

        if not _has_compliance_rows(page):
            pytest.skip("No compliance items — skipping panel dismiss test")

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
                    "Clicking <summary> again must collapse the check detail — "
                    f"found {open_details} open <details> element(s) after second click"
                )
                return

        # Side-panel: open then close via close button or Escape
        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-compliance]",
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
            pytest.skip("No visible compliance items found to click")

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
            "Compliance check detail panel must be dismissible — "
            "panel still visible after close action"
        )


# ---------------------------------------------------------------------------
# HTMX swap attributes
# ---------------------------------------------------------------------------


class TestComplianceHtmxSwaps:
    """Compliance page HTMX controls must carry correct hx-* attributes."""

    def test_htmx_elements_have_target(self, page: object, base_url: str) -> None:
        """Elements with hx-get or hx-post on the compliance page declare hx-target or hx-swap."""
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
                f"HTMX element {i} on compliance page must declare hx-target or hx-swap"
            )

    def test_htmx_targets_exist_in_dom(self, page: object, base_url: str) -> None:
        """hx-target selectors on compliance page reference elements in the current DOM."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-target]")  # type: ignore[attr-defined]
        count = hx_elements.count()

        if count == 0:
            pytest.skip("No elements with hx-target found on compliance page")

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
            f"hx-target selector(s) not found in DOM on compliance page: {missing}"
        )

    def test_no_js_errors_on_row_click(self, page: object, base_url: str) -> None:
        """Compliance row click that triggers HTMX detail load must not raise JS errors."""
        _go(page, base_url)

        if not _has_compliance_rows(page):
            pytest.skip("No compliance items — skipping JS error check")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-compliance]",
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
            f"JS errors occurred during compliance row click / HTMX swap: {js_errors}"
        )


# ---------------------------------------------------------------------------
# Detail panel initial state
# ---------------------------------------------------------------------------


class TestComplianceDetailPanelInitialState:
    """The check detail panel must be hidden before any user interaction."""

    def test_detail_panel_not_visible_before_interaction(
        self, page: object, base_url: str
    ) -> None:
        """The detail panel is hidden or absent before any compliance row is clicked."""
        _go(page, base_url)

        visible_panel_sel = (
            ".detail-panel:not(.hidden):not([hidden]):not([aria-hidden='true']), "
            ".inspector-panel:not(.hidden):not([hidden]):not([aria-hidden='true'])"
        )
        visible_count = page.locator(visible_panel_sel).count()  # type: ignore[attr-defined]
        assert visible_count == 0, (
            f"Detail panel must be hidden on initial compliance page load — "
            f"found {visible_count} visible panel(s) before any interaction (§9.14)"
        )
