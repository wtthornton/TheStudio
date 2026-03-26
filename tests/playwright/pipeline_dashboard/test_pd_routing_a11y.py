"""Story 76.5 — Routing Review Tab: Accessibility WCAG 2.2 AA.

Validates that /dashboard/?tab=routing meets WCAG 2.2 AA accessibility
requirements:

  SC 1.3.1  — Info and Relationships: heading hierarchy and semantic structure
  SC 1.3.6  — Identify Purpose: ARIA landmark regions (main, nav, header)
  SC 1.4.1  — Use of Color: status indicators pair colour with text or icon
  SC 2.1.1  — Keyboard: all interactive elements reachable by keyboard
  SC 2.4.11 — Focus Appearance (minimum): visible focus indicators
  SC 2.5.8  — Target Size (minimum): 24×24 px touch targets
  axe-core  — WCAG 2.x AA audit (zero critical / serious violations)

These tests verify *accessibility compliance*, not content or visual appearance.
Content is in test_pd_routing_intent.py (Story 76.5).
Style compliance is in test_pd_routing_style.py (Story 76.5).
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
    """Navigate to the routing tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "routing")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ARIA landmark regions (WCAG 2.2 SC 1.3.6)
# ---------------------------------------------------------------------------


class TestRoutingAriaLandmarks:
    """Required ARIA landmark regions must be present on the routing tab.

    Screen-reader users rely on landmark regions to navigate directly to the
    primary content areas without listening to the full page.
    """

    def test_aria_landmarks_present(self, page, base_url: str) -> None:
        """Page must include <main>, <nav>, and <header> landmarks."""
        _go(page, base_url)

        result = assert_aria_landmarks(page)
        assert result.passed, result.summary()

    def test_header_landmark_present(self, page, base_url: str) -> None:
        """Routing tab has a <header> element for the application chrome."""
        _go(page, base_url)

        header_count = page.locator("header, [role='banner']").count()
        assert header_count > 0, (
            "Routing tab must have a <header> / banner landmark "
            "containing the navigation and import controls"
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


class TestRoutingHeadingHierarchy:
    """Headings must follow a proper h1 → h2 → h3 nesting hierarchy.

    An incorrect heading order confuses screen-reader users who rely on
    headings to understand the page structure.
    """

    def test_page_has_at_least_one_heading(self, page, base_url: str) -> None:
        """Routing tab has at least one heading element (h1–h3)."""
        _go(page, base_url)

        heading_count = page.locator("h1, h2, h3, h4").count()
        assert heading_count > 0, (
            "Routing tab must have at least one heading element "
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

    def test_empty_state_heading_accessible(self, page, base_url: str) -> None:
        """Routing empty state heading has accessible text."""
        _go(page, base_url)

        if page.locator("[data-testid='routing-no-task-state']").count() == 0:
            pytest.skip("Routing tab not in empty state")

        heading = page.locator(
            "[data-testid='routing-no-task-state'] h1, "
            "[data-testid='routing-no-task-state'] h2, "
            "[data-testid='routing-no-task-state'] h3"
        )

        if heading.count() == 0:
            # Fall back: check for any heading with 'No Task Selected' text.
            all_headings = page.locator("h1, h2, h3")
            for i in range(all_headings.count()):
                h = all_headings.nth(i)
                if "No Task Selected" in (h.inner_text() or ""):
                    assert h.inner_text().strip(), (
                        "Empty state heading must have non-empty accessible text"
                    )
                    return
            pytest.skip("Empty state heading element not found")

        heading_text = heading.first.inner_text().strip()
        assert heading_text, "Routing empty state heading must have non-empty accessible text"

    def test_buttons_have_accessible_names(self, page, base_url: str) -> None:
        """All buttons on the routing tab have accessible names."""
        _go(page, base_url)

        unnamed = page.evaluate(
            """
            () => {
                return Array.from(document.querySelectorAll('button')).filter(btn => {
                    const text = btn.textContent.trim();
                    const ariaLabel = btn.getAttribute('aria-label') || '';
                    const ariaLabelledBy = btn.getAttribute('aria-labelledby') || '';
                    const title = btn.getAttribute('title') || '';
                    return !text && !ariaLabel && !ariaLabelledBy && !title;
                }).map(btn => ({
                    id: btn.id || '',
                    cls: btn.className.slice(0, 50),
                }));
            }
            """
        )

        assert not unnamed, (
            f"{len(unnamed)} button(s) have no accessible name (text, aria-label, or title): "
            + ", ".join(
                f"<button id={e['id']!r} class={e['cls']!r}>" for e in unnamed[:5]
            )
        )


# ---------------------------------------------------------------------------
# Focus indicators (WCAG 2.2 SC 2.4.11)
# ---------------------------------------------------------------------------


class TestRoutingFocusIndicators:
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


class TestRoutingKeyboardNavigation:
    """All interactive elements must be reachable by Tab in logical DOM order."""

    def test_interactive_elements_reachable(self, page, base_url: str) -> None:
        """Routing tab must expose at least one focusable interactive element."""
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
            "Routing tab must have a skip-to-main link or a <main> landmark "
            "so keyboard users can bypass repeated navigation (WCAG SC 2.1.1)"
        )


# ---------------------------------------------------------------------------
# Touch targets (WCAG 2.2 SC 2.5.8)
# ---------------------------------------------------------------------------


class TestRoutingTouchTargets:
    """All interactive elements must meet the 24×24 px minimum touch target."""

    def test_buttons_and_links_meet_minimum_size(self, page, base_url: str) -> None:
        """Visible buttons and links must be at least 24×24 px."""
        _go(page, base_url)

        result = assert_touch_targets(page, min_width=24, min_height=24)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Color-only status indicators (WCAG 2.2 SC 1.4.1)
# ---------------------------------------------------------------------------


class TestRoutingColorOnlyIndicators:
    """Status indicators must pair colour with text, icon, or accessible label."""

    def test_status_badges_not_color_only(self, page, base_url: str) -> None:
        """Routing status badges must not rely on colour alone."""
        _go(page, base_url)

        result = assert_no_color_only_indicators(page)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Images and alt text (WCAG 2.2 SC 1.1.1)
# ---------------------------------------------------------------------------


class TestRoutingImageAltText:
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


# ---------------------------------------------------------------------------
# axe-core WCAG 2.x AA audit
# ---------------------------------------------------------------------------


class TestRoutingAxeAudit:
    """Full axe-core WCAG 2.x AA audit must report zero critical/serious violations."""

    def test_no_axe_critical_violations(self, page, base_url: str) -> None:
        """axe-core must find zero critical violations on the routing tab."""
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
        """axe-core must find zero serious violations on the routing tab."""
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
                f"Routing tab has {len(blocking)} blocking axe violation(s) "
                f"({len(violations)} total):\n{report}"
            )
        else:
            assert True, "No axe violations — routing tab is fully WCAG 2.x AA compliant"
