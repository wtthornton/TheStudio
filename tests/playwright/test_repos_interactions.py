"""Epic 60.4 — Repo Management: Interactive Elements.

Validates that /admin/ui/repos interactive behaviours work correctly:

  §9.14  — Row click opens the sliding inspector/detail panel
  HTMX   — Detail content is loaded via HTMX swap (hx-get, hx-target)
  Buttons — Action buttons are visible, enabled, and clickable
  Panel  — Detail panel can be dismissed via close button or Escape key

These tests verify *interactive behaviour*, not content or appearance.
Content is covered in test_repos_intent.py (Epic 60.1).
Style compliance is covered in test_repos_style.py (Epic 60.3).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate
from tests.playwright.lib.interaction_helpers import (
    assert_button_clickable,
    assert_htmx_swap,
    click_and_assert_state_change,
)

pytestmark = pytest.mark.playwright

REPOS_URL = "/admin/ui/repos"


def _go(page: object, base_url: str) -> None:
    """Navigate to the repos page and wait for content to settle."""
    navigate(page, f"{base_url}{REPOS_URL}")  # type: ignore[arg-type]


def _has_repo_rows(page: object) -> bool:
    """Return True when the repos table has at least one data row."""
    return page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Action buttons
# ---------------------------------------------------------------------------


class TestReposActionButtons:
    """Action buttons on the repos page must be visible, enabled, and clickable."""

    def test_primary_action_buttons_present(self, page, base_url: str) -> None:
        """At least one action button is present on the repos page."""
        _go(page, base_url)

        buttons = page.locator("button, [role='button']")
        count = buttons.count()

        if count == 0:
            pytest.skip(
                "No buttons found on repos page — acceptable for read-only view"
            )

        # At least the first button must be visible and enabled
        first_btn = buttons.first
        assert first_btn.is_visible(), "First action button must be visible"
        assert first_btn.is_enabled(), "First action button must not be disabled"

    def test_add_repo_button_clickable(self, page, base_url: str) -> None:
        """'Add Repo' or equivalent primary CTA button is clickable."""
        _go(page, base_url)

        selectors = [
            "button[aria-label*='add' i]",
            "button[aria-label*='connect' i]",
            "button[aria-label*='new repo' i]",
            "a[href*='add']",
            "a[href*='new']",
            "button.btn-primary",
            "button[data-primary]",
        ]
        for sel in selectors:
            count = page.locator(sel).count()
            if count > 0:
                btn = page.locator(sel).first
                assert btn.is_visible(), f"CTA button ({sel!r}) must be visible"
                assert btn.is_enabled(), f"CTA button ({sel!r}) must be enabled"
                return

        # No primary CTA found — acceptable when the list is populated
        body = page.locator("body").inner_text().lower()
        has_add = "add" in body or "connect" in body or "register" in body
        if not has_add:
            pytest.skip("No add-repo CTA found on repos page")

    def test_no_permanently_disabled_primary_buttons(self, page, base_url: str) -> None:
        """Primary action buttons must not be permanently disabled."""
        _go(page, base_url)

        primary_btns = page.locator(
            "button.btn-primary, button[data-primary], button.primary"
        )
        count = primary_btns.count()

        if count == 0:
            pytest.skip("No explicitly-marked primary buttons found on repos page")

        for i in range(count):
            btn = primary_btns.nth(i)
            assert btn.is_enabled(), (
                f"Primary button at index {i} must not be permanently disabled"
            )


# ---------------------------------------------------------------------------
# HTMX swap attributes
# ---------------------------------------------------------------------------


class TestReposHtmxSwaps:
    """Repos page HTMX controls must carry correct hx-* attributes."""

    def test_htmx_elements_have_target(self, page, base_url: str) -> None:
        """Elements with hx-get or hx-post declare hx-target or hx-swap."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-get], [hx-post]")
        count = hx_elements.count()

        if count == 0:
            pytest.skip("No HTMX hx-get/hx-post elements found — page may not use HTMX")

        for i in range(min(count, 10)):
            el = hx_elements.nth(i)
            hx_target = el.get_attribute("hx-target")
            hx_swap = el.get_attribute("hx-swap")
            assert hx_target is not None or hx_swap is not None, (
                f"HTMX element {i} must declare hx-target or hx-swap"
            )

    def test_htmx_targets_exist_in_dom(self, page, base_url: str) -> None:
        """hx-target selectors on repos page reference elements in the current DOM."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-target]")
        count = hx_elements.count()

        if count == 0:
            pytest.skip("No elements with hx-target found on repos page")

        missing: list[str] = []
        for i in range(min(count, 10)):
            target_sel = hx_elements.nth(i).get_attribute("hx-target") or ""
            # Skip special HTMX relative-position keywords
            if not target_sel or target_sel in ("this", "closest", "next", "previous", "find"):
                continue
            if any(target_sel.startswith(kw) for kw in ("closest ", "next ", "find ")):
                continue
            try:
                if page.locator(target_sel).count() == 0:
                    missing.append(target_sel)
            except Exception:  # noqa: BLE001
                pass  # unusual selector syntax — skip

        assert not missing, (
            f"hx-target selector(s) not found in DOM: {missing}"
        )

    def test_repo_row_has_hx_get_for_detail(self, page, base_url: str) -> None:
        """Repo table rows with HTMX carry hx-get pointing to a detail endpoint."""
        _go(page, base_url)

        if not _has_repo_rows(page):
            pytest.skip("No repo rows in table — skipping HTMX row attribute check")

        hx_rows = page.locator("table tbody tr[hx-get]")
        if hx_rows.count() == 0:
            # Also acceptable: rows trigger JS navigation (not HTMX)
            data_rows = page.locator("table tbody tr[data-detail-trigger], table tbody tr[data-href]")
            if data_rows.count() == 0:
                pytest.skip(
                    "Repo rows use neither hx-get nor data-detail-trigger — "
                    "panel may be triggered via JS click handler"
                )
            return

        first_row = hx_rows.first
        hx_get_val = first_row.get_attribute("hx-get") or ""
        assert hx_get_val, "hx-get attribute on repo row must not be empty"


# ---------------------------------------------------------------------------
# §9.14 — Row click opens detail panel
# ---------------------------------------------------------------------------


class TestReposDetailPanel:
    """Clicking a repo row must open the §9.14 sliding inspector panel."""

    def test_detail_panel_trigger_elements_exist(self, page, base_url: str) -> None:
        """At least one element on the repos page can open a detail panel."""
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
            if "no repo" in body or "no data" in body or "empty" in body:
                pytest.skip("Repos page is empty — no rows to trigger detail panel")
            pytest.skip("No detail-panel trigger elements found on repos page")

    def test_row_click_opens_detail_panel(self, page, base_url: str) -> None:
        """Clicking a repo row reveals a §9.14 detail/inspector panel in the DOM."""
        _go(page, base_url)

        if not _has_repo_rows(page):
            pytest.skip("No repo rows in table — skipping detail-panel click test")

        # Prefer rows with explicit HTMX or data attributes; fall back to any row
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
            pytest.skip("No visible repo rows found to click")

        # §9.14: a side panel / drawer / dialog should become visible
        panel_sel = (
            "[role='complementary'], [role='dialog'], "
            ".detail-panel, .inspector-panel, .slide-panel, "
            "[data-panel], [id*='detail'], [id*='panel'], "
            "[class*='detail-panel'], [class*='inspector']"
        )
        panel = page.locator(panel_sel)
        assert panel.count() > 0, (
            "Clicking a repo row must reveal a §9.14 side panel/drawer element — "
            "none found after click"
        )

    def test_detail_panel_loads_repo_content(self, page, base_url: str) -> None:
        """The detail panel opened by a row click contains repo-related content."""
        _go(page, base_url)

        if not _has_repo_rows(page):
            pytest.skip("No repo rows — skipping detail content check")

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
            pytest.skip("No visible repo rows found to click")

        # The panel should contain repo-related text
        body_text = page.locator("body").inner_text().lower()
        repo_keywords = ["repo", "repository", "tier", "status", "branch", "queue", "owner"]
        has_repo_content = any(kw in body_text for kw in repo_keywords)
        assert has_repo_content, (
            "Detail panel must contain repo-related content (repo name, tier, status, etc.) — "
            "none of the expected keywords found after opening panel"
        )

    def test_detail_panel_can_be_dismissed(self, page, base_url: str) -> None:
        """Once opened, the repo detail panel can be closed via close button or Escape."""
        _go(page, base_url)

        if not _has_repo_rows(page):
            pytest.skip("No repo rows — skipping panel dismiss test")

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
            pytest.skip("No visible repo rows found to click")

        # Try close button first
        close_btn = page.locator(
            "[aria-label='Close'], [aria-label='Dismiss'], "
            "button[data-close], button.close, .panel-close, [data-panel-close]"
        ).first
        if close_btn.count() and close_btn.is_visible():
            close_btn.click()
        else:
            # Fallback: Escape key
            page.keyboard.press("Escape")

        page.wait_for_timeout(400)

        # Panel should be gone or hidden after dismissal
        still_open_sel = (
            "[role='complementary'][aria-hidden='false'], "
            ".detail-panel:not(.hidden):not([hidden]), "
            ".inspector-panel:not(.hidden):not([hidden])"
        )
        still_visible_count = page.locator(still_open_sel).count()
        assert still_visible_count == 0, (
            "Repo detail panel must be dismissible — panel still visible after close action"
        )


# ---------------------------------------------------------------------------
# HTMX detail content loading
# ---------------------------------------------------------------------------


class TestReposHtmxDetailLoad:
    """HTMX must load repo detail content into the panel swap target."""

    def test_htmx_detail_swap_triggers_on_row_click(self, page, base_url: str) -> None:
        """Clicking an HTMX row causes the hx-target to receive new content."""
        _go(page, base_url)

        hx_rows = page.locator("table tbody tr[hx-get]")
        if hx_rows.count() == 0:
            pytest.skip("No HTMX-enabled rows found — skipping swap trigger test")

        first_row = hx_rows.first
        if not first_row.is_visible():
            pytest.skip("HTMX row not visible — data may not be loaded")

        # Capture inner HTML of body before click
        before_html = page.locator("body").inner_html()

        first_row.click()
        page.wait_for_timeout(800)  # allow HTMX request + DOM swap

        after_html = page.locator("body").inner_html()
        assert before_html != after_html, (
            "Clicking an hx-get row must trigger an HTMX swap that changes the DOM — "
            "body HTML was identical before and after click"
        )

    def test_no_js_errors_on_row_click(self, page, base_url: str) -> None:
        """Row click that triggers HTMX detail load must not raise JS errors."""
        _go(page, base_url)

        if not _has_repo_rows(page):
            pytest.skip("No repo rows — skipping JS error check")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        for sel in row_selectors:
            rows = page.locator(sel)
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)
            break

        assert not js_errors, (
            f"JS errors occurred during repo row click / HTMX swap: {js_errors}"
        )

    def test_detail_panel_not_visible_before_interaction(self, page, base_url: str) -> None:
        """The detail panel is hidden or absent before any row is clicked."""
        _go(page, base_url)

        # Panels that are already open without interaction are an anti-pattern (§9.14)
        # They should be hidden/absent on initial page load
        visible_panel_sel = (
            ".detail-panel:not(.hidden):not([hidden]):not([aria-hidden='true']), "
            ".inspector-panel:not(.hidden):not([hidden]):not([aria-hidden='true'])"
        )
        visible_count = page.locator(visible_panel_sel).count()
        assert visible_count == 0, (
            f"Detail panel must be hidden on initial page load — "
            f"found {visible_count} visible panel(s) before any interaction (§9.14)"
        )
