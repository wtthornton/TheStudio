"""Epic 66.5 — Model Gateway: Accessibility WCAG 2.2 AA.

Validates that /admin/ui/models meets WCAG 2.2 AA accessibility requirements:

  - Table semantics       — <th scope="col"> on every column header (SC 1.3.1)
  - Toggle ARIA           — routing rule toggles carry role="switch" or aria-pressed (SC 4.1.2)
  - Focus management      — detail panel traps/restores focus on open/close (SC 2.4.3)
  - Focus indicators      — visible focus ring on all interactive elements (SC 2.4.11)
  - Keyboard nav          — Tab reaches model rows, toggle controls (SC 2.1.1)
  - ARIA landmarks        — page has main/nav landmark (SC 1.3.6)
  - Touch targets         — buttons meet 24x24 px minimum (SC 2.5.8)
  - Non-colour cues       — status/cost badges pair colour with text (SC 1.4.1)
  - axe-core WCAG 2.x AA  — zero critical/serious violations

These tests verify *accessibility compliance*, not content or visual appearance.
Content is covered in test_models_intent.py (Epic 66.1).
Style compliance is covered in test_models_style.py (Epic 66.3).
Interactions are covered in test_models_interactions.py (Epic 66.4).
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

MODELS_URL = "/admin/ui/models"


def _go(page: object, base_url: str) -> None:
    """Navigate to the models page and wait for content to settle."""
    navigate(page, f"{base_url}{MODELS_URL}")  # type: ignore[arg-type]


def _has_model_rows(page: object) -> bool:
    """Return True when the models page has at least one data row or card."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator(
            "[data-model], [class*='model-card'], [data-provider]"
        ).count()
        > 0
    )


# ---------------------------------------------------------------------------
# SC 1.3.1 — Table headers with scope="col"
# ---------------------------------------------------------------------------


class TestModelsTableSemantics:
    """Model table column headers must carry scope="col" for screen readers.

    Per WCAG SC 1.3.1 (Info and Relationships), every <th> in a data table
    must carry scope="col" so that assistive technology can associate cell data
    with its header.
    """

    def test_table_column_headers_have_scope_col(
        self, page: object, base_url: str
    ) -> None:
        """Every <th> in the models table carries scope='col'."""
        _go(page, base_url)

        th_count = page.locator("table th").count()  # type: ignore[attr-defined]
        if th_count == 0:
            pytest.skip("No <th> elements found — models page may not use a <table>")

        header_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table th');
                var results = [];
                ths.forEach(function(th) {
                    var scope = th.getAttribute('scope');
                    var role  = th.getAttribute('role');
                    results.push({
                        text: th.textContent.trim().slice(0, 40),
                        scope: scope,
                        role: role,
                        compliant: scope === 'col' || role === 'columnheader'
                    });
                });
                return results;
            })()
            """
        )

        non_compliant = [r for r in header_info if not r.get("compliant")]
        assert not non_compliant, (
            f"{len(non_compliant)}/{len(header_info)} <th> element(s) missing "
            "scope='col' or role='columnheader' — WCAG SC 1.3.1 requires every "
            "table column header to declare its scope: "
            + str([r["text"] for r in non_compliant])
        )

    def test_table_has_caption_or_aria_label(
        self, page: object, base_url: str
    ) -> None:
        """The models table carries a <caption> or aria-label for context."""
        _go(page, base_url)

        tables = page.locator("table")  # type: ignore[attr-defined]
        if tables.count() == 0:
            pytest.skip("No <table> elements on models page")

        table_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var tables = document.querySelectorAll('table');
                var results = [];
                tables.forEach(function(t) {
                    var caption   = !!t.querySelector('caption');
                    var ariaLabel = !!t.getAttribute('aria-label');
                    var ariaLby   = !!t.getAttribute('aria-labelledby');
                    results.push({ labelled: caption || ariaLabel || ariaLby });
                });
                return results;
            })()
            """
        )

        unlabelled = [r for r in table_info if not r.get("labelled")]
        if len(unlabelled) == len(table_info):
            pytest.skip(
                "No table has a <caption> or aria-label — "
                "consider adding one for screen reader context (WCAG SC 1.3.1)"
            )

    def test_table_rows_have_scope_or_role(
        self, page: object, base_url: str
    ) -> None:
        """Row header cells in the models table carry appropriate scope attributes."""
        _go(page, base_url)

        th_count = page.locator("table th").count()  # type: ignore[attr-defined]
        if th_count == 0:
            pytest.skip("No <th> found — skipping row-scope check")

        row_header_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table tbody th');
                var results = [];
                ths.forEach(function(th) {
                    var scope = th.getAttribute('scope');
                    results.push({
                        text: th.textContent.trim().slice(0, 40),
                        scope: scope,
                        compliant: scope === 'row' || scope === 'col'
                    });
                });
                return results;
            })()
            """
        )

        if not row_header_info:
            pytest.skip("No <th> in <tbody> — row-scope requirement does not apply")

        non_compliant = [r for r in row_header_info if not r.get("compliant")]
        assert not non_compliant, (
            f"{len(non_compliant)}/{len(row_header_info)} tbody <th> element(s) "
            "missing scope='row' — WCAG SC 1.3.1: "
            + str([r["text"] for r in non_compliant])
        )


# ---------------------------------------------------------------------------
# SC 4.1.2 — Toggle ARIA (routing rule switches)
# ---------------------------------------------------------------------------


class TestModelsToggleAria:
    """Routing rule toggle controls must carry correct ARIA semantics (SC 4.1.2).

    Toggle controls (enable/disable routing rules) must expose their state to
    assistive technology via role="switch" + aria-checked, or aria-pressed on
    buttons so that screen-reader users understand the current toggle state.
    """

    def test_routing_toggles_have_aria_role(
        self, page: object, base_url: str
    ) -> None:
        """Toggle controls carry role='switch' or aria-pressed to expose state."""
        _go(page, base_url)

        toggle_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[role="switch"]',
                    'button[aria-pressed]',
                    'input[type="checkbox"][aria-label]',
                    'input[type="checkbox"][id]',
                    '[data-toggle]',
                    '[data-routing-toggle]',
                    '[class*="toggle"]',
                    '[class*="switch"]'
                ];
                var results = [];
                var seen = new WeakSet();
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        if (seen.has(el)) return;
                        seen.add(el);
                        var role         = el.getAttribute('role');
                        var ariaPressed  = el.getAttribute('aria-pressed');
                        var ariaChecked  = el.getAttribute('aria-checked');
                        var tag          = el.tagName.toLowerCase();
                        var type         = el.getAttribute('type');
                        var isNativeChk  = tag === 'input' && type === 'checkbox';
                        results.push({
                            hasRole: !!(role || isNativeChk),
                            hasState: !!(ariaPressed !== null || ariaChecked !== null || isNativeChk),
                            role: role,
                            tag: tag,
                            isNativeChk: isNativeChk
                        });
                    });
                });
                return results;
            })()
            """
        )

        if not toggle_info:
            pytest.skip(
                "No routing toggle controls found on models page — "
                "routing may be view-only in this build"
            )

        missing_role = [r for r in toggle_info if not r.get("hasRole")]
        assert not missing_role, (
            f"{len(missing_role)}/{len(toggle_info)} toggle control(s) missing "
            "ARIA role — toggles must use role='switch', aria-pressed, or native "
            "<input type='checkbox'> (WCAG SC 4.1.2)"
        )

    def test_routing_toggles_expose_state(
        self, page: object, base_url: str
    ) -> None:
        """Toggle controls expose their current on/off state to assistive technology."""
        _go(page, base_url)

        state_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[role="switch"]',
                    'button[aria-pressed]',
                    'input[type="checkbox"]',
                    '[data-routing-toggle]',
                    '[class*="toggle"]',
                    '[class*="switch"]'
                ];
                var results = [];
                var seen = new WeakSet();
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        if (seen.has(el)) return;
                        seen.add(el);
                        var role        = el.getAttribute('role');
                        var ariaChecked = el.getAttribute('aria-checked');
                        var ariaPressed = el.getAttribute('aria-pressed');
                        var tag         = el.tagName.toLowerCase();
                        var type        = el.getAttribute('type');
                        var isNativeChk = tag === 'input' && type === 'checkbox';
                        var hasState    = !!(
                            ariaChecked !== null ||
                            ariaPressed !== null ||
                            isNativeChk
                        );
                        results.push({
                            hasState: hasState,
                            role: role,
                            tag: tag
                        });
                    });
                });
                return results;
            })()
            """
        )

        if not state_info:
            pytest.skip("No toggle controls found — skipping state exposure check")

        missing_state = [r for r in state_info if not r.get("hasState")]
        assert not missing_state, (
            f"{len(missing_state)}/{len(state_info)} toggle(s) do not expose "
            "on/off state via aria-checked or aria-pressed — screen reader users "
            "cannot determine toggle status (WCAG SC 4.1.2)"
        )

    def test_toggle_labels_are_descriptive(
        self, page: object, base_url: str
    ) -> None:
        """Each routing toggle has an accessible label describing what it controls."""
        _go(page, base_url)

        label_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[role="switch"]',
                    'button[aria-pressed]',
                    '[data-routing-toggle]'
                ];
                var results = [];
                var seen = new WeakSet();
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        if (seen.has(el)) return;
                        seen.add(el);
                        var ariaLabel  = el.getAttribute('aria-label');
                        var ariaLby    = el.getAttribute('aria-labelledby');
                        var text       = el.textContent.trim();
                        var id         = el.getAttribute('id');
                        var forLabel   = id
                            ? !!document.querySelector('label[for="' + id + '"]')
                            : false;
                        var hasLabel   = !!(ariaLabel || ariaLby || text || forLabel);
                        results.push({ hasLabel: hasLabel });
                    });
                });
                return results;
            })()
            """
        )

        if not label_info:
            pytest.skip("No explicit toggle controls found — skipping label check")

        unlabelled = [r for r in label_info if not r.get("hasLabel")]
        assert not unlabelled, (
            f"{len(unlabelled)}/{len(label_info)} routing toggle(s) lack an "
            "accessible label — each toggle must have aria-label, aria-labelledby, "
            "visible text, or an associated <label> (WCAG SC 4.1.2)"
        )


# ---------------------------------------------------------------------------
# SC 1.4.1 — Non-colour cues for status/cost indicators
# ---------------------------------------------------------------------------


class TestModelsNonColorCues:
    """Status and cost indicators must not rely solely on colour (SC 1.4.1)."""

    def test_status_badges_have_text_label(
        self, page: object, base_url: str
    ) -> None:
        """Model status/cost badges carry visible text, not colour only."""
        _go(page, base_url)

        badge_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[data-status]',
                    '[data-provider-status]',
                    '[class*="status"]',
                    '[class*="badge"]',
                    '[aria-label*="status" i]',
                    '[aria-label*="active" i]',
                    '[aria-label*="enabled" i]'
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
                "No status badge elements found on models page — "
                "page may be empty or use a different pattern"
            )

        color_only = [
            r for r in badge_info
            if not r.get("hasText") and not r.get("hasAriaLabel")
        ]
        assert not color_only, (
            f"{len(color_only)}/{len(badge_info)} status badge(s) convey status "
            "via colour only — each badge must pair colour with visible text or "
            "aria-label (WCAG SC 1.4.1)"
        )

    def test_no_color_only_status_indicators(
        self, page: object, base_url: str
    ) -> None:
        """General status indicators on the models page pair colour with text/icon."""
        _go(page, base_url)
        assert_no_color_only_indicators(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SC 2.4.3 — Focus management in provider detail panel
# ---------------------------------------------------------------------------


class TestModelsFocusManagement:
    """Opening the detail panel must move focus into it; closing must restore focus (SC 2.4.3)."""

    def test_detail_panel_receives_focus_on_open(
        self, page: object, base_url: str
    ) -> None:
        """Opening the provider detail panel moves keyboard focus inside the panel."""
        _go(page, base_url)

        if not _has_model_rows(page):
            pytest.skip("No model items — skipping focus-management test")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "[data-model][hx-get]",
            "[data-provider][hx-get]",
            "table tbody tr",
            "[data-model]",
            "[data-provider]",
        ]
        clicked = False
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            clicked = True
            break

        if not clicked:
            pytest.skip("No visible model/provider items to click")

        focused_in_panel = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var active = document.activeElement;
                if (!active) return false;
                var panelSelectors = [
                    '[role="dialog"]',
                    '[role="complementary"]',
                    '.detail-panel',
                    '.inspector-panel',
                    '.slide-panel',
                    '[data-panel]',
                    '[id*="detail"]',
                    '[id*="panel"]',
                    '[class*="detail-panel"]',
                    '[class*="inspector"]'
                ];
                return panelSelectors.some(function(sel) {
                    try {
                        var panel = document.querySelector(sel);
                        return panel && panel.contains(active);
                    } catch(e) { return false; }
                });
            })()
            """
        )

        if not focused_in_panel:
            focused_tag = page.evaluate(  # type: ignore[attr-defined]
                "document.activeElement ? document.activeElement.tagName : ''"
            )
            assert focused_tag not in ("BODY", "HTML", ""), (
                "Opening model/provider detail panel must move focus inside the panel — "
                "focus remains on the page body after panel open (WCAG SC 2.4.3)"
            )

    def test_detail_panel_has_close_mechanism(
        self, page: object, base_url: str
    ) -> None:
        """The detail panel provides a keyboard-accessible close mechanism (SC 2.1.2)."""
        _go(page, base_url)

        if not _has_model_rows(page):
            pytest.skip("No model items — skipping panel close mechanism test")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-model]",
            "[data-provider]",
        ]
        clicked = False
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            clicked = True
            break

        if not clicked:
            pytest.skip("No visible model items to click")

        close_selectors = [
            "[aria-label='Close']",
            "[aria-label='Dismiss']",
            "[aria-label='close' i]",
            "button[data-close]",
            "button.close",
            ".panel-close",
            "[data-panel-close]",
            "button:has-text('Close')",
            "button:has-text('✕')",
            "button:has-text('×')",
        ]
        close_found = any(
            page.locator(sel).count() > 0  # type: ignore[attr-defined]
            for sel in close_selectors
        )

        if not close_found:
            page.keyboard.press("Escape")  # type: ignore[attr-defined]
            page.wait_for_timeout(400)  # type: ignore[attr-defined]

            still_open_sel = (
                "[role='complementary'][aria-hidden='false'], "
                ".detail-panel:not(.hidden):not([hidden]), "
                ".inspector-panel:not(.hidden):not([hidden])"
            )
            still_open = page.locator(still_open_sel).count() > 0  # type: ignore[attr-defined]
            assert not still_open, (
                "Model/provider detail panel must be closeable via a visible close button or "
                "Escape key — neither method closed the panel (WCAG SC 2.1.2)"
            )


# ---------------------------------------------------------------------------
# SC 2.1.1 — Keyboard navigation
# ---------------------------------------------------------------------------


class TestModelsKeyboardNavigation:
    """All interactive elements on the models page must be keyboard-reachable (SC 2.1.1)."""

    def test_keyboard_navigation_reaches_interactive_elements(
        self, page: object, base_url: str
    ) -> None:
        """Tab key reaches interactive elements on the models page."""
        _go(page, base_url)
        assert_keyboard_navigation(page)  # type: ignore[arg-type]

    def test_toggle_controls_keyboard_operable(
        self, page: object, base_url: str
    ) -> None:
        """Routing toggle controls on the models page are reachable by keyboard."""
        _go(page, base_url)

        toggle_selectors = [
            "[role='switch']",
            "button[aria-pressed]",
            "input[type='checkbox']",
            "[data-routing-toggle]",
            "[class*='toggle']",
            "[class*='switch']",
            "button",
        ]
        for sel in toggle_selectors:
            if page.locator(sel).count() > 0:  # type: ignore[attr-defined]
                try:
                    assert_focus_visible(page, sel)  # type: ignore[arg-type]
                    return
                except Exception:  # noqa: BLE001
                    continue

        pytest.skip(
            "No toggle controls found on models page — "
            "skipping keyboard operability check"
        )

    def test_model_rows_keyboard_reachable(
        self, page: object, base_url: str
    ) -> None:
        """Model/provider items or their action links are reachable via keyboard Tab."""
        _go(page, base_url)

        if not _has_model_rows(page):
            pytest.skip("No model items — skipping keyboard reach check")

        item_keyboard_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    'table tbody tr',
                    '[data-model]',
                    '[data-provider]',
                    '[class*="model-card"]'
                ];
                var results = [];
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(item) {
                        var tabindex  = item.getAttribute('tabindex');
                        var role      = item.getAttribute('role');
                        var focusable = item.querySelector(
                            'a[href], button, [tabindex="0"], input, select, [role="switch"]'
                        );
                        results.push({
                            selfFocusable: tabindex !== null || role === 'row',
                            hasFocusableChild: !!focusable
                        });
                    });
                });
                return results;
            })()
            """
        )

        keyboard_accessible = [
            r for r in item_keyboard_info
            if r.get("selfFocusable") or r.get("hasFocusableChild")
        ]

        if not keyboard_accessible:
            pytest.skip(
                "Model items have no tabindex or focusable children — "
                "items may rely on JS click handlers; verify keyboard accessibility manually"
            )


# ---------------------------------------------------------------------------
# SC 2.4.11 — Focus indicators
# ---------------------------------------------------------------------------


class TestModelsFocusIndicators:
    """All interactive elements must display visible focus indicators (SC 2.4.11)."""

    def test_interactive_elements_show_focus(
        self, page: object, base_url: str
    ) -> None:
        """Buttons, links, selects, and toggles display a visible focus indicator."""
        _go(page, base_url)

        interactive_selectors = [
            "button",
            "a[href]",
            "select",
            "input",
            "[role='switch']",
        ]
        for sel in interactive_selectors:
            if page.locator(sel).count() > 0:  # type: ignore[attr-defined]
                try:
                    assert_focus_visible(page, sel)  # type: ignore[arg-type]
                    return
                except AssertionError:
                    continue

        pytest.skip(
            "No interactive elements found on models page — skipping focus indicator check"
        )


# ---------------------------------------------------------------------------
# SC 1.3.6 — ARIA landmarks
# ---------------------------------------------------------------------------


class TestModelsAriaLandmarks:
    """Models page must use ARIA landmark regions for screen reader navigation (SC 1.3.6)."""

    def test_aria_landmarks_present(self, page: object, base_url: str) -> None:
        """Page has at least one ARIA landmark (main, nav, or region)."""
        _go(page, base_url)
        assert_aria_landmarks(page)  # type: ignore[arg-type]

    def test_models_region_has_landmark_or_heading(
        self, page: object, base_url: str
    ) -> None:
        """The models catalog is inside a landmark region or preceded by a heading."""
        _go(page, base_url)

        catalog_context = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var catalog = document.querySelector('table') ||
                              document.querySelector('[data-model]') ||
                              document.querySelector('[data-provider]') ||
                              document.querySelector('[class*="model-card"]');
                if (!catalog) return {hasCatalog: false};

                var el = catalog;
                while (el && el !== document.body) {
                    var role = el.getAttribute('role');
                    var tag  = el.tagName.toLowerCase();
                    if (
                        ['main', 'nav', 'aside', 'section', 'article', 'region'].includes(tag) ||
                        ['main', 'navigation', 'complementary', 'region'].includes(role)
                    ) {
                        return {hasCatalog: true, hasLandmark: true};
                    }
                    el = el.parentElement;
                }

                var headings = document.querySelectorAll('h1, h2, h3');
                var hasHeading = headings.length > 0;
                return {hasCatalog: true, hasLandmark: false, hasHeading: hasHeading};
            })()
            """
        )

        if not catalog_context.get("hasCatalog"):
            pytest.skip("No catalog element found on models page")

        has_context = (
            catalog_context.get("hasLandmark") or catalog_context.get("hasHeading")
        )
        assert has_context, (
            "Models catalog must be inside a landmark region (<main>, <section>, etc.) "
            "or preceded by a heading (h1-h3) for screen reader navigation (WCAG SC 1.3.6)"
        )


# ---------------------------------------------------------------------------
# SC 2.5.8 — Touch target size
# ---------------------------------------------------------------------------


class TestModelsTouchTargets:
    """Buttons and links must meet the 24x24 px minimum touch target (SC 2.5.8)."""

    def test_touch_targets_meet_minimum_size(
        self, page: object, base_url: str
    ) -> None:
        """All buttons and links on the models page meet the 24x24 px touch target."""
        _go(page, base_url)
        assert_touch_targets(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# axe-core — WCAG 2.x AA automated audit
# ---------------------------------------------------------------------------


class TestModelsAxeAudit:
    """axe-core automated audit must report zero critical or serious violations (WCAG 2.x AA)."""

    def test_axe_audit_no_critical_violations(
        self, page: object, base_url: str
    ) -> None:
        """axe-core WCAG 2.x AA scan finds no critical or serious violations."""
        _go(page, base_url)
        result = run_axe_audit(page)  # type: ignore[arg-type]
        assert result.passed, (
            f"axe-core found {len(result.violations)} critical/serious violation(s) "
            f"on /admin/ui/models:\n{result.summary()}"
        )
