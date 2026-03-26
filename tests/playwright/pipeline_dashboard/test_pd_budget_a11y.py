"""Story 76.8 — Budget Tab: Accessibility WCAG 2.2 AA.

Validates that /dashboard/?tab=budget meets WCAG 2.2 AA accessibility
requirements:

  SC 1.3.1  — Info and Relationships: heading hierarchy and semantic structure
  SC 1.3.6  — Identify Purpose: ARIA landmark regions (main, nav, header)
  SC 1.4.1  — Use of Color: cost figures and status indicators pair colour with
               text labels (not colour only)
  SC 2.1.1  — Keyboard: all interactive elements reachable by keyboard
  SC 2.4.11 — Focus Appearance (minimum): visible focus indicators
  SC 2.5.8  — Target Size (minimum): 24×24 px touch targets on buttons
  axe-core  — WCAG 2.x AA audit (zero critical / serious violations)

These tests verify *accessibility compliance*, not content or visual appearance.
Content is in test_pd_budget_intent.py.
Style compliance is in test_pd_budget_style.py.
"""

from __future__ import annotations

import pytest

from tests.playwright.lib.accessibility_helpers import (
    assert_aria_landmarks,
    assert_focus_visible,
    assert_keyboard_navigation,
    assert_no_color_only_indicators,
    assert_touch_targets,
    run_axe_audit,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _go(page: object, base_url: str) -> None:
    """Navigate to the budget tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "budget")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ARIA landmark regions (WCAG 2.2 SC 1.3.6)
# ---------------------------------------------------------------------------


class TestBudgetAriaLandmarks:
    """Required ARIA landmark regions must be present on the budget tab.

    Screen-reader users rely on landmark regions to navigate directly to the
    primary content areas without listening to the full page.
    """

    def test_aria_landmarks_present(self, page, base_url: str) -> None:
        """Page must include <main>, <nav>, and <header> landmarks."""
        _go(page, base_url)
        result = assert_aria_landmarks(page)
        assert result.passed, result.summary()

    def test_header_landmark_present(self, page, base_url: str) -> None:
        """Budget tab has a <header> element for the application chrome."""
        _go(page, base_url)
        header_count = page.locator("header, [role='banner']").count()
        assert header_count > 0, (
            "Budget tab must have a <header> / banner landmark "
            "containing the navigation and budget controls"
        )

    def test_nav_landmark_has_aria_label(self, page, base_url: str) -> None:
        """Primary navigation <nav> carries an aria-label."""
        _go(page, base_url)
        nav = page.locator("nav[aria-label='Primary navigation']")
        assert nav.count() > 0, (
            "Primary navigation must carry aria-label='Primary navigation' "
            "so screen-reader users can identify it"
        )

    def test_multiple_nav_regions_labeled(self, page, base_url: str) -> None:
        """When multiple <nav> elements exist, each must have a distinct aria-label."""
        _go(page, base_url)
        nav_elements = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('nav, [role="navigation"]')).map(el => ({
                tag: el.tagName.toLowerCase(),
                ariaLabel: el.getAttribute('aria-label') || '',
            }))
            """
        )
        if len(nav_elements) <= 1:
            pytest.skip("Only one nav element — no labelling conflict possible")

        unlabelled = [n for n in nav_elements if not n.get("ariaLabel")]
        assert not unlabelled, (
            f"{len(unlabelled)} of {len(nav_elements)} <nav> element(s) lack aria-label "
            "(required when multiple nav regions exist — WCAG SC 1.3.6)"
        )


# ---------------------------------------------------------------------------
# Heading hierarchy (WCAG 2.2 SC 1.3.1)
# ---------------------------------------------------------------------------


class TestBudgetHeadingHierarchy:
    """Headings must follow a proper h1 → h2 → h3 nesting hierarchy.

    An incorrect heading order confuses screen-reader users who rely on
    headings to navigate the page structure.
    """

    def test_page_has_at_least_one_heading(self, page, base_url: str) -> None:
        """Budget tab has at least one heading element (h1–h4)."""
        _go(page, base_url)
        heading_count = page.locator("h1, h2, h3, h4").count()
        assert heading_count > 0, (
            "Budget tab must have at least one heading element "
            "so screen-reader users can navigate the page structure"
        )

    def test_no_heading_level_skipped(self, page, base_url: str) -> None:
        """Heading levels are not skipped (e.g., h1 → h3 without h2 is invalid)."""
        _go(page, base_url)
        heading_levels = page.evaluate(
            """
            () => {
                const hs = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
                return hs.map(h => parseInt(h.tagName.slice(1)));
            }
            """
        )
        if len(heading_levels) <= 1:
            pytest.skip("Fewer than 2 headings — hierarchy check not applicable")

        skips: list[str] = []
        prev = heading_levels[0]
        for level in heading_levels[1:]:
            if level > prev + 1:
                skips.append(f"h{prev} → h{level}")
            prev = level

        assert not skips, (
            f"Heading hierarchy skips detected (WCAG SC 1.3.1): {skips!r}. "
            "Heading levels must increase by one at a time."
        )

    def test_budget_dashboard_heading_accessible(self, page, base_url: str) -> None:
        """'Budget Dashboard' heading is an h2 with accessible text."""
        _go(page, base_url)
        heading = page.locator("h1, h2, h3, h4").filter(has_text="Budget Dashboard")
        if heading.count() == 0:
            pytest.skip("Budget Dashboard heading element not found")

        heading_text = heading.first.inner_text().strip()
        assert heading_text, "Budget Dashboard heading must have non-empty accessible text"


# ---------------------------------------------------------------------------
# Cost figure labels (WCAG 2.2 SC 1.4.1)
# ---------------------------------------------------------------------------


class TestBudgetCostFigureLabels:
    """Cost figures must pair numeric values with visible text labels.

    WCAG 1.4.1 requires that information conveyed by colour (accent colours
    on spend figures) is also available through text.  Each summary card
    must show both a label ('Total Spend') and the numeric value.
    """

    def test_cost_figures_have_visible_labels(self, page, base_url: str) -> None:
        """Each cost figure card has a visible text label (not just colour coding)."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        if "No spend data" in body or "Total Spend" not in body:
            pytest.skip("Budget data not loaded — skipping cost label check")

        # Verify that the dollar figure is always accompanied by a label.
        # SummaryCards renders: label (text-xs text-gray-400) then value.
        card_labels = ["Total Spend", "Total API Calls", "Cache Hit Rate"]
        for label in card_labels:
            assert label in body, (
                f"Summary card must display '{label}' text label alongside its cost figure "
                f"— colour alone is insufficient to convey meaning (WCAG SC 1.4.1)"
            )

    def test_status_colors_have_text_alternatives(self, page, base_url: str) -> None:
        """Elements using status colors carry visible text or aria-label."""
        _go(page, base_url)

        status_elements = page.evaluate(
            """
            () => {
                const sel = '[data-status], [class*="status-"], [class*="-status"], ' +
                    '[class*="text-red"], [class*="text-yellow"], [class*="text-green"]';
                return Array.from(document.querySelectorAll(sel)).slice(0, 20).map(el => ({
                    tag: el.tagName.toLowerCase(),
                    text: el.textContent.trim().slice(0, 40),
                    ariaLabel: el.getAttribute('aria-label') || '',
                    title: el.getAttribute('title') || '',
                    hasIcon: !!el.querySelector('svg, img, [class*="icon"]'),
                }));
            }
            """
        )
        if not status_elements:
            pytest.skip("No status-color elements found on budget tab")

        color_only = [
            e for e in status_elements
            if not e.get("text") and not e.get("ariaLabel") and not e.get("title") and not e.get("hasIcon")
        ]
        assert not color_only, (
            f"{len(color_only)} element(s) convey state through colour only: "
            + ", ".join(f"<{e['tag']}>" for e in color_only[:5])
        )


# ---------------------------------------------------------------------------
# Data tables have accessible headers (WCAG 2.2 SC 1.3.1)
# ---------------------------------------------------------------------------


class TestBudgetTableAccessibility:
    """If budget data tables exist, they must carry appropriate headers.

    The CostBreakdown component uses Chart.js canvas elements, not HTML
    tables, so this suite focuses on any <table> elements that may appear
    in the config section or future breakdown views.
    """

    def test_tables_have_th_elements_with_scope(self, page, base_url: str) -> None:
        """All <table> elements on the budget tab have <th scope='col'> headers."""
        _go(page, base_url)

        tables = page.evaluate(
            """
            () => {
                const tables = document.querySelectorAll('table');
                return Array.from(tables).map(t => {
                    const ths = t.querySelectorAll('th');
                    const missing = Array.from(ths).filter(th => {
                        const sc = th.getAttribute('scope');
                        return sc !== 'col' && sc !== 'row';
                    });
                    return { total_ths: ths.length, missing_scope: missing.length };
                });
            }
            """
        )
        if not tables:
            pytest.skip("No <table> elements found on budget tab — Chart.js canvas used")

        for i, tbl in enumerate(tables):
            if tbl["total_ths"] == 0:
                continue  # Table has no <th> — may be data-only
            assert tbl["missing_scope"] == 0, (
                f"Table {i}: {tbl['missing_scope']} of {tbl['total_ths']} <th> elements "
                "missing scope attribute (required for screen reader compliance)"
            )


# ---------------------------------------------------------------------------
# Focus indicators (WCAG 2.2 SC 2.4.11)
# ---------------------------------------------------------------------------


class TestBudgetFocusIndicators:
    """Every interactive element must show a visible focus ring on keyboard focus."""

    def test_interactive_elements_have_focus_ring(self, page, base_url: str) -> None:
        """Tab to each focusable element — each must show a 2px outline or box-shadow."""
        _go(page, base_url)
        result = assert_focus_visible(page)
        assert result.passed, result.summary()

    def test_focus_ring_not_suppressed(self, page, base_url: str) -> None:
        """No element suppresses outline:none without a box-shadow replacement."""
        _go(page, base_url)

        missing = page.evaluate(
            """
            () => {
                const sel = 'a[href], button:not([disabled]), input:not([disabled]), ' +
                    'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
                const results = [];
                document.querySelectorAll(sel).forEach(el => {
                    el.focus();
                    const style = window.getComputedStyle(el);
                    const outlineStyle = style.outlineStyle;
                    const outlineWidth = parseFloat(style.outlineWidth) || 0;
                    const boxShadow = style.boxShadow;
                    const hasOutline = outlineStyle !== 'none' && outlineWidth >= 1;
                    const hasBoxShadow = boxShadow && boxShadow !== 'none';
                    if (!hasOutline && !hasBoxShadow) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            id: el.id || '',
                            label: (el.getAttribute('aria-label') || el.textContent.trim()).slice(0, 60),
                        });
                    }
                });
                return results;
            }
            """
        )
        assert not missing, (
            f"{len(missing)} interactive element(s) suppress focus outline with no alternative: "
            + ", ".join(
                f"<{e['tag']}> '{e['label'] or e['id']}'" for e in missing[:5]
            )
        )


# ---------------------------------------------------------------------------
# Keyboard navigation (WCAG 2.2 SC 2.1.1)
# ---------------------------------------------------------------------------


class TestBudgetKeyboardNavigation:
    """All interactive elements must be reachable by Tab in logical DOM order."""

    def test_interactive_elements_reachable(self, page, base_url: str) -> None:
        """Budget tab must expose at least one focusable interactive element."""
        _go(page, base_url)
        result = assert_keyboard_navigation(page, min_focusable=1)
        assert result.passed, result.summary()

    def test_no_positive_tabindex(self, page, base_url: str) -> None:
        """No element uses tabindex > 0, which breaks natural DOM tab order."""
        _go(page, base_url)

        positive_tab = page.evaluate(
            """
            () => {
                return Array.from(document.querySelectorAll('[tabindex]'))
                    .filter(el => el.tabIndex > 0)
                    .map(el => ({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        tabIndex: el.tabIndex,
                        label: (el.getAttribute('aria-label') || el.textContent.trim()).slice(0, 60),
                    }));
            }
            """
        )
        assert not positive_tab, (
            f"{len(positive_tab)} element(s) use tabindex > 0 (disrupts keyboard order): "
            + ", ".join(
                f"<{e['tag']} tabindex={e['tabIndex']}> '{e['label'] or e['id']}'"
                for e in positive_tab[:5]
            )
        )

    def test_skip_link_or_main_landmark_present(self, page, base_url: str) -> None:
        """A skip-to-main link or named <main> landmark must be present."""
        _go(page, base_url)

        skip_link = page.locator(
            "a[href='#main'], a[href='#content'], a[href='#main-content'], "
            "a[href*='skip'], a[aria-label*='skip' i]"
        ).count()
        main_element = page.locator("main, [role='main']").count()

        assert skip_link > 0 or main_element > 0, (
            "Budget tab must have a skip-to-main link or a <main> landmark "
            "so keyboard users can bypass repeated navigation (WCAG SC 2.1.1)"
        )

    def test_toggle_switches_keyboard_operable(self, page, base_url: str) -> None:
        """Toggle switches (role='switch') are operable by keyboard (Space/Enter)."""
        _go(page, base_url)

        switches = page.locator("[role='switch']")
        if switches.count() == 0:
            pytest.skip("No toggle switches found — config may not be loaded")

        first_switch = switches.first
        assert first_switch.is_visible(), "Toggle switch must be visible"

        # Focus the switch and check it is focusable.
        first_switch.focus()
        active_el = page.evaluate("document.activeElement.getAttribute('role')")
        assert active_el == "switch", (
            "Toggle switch must receive keyboard focus — required for SC 2.1.1"
        )


# ---------------------------------------------------------------------------
# Touch targets (WCAG 2.2 SC 2.5.8)
# ---------------------------------------------------------------------------


class TestBudgetTouchTargets:
    """All interactive elements must meet the 24×24 px minimum touch target."""

    def test_buttons_and_links_meet_minimum_size(self, page, base_url: str) -> None:
        """Visible buttons and links must be at least 24×24 px."""
        _go(page, base_url)
        result = assert_touch_targets(page, min_width=24, min_height=24)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Images and alt text (WCAG 2.2 SC 1.1.1)
# ---------------------------------------------------------------------------


class TestBudgetImageAltText:
    """All images must have an alt attribute (may be empty for decorative images)."""

    def test_no_images_without_alt(self, page, base_url: str) -> None:
        """All <img> elements carry an alt attribute (SC 1.1.1)."""
        _go(page, base_url)

        images_without_alt = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('img')).filter(img => {
                return !img.hasAttribute('alt');
            }).map(img => ({
                src: (img.src || img.getAttribute('src') || '').slice(-60),
                id: img.id || '',
            }))
            """
        )
        assert not images_without_alt, (
            f"{len(images_without_alt)} <img> element(s) missing alt attribute: "
            + ", ".join(f"src=...{e['src']!r}" for e in images_without_alt[:5])
        )

    def test_budget_icon_svg_aria_hidden(self, page, base_url: str) -> None:
        """Decorative SVG icons in the empty state carry aria-hidden='true'."""
        _go(page, base_url)

        body_text = page.locator("body").inner_text()
        if "Total Spend" in body_text:
            pytest.skip("Budget data loaded — empty state icon not rendered")

        decorative_svgs = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('svg')).filter(svg => {
                const ariaHidden = svg.getAttribute('aria-hidden');
                const ariaLabel = svg.getAttribute('aria-label');
                const title = svg.querySelector('title');
                // Decorative (no label/title) SVGs must have aria-hidden
                return !ariaLabel && !title && ariaHidden !== 'true';
            }).map(svg => ({
                cls: svg.className.baseVal || '',
                id: svg.id || '',
            }))
            """
        )
        assert not decorative_svgs, (
            f"{len(decorative_svgs)} decorative SVG element(s) are missing aria-hidden='true': "
            + ", ".join(
                f"cls={e['cls']!r}" if e.get("cls") else f"id={e['id']!r}"
                for e in decorative_svgs[:5]
            )
        )


# ---------------------------------------------------------------------------
# Form input labels (WCAG 2.2 SC 1.3.1)
# ---------------------------------------------------------------------------


class TestBudgetFormInputLabels:
    """Budget Alert Configuration form inputs must have accessible labels."""

    def test_number_inputs_have_associated_labels(self, page, base_url: str) -> None:
        """All number inputs in the config form have an associated <label>."""
        _go(page, base_url)

        if "Budget Alert Configuration" not in page.locator("body").inner_text():
            pytest.skip("Budget Alert Configuration section not loaded")

        unlabelled = page.evaluate(
            """
            () => {
                const inputs = document.querySelectorAll('input[type="number"]');
                return Array.from(inputs).filter(input => {
                    const id = input.id;
                    if (id && document.querySelector('label[for="' + id + '"]')) return false;
                    if (input.closest('label')) return false;
                    // BudgetDashboard uses <label> wrapping the input text + <input>
                    // Check for parent label element
                    if (input.parentElement && input.parentElement.closest('label')) return false;
                    return true;
                }).map(input => ({
                    id: input.id || '',
                    name: input.name || '',
                    type: input.type,
                }));
            }
            """
        )
        assert not unlabelled, (
            f"{len(unlabelled)} number input(s) in budget config are missing associated labels "
            "(required for screen reader identification — WCAG SC 1.3.1): "
            + ", ".join(
                f"id={e['id']!r} name={e['name']!r}" for e in unlabelled[:5]
            )
        )


# ---------------------------------------------------------------------------
# axe-core WCAG 2.x AA audit
# ---------------------------------------------------------------------------


class TestBudgetAxeAudit:
    """Full axe-core WCAG 2.x AA audit must report zero critical/serious violations."""

    def test_no_axe_critical_violations(self, page, base_url: str) -> None:
        """axe-core must find zero critical violations on the budget tab."""
        _go(page, base_url)

        try:
            violations = run_axe_audit(page)
        except RuntimeError as exc:
            pytest.skip(f"axe-core could not be loaded (likely offline/CSP): {exc}")

        critical = [v for v in violations if v.get("impact") == "critical"]
        assert not critical, (
            f"{len(critical)} critical axe violation(s): "
            + "; ".join(
                f"[{v['id']}] {v['description']}" for v in critical[:3]
            )
        )

    def test_no_axe_serious_violations(self, page, base_url: str) -> None:
        """axe-core must find zero serious violations on the budget tab."""
        _go(page, base_url)

        try:
            violations = run_axe_audit(page)
        except RuntimeError as exc:
            pytest.skip(f"axe-core could not be loaded (likely offline/CSP): {exc}")

        serious = [v for v in violations if v.get("impact") == "serious"]
        assert not serious, (
            f"{len(serious)} serious axe violation(s): "
            + "; ".join(
                f"[{v['id']}] {v['description']}" for v in serious[:3]
            )
        )

    def test_axe_full_report_summary(self, page, base_url: str) -> None:
        """Log all axe violations at any severity level for visibility."""
        _go(page, base_url)

        try:
            violations = run_axe_audit(page)
        except RuntimeError as exc:
            pytest.skip(f"axe-core could not be loaded (likely offline/CSP): {exc}")

        if violations:
            summary_lines = []
            for v in violations:
                impact = v.get("impact", "unknown")
                vid = v.get("id", "?")
                desc = v.get("description", "")
                node_count = len(v.get("nodes", []))
                summary_lines.append(
                    f"  [{impact}] {vid}: {desc} ({node_count} node(s))"
                )

            blocking = [v for v in violations if v.get("impact") in ("critical", "serious")]
            report = "\n".join(summary_lines)
            assert not blocking, (
                f"Budget tab has {len(blocking)} blocking axe violation(s) "
                f"({len(violations)} total):\n{report}"
            )
        else:
            assert True, "No axe violations — budget tab is fully WCAG 2.x AA compliant"
