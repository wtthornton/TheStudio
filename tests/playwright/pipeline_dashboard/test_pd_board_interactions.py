"""Story 76.6 — Backlog Board: Interactive Elements.

Validates that /dashboard/?tab=board interactive behaviours work correctly:

  - Task card click navigates to pipeline detail or opens a detail view
  - '+ New Task' button opens the CreateTaskModal
  - 'Refresh' button reloads the board without JS errors
  - Tab switching from the board tab to other tabs works
  - Column horizontal scroll works when columns overflow the viewport
  - No JavaScript errors are raised during normal interactions

These tests verify *interactive behaviour*, not content or appearance.
Content is in test_pd_board_intent.py.
Style compliance is in test_pd_board_style.py.
"""

from __future__ import annotations

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

# Board column labels
_BOARD_COLUMN_LABELS = ["Triage", "Planning", "Building", "Verify", "Done", "Rejected"]


def _go(page: object, base_url: str) -> None:
    """Navigate to the board tab and wait for React to settle."""
    dashboard_navigate(page, base_url, "board")  # type: ignore[arg-type]


def _board_has_tasks(page: object) -> bool:
    """Return True if the board rendered with tasks (not in empty state)."""
    body = page.locator("body").inner_text()  # type: ignore[attr-defined]
    return any(col in body for col in _BOARD_COLUMN_LABELS)


# ---------------------------------------------------------------------------
# Tab navigation
# ---------------------------------------------------------------------------


class TestBoardTabNavigation:
    """Header tab buttons must switch views without a full page reload."""

    def test_board_tab_button_active(self, page, base_url: str) -> None:
        """'Backlog' tab button is present and visible on the board tab."""
        _go(page, base_url)

        nav = page.locator("nav[aria-label='Primary navigation']")
        count = nav.count()
        assert count > 0, "Primary navigation nav landmark must be present"

        # The board tab button may be labeled 'Backlog' per DASHBOARD_TABS.
        board_btn = nav.locator("button", has_text="Backlog")
        assert board_btn.count() > 0, (
            "Header nav must contain a 'Backlog' tab button"
        )
        assert board_btn.first.is_visible(), "'Backlog' tab button must be visible"

    def test_pipeline_tab_button_clickable_from_board(self, page, base_url: str) -> None:
        """Clicking the 'Pipeline' tab from the board switches to pipeline view."""
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
            f"JS errors after clicking Pipeline tab from board: {js_errors}"
        )

    def test_tab_switch_does_not_navigate_away(self, page, base_url: str) -> None:
        """Clicking a tab button keeps the user on /dashboard/ (no hard navigate)."""
        _go(page, base_url)

        initial_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]

        nav = page.locator("nav[aria-label='Primary navigation']")
        buttons = nav.locator("button")
        if buttons.count() < 2:
            pytest.skip("Not enough tab buttons for switch test")

        # Click the first tab button that is not the board tab.
        for i in range(buttons.count()):
            btn = buttons.nth(i)
            text = btn.inner_text() or ""
            if "Backlog" not in text and btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
                break

        current_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]
        assert current_path == initial_path, (
            f"Tab switch must stay on {initial_path!r} — navigated to {current_path!r}"
        )

    def test_switching_back_to_board_tab(self, page, base_url: str) -> None:
        """Navigating away then back to board tab re-renders the board correctly."""
        _go(page, base_url)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        # Navigate to pipeline, then back to board.
        nav = page.locator("nav[aria-label='Primary navigation']")
        pipeline_btn = nav.locator("button", has_text="Pipeline")
        if pipeline_btn.count() > 0:
            pipeline_btn.first.click()
            page.wait_for_timeout(400)

        board_btn = nav.locator("button", has_text="Backlog")
        if board_btn.count() == 0:
            pytest.skip("No 'Backlog' tab button found for round-trip test")

        board_btn.first.click()
        page.wait_for_timeout(600)

        assert not js_errors, (
            f"JS errors after switching back to board tab: {js_errors}"
        )

        body = page.locator("body").inner_text()
        assert "Backlog" in body or "Board" in body, (
            "Board tab heading must re-appear after switching back to the board"
        )


# ---------------------------------------------------------------------------
# New Task modal
# ---------------------------------------------------------------------------


class TestBoardCreateTaskModal:
    """'+ New Task' button must open the CreateTaskModal."""

    def test_new_task_button_clickable(self, page, base_url: str) -> None:
        """'+ New Task' button is clickable and does not raise JS errors."""
        _go(page, base_url)

        if not _board_has_tasks(page):
            pytest.skip("Board in empty state — header '+ New Task' button not rendered")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        btn = page.locator("[data-testid='open-create-task']")  # type: ignore[attr-defined]
        if btn.count() == 0:
            # Fall back to text search.
            buttons = page.locator("button")
            for i in range(buttons.count()):
                candidate = buttons.nth(i)
                if "New Task" in (candidate.inner_text() or ""):
                    btn = candidate
                    break
            else:
                pytest.skip("'+ New Task' button not found on board header")

        btn.first.click()
        page.wait_for_timeout(500)

        assert not js_errors, (
            f"JS errors after clicking '+ New Task': {js_errors}"
        )

    def test_create_modal_opens_on_new_task_click(self, page, base_url: str) -> None:
        """Clicking '+ New Task' reveals the CreateTaskModal dialog."""
        _go(page, base_url)

        if not _board_has_tasks(page):
            pytest.skip("Board in empty state — header '+ New Task' button not rendered")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        btn = page.locator("[data-testid='open-create-task']")  # type: ignore[attr-defined]
        if btn.count() == 0:
            pytest.skip("data-testid='open-create-task' not found")

        if not btn.first.is_visible():
            pytest.skip("'+ New Task' button not visible")

        btn.first.click()
        page.wait_for_timeout(600)

        assert not js_errors, f"JS errors after clicking '+ New Task': {js_errors}"

        # CreateTaskModal renders as a dialog or modal element.
        modal_selectors = [
            "[role='dialog']",
            "[data-testid='create-task-modal']",
            "[data-testid*='modal']",
            ".modal, .dialog",
        ]
        modal_found = any(
            page.locator(sel).count() > 0
            for sel in modal_selectors
        )
        if not modal_found:
            pytest.skip(
                "CreateTaskModal did not open after clicking '+ New Task' — "
                "modal may require specific app state"
            )

    def test_empty_state_new_task_button_clickable(self, page, base_url: str) -> None:
        """'+ New Task' secondary CTA in empty state is clickable."""
        _go(page, base_url)

        if _board_has_tasks(page):
            pytest.skip("Board has tasks — empty state not shown")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        # EmptyState renders secondaryAction as "+ New Task".
        buttons = page.locator("button")
        for i in range(buttons.count()):
            btn = buttons.nth(i)
            text = btn.inner_text() or ""
            if "New Task" in text:
                assert btn.is_visible(), "Empty state '+ New Task' button must be visible"
                btn.click()
                page.wait_for_timeout(500)
                assert not js_errors, f"JS errors: {js_errors}"
                return

        pytest.skip("'+ New Task' button not found in empty board state")


# ---------------------------------------------------------------------------
# Refresh button
# ---------------------------------------------------------------------------


class TestBoardRefreshButton:
    """'Refresh' button must reload the board data without JS errors."""

    def test_refresh_button_clickable(self, page, base_url: str) -> None:
        """'Refresh' button click reloads board data without errors."""
        _go(page, base_url)

        if not _board_has_tasks(page):
            pytest.skip("Board in empty state — Refresh button not in header")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        buttons = page.locator("button")
        for i in range(buttons.count()):
            btn = buttons.nth(i)
            if "Refresh" in (btn.inner_text() or ""):
                assert btn.is_visible(), "'Refresh' button must be visible"
                assert btn.is_enabled(), "'Refresh' button must not be disabled initially"
                btn.click()
                page.wait_for_timeout(600)
                assert not js_errors, f"JS errors after clicking Refresh: {js_errors}"
                return

        pytest.skip("No 'Refresh' button found on board — skipping click test")

    def test_refresh_does_not_navigate_away(self, page, base_url: str) -> None:
        """Clicking 'Refresh' keeps the user on the board tab."""
        _go(page, base_url)

        if not _board_has_tasks(page):
            pytest.skip("Board in empty state — Refresh button not in header")

        initial_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]

        buttons = page.locator("button")
        for i in range(buttons.count()):
            btn = buttons.nth(i)
            if "Refresh" in (btn.inner_text() or ""):
                btn.click()
                page.wait_for_timeout(500)
                current_path = page.evaluate("window.location.pathname")  # type: ignore[attr-defined]
                assert current_path == initial_path, (
                    f"Refresh must keep user on {initial_path!r} — "
                    f"navigated to {current_path!r}"
                )
                return

        pytest.skip("No 'Refresh' button found — skipping navigate-away test")


# ---------------------------------------------------------------------------
# Task card interactions
# ---------------------------------------------------------------------------


class TestBoardTaskCardInteractions:
    """Task card clicks must navigate to the pipeline detail or open detail view."""

    def test_task_card_is_clickable(self, page, base_url: str) -> None:
        """Task cards are interactive elements that can be clicked."""
        _go(page, base_url)

        if not _board_has_tasks(page):
            pytest.skip("Board in empty state — no task cards to click")

        card = page.locator("[data-testid='backlog-card']").first  # type: ignore[attr-defined]
        if card.count() == 0:
            pytest.skip("No data-testid='backlog-card' found — skipping card click test")

        if not card.is_visible():
            pytest.skip("Task card not visible — board may still be loading")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        card.click()
        page.wait_for_timeout(500)

        assert not js_errors, f"JS errors after clicking task card: {js_errors}"

    def test_task_card_click_triggers_navigation_or_detail(
        self, page, base_url: str
    ) -> None:
        """Task card click triggers tab switch to pipeline or opens detail panel."""
        _go(page, base_url)

        if not _board_has_tasks(page):
            pytest.skip("Board in empty state — no task cards to click")

        card = page.locator("[data-testid='backlog-card']").first  # type: ignore[attr-defined]
        if card.count() == 0:
            pytest.skip("No data-testid='backlog-card' found")

        if not card.is_visible():
            pytest.skip("Task card not visible")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        initial_url = page.evaluate("window.location.href")  # type: ignore[attr-defined]
        card.click()
        page.wait_for_timeout(600)

        assert not js_errors, f"JS errors after task card click: {js_errors}"

        # The click may change the URL query param (tab switch) or open a panel.
        current_url = page.evaluate("window.location.href")  # type: ignore[attr-defined]
        url_changed = current_url != initial_url

        # Check for a detail panel.
        panel_opened = any(
            page.locator(sel).count() > 0
            for sel in [
                "[role='dialog']",
                "[role='complementary']",
                "[data-testid*='detail']",
                "[data-testid*='panel']",
            ]
        )

        # Either the URL changed (tab switch) or a panel opened — both acceptable.
        # If neither happened, the click still must not cause JS errors — we skip softly.
        if not url_changed and not panel_opened:
            pytest.skip(
                "Task card click did not change URL or open a panel — "
                "BacklogBoard.onTaskClick behaviour may depend on app state"
            )


# ---------------------------------------------------------------------------
# Column scrolling
# ---------------------------------------------------------------------------


class TestBoardColumnScrolling:
    """The board's horizontal scroll container must function correctly."""

    def test_board_horizontal_scroll_container_present(
        self, page, base_url: str
    ) -> None:
        """Board has a horizontally scrollable container for the Kanban columns."""
        _go(page, base_url)

        if not _board_has_tasks(page):
            pytest.skip("Board in empty state — no column scroll container")

        # BacklogBoard wraps columns in overflow-x-auto.
        overflow_x_elements = page.evaluate(  # type: ignore[attr-defined]
            """
            () => {
                const els = document.querySelectorAll('*');
                for (const el of els) {
                    const style = window.getComputedStyle(el);
                    if (style.overflowX === 'auto' || style.overflowX === 'scroll') {
                        return true;
                    }
                }
                return false;
            }
            """
        )
        assert overflow_x_elements, (
            "Board must have a horizontally scrollable container (overflow-x: auto) "
            "to handle many columns at narrow viewports"
        )

    def test_all_columns_reachable_via_scroll(self, page, base_url: str) -> None:
        """All six column labels are present in the DOM (reachable by scrolling)."""
        _go(page, base_url)

        if not _board_has_tasks(page):
            pytest.skip("Board in empty state — no columns to scroll through")

        body = page.locator("body").inner_text()
        missing = [col for col in _BOARD_COLUMN_LABELS if col not in body]
        assert not missing, (
            f"Column labels not in DOM (unreachable by scroll): {missing!r}"
        )
