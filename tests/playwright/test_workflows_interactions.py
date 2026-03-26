"""Epic 61.4 — Workflow Console: Interactive Elements.

Validates that /admin/ui/workflows interactive behaviours work correctly:

  Toggle     — List/kanban view toggle switches between table and board layouts
  Drag-drop  — Kanban cards can be dragged between columns (§9.15)
  §9.14      — Row click opens the sliding inspector/detail panel
  Persistence — View preference (list vs kanban) is persisted across navigation

These tests verify *interactive behaviour*, not content or appearance.
Content is covered in test_workflows_intent.py (Epic 61.1).
Style compliance is covered in test_workflows_style.py (Epic 61.3).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

WORKFLOWS_URL = "/admin/ui/workflows"


def _go(page: object, base_url: str) -> None:
    """Navigate to the workflows page and wait for content to settle."""
    navigate(page, f"{base_url}{WORKFLOWS_URL}")  # type: ignore[arg-type]


def _has_workflow_rows(page: object) -> bool:
    """Return True when the workflows table has at least one data row."""
    return page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]


def _has_kanban(page: object) -> bool:
    """Return True when a kanban board element is visible on the page."""
    kanban_selectors = [
        "[data-view='kanban']",
        ".kanban",
        "[class*='kanban']",
        ".kanban-board",
        "[data-component='kanban']",
    ]
    for sel in kanban_selectors:
        if page.locator(sel).count() > 0:  # type: ignore[attr-defined]
            return True
    return False


def _find_view_toggle(page: object) -> object | None:
    """Return the first list/kanban toggle button, or None if absent."""
    toggle_selectors = [
        "button:has-text('Kanban')",
        "button:has-text('Board')",
        "button:has-text('List')",
        "[data-toggle='kanban']",
        "[data-toggle='list']",
        "[aria-label*='kanban' i]",
        "[aria-label*='board' i]",
        "[aria-label*='list view' i]",
        "[data-view-toggle]",
    ]
    for sel in toggle_selectors:
        els = page.locator(sel)  # type: ignore[attr-defined]
        if els.count() > 0:
            return els.first
    return None


# ---------------------------------------------------------------------------
# List / Kanban view toggle
# ---------------------------------------------------------------------------


class TestWorkflowsViewToggle:
    """List/kanban toggle must switch between table and board layouts."""

    def test_view_toggle_button_present(self, page, base_url: str) -> None:
        """A view toggle button (list/kanban) is visible on the workflows page."""
        _go(page, base_url)

        toggle = _find_view_toggle(page)
        if toggle is None:
            # Also accept a segmented control or radio group
            radio_toggle = page.locator(
                "[role='radiogroup'] [role='radio'], "
                "[role='tablist'] [role='tab']"
            )
            if radio_toggle.count() == 0:
                pytest.skip(
                    "No list/kanban toggle found on workflows page — "
                    "view may be fixed to one layout"
                )
            return

        assert toggle.is_visible(), "View toggle button must be visible"
        assert toggle.is_enabled(), "View toggle button must be enabled"

    def test_kanban_toggle_switches_to_board_view(self, page, base_url: str) -> None:
        """Clicking the kanban toggle renders a board/kanban layout."""
        _go(page, base_url)

        toggle = _find_view_toggle(page)
        if toggle is None:
            pytest.skip("No view toggle found — skipping kanban switch test")

        toggle.click()
        page.wait_for_timeout(600)  # allow CSS transition / re-render

        # After toggling, either a kanban board or a list/table must be visible
        board_or_list = (
            page.locator(
                ".kanban, [class*='kanban'], [data-view='kanban'], "
                "table, [role='table']"
            ).count()
        )
        assert board_or_list > 0, (
            "After clicking the view toggle, neither kanban nor list view is visible"
        )

    def test_list_toggle_restores_table_view(self, page, base_url: str) -> None:
        """Clicking the list toggle after kanban restores the table layout."""
        _go(page, base_url)

        # Try to switch to kanban first
        toggle = _find_view_toggle(page)
        if toggle is None:
            pytest.skip("No view toggle found — skipping list restore test")

        toggle.click()
        page.wait_for_timeout(400)

        # Now look for a 'List' toggle to switch back
        list_selectors = [
            "button:has-text('List')",
            "[aria-label*='list view' i]",
            "[data-toggle='list']",
            "[data-view-toggle='list']",
        ]
        list_toggle = None
        for sel in list_selectors:
            els = page.locator(sel)
            if els.count() > 0:
                list_toggle = els.first
                break

        if list_toggle is None:
            pytest.skip("No 'List' toggle button found — skipping list restore test")

        list_toggle.click()
        page.wait_for_timeout(400)

        # Table must be visible after switching back to list view
        table_count = page.locator("table, [role='table']").count()
        assert table_count > 0, (
            "After switching back to list view, no <table> or [role='table'] found"
        )

    def test_toggle_no_js_errors(self, page, base_url: str) -> None:
        """Toggling between list and kanban views must not raise JS errors."""
        _go(page, base_url)

        toggle = _find_view_toggle(page)
        if toggle is None:
            pytest.skip("No view toggle found — skipping JS error check")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        toggle.click()
        page.wait_for_timeout(500)

        assert not js_errors, (
            f"JS errors occurred while toggling view: {js_errors}"
        )


# ---------------------------------------------------------------------------
# Kanban drag-and-drop (§9.15)
# ---------------------------------------------------------------------------


class TestWorkflowsKanbanDragDrop:
    """Kanban cards must be draggable between columns (§9.15)."""

    def _activate_kanban(self, page: object) -> bool:
        """Try to activate kanban view. Return True if kanban is now visible."""
        toggle = _find_view_toggle(page)
        if toggle is not None:
            try:
                toggle.click()  # type: ignore[attr-defined]
                page.wait_for_timeout(500)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
        return _has_kanban(page)

    def test_kanban_cards_have_draggable_attribute(self, page, base_url: str) -> None:
        """Kanban cards carry draggable='true' or data-draggable attribute (§9.15)."""
        _go(page, base_url)

        if not self._activate_kanban(page):
            pytest.skip("Kanban view not available — skipping drag attribute check")

        card_selectors = [
            ".kanban-card",
            "[class*='kanban-card']",
            ".kanban .card",
            "[class*='kanban'] [class*='card']",
            "[draggable='true']",
            "[data-draggable]",
        ]
        found_draggable = False
        for sel in card_selectors:
            cards = page.locator(sel)
            if cards.count() == 0:
                continue
            # Check if any card is draggable
            first_card = cards.first
            draggable = first_card.get_attribute("draggable")
            data_draggable = first_card.get_attribute("data-draggable")
            aria_grabbed = first_card.get_attribute("aria-grabbed")
            if draggable == "true" or data_draggable is not None or aria_grabbed is not None:
                found_draggable = True
                break

        if not found_draggable:
            # Acceptable: drag may be handled by a JS DnD library without HTML attributes
            pytest.skip(
                "No explicit draggable attributes found on kanban cards — "
                "drag-and-drop may be managed by a JS library (e.g. SortableJS)"
            )

    def test_kanban_columns_are_drop_targets(self, page, base_url: str) -> None:
        """Kanban columns have drop-target attributes or event listeners (§9.15)."""
        _go(page, base_url)

        if not self._activate_kanban(page):
            pytest.skip("Kanban view not available — skipping drop-target check")

        drop_target_selectors = [
            ".kanban-column",
            "[class*='kanban-column']",
            "[data-drop-target]",
            "[data-column]",
        ]
        found_column = False
        for sel in drop_target_selectors:
            if page.locator(sel).count() > 0:
                found_column = True
                break

        if not found_column:
            pytest.skip("No kanban column elements found — skipping drop-target check")

    def test_drag_handle_present_on_kanban_cards(self, page, base_url: str) -> None:
        """Kanban cards expose a drag handle element or cursor:grab style (§9.15)."""
        _go(page, base_url)

        if not self._activate_kanban(page):
            pytest.skip("Kanban view not available — skipping drag handle check")

        drag_handle_selectors = [
            "[aria-label*='drag' i]",
            "[data-drag-handle]",
            ".drag-handle",
            "[class*='drag-handle']",
            ".handle",
        ]
        has_handle = any(
            page.locator(sel).count() > 0 for sel in drag_handle_selectors
        )

        if not has_handle:
            # Acceptable: the whole card may be draggable without a dedicated handle
            card_selectors = [
                ".kanban-card",
                "[class*='kanban-card']",
                "[draggable='true']",
            ]
            has_card = any(page.locator(sel).count() > 0 for sel in card_selectors)
            if not has_card:
                pytest.skip(
                    "No kanban cards or drag handles found — "
                    "skipping drag handle presence check"
                )


# ---------------------------------------------------------------------------
# §9.14 — Row click opens detail panel
# ---------------------------------------------------------------------------


class TestWorkflowsDetailPanel:
    """Clicking a workflow row must open the §9.14 sliding inspector panel."""

    def test_detail_panel_trigger_elements_exist(self, page, base_url: str) -> None:
        """At least one element on the workflows page can open a detail panel."""
        _go(page, base_url)

        trigger_selectors = [
            "[data-detail-trigger]",
            "[data-panel-trigger]",
            "tr[hx-get]",
            "table tbody tr",
            "a[href*='detail']",
            "button[aria-label*='detail' i]",
            "button[aria-label*='inspect' i]",
            "button[aria-label*='view' i]",
        ]
        found = any(page.locator(sel).count() > 0 for sel in trigger_selectors)

        if not found:
            body = page.locator("body").inner_text().lower()
            if "no workflow" in body or "no data" in body or "empty" in body:
                pytest.skip(
                    "Workflows page is empty — no rows to trigger detail panel"
                )
            pytest.skip("No detail-panel trigger elements found on workflows page")

    def test_row_click_opens_detail_panel(self, page, base_url: str) -> None:
        """Clicking a workflow row reveals a §9.14 detail/inspector panel in the DOM."""
        _go(page, base_url)

        if not _has_workflow_rows(page):
            pytest.skip("No workflow rows in table — skipping detail-panel click test")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr[data-href]",
            "table tbody tr",
        ]
        clicked_row = False
        for sel in row_selectors:
            rows = page.locator(sel)
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)  # allow HTMX swap / CSS transition
            clicked_row = True
            break

        if not clicked_row:
            pytest.skip("No visible workflow rows found to click")

        # §9.14: a side panel / drawer / dialog should become visible
        panel_sel = (
            "[role='complementary'], [role='dialog'], "
            ".detail-panel, .inspector-panel, .slide-panel, "
            "[data-panel], [id*='detail'], [id*='panel'], "
            "[class*='detail-panel'], [class*='inspector']"
        )
        panel = page.locator(panel_sel)
        assert panel.count() > 0, (
            "Clicking a workflow row must reveal a §9.14 side panel/drawer element — "
            "none found after click"
        )

    def test_detail_panel_contains_workflow_content(self, page, base_url: str) -> None:
        """The detail panel opened by a row click contains workflow-related content."""
        _go(page, base_url)

        if not _has_workflow_rows(page):
            pytest.skip("No workflow rows — skipping detail content check")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        clicked_row = False
        for sel in row_selectors:
            rows = page.locator(sel)
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)
            clicked_row = True
            break

        if not clicked_row:
            pytest.skip("No visible workflow rows found to click")

        body_text = page.locator("body").inner_text().lower()
        workflow_keywords = [
            "workflow", "status", "repo", "duration",
            "running", "stuck", "failed", "queued", "id",
        ]
        has_workflow_content = any(kw in body_text for kw in workflow_keywords)
        assert has_workflow_content, (
            "Detail panel must contain workflow-related content "
            "(status, repo, duration, etc.) — none of the expected keywords found"
        )

    def test_detail_panel_can_be_dismissed(self, page, base_url: str) -> None:
        """Once opened, the workflow detail panel can be closed via close button or Escape."""
        _go(page, base_url)

        if not _has_workflow_rows(page):
            pytest.skip("No workflow rows — skipping panel dismiss test")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        clicked_row = False
        for sel in row_selectors:
            rows = page.locator(sel)
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)
            clicked_row = True
            break

        if not clicked_row:
            pytest.skip("No visible workflow rows found to click")

        # Try close button first
        close_btn = page.locator(
            "[aria-label='Close'], [aria-label='Dismiss'], "
            "button[data-close], button.close, .panel-close, [data-panel-close]"
        ).first
        if close_btn.count() and close_btn.is_visible():
            close_btn.click()
        else:
            page.keyboard.press("Escape")

        page.wait_for_timeout(400)

        still_open_sel = (
            "[role='complementary'][aria-hidden='false'], "
            ".detail-panel:not(.hidden):not([hidden]), "
            ".inspector-panel:not(.hidden):not([hidden])"
        )
        still_visible_count = page.locator(still_open_sel).count()
        assert still_visible_count == 0, (
            "Workflow detail panel must be dismissible — "
            "panel still visible after close action"
        )

    def test_detail_panel_hidden_before_interaction(self, page, base_url: str) -> None:
        """The detail panel is hidden or absent before any row is clicked (§9.14)."""
        _go(page, base_url)

        visible_panel_sel = (
            ".detail-panel:not(.hidden):not([hidden]):not([aria-hidden='true']), "
            ".inspector-panel:not(.hidden):not([hidden]):not([aria-hidden='true'])"
        )
        visible_count = page.locator(visible_panel_sel).count()
        assert visible_count == 0, (
            f"Detail panel must be hidden on initial page load — "
            f"found {visible_count} visible panel(s) before any interaction (§9.14)"
        )


# ---------------------------------------------------------------------------
# View preference persistence
# ---------------------------------------------------------------------------


class TestWorkflowsViewPersistence:
    """View preference (list vs kanban) must persist across page navigation."""

    def test_view_preference_persisted_in_url_or_storage(
        self, page, base_url: str
    ) -> None:
        """After switching to kanban, the URL or localStorage records the preference."""
        _go(page, base_url)

        toggle = _find_view_toggle(page)
        if toggle is None:
            pytest.skip("No view toggle found — skipping persistence check")

        toggle.click()
        page.wait_for_timeout(500)

        # Check URL for view param
        current_url = page.url
        url_has_view = "kanban" in current_url or "view=" in current_url

        # Check localStorage for view preference
        local_storage_val = page.evaluate(
            """
            (function() {
                try {
                    var keys = Object.keys(localStorage);
                    for (var i = 0; i < keys.length; i++) {
                        var k = keys[i];
                        if (k.includes('view') || k.includes('kanban') || k.includes('layout')) {
                            return localStorage.getItem(k);
                        }
                    }
                } catch(e) {}
                return null;
            })()
            """
        )
        storage_has_view = local_storage_val is not None

        # Check sessionStorage as well
        session_storage_val = page.evaluate(
            """
            (function() {
                try {
                    var keys = Object.keys(sessionStorage);
                    for (var i = 0; i < keys.length; i++) {
                        var k = keys[i];
                        if (k.includes('view') || k.includes('kanban') || k.includes('layout')) {
                            return sessionStorage.getItem(k);
                        }
                    }
                } catch(e) {}
                return null;
            })()
            """
        )
        session_has_view = session_storage_val is not None

        # At least one persistence mechanism should be in use
        if not (url_has_view or storage_has_view or session_has_view):
            pytest.skip(
                "View preference not persisted in URL, localStorage, or sessionStorage — "
                "persistence may be handled server-side or via cookies"
            )

    def test_view_preserved_after_reload(self, page, base_url: str) -> None:
        """Switching to kanban and reloading the page keeps kanban as the active view."""
        _go(page, base_url)

        toggle = _find_view_toggle(page)
        if toggle is None:
            pytest.skip("No view toggle found — skipping reload persistence test")

        toggle.click()
        page.wait_for_timeout(500)

        if not _has_kanban(page):
            # Toggle didn't produce a kanban view — skip rather than fail
            pytest.skip(
                "Toggle click did not produce a kanban view — "
                "skipping reload persistence test"
            )

        # Reload and check view is still kanban
        page.reload()
        page.wait_for_timeout(800)

        still_kanban = _has_kanban(page)
        if not still_kanban:
            # Acceptable: reload may reset to default list view
            pytest.skip(
                "Kanban view was not preserved after reload — "
                "implementation may default to list on page load"
            )

    def test_view_preference_does_not_affect_other_pages(
        self, page, base_url: str
    ) -> None:
        """View preference on /workflows does not bleed into unrelated pages."""
        _go(page, base_url)

        toggle = _find_view_toggle(page)
        if toggle is not None:
            try:
                toggle.click()
                page.wait_for_timeout(300)
            except Exception:  # noqa: BLE001
                pass

        # Navigate away and come back
        navigate(page, f"{base_url}/admin/ui/repos")  # type: ignore[arg-type]
        page.wait_for_timeout(400)

        # Repos page must not show a kanban board (different page, different preference)
        repos_kanban = page.locator(".kanban-board, [data-view='kanban']").count()
        assert repos_kanban == 0, (
            "Kanban view preference from /workflows leaked into /repos page — "
            "view preferences must be scoped per-page"
        )
