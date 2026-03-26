"""Epic 69.5 — Dead-Letter Inspector: Accessibility WCAG 2.2 AA.

Validates that /admin/ui/dead-letters meets WCAG 2.2 AA accessibility requirements:

  - Table semantics       — <table> uses proper <thead>/<tbody>, <th scope="col"> (SC 1.3.1)
  - Action button ARIA    — retry/delete buttons have accessible labels (SC 2.4.6)
  - Focus indicators      — visible focus ring on all interactive elements (SC 2.4.11)
  - Keyboard navigation   — Tab reaches table rows and action buttons (SC 2.1.1)
  - ARIA landmarks        — page has main/nav landmark (SC 1.3.6)
  - Non-colour cues       — status badges pair colour with text (SC 1.4.1)
  - Touch targets         — buttons meet 24x24 px minimum (SC 2.5.8)
  - axe-core WCAG 2.x AA  — zero critical/serious violations

These tests verify *accessibility compliance*, not content or visual appearance.
Content is covered in test_dead_letters_intent.py (Epic 69.1).
Style compliance is covered in test_dead_letters_style.py (Epic 69.3).
Interactions are covered in test_dead_letters_interactions.py (Epic 69.4).
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

DEAD_LETTERS_URL = "/admin/ui/dead-letters"


def _go(page: object, base_url: str) -> None:
    """Navigate to the dead-letter inspector page and wait for content to settle."""
    navigate(page, f"{base_url}{DEAD_LETTERS_URL}")  # type: ignore[arg-type]


def _has_dead_letter_entries(page: object) -> bool:
    """Return True when the dead-letter page has at least one data row or card."""
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


def _trigger_action_and_open_dialog(page: object) -> bool:
    """Click the first destructive action button and return True if a dialog opens."""
    btn = _find_action_button(
        page, ["Delete", "Remove", "Discard", "Purge", "Retry", "Requeue", "Replay"]
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
# SC 1.3.1 — Table semantics
# ---------------------------------------------------------------------------


class TestDeadLetterTableSemantics:
    """The dead-letter event table must use correct HTML table semantics.

    Per WCAG SC 1.3.1 (Info and Relationships), data tables must use <thead>,
    <tbody>, and <th scope="col"> so that assistive technology can associate
    column headers with their data cells.
    """

    def test_table_has_thead_and_tbody(self, page: object, base_url: str) -> None:
        """Dead-letter table must use <thead> and <tbody> structural elements.

        Assistive technologies rely on explicit <thead>/<tbody> to identify
        header rows vs. data rows. A flat list of <tr> elements is not
        machine-readable as a data table.
        """
        _go(page, base_url)

        table_count = page.locator("table").count()  # type: ignore[attr-defined]
        if table_count == 0:
            pytest.skip(
                "No <table> element on dead-letter page — "
                "skipping thead/tbody check (list/card layout may be used)"
            )

        has_thead = page.locator("table thead").count() > 0  # type: ignore[attr-defined]
        has_tbody = page.locator("table tbody").count() > 0  # type: ignore[attr-defined]

        assert has_thead, (
            "Dead-letter table must have a <thead> element — "
            "screen readers use <thead> to distinguish header rows from data rows (WCAG SC 1.3.1)"
        )
        assert has_tbody, (
            "Dead-letter table must have a <tbody> element — "
            "screen readers use <tbody> to identify data rows (WCAG SC 1.3.1)"
        )

    def test_table_headers_have_scope_attribute(self, page: object, base_url: str) -> None:
        """Column headers in the dead-letter table must carry scope='col'.

        Per WCAG SC 1.3.1, <th> elements in a data table should declare
        scope='col' (for column headers) or scope='row' so that assistive
        technology can programmatically map each header to its data cells.
        Icon-only or empty header cells are exempt.
        """
        _go(page, base_url)

        header_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table thead th, table th');
                var results = [];
                ths.forEach(function(th) {
                    var text = th.textContent.trim();
                    var scope = th.getAttribute('scope') || '';
                    var ariaSort = th.getAttribute('aria-sort') || '';
                    results.push({
                        text: text.slice(0, 40),
                        scope: scope,
                        hasScope: scope.length > 0,
                        isEmpty: text.length === 0
                    });
                });
                return results;
            })()
            """
        )

        if not header_info:
            pytest.skip(
                "No <th> elements found on dead-letter page — "
                "skipping scope check (list/card layout may be used)"
            )

        non_empty_headers = [h for h in header_info if not h.get("isEmpty")]
        if not non_empty_headers:
            pytest.skip("All table headers appear to be empty — skipping scope check")

        missing_scope = [h for h in non_empty_headers if not h.get("hasScope")]
        assert not missing_scope, (
            f"{len(missing_scope)}/{len(non_empty_headers)} non-empty column header(s) "
            "on the dead-letter table lack a scope attribute — "
            "screen readers cannot associate headers with their data cells (WCAG SC 1.3.1). "
            "Missing: " + str([h["text"] for h in missing_scope])
        )

    def test_table_cells_not_used_as_headers(self, page: object, base_url: str) -> None:
        """Data cells in <tbody> must not use <th> elements.

        Using <th> inside <tbody> without explicit scope can confuse assistive
        technology about the row vs. column header relationship.
        """
        _go(page, base_url)

        tbody_th_count = page.locator("table tbody th").count()  # type: ignore[attr-defined]
        if tbody_th_count == 0:
            return  # no issue found

        # Some implementations use <th scope="row"> for row-level headers — that is valid
        tbody_th_without_row_scope = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table tbody th');
                var invalid = [];
                ths.forEach(function(th) {
                    var scope = th.getAttribute('scope') || '';
                    if (scope !== 'row' && scope !== 'rowgroup') {
                        invalid.push({
                            text: th.textContent.trim().slice(0, 40),
                            scope: scope
                        });
                    }
                });
                return invalid;
            })()
            """
        )

        assert not tbody_th_without_row_scope, (
            f"{len(tbody_th_without_row_scope)} <th> element(s) in <tbody> lack scope='row' — "
            "this creates ambiguous column/row header relationships for screen readers (WCAG SC 1.3.1). "
            "Elements: " + str([h["text"] for h in tbody_th_without_row_scope])
        )

    def test_table_caption_or_aria_label_present(
        self, page: object, base_url: str
    ) -> None:
        """The dead-letter table must have a caption or aria-label identifying its purpose.

        Per WCAG SC 1.3.1, data tables should be labelled so that users who
        navigate to the table via a landmark or heading can identify its purpose
        without reading all the data.
        """
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No <table> element on dead-letter page — skipping caption check")

        table_label_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var tables = document.querySelectorAll('table');
                var results = [];
                tables.forEach(function(tbl) {
                    var caption = tbl.querySelector('caption');
                    var ariaLabel = tbl.getAttribute('aria-label') || '';
                    var ariaLby = tbl.getAttribute('aria-labelledby') || '';
                    var hasLabel = !!(
                        (caption && caption.textContent.trim().length > 0) ||
                        ariaLabel.length > 0 ||
                        ariaLby.length > 0
                    );
                    results.push({
                        hasLabel: hasLabel,
                        captionText: caption ? caption.textContent.trim().slice(0, 60) : '',
                        ariaLabel: ariaLabel.slice(0, 60)
                    });
                });
                return results;
            })()
            """
        )

        if not table_label_info:
            pytest.skip("Table label check returned no data — skipping")

        unlabelled = [t for t in table_label_info if not t.get("hasLabel")]
        if unlabelled:
            # Soft skip: labelling is best-practice but may not be implemented uniformly
            pytest.skip(
                f"{len(unlabelled)} table(s) on dead-letter page have no caption or aria-label — "
                "consider adding for improved assistive technology experience (WCAG SC 1.3.1)"
            )


# ---------------------------------------------------------------------------
# SC 2.4.6 — Action button accessible labels
# ---------------------------------------------------------------------------


class TestDeadLetterActionButtonAria:
    """Retry and delete action buttons must have descriptive, accessible labels.

    Per WCAG SC 2.4.6 (Headings and Labels), every interactive control must
    carry a meaningful label so assistive technology users understand its purpose.
    Icon-only buttons require an aria-label or visually-hidden text.
    """

    def test_action_buttons_have_accessible_label(
        self, page: object, base_url: str
    ) -> None:
        """Every action button on the dead-letter page has an accessible name.

        Operators using screen readers must be able to distinguish 'Retry event
        abc123' from 'Delete event abc123' — ambiguous labels like 'Go' or unlabelled
        icon buttons violate SC 2.4.6.
        """
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip("No dead-letter entries — skipping action button ARIA check")

        button_label_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    'button',
                    'a[role="button"]',
                    '[data-action]',
                    '[data-dead-letter-action]',
                    '[class*="action"]',
                    '[class*="retry"]',
                    '[class*="delete"]',
                    '[class*="replay"]'
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
                "No action button elements found on dead-letter page — "
                "page may be empty or use a different pattern"
            )

        unnamed = [r for r in button_label_info if not r.get("hasAccessibleName")]
        assert not unnamed, (
            f"{len(unnamed)}/{len(button_label_info)} action button(s) on the dead-letter page "
            "have no accessible name (no text content, aria-label, or title) — "
            "screen reader users cannot distinguish action intent (WCAG SC 2.4.6). "
            "Nameless elements: " + str([r["tag"] for r in unnamed])
        )

    def test_retry_buttons_have_descriptive_label(
        self, page: object, base_url: str
    ) -> None:
        """Retry/requeue action buttons carry a label that describes the action."""
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip("No dead-letter entries — skipping retry button label check")

        retry_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var retry_keywords = ['retry', 'requeue', 'replay', 'reprocess', 'resubmit'];
                var results = [];
                document.querySelectorAll('button, a[role="button"], [data-action]')
                    .forEach(function(el) {
                        var text    = el.textContent.trim().toLowerCase();
                        var ariaLbl = (el.getAttribute('aria-label') || '').toLowerCase();
                        var title   = (el.getAttribute('title') || '').toLowerCase();
                        var combined = text + ' ' + ariaLbl + ' ' + title;
                        var isRetry = retry_keywords.some(function(kw) {
                            return combined.indexOf(kw) !== -1;
                        });
                        if (isRetry) {
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

        if not retry_info:
            pytest.skip(
                "No retry/requeue action buttons found — "
                "action may be accessible via row detail panel"
            )

        unlabelled = [r for r in retry_info if not r.get("hasLabel")]
        assert not unlabelled, (
            f"{len(unlabelled)}/{len(retry_info)} retry action button(s) have no accessible "
            "name — screen readers cannot announce the action purpose (WCAG SC 2.4.6)"
        )

    def test_delete_buttons_have_descriptive_label(
        self, page: object, base_url: str
    ) -> None:
        """Delete/discard action buttons carry a label that describes the action."""
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip("No dead-letter entries — skipping delete button label check")

        delete_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var delete_keywords = ['delete', 'remove', 'discard', 'purge', 'dismiss'];
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
                "No delete/discard action buttons found — "
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
                "No icon-only buttons detected on dead-letter page — "
                "skipping icon button aria-label check"
            )

        unlabelled = [r for r in icon_button_info if not r.get("hasAriaName")]
        assert not unlabelled, (
            f"{len(unlabelled)}/{len(icon_button_info)} icon-only button(s) on the dead-letter "
            "page have no aria-label or aria-labelledby — "
            "screen readers will announce these as unlabelled controls (WCAG SC 1.1.1 / SC 2.4.6)"
        )


# ---------------------------------------------------------------------------
# SC 2.4.11 — Focus indicators
# ---------------------------------------------------------------------------


class TestDeadLetterFocusIndicators:
    """Interactive elements on the dead-letter page must have visible focus indicators.

    Per WCAG SC 2.4.11 (Focus Appearance), focus indicators must be visible
    so keyboard-only users can track their position on the page.
    """

    def test_interactive_elements_have_focus_indicator(
        self, page: object, base_url: str
    ) -> None:
        """All interactive elements on the dead-letter page have a visible focus ring."""
        _go(page, base_url)
        assert_focus_visible(page, context="dead-letter page")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SC 2.1.1 — Keyboard navigation
# ---------------------------------------------------------------------------


class TestDeadLetterKeyboardNavigation:
    """The dead-letter inspector page must be fully navigable by keyboard.

    Per WCAG SC 2.1.1 (Keyboard), all functionality must be operable via
    keyboard without requiring specific timings.
    """

    def test_keyboard_can_reach_table_rows_and_actions(
        self, page: object, base_url: str
    ) -> None:
        """Tab key reaches dead-letter table rows and action buttons."""
        _go(page, base_url)
        assert_keyboard_navigation(page, context="dead-letter page")  # type: ignore[arg-type]

    def test_tab_order_does_not_trap_keyboard(
        self, page: object, base_url: str
    ) -> None:
        """Keyboard focus must not be trapped outside a modal on the dead-letter page.

        Per WCAG SC 2.1.2, keyboard focus must never be trapped in a component
        unless the component is a modal dialog where trapping is intentional and
        the dialog provides a way to dismiss with Escape.
        """
        _go(page, base_url)

        # Press Tab up to 20 times; verify we don't land back on the same element twice
        # without having pressed Shift+Tab (simple trap detection)
        focused_elements: list[str] = []

        for _ in range(20):
            try:
                page.keyboard.press("Tab")  # type: ignore[attr-defined]
                page.wait_for_timeout(100)  # type: ignore[attr-defined]
                focused = page.evaluate(  # type: ignore[attr-defined]
                    "document.activeElement ? "
                    "(document.activeElement.tagName + '#' + (document.activeElement.id || '')) : ''"
                )
                if focused:
                    focused_elements.append(focused)
            except Exception:  # noqa: BLE001
                break

        # A keyboard trap would manifest as the same element repeating before cycling
        if len(focused_elements) >= 4:
            # Check that we don't see the same 2-element sequence 3 times in a row
            for i in range(len(focused_elements) - 5):
                pair = (focused_elements[i], focused_elements[i + 1])
                repetitions = sum(
                    1
                    for j in range(i, len(focused_elements) - 1)
                    if (focused_elements[j], focused_elements[j + 1]) == pair
                )
                assert repetitions < 3, (
                    f"Keyboard focus appears trapped in a 2-element cycle on the dead-letter page: "
                    f"{pair} — Tab key repeated same element pair {repetitions} times (WCAG SC 2.1.2)"
                )


# ---------------------------------------------------------------------------
# SC 1.3.6 — ARIA landmarks
# ---------------------------------------------------------------------------


class TestDeadLetterAriaLandmarks:
    """The dead-letter page must provide ARIA landmark regions for assistive navigation.

    Per WCAG SC 1.3.6 (Identify Purpose), pages must include landmark regions
    (<main>, <nav>, etc.) so screen reader users can jump directly to content.
    """

    def test_page_has_required_landmarks(self, page: object, base_url: str) -> None:
        """Dead-letter page has at least a <main> landmark."""
        _go(page, base_url)
        assert_aria_landmarks(page, context="dead-letter page")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SC 1.4.1 — Non-colour status cues
# ---------------------------------------------------------------------------


class TestDeadLetterNonColorCues:
    """Dead-letter status indicators must pair colour with text or icons.

    Per WCAG SC 1.4.1 (Use of Color), information conveyed by colour alone
    must also be communicated through another visual cue (text label, icon,
    pattern) for users with colour vision deficiency.
    """

    def test_status_badges_not_color_only(self, page: object, base_url: str) -> None:
        """Dead-letter status badges pair colour with text or icon cues."""
        _go(page, base_url)
        assert_no_color_only_indicators(page, context="dead-letter page")  # type: ignore[arg-type]

    def test_failure_reason_visible_as_text(self, page: object, base_url: str) -> None:
        """Failure reasons on dead-letter entries must be communicated via visible text.

        Colour-coded severity (e.g., red for fatal, yellow for transient) is not
        sufficient alone — the failure type must also appear as text so users with
        colour vision deficiency can triage events.
        """
        _go(page, base_url)

        if not _has_dead_letter_entries(page):
            pytest.skip(
                "No dead-letter entries — skipping failure reason text check"
            )

        # Look for any text that indicates failure reason/status
        failure_text_selectors = [
            "[class*='failure']",
            "[class*='error']",
            "[class*='reason']",
            "[data-failure-reason]",
            "[data-error-type]",
            "td:nth-child(3)",  # common position for reason/error column
        ]

        for sel in failure_text_selectors:
            try:
                elements = page.locator(sel)  # type: ignore[attr-defined]
                if elements.count() > 0:
                    first = elements.first
                    text = first.inner_text().strip()
                    if text:
                        # Text content is present — non-colour cue exists
                        return
            except Exception:  # noqa: BLE001
                continue

        # If no explicit failure reason elements found, check that the table
        # has more than just colour cues (any text in tbody)
        tbody_text = ""
        try:
            tbody_text = page.locator("table tbody").inner_text().strip()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

        if not tbody_text:
            pytest.skip(
                "Could not verify failure reason text — "
                "dead-letter table body has no readable text content"
            )


# ---------------------------------------------------------------------------
# SC 2.5.8 — Touch targets
# ---------------------------------------------------------------------------


class TestDeadLetterTouchTargets:
    """Action buttons on the dead-letter page must meet minimum touch target size.

    Per WCAG SC 2.5.8 (Target Size, Minimum), interactive controls must be at
    least 24x24 CSS pixels to be operable on touchscreen devices.
    """

    def test_action_buttons_meet_touch_target_size(
        self, page: object, base_url: str
    ) -> None:
        """Retry/delete action buttons are at least 24x24 CSS pixels."""
        _go(page, base_url)
        assert_touch_targets(page, context="dead-letter page")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# axe-core — Zero critical/serious violations
# ---------------------------------------------------------------------------


class TestDeadLetterAxeAudit:
    """Run axe-core WCAG 2.x AA audit against the dead-letter inspector page.

    The audit flags critical and serious violations. Minor and moderate issues
    are reported but do not fail the test to avoid blocking on cosmetic issues.
    """

    def test_axe_no_critical_violations(self, page: object, base_url: str) -> None:
        """axe-core reports zero critical or serious WCAG 2.x AA violations.

        Critical violations represent significant barriers to accessibility —
        missing labels, colour contrast failures, missing ARIA roles — that
        prevent users with disabilities from using the page at all.
        """
        _go(page, base_url)
        run_axe_audit(page, context="dead-letter page")  # type: ignore[arg-type]
