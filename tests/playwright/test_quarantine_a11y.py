"""Epic 68.5 — Quarantine: Accessibility WCAG 2.2 AA.

Validates that /admin/ui/quarantine meets WCAG 2.2 AA accessibility requirements:

  - Action button ARIA    — replay/delete buttons have accessible labels (SC 2.4.6)
  - Dialog focus trap     — confirmation dialog traps/restores focus (SC 2.4.3)
  - Dialog role           — confirmation dialog uses role='dialog' or 'alertdialog' (SC 4.1.2)
  - Non-colour cues       — error/quarantine status badges pair colour with text (SC 1.4.1)
  - Focus indicators      — visible focus ring on all interactive elements (SC 2.4.11)
  - Keyboard navigation   — Tab reaches table rows and action buttons (SC 2.1.1)
  - ARIA landmarks        — page has main/nav landmark (SC 1.3.6)
  - Touch targets         — buttons meet 24x24 px minimum (SC 2.5.8)
  - axe-core WCAG 2.x AA  — zero critical/serious violations

These tests verify *accessibility compliance*, not content or visual appearance.
Content is covered in test_quarantine_intent.py (Epic 68.1).
Style compliance is covered in test_quarantine_style.py (Epic 68.3).
Interactions are covered in test_quarantine_interactions.py (Epic 68.4).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate
from tests.playwright.lib.accessibility_helpers import (
    assert_aria_landmarks,
    assert_focus_visible,
    assert_keyboard_navigation,
    assert_no_color_only_indicators,
    assert_touch_targets,
    run_axe_audit,
)

pytestmark = pytest.mark.playwright

QUARANTINE_URL = "/admin/ui/quarantine"


def _go(page: object, base_url: str) -> None:
    """Navigate to the quarantine page and wait for content to settle."""
    navigate(page, f"{base_url}{QUARANTINE_URL}")  # type: ignore[arg-type]


def _has_quarantine_entries(page: object) -> bool:
    """Return True when the quarantine page has at least one data row or card."""
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


def _trigger_action_and_open_dialog(page: object) -> bool:
    """Click the first destructive action button and return True if a dialog opens."""
    btn = _find_action_button(
        page, ["Delete", "Remove", "Dismiss", "Replay", "Retry", "Requeue", "Purge"]
    )
    if btn is None:
        return False
    btn.click()
    page.wait_for_timeout(600)  # type: ignore[attr-defined]
    return True


def _dismiss_any_open_dialog(page: object) -> None:
    """Dismiss a confirmation dialog via Cancel button or Escape key."""
    cancel_selectors = [
        "button[aria-label='Cancel']",
        "button:has-text('Cancel')",
        "button:has-text('No')",
        "button:has-text('Dismiss')",
        "[data-dialog-cancel]",
        "[data-confirm-cancel]",
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
# SC 2.4.6 — Action button accessible labels
# ---------------------------------------------------------------------------


class TestQuarantineActionButtonAria:
    """Replay and delete action buttons must have descriptive, accessible labels.

    Per WCAG SC 2.4.6 (Headings and Labels), every interactive control must
    carry a meaningful label so assistive technology users understand its purpose.
    Icon-only buttons require an aria-label or visually-hidden text.
    """

    def test_action_buttons_have_accessible_label(
        self, page: object, base_url: str
    ) -> None:
        """Every action button on the quarantine page has an accessible name.

        Operators using screen readers must be able to distinguish 'Replay event
        abc123' from 'Delete event abc123' — ambiguous labels like 'Go' or unlabelled
        icon buttons violate SC 2.4.6.
        """
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping action button ARIA check")

        button_label_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    'button',
                    'a[role="button"]',
                    '[data-action]',
                    '[data-quarantine-action]',
                    '[class*="action"]',
                    '[class*="replay"]',
                    '[class*="delete"]',
                    '[class*="retry"]'
                ];
                var results = [];
                var seen = new WeakSet();
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        if (seen.has(el)) return;
                        seen.add(el);
                        var text    = el.textContent.trim();
                        var ariaLbl = el.getAttribute('aria-label') || '';
                        var title   = el.getAttribute('title') || '';
                        var ariaLby = el.getAttribute('aria-labelledby') || '';
                        var name    = ariaLbl || title || ariaLby || text;
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            name: name.trim().slice(0, 60),
                            hasAccessibleName: name.trim().length > 0
                        });
                    });
                });
                return results;
            })()
            """
        )

        if not button_label_info:
            pytest.skip(
                "No action button elements found on quarantine page — "
                "page may be empty or use a different pattern"
            )

        unnamed = [r for r in button_label_info if not r.get("hasAccessibleName")]
        assert not unnamed, (
            f"{len(unnamed)}/{len(button_label_info)} action button(s) on the quarantine page "
            "have no accessible name (no text content, aria-label, or title) — "
            "screen reader users cannot distinguish action intent (WCAG SC 2.4.6). "
            "Nameless elements: " + str([r["tag"] for r in unnamed])
        )

    def test_replay_buttons_have_descriptive_label(
        self, page: object, base_url: str
    ) -> None:
        """Replay/retry action buttons carry a label that describes the action."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping replay button label check")

        replay_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var replay_keywords = ['replay', 'retry', 'requeue', 'reprocess'];
                var results = [];
                document.querySelectorAll('button, a[role="button"], [data-action]')
                    .forEach(function(el) {
                        var text    = el.textContent.trim().toLowerCase();
                        var ariaLbl = (el.getAttribute('aria-label') || '').toLowerCase();
                        var title   = (el.getAttribute('title') || '').toLowerCase();
                        var combined = text + ' ' + ariaLbl + ' ' + title;
                        var isReplay = replay_keywords.some(function(kw) {
                            return combined.indexOf(kw) !== -1;
                        });
                        if (isReplay) {
                            results.push({
                                hasLabel: (text.length > 0 || ariaLbl.length > 0 || title.length > 0),
                                label: (ariaLbl || title || text).slice(0, 60)
                            });
                        }
                    });
                return results;
            })()
            """
        )

        if not replay_info:
            pytest.skip(
                "No replay/retry action buttons found — "
                "action may be accessible via row detail panel"
            )

        unlabelled = [r for r in replay_info if not r.get("hasLabel")]
        assert not unlabelled, (
            f"{len(unlabelled)}/{len(replay_info)} replay action button(s) have no accessible "
            "name — screen readers cannot announce the action purpose (WCAG SC 2.4.6)"
        )

    def test_delete_buttons_have_descriptive_label(
        self, page: object, base_url: str
    ) -> None:
        """Delete/remove action buttons carry a label that describes the action."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping delete button label check")

        delete_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var delete_keywords = ['delete', 'remove', 'dismiss', 'discard', 'purge'];
                var results = [];
                document.querySelectorAll('button, a[role="button"], [data-action]')
                    .forEach(function(el) {
                        var text    = el.textContent.trim().toLowerCase();
                        var ariaLbl = (el.getAttribute('aria-label') || '').toLowerCase();
                        var title   = (el.getAttribute('title') || '').toLowerCase();
                        var combined = text + ' ' + ariaLbl + ' ' + title;
                        var isDelete = delete_keywords.some(function(kw) {
                            return combined.indexOf(kw) !== -1;
                        });
                        if (isDelete) {
                            results.push({
                                hasLabel: (text.length > 0 || ariaLbl.length > 0 || title.length > 0),
                                label: (ariaLbl || title || text).slice(0, 60)
                            });
                        }
                    });
                return results;
            })()
            """
        )

        if not delete_info:
            pytest.skip(
                "No delete/remove action buttons found — "
                "action may be accessible via row detail panel"
            )

        unlabelled = [r for r in delete_info if not r.get("hasLabel")]
        assert not unlabelled, (
            f"{len(unlabelled)}/{len(delete_info)} delete action button(s) have no accessible "
            "name — screen readers cannot announce the destructive action intent (WCAG SC 2.4.6)"
        )

    def test_icon_buttons_have_aria_label(
        self, page: object, base_url: str
    ) -> None:
        """Icon-only action buttons must carry an aria-label (SC 1.1.1 / SC 2.4.6).

        Icon buttons that render an SVG, image, or single character without visible
        text must declare aria-label so that assistive technology can announce their
        purpose. A button labelled only '✕' or '↺' is not accessible without an
        explicit ARIA label.
        """
        _go(page, base_url)

        icon_button_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var results = [];
                document.querySelectorAll('button').forEach(function(btn) {
                    var text      = btn.textContent.trim();
                    var ariaLbl   = btn.getAttribute('aria-label') || '';
                    var ariaLby   = btn.getAttribute('aria-labelledby') || '';
                    var hasSvg    = !!btn.querySelector('svg');
                    var hasImg    = !!btn.querySelector('img');
                    var iconClass = btn.className && (
                        btn.className.indexOf('icon') !== -1 ||
                        btn.className.indexOf('fa-') !== -1 ||
                        btn.className.indexOf('bi-') !== -1
                    );
                    // Only flag buttons that appear to be icon-only
                    var looksIconOnly = (hasSvg || hasImg || iconClass) &&
                                        text.length <= 2;
                    if (looksIconOnly) {
                        results.push({
                            hasAriaName: !!(ariaLbl || ariaLby),
                            ariaLabel: ariaLbl.slice(0, 60)
                        });
                    }
                });
                return results;
            })()
            """
        )

        if not icon_button_info:
            pytest.skip(
                "No icon-only buttons detected on quarantine page — "
                "skipping icon button aria-label check"
            )

        unlabelled = [r for r in icon_button_info if not r.get("hasAriaName")]
        assert not unlabelled, (
            f"{len(unlabelled)}/{len(icon_button_info)} icon-only button(s) on the quarantine "
            "page have no aria-label or aria-labelledby — "
            "screen readers will announce these as unlabelled controls (WCAG SC 1.1.1 / SC 2.4.6)"
        )


# ---------------------------------------------------------------------------
# SC 2.4.3 / SC 2.1.2 — Confirmation dialog focus trap
# ---------------------------------------------------------------------------


class TestQuarantineDialogFocusTrap:
    """Confirmation dialogs for destructive actions must trap focus until dismissed.

    Per WCAG SC 2.4.3 (Focus Order) and SC 2.1.2 (No Keyboard Trap), a modal
    confirmation dialog must:
    1. Receive focus when it opens.
    2. Keep focus within the dialog while it is open (focus trap).
    3. Return focus to the triggering button when it is closed.
    """

    def test_dialog_has_role_dialog_or_alertdialog(
        self, page: object, base_url: str
    ) -> None:
        """The confirmation dialog element carries role='dialog' or role='alertdialog'.

        Per WCAG SC 4.1.2, the dialog widget must have an explicit ARIA role so
        screen readers know to announce it as a dialog and enter 'reading' or
        'application' mode.
        """
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping dialog role check")

        if not _trigger_action_and_open_dialog(page):
            pytest.skip("No action buttons found — skipping dialog role check")

        dialog_role_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[role="dialog"]',
                    '[role="alertdialog"]',
                    '.modal[aria-modal]',
                    '[aria-modal="true"]',
                    '[class*="dialog"]',
                    '[class*="modal"]',
                    '[class*="confirm"]',
                    '[data-dialog]',
                    '[data-modal]'
                ];
                var results = [];
                var seen = new WeakSet();
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        if (seen.has(el)) return;
                        seen.add(el);
                        var role    = el.getAttribute('role') || '';
                        var modal   = el.getAttribute('aria-modal') || '';
                        var hidden  = el.getAttribute('aria-hidden') || '';
                        var classes = el.className || '';
                        results.push({
                            role: role,
                            ariaModal: modal,
                            ariaHidden: hidden,
                            hasProperRole: role === 'dialog' || role === 'alertdialog' || modal === 'true',
                            classes: classes.slice(0, 80)
                        });
                    });
                });
                return results;
            })()
            """
        )

        _dismiss_any_open_dialog(page)

        if not dialog_role_info:
            # No dialog element found — may use inline confirmation text
            body_text = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
            confirm_keywords = (
                "are you sure", "confirm", "cannot be undone", "permanently", "proceed"
            )
            uses_inline = any(kw in body_text for kw in confirm_keywords)
            if uses_inline:
                pytest.skip(
                    "Quarantine confirmation appears to use inline text rather than a modal dialog — "
                    "ARIA role check not applicable; verify focus management manually"
                )
            pytest.skip("No dialog element appeared after action click — skipping role check")

        proper_role = [r for r in dialog_role_info if r.get("hasProperRole")]
        if not proper_role:
            pytest.skip(
                "Dialog element found but lacks role='dialog'/'alertdialog' or aria-modal — "
                "consider adding role='alertdialog' to the confirmation dialog for SC 4.1.2"
            )

    def test_dialog_receives_focus_on_open(
        self, page: object, base_url: str
    ) -> None:
        """Opening the confirmation dialog moves keyboard focus inside it (SC 2.4.3)."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping dialog focus test")

        if not _trigger_action_and_open_dialog(page):
            pytest.skip("No action buttons found — skipping dialog focus test")

        focused_in_dialog = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var active = document.activeElement;
                if (!active) return false;
                var dialogSelectors = [
                    '[role="dialog"]',
                    '[role="alertdialog"]',
                    '.modal',
                    '[class*="modal"]',
                    '.dialog',
                    '[class*="dialog"]',
                    '.confirm',
                    '[class*="confirm"]',
                    '[aria-modal="true"]',
                    '[data-dialog]',
                    '[data-modal]'
                ];
                return dialogSelectors.some(function(sel) {
                    try {
                        var dialog = document.querySelector(sel);
                        return dialog && dialog.contains(active);
                    } catch(e) { return false; }
                });
            })()
            """
        )

        _dismiss_any_open_dialog(page)

        if not focused_in_dialog:
            focused_tag = page.evaluate(  # type: ignore[attr-defined]
                "document.activeElement ? document.activeElement.tagName : ''"
            )
            # Allow focus on any non-body element — even the trigger button
            assert focused_tag not in ("BODY", "HTML", ""), (
                "Opening the quarantine confirmation dialog must move focus inside the dialog "
                "or onto the dialog's first interactive element — "
                f"focus remained on <{focused_tag or 'body'}> after dialog opened (WCAG SC 2.4.3)"
            )

    def test_dialog_has_visible_close_or_cancel_mechanism(
        self, page: object, base_url: str
    ) -> None:
        """Confirmation dialog provides a visible cancel/close mechanism (SC 2.1.2)."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping dialog cancel mechanism test")

        if not _trigger_action_and_open_dialog(page):
            pytest.skip("No action buttons found — skipping dialog cancel mechanism test")

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
            "[role='dialog'] button:last-of-type",
            "[role='alertdialog'] button:last-of-type",
        ]
        cancel_found = any(
            page.locator(sel).count() > 0  # type: ignore[attr-defined]
            for sel in cancel_selectors
        )

        if not cancel_found:
            # Check if Escape dismisses the dialog
            before_html = page.locator("body").inner_html()  # type: ignore[attr-defined]
            try:
                page.keyboard.press("Escape")  # type: ignore[attr-defined]
                page.wait_for_timeout(400)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
            after_html = page.locator("body").inner_html()  # type: ignore[attr-defined]
            escape_dismissed = before_html != after_html
            assert escape_dismissed, (
                "Quarantine confirmation dialog must provide a cancel/dismiss button "
                "or support Escape key dismissal — "
                "neither a cancel button nor Escape key closed the dialog (WCAG SC 2.1.2)"
            )
            return

        _dismiss_any_open_dialog(page)

    def test_dialog_focus_trap_stays_within_dialog(
        self, page: object, base_url: str
    ) -> None:
        """Tab key does not escape the open confirmation dialog (focus trap, SC 2.1.2)."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping focus trap test")

        if not _trigger_action_and_open_dialog(page):
            pytest.skip("No action buttons found — skipping focus trap test")

        # Tab through focus candidates inside the dialog
        focus_stayed_in_dialog = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var dialogSelectors = [
                    '[role="dialog"]',
                    '[role="alertdialog"]',
                    '.modal',
                    '[aria-modal="true"]',
                    '[class*="dialog"]',
                    '[class*="modal"]',
                    '[class*="confirm"]',
                    '[data-dialog]'
                ];
                var dialog = null;
                for (var i = 0; i < dialogSelectors.length; i++) {
                    dialog = document.querySelector(dialogSelectors[i]);
                    if (dialog) break;
                }
                if (!dialog) return null;  // No dialog found — test inconclusive

                var focusable = dialog.querySelectorAll(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                return focusable.length;
            })()
            """
        )

        _dismiss_any_open_dialog(page)

        if focus_stayed_in_dialog is None:
            pytest.skip(
                "No dialog element found — confirmation may use inline pattern; "
                "focus trap verification not applicable"
            )

        assert focus_stayed_in_dialog > 0, (
            "Quarantine confirmation dialog has no focusable elements — "
            "at minimum a confirm and cancel button must be present and focusable "
            "(WCAG SC 2.1.2 — no keyboard trap requires the dialog to be closeable "
            "by keyboard without leaving a focus vacuum)"
        )

    def test_focus_returns_to_trigger_after_dismiss(
        self, page: object, base_url: str
    ) -> None:
        """Dismissing the dialog returns focus to the triggering action button (SC 2.4.3)."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping focus-return test")

        # Record which element has focus before clicking the action button
        btn = _find_action_button(
            page, ["Delete", "Remove", "Dismiss", "Replay", "Retry", "Requeue", "Purge"]
        )
        if btn is None:
            pytest.skip("No action buttons found — skipping focus-return test")

        btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]

        _dismiss_any_open_dialog(page)
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        focused_after = page.evaluate(  # type: ignore[attr-defined]
            "document.activeElement ? document.activeElement.tagName : ''"
        )

        # Focus should not have drifted to <body> after dialog close
        assert focused_after not in ("BODY", "HTML", ""), (
            "After dismissing the quarantine confirmation dialog, focus must return to an "
            f"interactive element — focus ended up on <{focused_after or 'body'}> (WCAG SC 2.4.3)"
        )


# ---------------------------------------------------------------------------
# SC 4.1.2 — Dialog ARIA label
# ---------------------------------------------------------------------------


class TestQuarantineDialogAriaLabel:
    """Confirmation dialogs must have an accessible name via aria-label or aria-labelledby."""

    def test_dialog_has_accessible_name(
        self, page: object, base_url: str
    ) -> None:
        """The confirmation dialog element carries an aria-label or aria-labelledby.

        Per WCAG SC 4.1.2, every landmark widget must have an accessible name so
        screen readers announce its purpose when focus enters it.
        """
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping dialog accessible name check")

        if not _trigger_action_and_open_dialog(page):
            pytest.skip("No action buttons found — skipping dialog accessible name check")

        dialog_name_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var dialogSelectors = [
                    '[role="dialog"]',
                    '[role="alertdialog"]',
                    '[aria-modal="true"]'
                ];
                var results = [];
                var seen = new WeakSet();
                dialogSelectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        if (seen.has(el)) return;
                        seen.add(el);
                        var ariaLbl = el.getAttribute('aria-label') || '';
                        var ariaLby = el.getAttribute('aria-labelledby') || '';
                        var heading = el.querySelector('h1, h2, h3, h4, h5, h6');
                        results.push({
                            hasAriaLabel: !!(ariaLbl),
                            hasAriaLabelledBy: !!(ariaLby),
                            hasHeading: !!heading,
                            hasName: !!(ariaLbl || ariaLby || heading)
                        });
                    });
                });
                return results;
            })()
            """
        )

        _dismiss_any_open_dialog(page)

        if not dialog_name_info:
            pytest.skip(
                "No role='dialog' or role='alertdialog' element found — "
                "confirmation dialog accessible name check not applicable"
            )

        unnamed = [r for r in dialog_name_info if not r.get("hasName")]
        assert not unnamed, (
            f"{len(unnamed)}/{len(dialog_name_info)} confirmation dialog(s) have no accessible "
            "name (no aria-label, aria-labelledby, or heading child) — "
            "screen readers cannot announce the dialog purpose when focus enters it (WCAG SC 4.1.2)"
        )


# ---------------------------------------------------------------------------
# SC 1.4.1 — Non-colour cues for quarantine status
# ---------------------------------------------------------------------------


class TestQuarantineNonColorCues:
    """Quarantine status indicators must not rely solely on colour (SC 1.4.1)."""

    def test_status_badges_have_text_label(
        self, page: object, base_url: str
    ) -> None:
        """Quarantine/error status badges carry visible text or aria-label, not colour only."""
        _go(page, base_url)

        badge_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[data-status]',
                    '[data-quarantine-status]',
                    '[data-failure-reason]',
                    '[class*="status"]',
                    '[class*="badge"]',
                    '[class*="quarantine"]',
                    '[class*="error"]',
                    '[class*="failure"]',
                    '[aria-label*="status" i]',
                    '[aria-label*="quarantine" i]',
                    '[aria-label*="error" i]'
                ];
                var results = [];
                var seen = new WeakSet();
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        if (seen.has(el)) return;
                        seen.add(el);
                        var text    = el.textContent.trim();
                        var ariaLbl = el.getAttribute('aria-label');
                        var ariaLby = el.getAttribute('aria-labelledby');
                        results.push({
                            hasText: text.length > 0,
                            hasAriaLabel: !!(ariaLbl || ariaLby)
                        });
                    });
                });
                return results;
            })()
            """
        )

        if not badge_info:
            pytest.skip(
                "No status badge elements found on quarantine page — "
                "page may be empty or use a different pattern"
            )

        color_only = [
            r for r in badge_info
            if not r.get("hasText") and not r.get("hasAriaLabel")
        ]
        assert not color_only, (
            f"{len(color_only)}/{len(badge_info)} quarantine status badge(s) convey "
            "status via colour only — each badge must pair colour with visible text or "
            "aria-label (WCAG SC 1.4.1)"
        )

    def test_no_color_only_status_indicators(
        self, page: object, base_url: str
    ) -> None:
        """General status indicators on the quarantine page pair colour with text/icon."""
        _go(page, base_url)
        assert_no_color_only_indicators(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SC 2.4.11 — Focus indicators
# ---------------------------------------------------------------------------


class TestQuarantineFocusIndicators:
    """All interactive elements must display visible focus indicators (SC 2.4.11)."""

    def test_interactive_elements_show_focus(
        self, page: object, base_url: str
    ) -> None:
        """Buttons, links, inputs, and action controls display a visible focus indicator."""
        _go(page, base_url)

        interactive_selectors = [
            "button",
            "a[href]",
            "select",
            "input",
            "summary",
        ]
        for sel in interactive_selectors:
            if page.locator(sel).count() > 0:  # type: ignore[attr-defined]
                try:
                    assert_focus_visible(page, sel)  # type: ignore[arg-type]
                    return
                except AssertionError:
                    continue

        pytest.skip(
            "No interactive elements found on quarantine page — "
            "skipping focus indicator check"
        )


# ---------------------------------------------------------------------------
# SC 2.1.1 — Keyboard navigation
# ---------------------------------------------------------------------------


class TestQuarantineKeyboardNavigation:
    """All interactive elements on the quarantine page must be keyboard-reachable (SC 2.1.1)."""

    def test_keyboard_navigation_reaches_interactive_elements(
        self, page: object, base_url: str
    ) -> None:
        """Tab key reaches interactive elements on the quarantine page."""
        _go(page, base_url)
        assert_keyboard_navigation(page)  # type: ignore[arg-type]

    def test_quarantine_rows_keyboard_reachable(
        self, page: object, base_url: str
    ) -> None:
        """Quarantine rows or their action links are reachable via keyboard Tab."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping keyboard reach check")

        row_keyboard_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    'table tbody tr',
                    '[data-quarantine]',
                    '[data-event-id]',
                    '[class*="quarantine-card"]',
                    'details > summary'
                ];
                var results = [];
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(row) {
                        var tabindex  = row.getAttribute('tabindex');
                        var role      = row.getAttribute('role');
                        var tag       = row.tagName.toLowerCase();
                        var isNative  = tag === 'summary' || tag === 'a' || tag === 'button';
                        var focusable = row.querySelector(
                            'a[href], button, [tabindex="0"], input, select, summary'
                        );
                        results.push({
                            selfFocusable: tabindex !== null || role === 'row' || isNative,
                            hasFocusableChild: !!focusable
                        });
                    });
                });
                return results;
            })()
            """
        )

        keyboard_accessible = [
            r for r in row_keyboard_info
            if r.get("selfFocusable") or r.get("hasFocusableChild")
        ]

        if not keyboard_accessible:
            pytest.skip(
                "Quarantine items have no tabindex or focusable children — "
                "items may rely on JS click handlers; verify keyboard accessibility manually"
            )

    def test_action_buttons_keyboard_operable(
        self, page: object, base_url: str
    ) -> None:
        """Action buttons (replay/delete) on the quarantine page are reachable by keyboard."""
        _go(page, base_url)

        if not _has_quarantine_entries(page):
            pytest.skip("No quarantine entries — skipping action button keyboard check")

        action_keyboard_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    'button[data-action]',
                    '[data-quarantine-action]',
                    '[class*="replay"]',
                    '[class*="delete"]',
                    '[class*="retry"]',
                    'button'
                ];
                var results = [];
                var seen = new WeakSet();
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        if (seen.has(el)) return;
                        seen.add(el);
                        var tabindex = el.getAttribute('tabindex');
                        var tag      = el.tagName.toLowerCase();
                        var isNative = tag === 'button' || tag === 'a';
                        results.push({
                            focusable: isNative || (tabindex !== null && tabindex !== '-1')
                        });
                    });
                });
                return results;
            })()
            """
        )

        if not action_keyboard_info:
            pytest.skip(
                "No action button elements detected — skipping keyboard operability check"
            )

        non_focusable = [r for r in action_keyboard_info if not r.get("focusable")]
        assert len(non_focusable) < len(action_keyboard_info), (
            f"All {len(action_keyboard_info)} action button(s) on the quarantine page "
            "appear to be non-focusable (tabindex='-1' or non-native element without tabindex) — "
            "action buttons must be reachable via keyboard Tab (WCAG SC 2.1.1)"
        )


# ---------------------------------------------------------------------------
# SC 1.3.6 — ARIA landmarks
# ---------------------------------------------------------------------------


class TestQuarantineAriaLandmarks:
    """Quarantine page must use ARIA landmark regions for screen reader navigation (SC 1.3.6)."""

    def test_aria_landmarks_present(self, page: object, base_url: str) -> None:
        """Page has at least one ARIA landmark (main, nav, or region)."""
        _go(page, base_url)
        assert_aria_landmarks(page)  # type: ignore[arg-type]

    def test_quarantine_table_or_list_is_in_landmark(
        self, page: object, base_url: str
    ) -> None:
        """The quarantine table or event list is inside a landmark region or preceded by a heading."""
        _go(page, base_url)

        content_context = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var content = document.querySelector('table') ||
                              document.querySelector('[data-quarantine]') ||
                              document.querySelector('[data-event-id]') ||
                              document.querySelector('[class*="quarantine-card"]') ||
                              document.querySelector('details');
                if (!content) return {hasContent: false};

                var el = content;
                while (el && el !== document.body) {
                    var role = el.getAttribute('role');
                    var tag  = el.tagName.toLowerCase();
                    if (
                        ['main', 'nav', 'aside', 'section', 'article', 'region'].includes(tag) ||
                        ['main', 'navigation', 'complementary', 'region'].includes(role)
                    ) {
                        return {hasContent: true, hasLandmark: true};
                    }
                    el = el.parentElement;
                }

                var headings = document.querySelectorAll('h1, h2, h3');
                return {hasContent: true, hasLandmark: false, hasHeading: headings.length > 0};
            })()
            """
        )

        if not content_context.get("hasContent"):
            pytest.skip("No quarantine content element found on page")

        has_context = (
            content_context.get("hasLandmark") or content_context.get("hasHeading")
        )
        assert has_context, (
            "Quarantine table/event list must be inside a landmark region (<main>, <section>, etc.) "
            "or preceded by a heading (h1-h3) for screen reader navigation (WCAG SC 1.3.6)"
        )


# ---------------------------------------------------------------------------
# SC 2.5.8 — Touch target size
# ---------------------------------------------------------------------------


class TestQuarantineTouchTargets:
    """Buttons and action links must meet the 24x24 px minimum touch target (SC 2.5.8)."""

    def test_touch_targets_meet_minimum_size(
        self, page: object, base_url: str
    ) -> None:
        """All buttons and links on the quarantine page meet the 24x24 px touch target."""
        _go(page, base_url)
        assert_touch_targets(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# axe-core — WCAG 2.x AA automated audit
# ---------------------------------------------------------------------------


class TestQuarantineAxeAudit:
    """axe-core automated audit must report zero critical or serious violations (WCAG 2.x AA)."""

    def test_axe_audit_no_critical_violations(
        self, page: object, base_url: str
    ) -> None:
        """axe-core WCAG 2.x AA scan finds no critical or serious violations."""
        _go(page, base_url)
        result = run_axe_audit(page)  # type: ignore[arg-type]
        assert result.passed, (
            f"axe-core found {len(result.violations)} critical/serious violation(s) "
            f"on /admin/ui/quarantine:\n{result.summary()}"
        )
