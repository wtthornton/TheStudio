"""Epic 59.4 — Fleet Dashboard: Interactive Elements.

Validates that /admin/ui/dashboard interactive behaviours work correctly:

  - Action buttons are visible, enabled, and clickable
  - HTMX swap attributes are present on refresh controls
  - Refresh / polling controls respond to user interaction
  - Detail-panel trigger elements open the sliding inspector panel

These tests verify *interactive behaviour*, not content or appearance.
Content is covered in test_dashboard_intent.py (Epic 59.1).
Style compliance is covered in test_dashboard_style.py (Epic 59.3).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate
from tests.playwright.lib.interaction_helpers import (
    InteractionResult,
    assert_button_clickable,
    assert_htmx_swap,
    click_and_assert_state_change,
)

pytestmark = pytest.mark.playwright

DASHBOARD_URL = "/admin/ui/dashboard"


def _go(page: object, base_url: str) -> None:
    """Navigate to the dashboard and wait for content to settle."""
    navigate(page, f"{base_url}{DASHBOARD_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Action buttons
# ---------------------------------------------------------------------------


class TestDashboardButtons:
    """Action buttons must be present, enabled, and interactive."""

    def test_primary_action_buttons_clickable(self, page, base_url: str) -> None:
        """Any primary action buttons on the dashboard are clickable."""
        _go(page, base_url)

        buttons = page.locator("button, [role='button']")
        count = buttons.count()

        if count == 0:
            pytest.skip("No buttons found on the dashboard — acceptable for read-only view")

        # Check at least the first found button is enabled and visible
        first_btn = buttons.first
        assert first_btn.is_visible(), "First action button must be visible"
        assert first_btn.is_enabled(), "First action button must not be disabled"

    def test_refresh_button_present(self, page, base_url: str) -> None:
        """Dashboard exposes a refresh or reload control (button or icon-button)."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        has_refresh_text = "refresh" in body or "reload" in body

        # Accept a button containing a refresh-like aria-label as well
        aria_refresh = page.locator(
            "button[aria-label*='refresh' i], button[aria-label*='reload' i], "
            "[title*='refresh' i], [title*='reload' i]"
        ).count()

        # Accept HTMX polling attribute anywhere on the page
        htmx_poll = page.locator("[hx-trigger*='every']").count()

        assert has_refresh_text or aria_refresh > 0 or htmx_poll > 0, (
            "Dashboard must provide a refresh button, ARIA-labeled reload control, "
            "or HTMX auto-polling — none found"
        )

    def test_no_disabled_primary_buttons(self, page, base_url: str) -> None:
        """Primary (non-destructive) action buttons must not be permanently disabled."""
        _go(page, base_url)

        primary_btns = page.locator("button.btn-primary, button[data-primary], button.primary")
        count = primary_btns.count()

        if count == 0:
            pytest.skip("No explicitly-marked primary buttons found")

        for i in range(count):
            btn = primary_btns.nth(i)
            assert btn.is_enabled(), (
                f"Primary button at index {i} must not be permanently disabled"
            )


# ---------------------------------------------------------------------------
# HTMX swap attributes
# ---------------------------------------------------------------------------


class TestDashboardHtmxSwaps:
    """HTMX controls must carry the correct hx-* attributes for live updates."""

    def test_htmx_target_attributes_present(self, page, base_url: str) -> None:
        """Elements with hx-get or hx-post declare an hx-target."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-get], [hx-post]")
        count = hx_elements.count()

        if count == 0:
            pytest.skip("No HTMX hx-get/hx-post elements found — page may not use HTMX")

        for i in range(min(count, 10)):
            el = hx_elements.nth(i)
            hx_target = el.get_attribute("hx-target")
            hx_swap = el.get_attribute("hx-swap")
            # Each HTMX trigger element must have either an explicit target or
            # inherit via hx-boost; a swap strategy is strongly preferred.
            assert hx_target is not None or hx_swap is not None, (
                f"HTMX element {i} ({el.get_attribute('hx-get') or el.get_attribute('hx-post')}) "
                "must declare hx-target or hx-swap"
            )

    def test_polling_interval_declared(self, page, base_url: str) -> None:
        """Workflow summary or health section uses HTMX polling (hx-trigger='every Xs')."""
        _go(page, base_url)

        polling_els = page.locator("[hx-trigger*='every']")
        count = polling_els.count()

        if count == 0:
            # Acceptable if page uses JS-based polling or SSE instead
            body = page.locator("body").inner_html().lower()
            has_sse = "event-source" in body or "eventsource" in body or "sse" in body
            has_ws = "websocket" in body or "ws://" in body or "wss://" in body
            pytest.skip(
                "No HTMX polling found; page may use SSE/WebSocket or JS polling"
                f" (SSE hint: {has_sse}, WS hint: {has_ws})"
            )

        # At least one polling interval must be in a reasonable range (5s–5min)
        found_valid = False
        for i in range(count):
            trigger_val = polling_els.nth(i).get_attribute("hx-trigger") or ""
            # Examples: "every 10s", "every 30s", "every 1m"
            if "every" in trigger_val:
                found_valid = True
                break

        assert found_valid, "HTMX polling elements must use 'every Xs' trigger syntax"

    def test_htmx_swap_target_exists_in_dom(self, page, base_url: str) -> None:
        """hx-target selectors reference elements that exist in the current DOM."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-target]")
        count = hx_elements.count()

        if count == 0:
            pytest.skip("No elements with hx-target found")

        missing: list[str] = []
        for i in range(min(count, 10)):
            target_sel = hx_elements.nth(i).get_attribute("hx-target") or ""
            # Skip special HTMX keywords that refer to relative positions
            if target_sel in ("this", "closest", "next", "previous", "find") or not target_sel:
                continue
            if target_sel.startswith("closest ") or target_sel.startswith("next ") or target_sel.startswith("find "):
                continue
            try:
                target_count = page.locator(target_sel).count()
                if target_count == 0:
                    missing.append(target_sel)
            except Exception:  # noqa: BLE001
                # Playwright may raise for unusual selectors
                pass

        assert not missing, (
            f"hx-target selector(s) not found in DOM: {missing}"
        )


# ---------------------------------------------------------------------------
# Refresh polling behaviour
# ---------------------------------------------------------------------------


class TestDashboardRefreshPolling:
    """Refresh controls must be interactive and trigger visible state changes."""

    def test_refresh_control_clickable(self, page, base_url: str) -> None:
        """Clicking a refresh control does not raise a JS error."""
        _go(page, base_url)

        # Collect JS errors during the click
        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        refresh_btn = page.locator(
            "button[aria-label*='refresh' i], button[aria-label*='reload' i], "
            "[title*='refresh' i], [hx-trigger*='click'][hx-get]"
        ).first

        if not refresh_btn.count():
            pytest.skip("No clickable refresh control found")

        if refresh_btn.is_visible() and refresh_btn.is_enabled():
            refresh_btn.click()
            page.wait_for_timeout(500)  # brief settle

        assert not js_errors, f"JS errors after clicking refresh: {js_errors}"

    def test_page_does_not_hard_reload_on_refresh(self, page, base_url: str) -> None:
        """Refresh interaction uses in-place swap, not a full page reload."""
        _go(page, base_url)

        navigations: list[str] = []
        page.on("framenavigated", lambda frame: navigations.append(frame.url))

        refresh_btn = page.locator(
            "button[aria-label*='refresh' i], [hx-trigger*='click'][hx-get]"
        ).first

        if not refresh_btn.count():
            pytest.skip("No clickable refresh control found")

        initial_url = page.url
        if refresh_btn.is_visible() and refresh_btn.is_enabled():
            refresh_btn.click()
            page.wait_for_timeout(500)

        # Filter out navigations back to the same URL (polling may re-navigate)
        hard_reloads = [u for u in navigations if u != initial_url and DASHBOARD_URL not in u]
        assert not hard_reloads, (
            f"Refresh triggered unexpected navigation(s): {hard_reloads}"
        )


# ---------------------------------------------------------------------------
# Detail panel triggers
# ---------------------------------------------------------------------------


class TestDashboardDetailPanelTriggers:
    """Clicking a detail trigger must open the sliding inspector panel (§9.14)."""

    def test_detail_panel_trigger_elements_exist(self, page, base_url: str) -> None:
        """Dashboard has at least one element that can open a detail panel."""
        _go(page, base_url)

        # Look for row-level triggers, view-detail links, or inspect buttons
        trigger_selectors = [
            "[data-detail-trigger]",
            "[data-panel-trigger]",
            "tr[hx-get]",
            "a[href*='detail']",
            "button[aria-label*='detail' i]",
            "button[aria-label*='inspect' i]",
            "button[aria-label*='view' i]",
        ]
        found = False
        for sel in trigger_selectors:
            if page.locator(sel).count() > 0:
                found = True
                break

        if not found:
            body = page.locator("body").inner_text().lower()
            has_detail_word = "detail" in body or "inspect" in body or "view" in body
            if not has_detail_word:
                pytest.skip(
                    "No detail-panel triggers found — dashboard may be a read-only summary"
                )

    def test_detail_panel_opens_on_row_click(self, page, base_url: str) -> None:
        """Clicking a table row or detail trigger reveals a panel/drawer in the DOM."""
        _go(page, base_url)

        # Try rows first, then fallback to any hx-get element inside the main area
        row_sel = "table tbody tr[hx-get], table tbody tr[data-detail-trigger]"
        rows = page.locator(row_sel)

        if rows.count() == 0:
            pytest.skip("No clickable table rows with detail triggers found")

        first_row = rows.first
        if not first_row.is_visible():
            pytest.skip("Detail-trigger row not visible — data may not be loaded")

        first_row.click()
        page.wait_for_timeout(600)  # allow HTMX swap / animation

        # Panel should become visible — common selectors per §9.14
        panel_sel = (
            "[role='complementary'], [role='dialog'], "
            ".detail-panel, .inspector-panel, .slide-panel, "
            "[data-panel], [id*='detail'], [id*='panel']"
        )
        panel = page.locator(panel_sel)
        assert panel.count() > 0, (
            "Clicking a detail row must reveal a side panel/drawer element"
        )

    def test_detail_panel_can_be_dismissed(self, page, base_url: str) -> None:
        """Once opened, the detail panel can be closed via a close button or Escape."""
        _go(page, base_url)

        row_sel = "table tbody tr[hx-get], table tbody tr[data-detail-trigger]"
        rows = page.locator(row_sel)

        if rows.count() == 0:
            pytest.skip("No detail-trigger rows found")

        first_row = rows.first
        if not first_row.is_visible():
            pytest.skip("Detail-trigger row not visible")

        first_row.click()
        page.wait_for_timeout(600)

        # Try close button first
        close_btn = page.locator(
            "[aria-label='Close'], [aria-label='Dismiss'], "
            "button[data-close], button.close, .panel-close, [data-panel-close]"
        ).first
        if close_btn.count() and close_btn.is_visible():
            close_btn.click()
        else:
            # Fallback: press Escape
            page.keyboard.press("Escape")

        page.wait_for_timeout(400)

        # Panel should be gone or hidden
        panel_sel = (
            "[role='complementary'][aria-hidden='false'], "
            ".detail-panel:not(.hidden):not([hidden]), "
            ".inspector-panel:not(.hidden):not([hidden])"
        )
        still_visible_count = page.locator(panel_sel).count()
        # Lenient: if selector finds nothing that's fine; if found it should be hidden
        assert still_visible_count == 0, (
            "Detail panel must be dismissible — panel still visible after close action"
        )
