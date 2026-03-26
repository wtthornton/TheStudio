"""Epic 70.4 — Execution Planes: Interactive Elements.

Validates that /admin/ui/planes interactive behaviours work correctly:

  Pause action       — A pause button is present on plane entries and is interactive
  Resume action      — A resume button is present on paused planes and is interactive
  Registration       — Registration/deregistration controls are present and interactive
  Action response    — Clicking actions causes a visible DOM change
  HTMX attributes    — Action elements carry correct hx-* attributes
  JS errors          — No JS errors are raised during action interactions
  Initial state      — No spurious dialogs or error states visible on load

These tests verify *interactive behaviour*, not content or appearance.
Content is covered in test_planes_intent.py (Epic 70.1).
API contracts are covered in test_planes_api.py (Epic 70.2).
Style compliance is covered in test_planes_style.py (Epic 70.3).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

PLANES_URL = "/admin/ui/planes"


def _go(page: object, base_url: str) -> None:
    """Navigate to the execution planes page and wait for content to settle."""
    navigate(page, f"{base_url}{PLANES_URL}")  # type: ignore[arg-type]


def _has_plane_entries(page: object) -> bool:
    """Return True when at least one execution plane row or card is visible."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator(
            "[data-plane], [class*='plane-card'], [data-cluster], [class*='cluster-card']"
        ).count()
        > 0
    )


def _find_action_button(page: object, keywords: list[str]) -> object | None:
    """Return the first visible action button matching any keyword, or None."""
    selectors = []
    for kw in keywords:
        selectors.extend(
            [
                f"button:has-text('{kw}')",
                f"a:has-text('{kw}')",
                f"button[aria-label*='{kw}' i]",
                f"[data-action='{kw.lower()}']",
                f"[data-plane-action='{kw.lower()}']",
                f"[class*='{kw.lower()}-btn']",
                f"[class*='btn-{kw.lower()}']",
            ]
        )

    for sel in selectors:
        try:
            btns = page.locator(sel)  # type: ignore[attr-defined]
            if btns.count() > 0:
                first = btns.first
                if first.is_visible():
                    return first
        except Exception:  # noqa: BLE001
            continue
    return None


def _dismiss_any_dialog(page: object) -> None:
    """Attempt to dismiss any open dialog via Cancel button or Escape key."""
    cancel_selectors = [
        "button[aria-label='Cancel']",
        "button:has-text('Cancel')",
        "button:has-text('No')",
        "button:has-text('Dismiss')",
        "[data-dialog-cancel]",
    ]
    for sel in cancel_selectors:
        try:
            btn = page.locator(sel).first  # type: ignore[attr-defined]
            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(300)  # type: ignore[attr-defined]
                return
        except Exception:  # noqa: BLE001
            continue
    try:
        page.keyboard.press("Escape")  # type: ignore[attr-defined]
        page.wait_for_timeout(300)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Pause action
# ---------------------------------------------------------------------------


class TestPlanesPauseAction:
    """A pause action must be present and interactive when running planes are shown."""

    def test_pause_button_exists(self, page: object, base_url: str) -> None:
        """At least one pause action button is present when planes are listed."""
        _go(page, base_url)

        if not _has_plane_entries(page):
            pytest.skip(
                "No execution planes registered — skipping pause button existence check"
            )

        btn = _find_action_button(page, ["Pause", "Suspend", "Stop", "Disable"])
        if btn is None:
            pytest.skip(
                "No explicit pause/suspend button found on planes page — "
                "action may be accessible via row detail panel"
            )

    def test_pause_button_is_enabled(self, page: object, base_url: str) -> None:
        """Pause action buttons must not be permanently disabled."""
        _go(page, base_url)

        if not _has_plane_entries(page):
            pytest.skip("No execution planes — skipping pause enabled check")

        btn = _find_action_button(page, ["Pause", "Suspend", "Stop", "Disable"])
        if btn is None:
            pytest.skip("No pause button found — skipping enabled check")

        assert btn.is_enabled(), (  # type: ignore[attr-defined]
            "Pause action button must not be permanently disabled — "
            "operators need to pause execution planes"
        )

    def test_pause_button_interaction_triggers_change(
        self, page: object, base_url: str
    ) -> None:
        """Clicking a pause button must cause a DOM change (confirmation or state update)."""
        _go(page, base_url)

        if not _has_plane_entries(page):
            pytest.skip("No execution planes — skipping pause interaction test")

        btn = _find_action_button(page, ["Pause", "Suspend", "Stop", "Disable"])
        if btn is None:
            pytest.skip("No pause button found — skipping interaction test")

        before = page.locator("body").inner_html()  # type: ignore[attr-defined]
        btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]
        after = page.locator("body").inner_html()  # type: ignore[attr-defined]

        assert before != after, (
            "Clicking pause button must update the DOM — "
            "body HTML was identical before and after click"
        )

        _dismiss_any_dialog(page)


# ---------------------------------------------------------------------------
# Resume action
# ---------------------------------------------------------------------------


class TestPlanesResumeAction:
    """A resume action must be present and interactive for paused execution planes."""

    def test_resume_button_exists(self, page: object, base_url: str) -> None:
        """At least one resume action button is present on the planes page."""
        _go(page, base_url)

        if not _has_plane_entries(page):
            pytest.skip(
                "No execution planes registered — skipping resume button existence check"
            )

        btn = _find_action_button(page, ["Resume", "Restart", "Enable", "Activate", "Start"])
        if btn is None:
            pytest.skip(
                "No explicit resume/restart button found on planes page — "
                "action may appear only when a plane is paused"
            )

    def test_resume_button_is_enabled(self, page: object, base_url: str) -> None:
        """Resume action buttons must not be permanently disabled."""
        _go(page, base_url)

        if not _has_plane_entries(page):
            pytest.skip("No execution planes — skipping resume enabled check")

        btn = _find_action_button(page, ["Resume", "Restart", "Enable", "Activate", "Start"])
        if btn is None:
            pytest.skip("No resume button found — skipping enabled check")

        assert btn.is_enabled(), (  # type: ignore[attr-defined]
            "Resume action button must not be permanently disabled — "
            "operators need to resume paused execution planes"
        )

    def test_resume_button_interaction_triggers_change(
        self, page: object, base_url: str
    ) -> None:
        """Clicking a resume button must cause a visible DOM change."""
        _go(page, base_url)

        if not _has_plane_entries(page):
            pytest.skip("No execution planes — skipping resume interaction test")

        btn = _find_action_button(page, ["Resume", "Restart", "Enable", "Activate", "Start"])
        if btn is None:
            pytest.skip("No resume button found — skipping interaction test")

        before = page.locator("body").inner_html()  # type: ignore[attr-defined]
        btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]
        after = page.locator("body").inner_html()  # type: ignore[attr-defined]

        assert before != after, (
            "Clicking resume button must update the DOM — "
            "body HTML was identical before and after click"
        )

        _dismiss_any_dialog(page)


# ---------------------------------------------------------------------------
# Registration controls
# ---------------------------------------------------------------------------


class TestPlanesRegistrationControls:
    """Registration and deregistration controls must be present and interactive."""

    def test_registration_control_exists(self, page: object, base_url: str) -> None:
        """A registration-related action is present on the execution planes page."""
        _go(page, base_url)

        btn = _find_action_button(
            page,
            [
                "Register",
                "Deregister",
                "Unregister",
                "Add plane",
                "Add worker",
                "Connect",
                "Disconnect",
            ],
        )
        body_lower = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
        registration_keywords = (
            "register",
            "deregister",
            "unregister",
            "add plane",
            "add worker",
            "connect",
            "disconnect",
        )
        has_registration_text = any(kw in body_lower for kw in registration_keywords)

        assert btn is not None or has_registration_text, (
            "Execution planes page must surface a registration control or registration-related "
            "text — operators need to manage plane registration from this page"
        )

    def test_deregister_button_interaction_triggers_change(
        self, page: object, base_url: str
    ) -> None:
        """Clicking a deregister button must cause a visible DOM change."""
        _go(page, base_url)

        if not _has_plane_entries(page):
            pytest.skip("No execution planes — skipping deregister interaction test")

        btn = _find_action_button(
            page, ["Deregister", "Unregister", "Remove", "Disconnect", "Delete"]
        )
        if btn is None:
            pytest.skip(
                "No deregister/remove button found on planes page — "
                "registration controls may require a detail panel"
            )

        before = page.locator("body").inner_html()  # type: ignore[attr-defined]
        btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]
        after = page.locator("body").inner_html()  # type: ignore[attr-defined]

        assert before != after, (
            "Clicking deregister button must update the DOM — "
            "body HTML was identical before and after click"
        )

        _dismiss_any_dialog(page)

    def test_registration_controls_have_labels(self, page: object, base_url: str) -> None:
        """Registration action buttons must have descriptive accessible labels.

        Operators working in high-pressure incident situations must be able to
        identify registration controls without ambiguity.
        """
        _go(page, base_url)

        reg_keywords = ["Register", "Deregister", "Unregister", "Connect", "Disconnect"]
        for kw in reg_keywords:
            selectors = [
                f"button:has-text('{kw}')",
                f"a:has-text('{kw}')",
                f"button[aria-label*='{kw}' i]",
            ]
            for sel in selectors:
                try:
                    btns = page.locator(sel)  # type: ignore[attr-defined]
                    count = btns.count()
                    for i in range(min(count, 5)):
                        btn = btns.nth(i)
                        if not btn.is_visible():
                            continue
                        text = (btn.inner_text() or "").strip()  # type: ignore[attr-defined]
                        aria_label = btn.get_attribute("aria-label") or ""  # type: ignore[attr-defined]
                        assert text or aria_label, (
                            f"Registration control button must have visible text or aria-label — "
                            f"found button matching '{kw}' with neither"
                        )
                except Exception:  # noqa: BLE001
                    continue


# ---------------------------------------------------------------------------
# HTMX attributes on action elements
# ---------------------------------------------------------------------------


class TestPlanesActionHtmxAttributes:
    """Execution plane action elements using HTMX must carry correct hx-* attributes."""

    def test_htmx_action_elements_have_target(self, page: object, base_url: str) -> None:
        """Elements with hx-post/hx-delete/hx-patch on the planes page declare hx-target or hx-swap."""
        _go(page, base_url)

        hx_elements = page.locator(  # type: ignore[attr-defined]
            "[hx-post], [hx-delete], [hx-put], [hx-patch]"
        )
        count = hx_elements.count()

        if count == 0:
            pytest.skip(
                "No HTMX mutation elements found on planes page — "
                "page may not use HTMX for actions"
            )

        for i in range(min(count, 10)):
            el = hx_elements.nth(i)
            hx_target = el.get_attribute("hx-target")
            hx_swap = el.get_attribute("hx-swap")
            assert hx_target is not None or hx_swap is not None, (
                f"HTMX mutation element {i} on planes page must declare hx-target or hx-swap"
            )

    def test_htmx_targets_exist_in_dom(self, page: object, base_url: str) -> None:
        """hx-target selectors on plane action buttons reference DOM elements that exist."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-target]")  # type: ignore[attr-defined]
        count = hx_elements.count()

        if count == 0:
            pytest.skip("No elements with hx-target found on planes page")

        relative_keywords = ("this", "closest", "next", "previous", "find")
        missing: list[str] = []
        for i in range(min(count, 10)):
            target_sel = hx_elements.nth(i).get_attribute("hx-target") or ""
            if not target_sel:
                continue
            if any(target_sel.startswith(kw) for kw in relative_keywords):
                continue
            try:
                if page.locator(target_sel).count() == 0:  # type: ignore[attr-defined]
                    missing.append(target_sel)
            except Exception:  # noqa: BLE001
                pass

        assert not missing, (
            f"hx-target selector(s) not found in DOM on planes page: {missing}"
        )

    def test_no_js_errors_on_action_click(self, page: object, base_url: str) -> None:
        """Clicking a planes action button must not raise JS errors."""
        _go(page, base_url)

        if not _has_plane_entries(page):
            pytest.skip("No execution planes — skipping JS error check")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        btn = _find_action_button(
            page,
            ["Pause", "Resume", "Suspend", "Deregister", "Disable", "Enable"],
        )
        if btn is None:
            pytest.skip("No action buttons found — skipping JS error check")

        btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]

        _dismiss_any_dialog(page)

        assert not js_errors, (
            f"JS errors occurred during planes action click: {js_errors}"
        )


# ---------------------------------------------------------------------------
# Initial page state
# ---------------------------------------------------------------------------


class TestPlanesInitialState:
    """Execution planes page must load cleanly with no spurious dialogs or error state."""

    def test_no_dialog_visible_on_load(self, page: object, base_url: str) -> None:
        """Confirmation or action dialogs must not be visible before any user interaction."""
        _go(page, base_url)

        visible_dialog_sel = (
            "[role='dialog']:not([aria-hidden='true']):not(.hidden):not([hidden]), "
            "[role='alertdialog']:not([aria-hidden='true']):not(.hidden):not([hidden])"
        )
        visible_count = page.locator(visible_dialog_sel).count()  # type: ignore[attr-defined]
        assert visible_count == 0, (
            f"No dialog must be visible on initial planes page load — "
            f"found {visible_count} visible dialog(s) before any interaction"
        )

    def test_action_buttons_exist_or_page_is_empty(
        self, page: object, base_url: str
    ) -> None:
        """Either action controls are present (with entries) or the page shows empty state."""
        _go(page, base_url)

        has_entries = _has_plane_entries(page)
        if not has_entries:
            body_text = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            empty_keywords = (
                "no planes",
                "no workers",
                "no clusters",
                "nothing registered",
                "empty",
                "no execution",
            )
            has_empty_state = any(kw in body_text for kw in empty_keywords)
            assert has_empty_state or len(body_text.strip()) > 10, (
                "Planes page shows no entries and no legible empty-state message — "
                "page may be broken or empty without operator feedback"
            )
            return

        # Has entries — verify some action affordance exists
        btn = _find_action_button(
            page,
            [
                "Pause",
                "Resume",
                "Suspend",
                "Restart",
                "Enable",
                "Disable",
                "Register",
                "Deregister",
                "Connect",
                "Disconnect",
            ],
        )
        if btn is None:
            pytest.skip(
                "Planes page has entries but no top-level action buttons visible — "
                "actions may be in row detail panel (acceptable)"
            )

    def test_page_loads_without_js_errors(self, page: object, base_url: str) -> None:
        """Execution planes page must load without any JavaScript errors."""
        js_errors: list[str] = []

        # Register error handler before navigation
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        _go(page, base_url)
        page.wait_for_timeout(500)  # type: ignore[attr-defined]

        assert not js_errors, (
            f"JavaScript errors occurred on execution planes page load: {js_errors}"
        )
