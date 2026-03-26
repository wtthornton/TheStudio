"""Story 76.4 — Intent Review Tab: Accessibility WCAG 2.2 AA.

Validates that /dashboard/?tab=intent meets WCAG 2.2 AA accessibility
requirements:

  SC 1.3.1  — Info and Relationships: heading hierarchy and semantic structure
  SC 1.3.6  — Identify Purpose: ARIA landmark regions (main, nav, header)
  SC 1.1.1  — Non-text Content: images have alt text
  SC 2.1.1  — Keyboard: all interactive elements reachable by keyboard
  SC 2.4.11 — Focus Appearance (minimum): visible focus indicators
  SC 2.5.8  — Target Size (minimum): 24×24 px touch targets
  axe-core  — WCAG 2.x AA audit (zero critical / serious violations)

These tests verify *accessibility compliance*, not content or visual appearance.
Content is in test_pd_intent_intent.py.
Style compliance is in test_pd_intent_style.py.
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
    """Navigate to the intent tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "intent")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ARIA landmark regions (WCAG 2.2 SC 1.3.6)
# ---------------------------------------------------------------------------


class TestIntentAriaLandmarks:
    """Required ARIA landmark regions must be present on the intent tab.

    Screen-reader users rely on landmark regions to navigate directly to the
    primary content areas without listening to the full page.
    """

    def test_aria_landmarks_present(self, page, base_url: str) -> None:
        """Page must include <main>, <nav>, and <header> landmarks."""
        _go(page, base_url)

        result = assert_aria_landmarks(page)
        assert result.passed, result.summary()

    def test_header_landmark_present(self, page, base_url: str) -> None:
        """Intent tab has a <header> element for the application chrome."""
        _go(page, base_url)

        header_count = page.locator("header, [role='banner']").count()
        assert header_count > 0, (
            "Intent tab must have a <header> / banner landmark "
            "containing the navigation controls"
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


class TestIntentHeadingHierarchy:
    """Headings must follow a proper h1 → h2 → h3 nesting hierarchy.

    The intent tab empty state presents a heading ('No Task Selected').  An
    incorrect heading order confuses screen-reader users who rely on headings
    to navigate the page structure.
    """

    def test_page_has_at_least_one_heading(self, page, base_url: str) -> None:
        """Intent tab has at least one heading element (h1–h4)."""
        _go(page, base_url)

        heading_count = page.locator("h1, h2, h3, h4").count()
        assert heading_count > 0, (
            "Intent tab must have at least one heading element "
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
        """Intent empty state heading is accessible (non-empty text in a heading tag)."""
        _go(page, base_url)

        empty_state = page.locator("[data-testid='intent-no-task-state']")
        if empty_state.count() == 0:
            pytest.skip("Intent empty state not found — skipping heading accessibility check")

        heading = empty_state.locator("h1, h2, h3, h4").first
        if heading.count() == 0:
            # Fall back to any element with role="heading"
            heading = empty_state.locator("[role='heading']").first

        if heading.count() == 0:
            pytest.skip("No heading element found in intent empty state")

        heading_text = heading.inner_text().strip()
        assert heading_text, (
            "Intent empty state heading must have non-empty accessible text "
            "(WCAG SC 1.3.1)"
        )


# ---------------------------------------------------------------------------
# Action button accessibility
# ---------------------------------------------------------------------------


class TestIntentActionButtonsA11y:
    """CTA buttons in the intent empty state must be accessible.

    Buttons must have accessible names so screen-reader users can understand
    their purpose without visual context.
    """

    def test_go_to_pipeline_button_has_accessible_name(
        self, page, base_url: str
    ) -> None:
        """'Go to Pipeline' button has an accessible name."""
        _go(page, base_url)

        button_info = page.evaluate(
            """
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                for (const btn of buttons) {
                    const text = (btn.textContent || '').trim();
                    const aria = btn.getAttribute('aria-label') || '';
                    if (text.includes('Go to Pipeline') || aria.includes('Go to Pipeline')) {
                        return { text, ariaLabel: aria, found: true };
                    }
                }
                return { found: false };
            }
            """
        )

        if not button_info.get("found"):
            pytest.skip("'Go to Pipeline' button not found — skipping name check")

        has_name = bool(
            button_info.get("text") or button_info.get("ariaLabel")
        )
        assert has_name, (
            "'Go to Pipeline' button must have an accessible name "
            "(via text content or aria-label)"
        )

    def test_open_backlog_button_has_accessible_name(
        self, page, base_url: str
    ) -> None:
        """'Open Backlog' button has an accessible name."""
        _go(page, base_url)

        button_info = page.evaluate(
            """
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                for (const btn of buttons) {
                    const text = (btn.textContent || '').trim();
                    const aria = btn.getAttribute('aria-label') || '';
                    if (text.includes('Open Backlog') || aria.includes('Open Backlog')) {
                        return { text, ariaLabel: aria, found: true };
                    }
                }
                return { found: false };
            }
            """
        )

        if not button_info.get("found"):
            pytest.skip("'Open Backlog' button not found — skipping name check")

        has_name = bool(
            button_info.get("text") or button_info.get("ariaLabel")
        )
        assert has_name, (
            "'Open Backlog' button must have an accessible name "
            "(via text content or aria-label)"
        )

    def test_buttons_are_keyboard_focusable(self, page, base_url: str) -> None:
        """CTA buttons in the intent empty state are keyboard-focusable."""
        _go(page, base_url)

        buttons_info = page.evaluate(
            """
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                return buttons.map(btn => ({
                    text: (btn.textContent || '').trim().slice(0, 60),
                    tabIndex: btn.tabIndex,
                    disabled: btn.disabled,
                }));
            }
            """
        )

        # Filter to CTA buttons only
        cta_labels = {"Go to Pipeline", "Open Backlog"}
        cta_buttons = [
            b for b in buttons_info
            if any(label in b.get("text", "") for label in cta_labels)
        ]

        if not cta_buttons:
            pytest.skip("No CTA buttons found in intent empty state")

        non_focusable = [
            b for b in cta_buttons
            if b.get("disabled") or b.get("tabIndex", 0) < 0
        ]
        assert not non_focusable, (
            f"{len(non_focusable)} CTA button(s) are not keyboard-focusable: "
            + ", ".join(f"'{b['text']}'" for b in non_focusable)
        )


# ---------------------------------------------------------------------------
# Focus indicators (WCAG 2.2 SC 2.4.11)
# ---------------------------------------------------------------------------


class TestIntentFocusIndicators:
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


class TestIntentKeyboardNavigation:
    """All interactive elements must be reachable by Tab in logical DOM order."""

    def test_interactive_elements_reachable(self, page, base_url: str) -> None:
        """Intent tab must expose at least one focusable interactive element."""
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
            "Intent tab must have a skip-to-main link or a <main> landmark "
            "so keyboard users can bypass repeated navigation (WCAG SC 2.1.1)"
        )


# ---------------------------------------------------------------------------
# Touch targets (WCAG 2.2 SC 2.5.8)
# ---------------------------------------------------------------------------


class TestIntentTouchTargets:
    """All interactive elements must meet the 24×24 px minimum touch target."""

    def test_buttons_and_links_meet_minimum_size(self, page, base_url: str) -> None:
        """Visible buttons and links must be at least 24×24 px."""
        _go(page, base_url)

        result = assert_touch_targets(page, min_width=24, min_height=24)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Color-only status indicators (WCAG 2.2 SC 1.4.1)
# ---------------------------------------------------------------------------


class TestIntentColorOnlyIndicators:
    """Status indicators must pair colour with text, icon, or accessible label."""

    def test_status_badges_not_color_only(self, page, base_url: str) -> None:
        """Any status elements on the intent tab must not rely on colour alone."""
        _go(page, base_url)

        result = assert_no_color_only_indicators(page)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Images and alt text (WCAG 2.2 SC 1.1.1)
# ---------------------------------------------------------------------------


class TestIntentImageAltText:
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


class TestIntentAxeAudit:
    """Full axe-core WCAG 2.x AA audit must report zero critical/serious violations."""

    def test_no_axe_critical_violations(self, page, base_url: str) -> None:
        """axe-core must find zero critical violations on the intent tab."""
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
        """axe-core must find zero serious violations on the intent tab."""
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

            blocking = [
                v for v in violations if v.get("impact") in ("critical", "serious")
            ]
            report = "\n".join(summary_lines)
            assert not blocking, (
                f"Intent tab has {len(blocking)} blocking axe violation(s) "
                f"({len(violations)} total):\n{report}"
            )
        else:
            assert True, "No axe violations — intent tab is fully WCAG 2.x AA compliant"


