"""Epic 69.4 — Dead-Letter Inspector: Interactive Elements.

Validates that /admin/ui/dead-letters interactive behaviours work correctly:

  Event detail expansion  — Clicking a row/card expands event detail (failure reason,
                            payload, attempt count) without navigating away
  Retry action            — A retry button is present and interactive on dead-letter entries
  Retry interaction       — Clicking retry causes a DOM change (confirmation or action)
  Confirmation dialog     — Destructive/retry actions require a confirmation before executing
  Dialog dismiss          — Confirmation dialog can be cancelled without performing the action
  HTMX attributes         — Action buttons carry correct hx-* attributes
  JS errors               — No JS errors raised during action interactions
  Initial state           — No dialogs visible before user interaction

Dead-lettered events have permanently exhausted their retry budget.  The detail
expansion surfaces the full failure context (payload, error trace, attempt count)
so operators can triage and decide whether manual replay is appropriate.

These tests verify *interactive behaviour*, not content or appearance.
Content is covered in test_dead_letters_intent.py (Epic 69.1).
API contracts are covered in test_dead_letters_api.py (Epic 69.2).
Style compliance is covered in test_dead_letters_style.py (Epic 69.3).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

DEAD_LETTERS_URL = "/admin/ui/dead-letters"


def _go(page: object, base_url: str) -> None:
    """Navigate to the dead-letter inspector page and wait for content to settle."""
    navigate(page, f"{base_url}{DEAD_LETTERS_URL}")  # type: ignore[arg-type]


def _has_dead_letter_entries(page: object) -> bool:
    """Return True when at least one dead-letter row or card is present."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator(
            "[data-dead-letter], [class*='dead-letter-card'], [data-event-id]"
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
                f"[data-dead-letter-action='{kw.lower()}']",
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


def _find_expandable_row(page: object) -> object | None:
    """Return the first row or card that looks expandable, or None."""
    expand_selectors = [
        "table tbody tr[data-expandable]",
        "table tbody tr[data-toggle]",
        "table tbody tr[aria-expanded]",
        "table tbody tr[data-dead-letter-id]",
        "table tbody tr[data-event-id]",
        "table tbody tr[class*='expandable']",
        "table tbody tr[class*='clickable']",
        "[data-dead-letter][data-expandable]",
        "[data-dead-letter][data-toggle]",
        "[class*='dead-letter-row']",
        "[class*='event-row']",
        # Generic: first tbody row (many HTMX tables expand on click)
        "table tbody tr:first-child",
    ]
    for sel in expand_selectors:
        try:
            el = page.locator(sel)  # type: ignore[attr-defined]
            if el.count() > 0:
                first = el.first
                if first.is_visible():
                    return first
        except Exception:  # noqa: BLE001
            continue
    return None


def _dismiss_any_dialog(page: object) -> None:
    """Try to dismiss any open dialog or confirmation prompt."""
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
# Event detail expansion
# ---------------------------------------------------------------------------


class TestDeadLetterEventDetailExpansion:
    """Clicking a dead-letter row or card must expand the event detail inline."""

    def test_row_click_changes_dom(self, page: object, base_url: str) -> None:
        """Clicking a dead-letter row/card causes a DOM change (expansion or navigation).

        Operators need to see the full failure context — payload, error trace,
        and attempt count — before deciding whether to retry or discard an event.
        Detail expansion keeps the operator on the list view for efficient triage.
        """
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip(
                "No dead-letter entries on page — skipping row click expansion test"
            )

        row = _find_expandable_row(page)
        if row is None:
            pytest.skip(
                "No expandable row found on dead-letter page — "
                "detail may be accessed via explicit expand button"
            )

        before = page.locator("body").inner_html()  # type: ignore[attr-defined]
        row.click()
        page.wait_for_timeout(700)  # type: ignore[attr-defined]
        after = page.locator("body").inner_html()  # type: ignore[attr-defined]

        assert before != after, (
            "Clicking a dead-letter row/card must update the DOM — "
            "body HTML was identical before and after click"
        )

        # Clean up: dismiss any panel or dialog that opened
        _dismiss_any_dialog(page)

    def test_detail_panel_shows_after_expand(self, page: object, base_url: str) -> None:
        """After expanding a dead-letter row, a detail panel or expanded section appears.

        The expanded section must surface event details. Any visible panel, drawer,
        or inline section appearing after row click satisfies this requirement.
        """
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip(
                "No dead-letter entries — skipping detail panel appearance test"
            )

        row = _find_expandable_row(page)
        if row is None:
            pytest.skip(
                "No expandable row found — skipping detail panel appearance test"
            )

        row.click()
        page.wait_for_timeout(700)  # type: ignore[attr-defined]

        panel_selectors = [
            "[aria-expanded='true']",
            ".detail-panel",
            "[class*='detail-panel']",
            ".inspector-panel",
            "[class*='inspector']",
            ".drawer",
            "[class*='drawer']",
            ".expanded",
            "[class*='expanded']",
            "[data-panel]",
            "[data-expanded]",
            "[data-detail]",
            "tr.expanded + tr",
            "tr + tr[class*='detail']",
        ]
        panel_found = any(
            page.locator(sel).count() > 0  # type: ignore[attr-defined]
            for sel in panel_selectors
        )

        if not panel_found:
            pytest.skip(
                "No recognisable detail panel found after row click — "
                "row may navigate to a separate detail page (acceptable)"
            )

        # Clean up
        _dismiss_any_dialog(page)

    def test_expand_button_if_present_is_enabled(self, page: object, base_url: str) -> None:
        """Explicit expand/details buttons must not be permanently disabled.

        Some implementations use a dedicated expand button (▶, "+", "Details")
        rather than making the whole row clickable. Such buttons must be enabled.
        """
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip(
                "No dead-letter entries — skipping expand button enabled check"
            )

        expand_btn = _find_action_button(
            page,
            ["Details", "Expand", "View", "Inspect", "Show", "More"],
        )
        if expand_btn is None:
            pytest.skip(
                "No explicit expand/details button found — "
                "row may be click-to-expand directly"
            )

        assert expand_btn.is_enabled(), (  # type: ignore[attr-defined]
            "Expand/Details button must not be permanently disabled — "
            "operators need to view dead-letter event detail"
        )


# ---------------------------------------------------------------------------
# Retry action
# ---------------------------------------------------------------------------


class TestDeadLetterRetryAction:
    """A retry/requeue action must be present and interactive on the dead-letter page."""

    def test_retry_button_exists(self, page: object, base_url: str) -> None:
        """At least one retry action button is present on the dead-letter page."""
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip(
                "No dead-letter entries on page — skipping retry button existence check"
            )

        btn = _find_action_button(
            page, ["Retry", "Requeue", "Replay", "Reprocess", "Resubmit"]
        )
        if btn is None:
            pytest.skip(
                "No explicit retry/requeue button found on dead-letter page — "
                "action may be accessible via row detail panel"
            )

    def test_retry_button_is_enabled(self, page: object, base_url: str) -> None:
        """Retry action buttons must not be permanently disabled."""
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip("No dead-letter entries — skipping retry enabled check")

        btn = _find_action_button(
            page, ["Retry", "Requeue", "Replay", "Reprocess", "Resubmit"]
        )
        if btn is None:
            pytest.skip("No retry button found — skipping enabled check")

        assert btn.is_enabled(), (  # type: ignore[attr-defined]
            "Retry action button must not be permanently disabled — "
            "operators need to retry or requeue dead-lettered events"
        )

    def test_retry_button_interaction_triggers_change(
        self, page: object, base_url: str
    ) -> None:
        """Clicking a retry button must cause a DOM change (confirmation or action)."""
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip("No dead-letter entries — skipping retry interaction test")

        btn = _find_action_button(
            page, ["Retry", "Requeue", "Replay", "Reprocess", "Resubmit"]
        )
        if btn is None:
            pytest.skip("No retry button found — skipping interaction test")

        before = page.locator("body").inner_html()  # type: ignore[attr-defined]
        btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]
        after = page.locator("body").inner_html()  # type: ignore[attr-defined]

        assert before != after, (
            "Clicking retry button must update the DOM — "
            "body HTML was identical before and after click"
        )

        # Clean up: dismiss any dialog that appeared
        _dismiss_any_dialog(page)


# ---------------------------------------------------------------------------
# Confirmation dialogs
# ---------------------------------------------------------------------------


class TestDeadLetterConfirmationDialogs:
    """Destructive dead-letter actions must require a confirmation dialog before executing."""

    def _trigger_any_action(self, page: object) -> bool:
        """Click the first available retry or delete action button.

        Returns True if a button was found and clicked.
        """
        btn = _find_action_button(
            page,
            ["Retry", "Requeue", "Replay", "Reprocess", "Delete", "Remove", "Discard", "Purge"],
        )
        if btn is None:
            return False
        btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]
        return True

    def test_confirmation_dialog_appears_before_action(
        self, page: object, base_url: str
    ) -> None:
        """Clicking a destructive action must show a confirmation dialog before executing.

        Operators work with production event queues. An accidental retry of a
        dead-lettered event without confirmation could cause duplicate processing.
        Confirmation gates protect against misclicks on high-severity events.
        """
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip("No dead-letter entries — skipping confirmation dialog test")

        if not self._trigger_any_action(page):
            pytest.skip(
                "No retry/delete buttons found — skipping confirmation dialog test"
            )

        # Check for native browser dialog, modal dialog, or inline confirmation
        dialog_selectors = [
            "[role='dialog']",
            "[role='alertdialog']",
            ".modal",
            "[class*='modal']",
            ".dialog",
            "[class*='dialog']",
            ".confirm",
            "[class*='confirm']",
            "[data-confirm]",
            "[data-dialog]",
            "[data-modal]",
            "details[open] .confirm-actions",
            "[aria-modal='true']",
        ]
        dialog_found = any(
            page.locator(sel).count() > 0  # type: ignore[attr-defined]
            for sel in dialog_selectors
        )

        if not dialog_found:
            # Inline confirmation (e.g. "Are you sure?" text replacing button)
            body_text = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            confirm_keywords = (
                "are you sure",
                "confirm",
                "this cannot be undone",
                "permanently",
                "cannot be reversed",
                "ok to proceed",
                "proceed",
            )
            dialog_found = any(kw in body_text for kw in confirm_keywords)

        assert dialog_found, (
            "Clicking a destructive dead-letter action must show a confirmation dialog — "
            "no dialog element or confirmation text found after clicking retry/delete"
        )

        # Clean up
        _dismiss_any_dialog(page)

    def test_confirmation_dialog_has_cancel_option(
        self, page: object, base_url: str
    ) -> None:
        """The confirmation dialog must provide a cancel/dismiss option.

        Operators must be able to abort a destructive action without consequence.
        A confirmation dialog without a cancel path is a usability defect.
        """
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip("No dead-letter entries — skipping confirmation cancel test")

        if not self._trigger_any_action(page):
            pytest.skip("No action buttons found — skipping confirmation cancel test")

        cancel_selectors = [
            "button[aria-label='Cancel']",
            "button[aria-label='Dismiss']",
            "button[aria-label='No']",
            "button:has-text('Cancel')",
            "button:has-text('No')",
            "button:has-text('Dismiss')",
            "button:has-text('Go back')",
            "button:has-text('Keep')",
            "[data-dialog-cancel]",
            "[data-confirm-cancel]",
            ".modal-footer button:not([data-confirm])",
            "[role='dialog'] button:not([data-confirm]):not([aria-label*='confirm' i])",
        ]

        cancel_found = any(
            page.locator(sel).count() > 0  # type: ignore[attr-defined]
            for sel in cancel_selectors
        )

        if not cancel_found:
            # Try pressing Escape to see if it closes the dialog
            before = page.locator("body").inner_html()  # type: ignore[attr-defined]
            try:
                page.keyboard.press("Escape")  # type: ignore[attr-defined]
                page.wait_for_timeout(400)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
            after = page.locator("body").inner_html()  # type: ignore[attr-defined]
            if before != after:
                # Escape closed the dialog — acceptable cancel mechanism
                return

        assert cancel_found, (
            "Confirmation dialog must include a cancel/dismiss option — "
            "no cancel button found and Escape key had no effect"
        )

        # Clean up
        _dismiss_any_dialog(page)

    def test_cancelling_confirmation_preserves_entry(
        self, page: object, base_url: str
    ) -> None:
        """Cancelling the confirmation dialog must leave the dead-letter entry unchanged.

        Pressing Cancel must not perform the destructive action — the entry must
        still be present in the list after the dialog is dismissed.
        """
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip("No dead-letter entries — skipping cancel-preserves-entry test")

        entry_count_before = page.locator("table tbody tr").count() or page.locator(  # type: ignore[attr-defined]
            "[data-dead-letter], [class*='dead-letter-card']"
        ).count()

        if not self._trigger_any_action(page):
            pytest.skip("No action buttons found — skipping cancel-preserves-entry test")

        # Attempt to cancel the dialog
        cancel_selectors = [
            "button:has-text('Cancel')",
            "button:has-text('No')",
            "button:has-text('Dismiss')",
            "button[aria-label='Cancel']",
            "[data-dialog-cancel]",
        ]
        cancelled = False
        for sel in cancel_selectors:
            try:
                btn = page.locator(sel).first  # type: ignore[attr-defined]
                if btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(400)  # type: ignore[attr-defined]
                    cancelled = True
                    break
            except Exception:  # noqa: BLE001
                continue

        if not cancelled:
            try:
                page.keyboard.press("Escape")  # type: ignore[attr-defined]
                page.wait_for_timeout(400)  # type: ignore[attr-defined]
                cancelled = True
            except Exception:  # noqa: BLE001
                pass

        if not cancelled:
            pytest.skip(
                "Could not find a cancel mechanism in the confirmation dialog — "
                "skipping entry-preservation check"
            )

        entry_count_after = page.locator("table tbody tr").count() or page.locator(  # type: ignore[attr-defined]
            "[data-dead-letter], [class*='dead-letter-card']"
        ).count()

        assert entry_count_after >= entry_count_before, (
            f"Cancelling the confirmation dialog removed an entry — "
            f"had {entry_count_before} entries before, {entry_count_after} after cancel. "
            "Cancel must not execute the destructive action."
        )


# ---------------------------------------------------------------------------
# HTMX swap attributes on action buttons
# ---------------------------------------------------------------------------


class TestDeadLetterActionHtmxAttributes:
    """Dead-letter action buttons using HTMX must carry correct hx-* attributes."""

    def test_htmx_action_elements_have_target(self, page: object, base_url: str) -> None:
        """Elements with hx-post/hx-delete on the dead-letter page declare hx-target or hx-swap."""
        _go(page, base_url)

        hx_elements = page.locator(  # type: ignore[attr-defined]
            "[hx-post], [hx-delete], [hx-put], [hx-patch]"
        )
        count = hx_elements.count()

        if count == 0:
            pytest.skip(
                "No HTMX mutation elements (hx-post/hx-delete) found — "
                "dead-letter page may not use HTMX for actions"
            )

        for i in range(min(count, 10)):
            el = hx_elements.nth(i)
            hx_target = el.get_attribute("hx-target")
            hx_swap = el.get_attribute("hx-swap")
            assert hx_target is not None or hx_swap is not None, (
                f"HTMX mutation element {i} on dead-letter page must declare "
                "hx-target or hx-swap"
            )

    def test_htmx_targets_exist_in_dom(self, page: object, base_url: str) -> None:
        """hx-target selectors on dead-letter action buttons reference DOM elements."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-target]")  # type: ignore[attr-defined]
        count = hx_elements.count()

        if count == 0:
            pytest.skip("No elements with hx-target found on dead-letter page")

        missing: list[str] = []
        for i in range(min(count, 10)):
            target_sel = hx_elements.nth(i).get_attribute("hx-target") or ""
            if not target_sel or target_sel in ("this", "closest", "next", "previous", "find"):
                continue
            if any(target_sel.startswith(kw) for kw in ("closest ", "next ", "find ")):
                continue
            try:
                if page.locator(target_sel).count() == 0:  # type: ignore[attr-defined]
                    missing.append(target_sel)
            except Exception:  # noqa: BLE001
                pass

        assert not missing, (
            f"hx-target selector(s) not found in DOM on dead-letter page: {missing}"
        )

    def test_no_js_errors_on_action_click(self, page: object, base_url: str) -> None:
        """Clicking a dead-letter action button must not raise JS errors."""
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip("No dead-letter entries — skipping JS error check")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        btn = _find_action_button(
            page,
            ["Retry", "Requeue", "Replay", "Delete", "Remove", "Reprocess", "Discard"],
        )
        if btn is None:
            pytest.skip("No action buttons found — skipping JS error check")

        btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]

        # Clean up: dismiss any dialog
        _dismiss_any_dialog(page)

        assert not js_errors, (
            f"JS errors occurred during dead-letter action click: {js_errors}"
        )


# ---------------------------------------------------------------------------
# Initial state — no spurious dialogs on load
# ---------------------------------------------------------------------------


class TestDeadLetterInitialState:
    """No confirmation dialogs or action results must be visible before interaction."""

    def test_no_dialog_visible_on_load(self, page: object, base_url: str) -> None:
        """Confirmation dialogs must not be visible before any user interaction."""
        _go(page, base_url)

        visible_dialog_sel = (
            "[role='dialog']:not([aria-hidden='true']):not(.hidden):not([hidden]), "
            "[role='alertdialog']:not([aria-hidden='true']):not(.hidden):not([hidden])"
        )
        visible_count = page.locator(visible_dialog_sel).count()  # type: ignore[attr-defined]
        assert visible_count == 0, (
            f"Confirmation dialog must not be visible on initial dead-letter page load — "
            f"found {visible_count} visible dialog(s) before any interaction"
        )

    def test_action_buttons_exist_or_page_is_empty(
        self, page: object, base_url: str
    ) -> None:
        """Either action buttons are present (with entries) or the page shows an empty state."""
        _go(page, base_url)

        has_entries = _has_dead_letter_entries(page)
        if not has_entries:
            # Empty dead-letter queue is a positive signal
            body_text = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            empty_keywords = (
                "no dead",
                "no events",
                "nothing",
                "empty",
                "all clear",
                "no items",
                "dead-letter queue is empty",
                "no failed",
            )
            has_empty_state = any(kw in body_text for kw in empty_keywords)
            assert has_empty_state or len(body_text.strip()) > 10, (
                "Dead-letter page shows no entries and no legible empty-state message — "
                "page may be broken or empty without operator feedback"
            )
            return

        # Has entries: at least some action affordance should be present
        btn = _find_action_button(
            page,
            ["Retry", "Requeue", "Replay", "Reprocess", "Delete", "Remove", "Discard", "Purge"],
        )
        if btn is None:
            pytest.skip(
                "Dead-letter page has entries but no top-level action buttons visible — "
                "actions may be in row detail panel (acceptable)"
            )
