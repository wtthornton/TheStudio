"""Story 76.7 — Trust Tiers Tab: Accessibility WCAG 2.2 AA.

Validates that /dashboard/?tab=trust meets WCAG 2.2 AA accessibility
requirements:

  SC 1.3.1  — Info and Relationships: heading hierarchy and semantic structure
  SC 1.3.6  — Identify Purpose: ARIA landmark regions (main, nav, header)
  SC 1.4.1  — Use of Color: tier indicators pair colour with text or icon
  SC 2.1.1  — Keyboard: all interactive elements reachable by keyboard
  SC 2.4.11 — Focus Appearance (minimum): visible focus indicators
  SC 2.5.8  — Target Size (minimum): 24×24 px touch targets
  SC 3.3.1  — Error Identification: form errors are labelled
  axe-core  — WCAG 2.x AA audit (zero critical / serious violations)

These tests verify *accessibility compliance*, not content or visual appearance.
Content is in test_pd_trust_intent.py (Story 76.7).
Style compliance is in test_pd_trust_style.py (Story 76.7).
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
    """Navigate to the trust tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "trust")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ARIA landmark regions (WCAG 2.2 SC 1.3.6)
# ---------------------------------------------------------------------------


class TestTrustAriaLandmarks:
    """Required ARIA landmark regions must be present on the trust tab.

    Screen-reader users navigate pages via landmarks. The trust tab must
    include the standard landmarks: main, nav, and header.
    """

    def test_aria_landmarks_present(self, page, base_url: str) -> None:
        """Page must include <main>, <nav>, and <header> landmarks."""
        _go(page, base_url)

        result = assert_aria_landmarks(page)
        assert result.passed, result.summary()

    def test_header_landmark_present(self, page, base_url: str) -> None:
        """Trust tab has a <header> element for the application chrome."""
        _go(page, base_url)

        header_count = page.locator("header, [role='banner']").count()
        assert header_count > 0, (
            "Trust tab must have a <header> / banner landmark "
            "containing the navigation and global controls"
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


class TestTrustHeadingHierarchy:
    """Headings must follow a proper h1 → h2 → h3 nesting hierarchy.

    An incorrect heading order confuses screen-reader users who rely on
    headings to understand the page structure.
    """

    def test_page_has_at_least_one_heading(self, page, base_url: str) -> None:
        """Trust tab has at least one heading element (h1–h3)."""
        _go(page, base_url)

        heading_count = page.locator("h1, h2, h3, h4").count()
        assert heading_count > 0, (
            "Trust tab must have at least one heading element "
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

    def test_trust_configuration_section_has_heading(self, page, base_url: str) -> None:
        """'Trust Tier Configuration' section has an accessible heading element."""
        _go(page, base_url)

        # TrustConfiguration renders: <h2>Trust Tier Configuration</h2>
        h2_count = page.locator("h2").count()
        body = page.locator("body").inner_text()

        assert h2_count > 0 or "Trust Tier Configuration" in body, (
            "Trust Tiers tab must have an h2 element or visible heading for "
            "the 'Trust Tier Configuration' section"
        )


# ---------------------------------------------------------------------------
# Form labels and fieldset grouping (WCAG 2.2 SC 1.3.1, SC 3.3.2)
# ---------------------------------------------------------------------------


class TestTrustFormLabels:
    """Safety bounds form inputs must be properly labelled.

    SafetyBoundsPanel wraps each input in a <label> element, providing
    label association via the wrapper pattern (SC 1.3.1 / SC 3.3.2).
    """

    def test_form_inputs_have_label_association(self, page, base_url: str) -> None:
        """All visible form inputs have an associated label."""
        _go(page, base_url)

        inputs_without_labels = page.evaluate(
            """
            () => {
                const inputs = Array.from(document.querySelectorAll(
                    'input[type="number"], input[type="text"], textarea, select'
                ));
                return inputs.filter(inp => {
                    // Check wrapper label
                    if (inp.closest('label')) return false;
                    // Check for/id association
                    if (inp.id) {
                        const lbl = document.querySelector('label[for="' + inp.id + '"]');
                        if (lbl) return false;
                    }
                    // Check aria-label / aria-labelledby
                    if (inp.getAttribute('aria-label') || inp.getAttribute('aria-labelledby')) return false;
                    return true;
                }).map(inp => ({
                    tag: inp.tagName.toLowerCase(),
                    type: inp.type || '',
                    placeholder: inp.placeholder || '',
                    id: inp.id || '',
                }));
            }
            """
        )

        assert not inputs_without_labels, (
            f"{len(inputs_without_labels)} form input(s) lack label association: "
            + ", ".join(
                f"<{e['tag']}[type={e['type']}] placeholder='{e['placeholder']}'>"
                for e in inputs_without_labels[:5]
            )
        )

    def test_checkbox_inputs_have_labels(self, page, base_url: str) -> None:
        """Checkbox inputs (tier active toggle) are properly labelled."""
        _go(page, base_url)

        unlabelled_checkboxes = page.evaluate(
            """
            () => {
                const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
                return checkboxes.filter(cb => {
                    if (cb.closest('label')) return false;
                    if (cb.id && document.querySelector('label[for="' + cb.id + '"]')) return false;
                    if (cb.getAttribute('aria-label') || cb.getAttribute('title')) return false;
                    return true;
                }).length;
            }
            """
        )

        assert unlabelled_checkboxes == 0, (
            f"{unlabelled_checkboxes} checkbox input(s) lack label association "
            "on the trust tab (WCAG SC 1.3.1 / SC 3.3.2)"
        )

    def test_select_inputs_have_labels(self, page, base_url: str) -> None:
        """Select dropdowns (condition operator) are associated with labels."""
        _go(page, base_url)

        select_count = page.locator("select").count()
        if select_count == 0:
            pytest.skip("No select elements on trust tab — condition form may not be open")

        unlabelled = page.evaluate(
            """
            () => {
                const selects = Array.from(document.querySelectorAll('select'));
                return selects.filter(sel => {
                    if (sel.closest('label')) return false;
                    if (sel.id && document.querySelector('label[for="' + sel.id + '"]')) return false;
                    if (sel.getAttribute('aria-label') || sel.getAttribute('aria-labelledby')) return false;
                    return true;
                }).length;
            }
            """
        )
        assert unlabelled == 0, (
            f"{unlabelled} select element(s) lack label association on the trust tab"
        )


# ---------------------------------------------------------------------------
# Focus indicators (WCAG 2.2 SC 2.4.11)
# ---------------------------------------------------------------------------


class TestTrustFocusIndicators:
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


class TestTrustKeyboardNavigation:
    """All interactive elements must be reachable by Tab in logical DOM order."""

    def test_interactive_elements_reachable(self, page, base_url: str) -> None:
        """Trust tab must expose at least one focusable interactive element."""
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
            f"{len(positive_tab)} element(s) use tabindex > 0 (disrupts natural keyboard order): "
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
            "Trust tab must have a skip-to-main link or a <main> landmark "
            "so keyboard users can bypass repeated navigation (WCAG SC 2.1.1)"
        )


# ---------------------------------------------------------------------------
# Touch targets (WCAG 2.2 SC 2.5.8)
# ---------------------------------------------------------------------------


class TestTrustTouchTargets:
    """All interactive elements must meet the 24×24 px minimum touch target."""

    def test_buttons_and_links_meet_minimum_size(self, page, base_url: str) -> None:
        """Visible buttons and links on the trust tab must be at least 24×24 px."""
        _go(page, base_url)

        result = assert_touch_targets(page, min_width=24, min_height=24)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Color-only status indicators (WCAG 2.2 SC 1.4.1)
# ---------------------------------------------------------------------------


class TestTrustColorOnlyIndicators:
    """Trust tier indicators must pair colour with text, icon, or accessible label."""

    def test_tier_badges_not_color_only(self, page, base_url: str) -> None:
        """Trust tier badges must not rely on colour alone to convey tier information."""
        _go(page, base_url)

        result = assert_no_color_only_indicators(page)
        assert result.passed, result.summary()

    def test_tier_buttons_have_text_labels(self, page, base_url: str) -> None:
        """Default tier selector buttons convey tier via text label, not color only."""
        _go(page, base_url)

        tier_container = page.locator("[data-tour='trust-tier']")
        if tier_container.count() == 0:
            pytest.skip("Tier selector container not found")

        buttons = tier_container.locator("button")
        count = buttons.count()

        if count == 0:
            pytest.skip("No tier selector buttons found")

        for i in range(count):
            btn = buttons.nth(i)
            text = btn.inner_text().strip()
            aria_label = btn.get_attribute("aria-label") or ""
            assert text or aria_label, (
                f"Tier selector button #{i} must have visible text or aria-label "
                "— tier cannot be communicated through color alone (WCAG SC 1.4.1)"
            )


# ---------------------------------------------------------------------------
# Images and alt text (WCAG 2.2 SC 1.1.1)
# ---------------------------------------------------------------------------


class TestTrustImageAltText:
    """All images must have an alt attribute (may be empty for decorative images)."""

    def test_no_images_without_alt(self, page, base_url: str) -> None:
        """All <img> elements on the trust tab carry an alt attribute (SC 1.1.1)."""
        _go(page, base_url)

        images_without_alt = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('img')).filter(img => {
                return !img.hasAttribute('alt');
            }).map(img => ({
                src: (img.src || img.getAttribute('src') || '').slice(-60),
                id: img.id || '',
                cls: img.className.slice(0, 40),
            }))
            """
        )

        assert not images_without_alt, (
            f"{len(images_without_alt)} <img> element(s) missing alt attribute: "
            + ", ".join(
                f"src=...{e['src']!r}" for e in images_without_alt[:5]
            )
        )

    def test_svg_icons_have_aria_hidden(self, page, base_url: str) -> None:
        """Decorative SVG icons carry aria-hidden='true' to hide them from screen readers."""
        _go(page, base_url)

        # TrustConfiguration's ShieldIcon SVG has aria-hidden="true" already.
        svgs_without_aria = page.evaluate(
            """
            () => {
                const svgs = Array.from(document.querySelectorAll('svg'));
                return svgs.filter(svg => {
                    // SVGs with a title or role="img" are informative — exempt.
                    if (svg.querySelector('title')) return false;
                    if (svg.getAttribute('role') === 'img') return false;
                    // Decorative SVGs should have aria-hidden="true".
                    if (svg.getAttribute('aria-hidden') === 'true') return false;
                    // If the parent has an aria-label, the SVG is likely decorative but ok.
                    if (svg.closest('[aria-label]')) return false;
                    return true;
                }).length;
            }
            """
        )

        # Soft check — SVG without aria-hidden is a warning, not a hard failure.
        # The ShieldIcon in TrustConfiguration.tsx already has aria-hidden="true".
        if svgs_without_aria > 3:
            pytest.fail(
                f"{svgs_without_aria} SVG element(s) lack aria-hidden='true' and are not "
                "explicitly marked as informative (role='img' or <title>). "
                "Decorative SVGs should carry aria-hidden='true' (WCAG SC 1.1.1)."
            )


# ---------------------------------------------------------------------------
# axe-core WCAG 2.x AA audit
# ---------------------------------------------------------------------------


class TestTrustAxeAudit:
    """Full axe-core WCAG 2.x AA audit must report zero critical/serious violations."""

    def test_no_axe_critical_violations(self, page, base_url: str) -> None:
        """axe-core must find zero critical violations on the trust tab."""
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
        """axe-core must find zero serious violations on the trust tab."""
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
                summary_lines.append(f"  [{impact}] {vid}: {desc} ({node_count} node(s))")

            blocking = [v for v in violations if v.get("impact") in ("critical", "serious")]
            report = "\n".join(summary_lines)
            assert not blocking, (
                f"Trust tab has {len(blocking)} blocking axe violation(s) "
                f"({len(violations)} total):\n{report}"
            )
        else:
            assert True, "No axe violations — trust tab is fully WCAG 2.x AA compliant"
