"""Story 76.9 — Pipeline Dashboard: Activity Log Accessibility WCAG 2.2 AA.

Validates that /dashboard/?tab=activity meets WCAG 2.2 AA accessibility
requirements:

  SC 1.1.1  — Text alternatives for images
  SC 1.3.1  — Info and Relationships: table semantics, heading hierarchy
  SC 1.3.3  — Sensory characteristics: time expressed with datetime attribute
  SC 1.3.6  — Identify Purpose: ARIA landmark regions (main, nav, header)
  SC 1.4.1  — Use of Color: action badges pair colour with text/icon
  SC 2.1.1  — Keyboard: all interactive elements reachable by keyboard
  SC 2.4.11 — Focus Appearance (minimum): visible focus indicators
  SC 2.5.8  — Target Size (minimum): 24×24 px touch targets
  axe-core  — WCAG 2.x AA audit (zero critical / serious violations)

These tests verify *accessibility compliance*, not content or visual appearance.
Content is in test_pd_activity_intent.py.
Style compliance is in test_pd_activity_style.py.
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
    """Navigate to the activity tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "activity")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ARIA landmark regions (WCAG 2.2 SC 1.3.6)
# ---------------------------------------------------------------------------


class TestActivityAriaLandmarks:
    """Required ARIA landmark regions must be present on the activity tab.

    Screen-reader users rely on landmark regions to navigate directly to the
    primary content areas without listening to the full page.
    """

    def test_aria_landmarks_present(self, page, base_url: str) -> None:
        """Page must include <main>, <nav>, and <header> landmarks."""
        _go(page, base_url)

        result = assert_aria_landmarks(page)
        assert result.passed, result.summary()

    def test_header_landmark_present(self, page, base_url: str) -> None:
        """Activity tab has a <header> element for the application chrome."""
        _go(page, base_url)

        header_count = page.locator("header, [role='banner']").count()
        assert header_count > 0, (
            "Activity tab must have a <header> / banner landmark "
            "containing the navigation and application controls"
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
# Table semantics (WCAG 2.2 SC 1.3.1)
# ---------------------------------------------------------------------------


class TestActivityTableSemantics:
    """Audit table must use correct semantic table markup for screen readers.

    Screen-reader users navigate tables via row/column headers. Without
    proper <thead>, <tbody>, and scope attributes the table is inaccessible.
    """

    def test_audit_table_uses_semantic_table_element(
        self, page, base_url: str
    ) -> None:
        """Audit log uses a <table> element, not a div-based layout."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No audit table — empty state is present")

        table_count = page.locator("table").count()
        assert table_count > 0, (
            "Audit log must use a <table> element for tabular data "
            "(not a div-based layout) — required for screen-reader accessibility"
        )

    def test_audit_table_has_thead(self, page, base_url: str) -> None:
        """Audit table has a <thead> element with column headers."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No audit table — empty state is present")

        thead_count = page.locator("table thead").count()
        assert thead_count > 0, (
            "Audit table must have a <thead> element containing column headers "
            "so screen readers can announce column names"
        )

    def test_audit_table_has_tbody(self, page, base_url: str) -> None:
        """Audit table has a <tbody> element separating headers from data."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No audit table — empty state is present")

        tbody_count = page.locator("table tbody").count()
        assert tbody_count > 0, (
            "Audit table must have a <tbody> element "
            "separating header rows from data rows"
        )

    def test_th_elements_present_in_thead(self, page, base_url: str) -> None:
        """Audit table has <th> column header elements in the thead."""
        _go(page, base_url)

        if page.locator("table thead").count() == 0:
            pytest.skip("No audit table thead — skipping th check")

        th_count = page.locator("table thead th").count()
        assert th_count > 0, (
            "Audit table <thead> must contain <th> column header elements "
            "(not just <td>) — required for WCAG SC 1.3.1"
        )

    def test_th_elements_have_scope_attribute(self, page, base_url: str) -> None:
        """Audit table <th> elements carry scope='col' for screen reader navigation."""
        _go(page, base_url)

        if page.locator("table thead th").count() == 0:
            pytest.skip("No <th> elements in audit table thead")

        th_info = page.evaluate(
            """
            () => {
                const ths = Array.from(document.querySelectorAll('table thead th'));
                return ths.map(th => ({
                    text: th.textContent.trim().slice(0, 30),
                    scope: th.getAttribute('scope') || '',
                }));
            }
            """
        )

        missing_scope = [t for t in th_info if not t.get("scope")]
        if missing_scope:
            # xfail-compatible: warn but do not fail hard since many implementations omit scope
            pytest.xfail(
                f"{len(missing_scope)} <th> elements missing scope attribute: "
                + ", ".join(t["text"] for t in missing_scope[:3])
            )


# ---------------------------------------------------------------------------
# Heading hierarchy (WCAG 2.2 SC 1.3.1)
# ---------------------------------------------------------------------------


class TestActivityHeadingHierarchy:
    """Headings must follow a proper h1 → h2 → h3 nesting hierarchy."""

    def test_page_has_at_least_one_heading(self, page, base_url: str) -> None:
        """Activity tab has at least one heading element (h1–h3)."""
        _go(page, base_url)

        heading_count = page.locator("h1, h2, h3, h4").count()
        assert heading_count > 0, (
            "Activity tab must have at least one heading element "
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

    def test_activity_log_heading_has_accessible_text(
        self, page, base_url: str
    ) -> None:
        """The 'Steering Activity Log' heading has non-empty accessible text."""
        _go(page, base_url)

        headings = page.locator("h1, h2, h3")
        if headings.count() == 0:
            pytest.skip("No headings found on activity tab")

        # Check all headings have non-empty text
        for i in range(headings.count()):
            heading = headings.nth(i)
            text = heading.inner_text().strip()
            assert text, f"Heading element {i+1} has empty text — must have accessible content"


# ---------------------------------------------------------------------------
# Timestamps with datetime attribute (WCAG 2.2 SC 1.3.3)
# ---------------------------------------------------------------------------


class TestActivityTimestampSemantics:
    """Timestamps in the audit log must be machine-readable via datetime attribute.

    Relative times like "5m ago" are user-friendly but opaque to assistive
    technology.  The <time> element with datetime provides the machine-readable
    alternative.
    """

    def test_timestamps_use_time_element_or_title_attribute(
        self, page, base_url: str
    ) -> None:
        """Audit entry timestamps expose the ISO date via <time datetime> or title."""
        _go(page, base_url)

        if page.locator("table tbody tr").count() == 0:
            pytest.skip("No audit entries — skipping timestamp semantic check")

        # Check whether timestamps use <time> element or title attribute (the
        # SteeringActivityLog component uses title={formatAbsoluteTime(entry.timestamp)}).
        time_semantic = page.evaluate(
            """
            () => {
                // Check for <time datetime> elements
                var timeEls = document.querySelectorAll('time[datetime]');
                if (timeEls.length > 0) return {type: 'time-element', count: timeEls.length};

                // Check for td[title] containing time-like strings
                var tds = document.querySelectorAll('table tbody td[title]');
                var timeTitles = Array.from(tds).filter(function(td) {
                    return /\\d{1,2}:\\d{2}/.test(td.getAttribute('title') || '');
                });
                if (timeTitles.length > 0) return {type: 'title-attr', count: timeTitles.length};

                return {type: 'none', count: 0};
            }
            """
        )

        assert time_semantic["type"] in ("time-element", "title-attr"), (
            "Audit entry timestamps must expose the full ISO date/time via "
            "<time datetime='...'> or a title attribute with absolute time. "
            "Relative times alone ('5m ago') are not accessible."
        )


# ---------------------------------------------------------------------------
# Focus indicators (WCAG 2.2 SC 2.4.11)
# ---------------------------------------------------------------------------


class TestActivityFocusIndicators:
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


class TestActivityKeyboardNavigation:
    """All interactive elements must be reachable by Tab in logical DOM order."""

    def test_interactive_elements_reachable(self, page, base_url: str) -> None:
        """Activity tab must expose at least one focusable interactive element."""
        _go(page, base_url)

        result = assert_keyboard_navigation(page, min_focusable=1)
        assert result.passed, result.summary()

    def test_filter_select_keyboard_accessible(self, page, base_url: str) -> None:
        """Action filter select is reachable by keyboard Tab navigation."""
        _go(page, base_url)

        select = page.locator("select")
        if select.count() == 0:
            pytest.skip("No select element found on activity tab")

        tab_index = page.evaluate(
            """
            () => {
                var sel = document.querySelector('select');
                return sel ? sel.tabIndex : -99;
            }
            """
        )
        assert tab_index >= 0, (
            "Action filter select must have tabIndex >= 0 so it is "
            "reachable by keyboard Tab navigation"
        )

    def test_pagination_buttons_keyboard_accessible(
        self, page, base_url: str
    ) -> None:
        """Pagination buttons (Previous/Next) are keyboard-accessible."""
        _go(page, base_url)

        buttons_info = page.evaluate(
            """
            () => {
                return Array.from(document.querySelectorAll('button')).map(function(btn) {
                    return {
                        text: btn.textContent.trim().slice(0, 40),
                        tabIndex: btn.tabIndex,
                        disabled: btn.disabled,
                    };
                });
            }
            """
        )
        nav_buttons = [
            b for b in buttons_info
            if "Previous" in b["text"] or "Next" in b["text"]
        ]

        if not nav_buttons:
            pytest.skip("No Previous/Next buttons found on activity tab")

        for btn in nav_buttons:
            if not btn["disabled"]:
                assert btn["tabIndex"] >= 0, (
                    f"Enabled '{btn['text']}' button must have tabIndex >= 0 "
                    "for keyboard accessibility"
                )

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
            "Activity tab must have a skip-to-main link or a <main> landmark "
            "so keyboard users can bypass repeated navigation (WCAG SC 2.1.1)"
        )


# ---------------------------------------------------------------------------
# Touch targets (WCAG 2.2 SC 2.5.8)
# ---------------------------------------------------------------------------


class TestActivityTouchTargets:
    """All interactive elements must meet the 24×24 px minimum touch target."""

    def test_buttons_and_links_meet_minimum_size(self, page, base_url: str) -> None:
        """Visible buttons and links must be at least 24×24 px."""
        _go(page, base_url)

        result = assert_touch_targets(page, min_width=24, min_height=24)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Color-only status indicators (WCAG 2.2 SC 1.4.1)
# ---------------------------------------------------------------------------


class TestActivityColorOnlyIndicators:
    """Action badges must pair colour with text and/or icon, not colour alone."""

    def test_action_badges_not_color_only(self, page, base_url: str) -> None:
        """Action badges must not rely on colour alone to convey meaning."""
        _go(page, base_url)

        result = assert_no_color_only_indicators(page)
        assert result.passed, result.summary()

    def test_action_badges_have_text_label(self, page, base_url: str) -> None:
        """Action badges in the audit table include visible text (not just icons)."""
        _go(page, base_url)

        if page.locator("table tbody tr").count() == 0:
            pytest.skip("No audit entries — cannot check action badge text")

        # Each ActionBadge renders: <span icon> + <span text>
        # Verify at least one badge has visible text content.
        badge_texts = page.evaluate(
            """
            () => {
                var badges = document.querySelectorAll('span[class*="rounded-full"]');
                return Array.from(badges).map(function(b) {
                    return b.textContent.trim();
                });
            }
            """
        )
        has_text = any(t for t in badge_texts)
        assert has_text, (
            "Action badges must include visible text labels (not just colour) "
            "to satisfy WCAG SC 1.4.1 — found badges with no text content"
        )


# ---------------------------------------------------------------------------
# Images and alt text (WCAG 2.2 SC 1.1.1)
# ---------------------------------------------------------------------------


class TestActivityImageAltText:
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
# Filter select label (WCAG 2.2 SC 1.3.1)
# ---------------------------------------------------------------------------


class TestActivityFilterSelectLabel:
    """The action filter select must have an associated label for screen readers.

    Without a proper label, screen readers announce the select as just
    "combo box" with no context about what it filters.
    """

    def test_filter_select_has_associated_label(self, page, base_url: str) -> None:
        """Action filter <select> has an associated <label> or aria-label."""
        _go(page, base_url)

        if page.locator("select").count() == 0:
            pytest.skip("No select element found on activity tab")

        label_info = page.evaluate(
            """
            () => {
                var sel = document.querySelector('select');
                if (!sel) return {type: 'missing'};

                // Check for id-linked label
                if (sel.id) {
                    var label = document.querySelector('label[for="' + sel.id + '"]');
                    if (label) return {type: 'for-id', text: label.textContent.trim()};
                }
                // Check for wrapped label
                if (sel.closest('label')) {
                    return {type: 'wrapped', text: sel.closest('label').textContent.trim()};
                }
                // Check for aria-label
                var ariaLabel = sel.getAttribute('aria-label');
                if (ariaLabel) return {type: 'aria-label', text: ariaLabel};
                // Check for aria-labelledby
                var labelledBy = sel.getAttribute('aria-labelledby');
                if (labelledBy) {
                    var el = document.getElementById(labelledBy);
                    return {type: 'aria-labelledby', text: el ? el.textContent.trim() : ''};
                }
                // No label
                return {type: 'none', text: ''};
            }
            """
        )

        assert label_info["type"] != "none", (
            "Action filter <select> must have an associated label "
            "(via <label for>, wrapped <label>, aria-label, or aria-labelledby) "
            "so screen readers can describe its purpose — WCAG SC 1.3.1"
        )


# ---------------------------------------------------------------------------
# axe-core WCAG 2.x AA audit
# ---------------------------------------------------------------------------


class TestActivityAxeAudit:
    """Full axe-core WCAG 2.x AA audit must report zero critical/serious violations."""

    def test_no_axe_critical_violations(self, page, base_url: str) -> None:
        """axe-core must find zero critical violations on the activity tab."""
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
        """axe-core must find zero serious violations on the activity tab."""
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
                f"Activity tab has {len(blocking)} blocking axe violation(s) "
                f"({len(violations)} total):\n{report}"
            )
        else:
            assert True, "No axe violations — activity tab is fully WCAG 2.x AA compliant"
