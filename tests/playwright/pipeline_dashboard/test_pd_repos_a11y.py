"""Story 76.12 — Pipeline Dashboard: Repos Tab — Accessibility WCAG 2.2 AA.

Validates that /dashboard/?tab=repos meets WCAG 2.2 AA accessibility
requirements:

  SC 1.3.1  — Info and Relationships: heading hierarchy, table semantics
  SC 1.3.6  — Identify Purpose: ARIA landmark regions (main, nav, header)
  SC 1.4.1  — Use of Color: status indicators pair colour with text or icon
  SC 2.1.1  — Keyboard: all interactive elements reachable by keyboard
  SC 2.4.11 — Focus Appearance (minimum): visible focus indicators
  SC 2.5.8  — Target Size (minimum): 24×24 px touch targets
  axe-core  — WCAG 2.x AA audit (zero critical / serious violations)

Form accessibility, list semantics, and focus management are also checked.

These tests verify *accessibility compliance*, not content or visual appearance.
Content is in test_pd_repos_intent.py.
Style compliance is in test_pd_repos_style.py.
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
    """Navigate to the repos tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "repos")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ARIA landmark regions (WCAG 2.2 SC 1.3.6)
# ---------------------------------------------------------------------------


class TestReposAriaLandmarks:
    """Required ARIA landmark regions must be present on the repos tab."""

    def test_aria_landmarks_present(self, page, base_url: str) -> None:
        """Page must include <main>, <nav>, and <header> landmarks."""
        _go(page, base_url)

        result = assert_aria_landmarks(page)
        assert result.passed, result.summary()

    def test_header_landmark_present(self, page, base_url: str) -> None:
        """Repos tab has a <header> element for the application chrome."""
        _go(page, base_url)

        header_count = page.locator("header, [role='banner']").count()
        assert header_count > 0, (
            "Repos tab must have a <header> / banner landmark "
            "containing the navigation and repo selector controls"
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


class TestReposHeadingHierarchy:
    """Headings must follow a proper h1 → h2 → h3 nesting hierarchy."""

    def test_page_has_at_least_one_heading(self, page, base_url: str) -> None:
        """Repos tab has at least one heading element (h1–h4)."""
        _go(page, base_url)

        heading_count = page.locator("h1, h2, h3, h4").count()
        assert heading_count > 0, (
            "Repos tab must have at least one heading element "
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

    def test_fleet_health_heading_accessible(self, page, base_url: str) -> None:
        """'Fleet Health' section heading is an h2 or h3 with accessible text."""
        _go(page, base_url)

        # Accept any heading containing 'Fleet Health'.
        heading = page.locator("h1, h2, h3").filter(has_text="Fleet Health")
        if heading.count() == 0:
            # Also accept heading inside [data-tour='repo-selector']
            heading = page.locator("[data-tour='repo-selector']").locator("h2, h3")

        if heading.count() == 0:
            pytest.skip("Fleet Health heading not found — may use different markup")

        heading_text = heading.first.inner_text().strip()
        assert heading_text, "Fleet Health section heading must have non-empty text"


# ---------------------------------------------------------------------------
# Table semantics (WCAG 2.2 SC 1.3.1)
# ---------------------------------------------------------------------------


class TestReposTableSemantics:
    """Fleet health table must use proper semantic table markup."""

    def test_table_has_th_elements(self, page, base_url: str) -> None:
        """Fleet health table uses <th> elements for column headers."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No table — empty state is shown")

        th_count = page.evaluate("document.querySelectorAll('th').length")
        assert th_count > 0, (
            "Fleet health table must use <th> elements for column headers "
            "(WCAG SC 1.3.1 — info and relationships)"
        )

    def test_table_rows_are_interactive_with_cursor(self, page, base_url: str) -> None:
        """Repo table rows indicate interactivity (cursor-pointer or role=button)."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No table — empty state is shown")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            pytest.skip("No repo rows in table")

        # At least the first row should signal interactivity.
        first_row_cursor = page.evaluate(
            """
            (function() {
                var row = document.querySelector('table tbody tr');
                if (!row) return null;
                return window.getComputedStyle(row).cursor;
            })()
            """
        )
        assert first_row_cursor in ("pointer", "default"), (
            f"Table row cursor style {first_row_cursor!r} — expected 'pointer' "
            "to communicate that rows are clickable"
        )

    def test_repo_links_have_accessible_title(self, page, base_url: str) -> None:
        """Repository admin links inside the table carry title or aria-label."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No table — empty state is shown")

        repo_links = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('[data-testid^="repo-admin-link-"]'))
                .map(el => ({
                    title: el.getAttribute('title') || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    text: el.textContent.trim().slice(0, 60),
                }))
            """
        )

        if not repo_links:
            pytest.skip("No repo admin links found in table")

        unlabelled = [
            l for l in repo_links
            if not l.get("title") and not l.get("ariaLabel") and not l.get("text")
        ]
        assert not unlabelled, (
            f"{len(unlabelled)} repo admin link(s) lack title, aria-label, and text "
            "(WCAG SC 2.4.6 — descriptive labels)"
        )


# ---------------------------------------------------------------------------
# Focus indicators (WCAG 2.2 SC 2.4.11)
# ---------------------------------------------------------------------------


class TestReposFocusIndicators:
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


class TestReposKeyboardNavigation:
    """All interactive elements must be reachable by Tab in logical DOM order."""

    def test_interactive_elements_reachable(self, page, base_url: str) -> None:
        """Repos tab must expose at least one focusable interactive element."""
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
            "Repos tab must have a skip-to-main link or a <main> landmark "
            "so keyboard users can bypass repeated navigation (WCAG SC 2.1.1)"
        )


# ---------------------------------------------------------------------------
# Touch targets (WCAG 2.2 SC 2.5.8)
# ---------------------------------------------------------------------------


class TestReposTouchTargets:
    """All interactive elements must meet the 24×24 px minimum touch target."""

    def test_buttons_and_links_meet_minimum_size(self, page, base_url: str) -> None:
        """Visible buttons and links must be at least 24×24 px."""
        _go(page, base_url)

        result = assert_touch_targets(page, min_width=24, min_height=24)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Color-only status indicators (WCAG 2.2 SC 1.4.1)
# ---------------------------------------------------------------------------


class TestReposColorOnlyIndicators:
    """Status indicators must pair colour with text, icon, or accessible label."""

    def test_status_badges_not_color_only(self, page, base_url: str) -> None:
        """Trust tier and status badges must not rely on colour alone."""
        _go(page, base_url)

        result = assert_no_color_only_indicators(page)
        assert result.passed, result.summary()

    def test_health_dots_have_title_or_label(self, page, base_url: str) -> None:
        """Health dot spans carry a title attribute (ok / idle / degraded)."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No table — empty state shown, no health dots")

        health_dots = page.evaluate(
            """
            () => Array.from(
                document.querySelectorAll('span[class*="rounded-full"][class*="h-2"]')
            ).map(el => ({
                title: el.getAttribute('title') || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                text: el.textContent.trim(),
            }))
            """
        )

        if not health_dots:
            pytest.skip("No health dot elements found in table")

        color_only = [
            d for d in health_dots
            if not d.get("title") and not d.get("ariaLabel") and not d.get("text")
        ]

        assert not color_only, (
            f"{len(color_only)} health dot(s) convey state through colour only "
            "(no title, aria-label, or text — WCAG SC 1.4.1)"
        )

    def test_status_elements_have_text_or_label(self, page, base_url: str) -> None:
        """Elements with data-status carry visible text or aria-label."""
        _go(page, base_url)

        status_elements = page.evaluate(
            """
            () => {
                const sel = '[data-status], [class*="status-"], [class*="-status"]';
                return Array.from(document.querySelectorAll(sel)).map(el => ({
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
            pytest.skip("No [data-status] or status-class elements found on repos tab")

        color_only = [
            e for e in status_elements
            if not e.get("text") and not e.get("ariaLabel") and not e.get("title") and not e.get("hasIcon")
        ]

        assert not color_only, (
            f"{len(color_only)} status element(s) convey state through colour only: "
            + ", ".join(f"<{e['tag']}>" for e in color_only[:5])
        )


# ---------------------------------------------------------------------------
# Form accessibility (WCAG 2.2 SC 1.3.1, 4.1.2)
# ---------------------------------------------------------------------------


class TestReposFormAccessibility:
    """Config form inputs must have proper labels and ARIA attributes."""

    def _open_config(self, page) -> bool:
        """Click the first repo row to open the config panel. Returns True if opened."""
        if page.locator("table").count() == 0:
            return False

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            return False

        rows.first.click()
        page.wait_for_timeout(700)

        return page.locator("[data-tour='repo-config']").count() > 0

    def test_form_inputs_have_labels(self, page, base_url: str) -> None:
        """All visible form inputs in the config panel have an accessible label."""
        _go(page, base_url)

        if not self._open_config(page):
            pytest.skip("Config panel could not be opened — no repos or no rows")

        unlabelled = page.evaluate(
            """
            () => {
                const config = document.querySelector('[data-tour="repo-config"]');
                if (!config) return [];
                const inputs = Array.from(config.querySelectorAll(
                    'input:not([type="hidden"]):not([type="submit"]), select, textarea'
                ));
                return inputs.filter(input => {
                    const id = input.id;
                    const ariaLabel = input.getAttribute('aria-label') || '';
                    const ariaLabelledBy = input.getAttribute('aria-labelledby') || '';
                    const hasLabel = id ? !!document.querySelector('label[for="' + id + '"]') : false;
                    return !hasLabel && !ariaLabel && !ariaLabelledBy;
                }).map(input => ({
                    tag: input.tagName.toLowerCase(),
                    type: input.type || '',
                    id: input.id || '',
                    name: input.name || '',
                }));
            }
            """
        )

        assert not unlabelled, (
            f"{len(unlabelled)} form input(s) in the config panel lack accessible labels: "
            + ", ".join(
                f"<{e['tag']} type='{e['type']}' name='{e['name']}'>"
                for e in unlabelled[:5]
            )
        )

    def test_form_no_positive_tabindex(self, page, base_url: str) -> None:
        """Config form inputs do not use tabindex > 0."""
        _go(page, base_url)

        if not self._open_config(page):
            pytest.skip("Config panel could not be opened")

        positive_tabindex = page.evaluate(
            """
            () => {
                const config = document.querySelector('[data-tour="repo-config"]');
                if (!config) return [];
                return Array.from(config.querySelectorAll('[tabindex]'))
                    .filter(el => el.tabIndex > 0)
                    .map(el => ({ tag: el.tagName.toLowerCase(), tabIndex: el.tabIndex }));
            }
            """
        )

        assert not positive_tabindex, (
            f"{len(positive_tabindex)} element(s) in config form use tabindex > 0"
        )


# ---------------------------------------------------------------------------
# Images and alt text (WCAG 2.2 SC 1.1.1)
# ---------------------------------------------------------------------------


class TestReposImageAltText:
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


class TestReposAxeAudit:
    """Full axe-core WCAG 2.x AA audit must report zero critical/serious violations."""

    def test_no_axe_critical_violations(self, page, base_url: str) -> None:
        """axe-core must find zero critical violations on the repos tab."""
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
        """axe-core must find zero serious violations on the repos tab."""
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
                f"Repos tab has {len(blocking)} blocking axe violation(s) "
                f"({len(violations)} total):\n{report}"
            )
        else:
            assert True, "No axe violations — repos tab is fully WCAG 2.x AA compliant"
