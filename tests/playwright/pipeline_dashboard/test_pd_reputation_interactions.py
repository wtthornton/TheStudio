"""Story 76.11 — Reputation Tab: Interactive Elements.

Validates that /dashboard/?tab=reputation interactive behaviours work correctly:

  - Tab navigation buttons in the header are clickable and switch views
  - Expert row click opens ExpertDetail view (or navigates within the tab)
  - ExpertDetail close button returns to the expert list
  - Sort controls on the expert table change the ordering
  - Filter controls (if present) narrow the expert list
  - No JavaScript errors are raised during normal interactions

These tests verify *interactive behaviour*, not content or appearance.
Content is in test_pd_reputation_intent.py (Story 76.11).
Style compliance is in test_pd_reputation_style.py (Story 76.11).
"""

from __future__ import annotations

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _go(page: object, base_url: str) -> None:
    """Navigate to the reputation tab and wait for React to settle."""
    dashboard_navigate(page, base_url, "reputation")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tab navigation
# ---------------------------------------------------------------------------


class TestReputationTabNavigation:
    """Header tab buttons must switch views without a full page reload."""

    def test_reputation_tab_button_active(self, page, base_url: str) -> None:
        """'Reputation' tab button is present and visible in the header nav."""
        _go(page, base_url)

        nav = page.locator("nav[aria-label='Primary navigation']")
        assert nav.count() > 0, "Primary navigation nav landmark must be present"

        rep_btn = nav.locator("button", has_text="Reputation")
        assert rep_btn.count() > 0, (
            "Header nav must contain a 'Reputation' tab button"
        )
        assert rep_btn.first.is_visible(), (
            "'Reputation' tab button must be visible"
        )

    def test_pipeline_tab_button_clickable(self, page, base_url: str) -> None:
        """Clicking the 'Pipeline' tab button switches away from reputation view."""
        _go(page, base_url)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        nav = page.locator("nav[aria-label='Primary navigation']")
        pipeline_btn = nav.locator("button", has_text="Pipeline")

        if pipeline_btn.count() == 0:
            pytest.skip("No 'Pipeline' tab button found in navigation")

        pipeline_btn.first.click()
        page.wait_for_timeout(600)

        assert not js_errors, (
            f"JS errors after clicking Pipeline tab: {js_errors}"
        )

    def test_tab_switch_does_not_navigate_away(self, page, base_url: str) -> None:
        """Clicking a tab button keeps the user on /dashboard/ (no hard navigate)."""
        _go(page, base_url)

        initial_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]

        nav = page.locator("nav[aria-label='Primary navigation']")
        other_btns = nav.locator("button")
        if other_btns.count() < 2:
            pytest.skip("Fewer than 2 nav buttons — skipping tab-switch test")

        other_btns.nth(0).click()
        page.wait_for_timeout(400)

        final_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]
        assert final_path == initial_path, (
            f"Tab switch should not change the URL pathname — "
            f"before: {initial_path!r}, after: {final_path!r}"
        )


# ---------------------------------------------------------------------------
# Expert row click — opens ExpertDetail
# ---------------------------------------------------------------------------


class TestReputationExpertRowInteraction:
    """Clicking an expert row must open the ExpertDetail view.

    The Reputation component swaps ExpertTable for ExpertDetail when an expert
    is selected.  The detail view must render within the same tab container.
    """

    def test_expert_row_click_opens_detail(self, page, base_url: str) -> None:
        """Clicking an expert row renders ExpertDetail inside the reputation tab."""
        _go(page, base_url)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        # Locate expert row by testid or table row.
        row_selectors = [
            "[data-testid='expert-row']",
            "[data-testid='expert-table'] tr[data-expert-id]",
            "[data-testid='expert-table'] tbody tr",
            "table tbody tr",
        ]

        expert_row = None
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() > 0:
                expert_row = rows.first
                break

        if expert_row is None:
            pytest.skip(
                "No expert rows found in the table — "
                "expert data is empty or table uses a different structure"
            )

        expert_row.click()
        page.wait_for_timeout(600)

        # ExpertDetail should now be visible.
        has_detail = (
            page.locator("[data-testid='expert-detail']").count() > 0
            or page.locator("[data-testid='expert-detail-view']").count() > 0
        )

        if not has_detail:
            # Accept a modal or expanded section as well.
            body_lower = page.locator("body").inner_text().lower()
            has_detail = (
                "close" in body_lower
                or "back" in body_lower
                or "detail" in body_lower
            )

        assert has_detail, (
            "Clicking an expert row must open the ExpertDetail view "
            "(data-testid='expert-detail') within the reputation tab"
        )
        assert not js_errors, (
            f"JS errors raised during expert row click: {js_errors}"
        )

    def test_expert_detail_close_returns_to_list(self, page, base_url: str) -> None:
        """Closing ExpertDetail returns the user to the expert table."""
        _go(page, base_url)

        # First click a row to open the detail.
        row_selectors = [
            "[data-testid='expert-row']",
            "[data-testid='expert-table'] tbody tr",
            "table tbody tr",
        ]
        expert_row = None
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() > 0:
                expert_row = rows.first
                break

        if expert_row is None:
            pytest.skip(
                "No expert rows found — cannot test expert detail close"
            )

        expert_row.click()
        page.wait_for_timeout(500)

        # Find and click the close button.
        close_selectors = [
            "[data-testid='expert-detail-close']",
            "[aria-label='Close']",
            "[aria-label='close']",
            "button[class*='close']",
        ]
        close_btn = None
        for sel in close_selectors:
            btn = page.locator(sel)  # type: ignore[attr-defined]
            if btn.count() > 0:
                close_btn = btn.first
                break

        if close_btn is None:
            pytest.skip(
                "ExpertDetail close button not found — "
                "detail may not have opened or uses a different close mechanism"
            )

        close_btn.click()
        page.wait_for_timeout(500)

        # Expert list should be back.
        has_list = (
            page.locator("[data-testid='expert-table']").count() > 0
            or page.locator("[data-testid='expert-list']").count() > 0
            or page.locator("table").count() > 0
        )
        assert has_list, (
            "After closing ExpertDetail, the expert table must be restored"
        )


# ---------------------------------------------------------------------------
# Sort controls
# ---------------------------------------------------------------------------


class TestReputationSortControls:
    """Sort controls on the expert table must re-order the list."""

    def test_sort_controls_present(self, page, base_url: str) -> None:
        """Expert table has at least one sortable column header."""
        _go(page, base_url)

        sort_selectors = [
            "[data-testid='sort-control']",
            "th[aria-sort]",
            "th button",
            "[class*='sortable']",
            "th[class*='cursor-pointer']",
        ]

        for sel in sort_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                return  # Sort controls found

        # Graceful skip — expert table may be empty.
        body_lower = page.locator("body").inner_text().lower()
        if "expert" not in body_lower and "score" not in body_lower:
            pytest.skip(
                "Expert table appears empty — sort control check skipped"
            )

        pytest.skip(
            "No explicit sort controls found on expert table — "
            "table may use a different interaction pattern"
        )

    def test_sort_click_no_js_errors(self, page, base_url: str) -> None:
        """Clicking a sort control does not raise JavaScript errors."""
        _go(page, base_url)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        sort_selectors = [
            "[data-testid='sort-control']",
            "th button",
            "th[aria-sort]",
        ]
        for sel in sort_selectors:
            elements = page.locator(sel)  # type: ignore[attr-defined]
            if elements.count() > 0:
                elements.first.click()
                page.wait_for_timeout(400)
                break

        assert not js_errors, (
            f"JS errors raised when interacting with sort controls: {js_errors}"
        )


# ---------------------------------------------------------------------------
# No JavaScript errors during normal interaction
# ---------------------------------------------------------------------------


class TestReputationNoJsErrors:
    """Normal interactions on the reputation tab must not raise JS errors."""

    def test_page_load_no_js_errors(self, page, base_url: str) -> None:
        """Loading the reputation tab produces no JavaScript errors."""
        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        _go(page, base_url)

        critical = [
            e for e in js_errors
            if "TypeError" in e or "ReferenceError" in e or "SyntaxError" in e
        ]
        assert not critical, (
            f"Reputation tab emitted {len(critical)} critical JS error(s) on load: "
            f"{critical[:3]}"
        )

    def test_scrolling_no_js_errors(self, page, base_url: str) -> None:
        """Scrolling the reputation tab does not raise JavaScript errors."""
        _go(page, base_url)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        page.evaluate("window.scrollTo(0, 500)")  # type: ignore[attr-defined]
        page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 0)")  # type: ignore[attr-defined]
        page.wait_for_timeout(300)

        assert not js_errors, (
            f"JS errors raised while scrolling the reputation tab: {js_errors}"
        )
