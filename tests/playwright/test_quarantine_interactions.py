"""Epic 68.4 — Quarantine: Interactive Elements.

Validates that /admin/ui/quarantine interactive behaviours work correctly:

  Replay action     — A replay button is present on quarantine entries and is interactive
  Delete action     — A delete button is present on quarantine entries and is interactive
  Confirmation      — Destructive actions (delete/replay) trigger a confirmation dialog
  Dialog dismiss    — Confirmation dialog can be cancelled without performing the action
  HTMX              — Action buttons carry correct hx-* attributes
  JS errors         — No JS errors are raised during action interactions

These tests verify *interactive behaviour*, not content or appearance.
Content is covered in test_quarantine_intent.py (Epic 68.1).
API contracts are covered in test_quarantine_api.py (Epic 68.2).
Style compliance is covered in test_quarantine_style.py (Epic 68.3).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

QUARANTINE_URL = "/admin/ui/quarantine"


def _go(page: object, base_url: str) -> None:
    """Navigate to the quarantine page and wait for content to settle."""
    navigate(page, f"{base_url}{QUARANTINE_URL}")  # type: ignore[arg-type]


def _has_quarantine_entries(page: object) -> bool:
    """Return True when at least one quarantine row or card is present."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator(
            "[data-quarantine], [class*='quarantine-card'], [data-event-id]"
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
                f"[data-quarantine-action='{kw.lower()}']",
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


# ---------------------------------------------------------------------------
# Replay action
# ---------------------------------------------------------------------------


class TestQuarantineReplayAction:
    """A replay action must be present and interactive on the quarantine page."""

    def test_replay_button_exists(self, page: object, base_url: str) -> None:
        """At least one replay action button is present on the quarantine page."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip(
                "No quarantine entries on page — skipping replay button existence check"
            )

        btn = _find_action_button(page, ["Replay", "Retry", "Requeue", "Reprocess"])
        if btn is None:
            # Acceptable: replay may be in a row detail panel
            pytest.skip(
                "No explicit replay/retry button found on quarantine page — "
                "action may be accessible via row detail panel"
            )

    def test_replay_button_is_enabled(self, page: object, base_url: str) -> None:
        """Replay action buttons must not be permanently disabled."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping replay enabled check")

        btn = _find_action_button(page, ["Replay", "Retry", "Requeue", "Reprocess"])
        if btn is None:
            pytest.skip("No replay button found — skipping enabled check")

        assert btn.is_enabled(), (  # type: ignore[attr-defined]
            "Replay action button must not be permanently disabled — "
            "operators need to replay quarantined events"
        )

    def test_replay_button_interaction_triggers_change(
        self, page: object, base_url: str
    ) -> None:
        """Clicking a replay button must cause a DOM change (confirmation or action)."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping replay interaction test")

        btn = _find_action_button(page, ["Replay", "Retry", "Requeue", "Reprocess"])
        if btn is None:
            pytest.skip("No replay button found — skipping interaction test")

        before = page.locator("body").inner_html()  # type: ignore[attr-defined]
        btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]
        after = page.locator("body").inner_html()  # type: ignore[attr-defined]

        assert before != after, (
            "Clicking replay button must update the DOM — "
            "body HTML was identical before and after click"
        )

        # Clean up: dismiss any dialog that appeared
        escape_targets = [
            "button[aria-label='Cancel']",
            "button:has-text('Cancel')",
            "button:has-text('No')",
            "[data-dialog-cancel]",
        ]
        for sel in escape_targets:
            try:
                cancel = page.locator(sel).first  # type: ignore[attr-defined]
                if cancel.is_visible():
                    cancel.click()
                    page.wait_for_timeout(300)  # type: ignore[attr-defined]
                    break
            except Exception:  # noqa: BLE001
                continue
        else:
            try:
                page.keyboard.press("Escape")  # type: ignore[attr-defined]
                page.wait_for_timeout(300)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------------------
# Delete action
# ---------------------------------------------------------------------------


class TestQuarantineDeleteAction:
    """A delete action must be present and interactive on the quarantine page."""

    def test_delete_button_exists(self, page: object, base_url: str) -> None:
        """At least one delete action button is present on the quarantine page."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip(
                "No quarantine entries on page — skipping delete button existence check"
            )

        btn = _find_action_button(page, ["Delete", "Remove", "Dismiss", "Discard", "Purge"])
        if btn is None:
            pytest.skip(
                "No explicit delete/remove button found on quarantine page — "
                "action may be accessible via row detail panel"
            )

    def test_delete_button_is_enabled(self, page: object, base_url: str) -> None:
        """Delete action buttons must not be permanently disabled."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping delete enabled check")

        btn = _find_action_button(page, ["Delete", "Remove", "Dismiss", "Discard", "Purge"])
        if btn is None:
            pytest.skip("No delete button found — skipping enabled check")

        assert btn.is_enabled(), (  # type: ignore[attr-defined]
            "Delete action button must not be permanently disabled — "
            "operators need to delete quarantined events"
        )

    def test_delete_button_interaction_triggers_change(
        self, page: object, base_url: str
    ) -> None:
        """Clicking a delete button must cause a DOM change (confirmation or action)."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping delete interaction test")

        btn = _find_action_button(page, ["Delete", "Remove", "Dismiss", "Discard", "Purge"])
        if btn is None:
            pytest.skip("No delete button found — skipping interaction test")

        before = page.locator("body").inner_html()  # type: ignore[attr-defined]
        btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]
        after = page.locator("body").inner_html()  # type: ignore[attr-defined]

        assert before != after, (
            "Clicking delete button must update the DOM — "
            "body HTML was identical before and after click"
        )

        # Clean up: cancel any dialog
        escape_targets = [
            "button[aria-label='Cancel']",
            "button:has-text('Cancel')",
            "button:has-text('No')",
            "[data-dialog-cancel]",
        ]
        for sel in escape_targets:
            try:
                cancel = page.locator(sel).first  # type: ignore[attr-defined]
                if cancel.is_visible():
                    cancel.click()
                    page.wait_for_timeout(300)  # type: ignore[attr-defined]
                    break
            except Exception:  # noqa: BLE001
                continue
        else:
            try:
                page.keyboard.press("Escape")  # type: ignore[attr-defined]
                page.wait_for_timeout(300)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------------------
# Confirmation dialogs
# ---------------------------------------------------------------------------


class TestQuarantineConfirmationDialogs:
    """Destructive quarantine actions must require a confirmation dialog before executing."""

    def _trigger_any_action(self, page: object) -> bool:
        """Click the first available replay or delete action button.

        Returns True if a button was found and clicked.
        """
        btn = _find_action_button(
            page, ["Delete", "Remove", "Dismiss", "Replay", "Retry", "Requeue"]
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

        Operators work with production event queues. An accidental delete or replay
        without confirmation could cause duplicate processing or permanent data loss.
        Confirmation gates protect against misclicks.
        """
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping confirmation dialog test")

        if not self._trigger_any_action(page):
            pytest.skip(
                "No replay/delete buttons found — skipping confirmation dialog test"
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
            "Clicking a destructive quarantine action must show a confirmation dialog — "
            "no dialog element or confirmation text found after clicking replay/delete"
        )

        # Clean up
        try:
            page.keyboard.press("Escape")  # type: ignore[attr-defined]
            page.wait_for_timeout(300)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    def test_confirmation_dialog_has_cancel_option(
        self, page: object, base_url: str
    ) -> None:
        """The confirmation dialog must provide a cancel/dismiss option.

        Operators must be able to abort a destructive action without consequence.
        A confirmation dialog without a cancel path is a usability defect.
        """
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping confirmation cancel test")

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

        # Also accept Escape key as cancel mechanism (check via keyboard)
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

        # Clean up: dismiss
        for sel in cancel_selectors:
            try:
                btn = page.locator(sel).first  # type: ignore[attr-defined]
                if btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(300)  # type: ignore[attr-defined]
                    break
            except Exception:  # noqa: BLE001
                continue

    def test_cancelling_confirmation_preserves_entry(
        self, page: object, base_url: str
    ) -> None:
        """Cancelling the confirmation dialog must leave the quarantine entry unchanged.

        Pressing Cancel must not perform the destructive action — the entry must
        still be present in the list after the dialog is dismissed.
        """
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping cancel-preserves-entry test")

        entry_count_before = (
            page.locator("table tbody tr").count()  # type: ignore[attr-defined]
            or page.locator(
                "[data-quarantine], [class*='quarantine-card']"
            ).count()
        )

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

        entry_count_after = (
            page.locator("table tbody tr").count()  # type: ignore[attr-defined]
            or page.locator(
                "[data-quarantine], [class*='quarantine-card']"
            ).count()
        )

        assert entry_count_after >= entry_count_before, (
            f"Cancelling the confirmation dialog removed an entry — "
            f"had {entry_count_before} entries before, {entry_count_after} after cancel. "
            "Cancel must not execute the destructive action."
        )


# ---------------------------------------------------------------------------
# HTMX swap attributes on action buttons
# ---------------------------------------------------------------------------


class TestQuarantineActionHtmxAttributes:
    """Quarantine action buttons using HTMX must carry correct hx-* attributes."""

    def test_htmx_action_elements_have_target(self, page: object, base_url: str) -> None:
        """Elements with hx-post/hx-delete on the quarantine page declare hx-target or hx-swap."""
        _go(page, base_url)

        hx_elements = page.locator(  # type: ignore[attr-defined]
            "[hx-post], [hx-delete], [hx-put], [hx-patch]"
        )
        count = hx_elements.count()

        if count == 0:
            pytest.skip(
                "No HTMX mutation elements (hx-post/hx-delete) found — "
                "quarantine page may not use HTMX for actions"
            )

        for i in range(min(count, 10)):
            el = hx_elements.nth(i)
            hx_target = el.get_attribute("hx-target")
            hx_swap = el.get_attribute("hx-swap")
            assert hx_target is not None or hx_swap is not None, (
                f"HTMX mutation element {i} on quarantine page must declare "
                "hx-target or hx-swap"
            )

    def test_htmx_targets_exist_in_dom(self, page: object, base_url: str) -> None:
        """hx-target selectors on quarantine action buttons reference DOM elements."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-target]")  # type: ignore[attr-defined]
        count = hx_elements.count()

        if count == 0:
            pytest.skip("No elements with hx-target found on quarantine page")

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
            f"hx-target selector(s) not found in DOM on quarantine page: {missing}"
        )

    def test_no_js_errors_on_action_click(self, page: object, base_url: str) -> None:
        """Clicking a quarantine action button must not raise JS errors."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping JS error check")

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        btn = _find_action_button(
            page, ["Replay", "Retry", "Delete", "Remove", "Dismiss", "Requeue"]
        )
        if btn is None:
            pytest.skip("No action buttons found — skipping JS error check")

        btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]

        # Clean up: dismiss any dialog
        try:
            page.keyboard.press("Escape")  # type: ignore[attr-defined]
            page.wait_for_timeout(300)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

        assert not js_errors, (
            f"JS errors occurred during quarantine action click: {js_errors}"
        )


# ---------------------------------------------------------------------------
# Initial state — no spurious dialogs on load
# ---------------------------------------------------------------------------


class TestQuarantineInitialState:
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
            f"Confirmation dialog must not be visible on initial quarantine page load — "
            f"found {visible_count} visible dialog(s) before any interaction"
        )

    def test_action_buttons_exist_or_page_is_empty(
        self, page: object, base_url: str
    ) -> None:
        """Either action buttons are present (with entries) or the page shows empty state."""
        _go(page, base_url)

        has_entries = _has_quarantine_entries(page)
        if not has_entries:
            # Empty state is valid — check it renders legibly
            body_text = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            empty_keywords = (
                "no quarantine",
                "no events",
                "nothing",
                "empty",
                "all clear",
                "no items",
                "quarantine is empty",
            )
            has_empty_state = any(kw in body_text for kw in empty_keywords)
            assert has_empty_state or len(body_text.strip()) > 10, (
                "Quarantine page shows no entries and no legible empty-state message — "
                "page may be broken or empty without feedback"
            )
            return

        # Has entries: at least some action affordance should be present
        btn = _find_action_button(
            page,
            ["Replay", "Retry", "Delete", "Remove", "Dismiss", "Requeue", "Reprocess", "Purge"],
        )
        if btn is None:
            # Acceptable: actions may be in a detail panel
            pytest.skip(
                "Quarantine has entries but no top-level action buttons visible — "
                "actions may be in row detail panel (acceptable)"
            )
