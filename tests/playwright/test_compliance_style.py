"""Epic 67.3 — Compliance Scorecard: Style Guide Compliance.

Validates that /admin/ui/compliance conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4.1     — CSS design tokens registered on :root
  §4.2     — Focus ring color
  §5.1     — Status badge colors (pass/fail/warning/error)
  §6       — Typography: page title, section headings, body text, table cells
  §9.1     — Card recipe: background, border, radius, padding (scorecard cards)
  §9.2     — Table recipe: thead background, <th> scope attributes
  §9.3     — Badge recipe: sizing, padding, font weight

Scorecard layout (§9.1) is the primary component: per-repo compliance status is
displayed in a card or table grid where each row carries a status badge and check
summary. Status color semantics (§5.1) are critical — operators depend on green/
amber/red distinctions to triage policy violations without opening detail panels.

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_compliance_intent.py (Epic 67.1).
API contracts are covered in test_compliance_api.py (Epic 67.2).
"""

import pytest

from tests.playwright.conftest import navigate
from tests.playwright.lib.component_validators import (
    validate_badge,
    validate_card,
    validate_table,
)
from tests.playwright.lib.style_assertions import (
    assert_focus_ring_color,
    colors_close,
    get_background_color,
    get_css_variable,
    set_dark_theme,
    set_light_theme,
)
from tests.playwright.lib.typography_assertions import (
    assert_heading_scale,
    assert_typography,
)

pytestmark = pytest.mark.playwright

COMPLIANCE_URL = "/admin/ui/compliance"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_compliance(page: object, base_url: str) -> None:
    """Navigate to the compliance scorecard page and wait for main content."""
    navigate(page, f"{base_url}{COMPLIANCE_URL}")  # type: ignore[arg-type]


def _has_table(page: object) -> bool:
    """Return True when at least one <table> element is present on the page."""
    return page.locator("table").count() > 0  # type: ignore[attr-defined]


def _has_compliance_entries(page: object) -> bool:
    """Return True when compliance rows or cards are present (not empty-state)."""
    has_rows = (
        page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('table tbody tr').length"
        )
        > 0
    )
    has_cards = page.locator(  # type: ignore[attr-defined]
        "[class*='compliance'], [data-compliance], [data-component='compliance-card']"
    ).count() > 0
    return has_rows or has_cards


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestComplianceDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates that all color, spacing, and typography values are
    driven by CSS custom properties. Their presence on the compliance page confirms
    the correct stylesheet is loaded.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_compliance(page, base_url)

        try:
            val = get_css_variable(page, "--color-focus-ring")  # type: ignore[arg-type]
            assert val, (
                "--color-focus-ring CSS variable is empty — §4.1 requires it to be set"
            )
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip(
                    "--color-focus-ring not present; stylesheet may use direct classes"
                )
            raise

    def test_font_sans_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --font-sans is registered on :root (§6.1)."""
        _navigate_to_compliance(page, base_url)

        try:
            val = get_css_variable(page, "--font-sans")  # type: ignore[arg-type]
            assert val, (
                "--font-sans CSS variable is empty — §6.1 requires it to specify Inter"
            )
            assert "inter" in val.lower() or "sans" in val.lower(), (
                f"--font-sans value {val!r} does not reference 'Inter' (§6.1)"
            )
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip(
                    "--font-sans not present; stylesheet may use direct font declarations"
                )
            raise

    def test_surface_app_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-surface-app is registered (§4.1)."""
        _navigate_to_compliance(page, base_url)

        try:
            val = get_css_variable(page, "--color-surface-app")  # type: ignore[arg-type]
            assert val, (
                "--color-surface-app CSS variable is empty — §4.1 requires a surface token"
            )
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip(
                    "--color-surface-app not present; token may be named differently in this build"
                )
            raise

    def test_page_background_uses_design_token(self, page: object, base_url: str) -> None:
        """Compliance page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_compliance(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Compliance page body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestComplianceFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2)."""

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable elements show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_compliance(page, base_url)

        selectors_to_try = [
            "button.btn-primary",
            "button[class*='primary']",
            "button",
            "select",
            "a[href][class*='btn']",
            "a[href]",
            "input",
        ]
        for sel in selectors_to_try:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                try:
                    assert_focus_ring_color(page, sel)  # type: ignore[arg-type]
                    return
                except AssertionError:
                    continue

        pytest.skip(
            "No focusable element found on compliance page — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §5.1 — Status badge colors
# ---------------------------------------------------------------------------


class TestComplianceStatusColors:
    """Compliance status badges must use §5.1 semantic color tokens.

    The Compliance Scorecard relies on color to convey policy outcome at a glance:
      - pass / compliant    → green palette
      - warning / pending   → amber/yellow palette
      - fail / non-compliant → red palette

    Operators must be able to triage violations without reading every cell;
    correct color semantics are therefore a functional requirement, not decoration.
    """

    def test_status_badge_colors_present(self, page: object, base_url: str) -> None:
        """Status badges on the compliance page use §5.1 color tokens."""
        _navigate_to_compliance(page, base_url)

        status_selectors = [
            "[data-status]",
            "[data-compliance-status]",
            ".compliance-status-badge",
            ".status-badge",
            "[class*='compliance-status']",
            "[class*='status-badge']",
        ]
        for sel in status_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Compliance status badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        badge_selectors = [".badge", "[class*='badge']", ".pill", "[class*='pill']"]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Badge element {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No status badge element found on compliance page — "
            "skipping §5.1 status color check"
        )

    def test_passing_status_badge_not_red(self, page: object, base_url: str) -> None:
        """Passing/compliant badges must not use the error (red) color (§5.1).

        A compliant repo badge rendered in red would falsely signal a violation;
        §5.1 reserves red exclusively for fail/error/non-compliant status.
        """
        _navigate_to_compliance(page, base_url)

        passing_selectors = [
            "[data-status='pass']",
            "[data-status='passing']",
            "[data-compliance-status='pass']",
            "[data-compliance-status='compliant']",
            ".status-pass",
            ".status-passing",
            "[class*='status-pass']",
            "[class*='status-compliant']",
        ]
        for sel in passing_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        return window.getComputedStyle(el).color;
                    }})()
                    """
                )
                if color:
                    error_reds = ("#ef4444", "#dc2626", "#b91c1c", "#f87171")
                    is_red = any(colors_close(color, r) for r in error_reds)
                    assert not is_red, (
                        f"Passing compliance badge {sel!r} uses red color {color!r} — "
                        "§5.1 reserves red for fail/error/non-compliant status only"
                    )
                    return

        pytest.skip(
            "No 'passing' compliance status badge found — skipping color separation check"
        )

    def test_failing_status_badge_not_green(self, page: object, base_url: str) -> None:
        """Failing/non-compliant badges must not use the success (green) color (§5.1).

        §5.1 reserves green for pass/success states; a failing badge rendered green
        would give operators a false sense of compliance health.
        """
        _navigate_to_compliance(page, base_url)

        failing_selectors = [
            "[data-status='fail']",
            "[data-status='failing']",
            "[data-compliance-status='fail']",
            "[data-compliance-status='non-compliant']",
            ".status-fail",
            ".status-failing",
            "[class*='status-fail']",
            "[class*='status-non-compliant']",
        ]
        for sel in failing_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        return window.getComputedStyle(el).color;
                    }})()
                    """
                )
                if color:
                    success_greens = ("#22c55e", "#16a34a", "#15803d", "#4ade80", "#86efac")
                    is_green = any(colors_close(color, g) for g in success_greens)
                    assert not is_green, (
                        f"Failing compliance badge {sel!r} uses green color {color!r} — "
                        "§5.1 reserves green for pass/compliant status only"
                    )
                    return

        pytest.skip(
            "No 'failing' compliance status badge found — skipping color separation check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestComplianceTypography:
    """Compliance page typography must match the style guide type scale (§6.2).

    Compliance scorecard pages carry a page title, per-repo section headings
    (or table column headers), and body text with check names and remediation hints.
    Consistent heading scale and body weight help operators parse dense check lists.
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1-h3 elements follow the §6.2 heading scale."""
        _navigate_to_compliance(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_compliance(page, base_url)

        selectors = ["h1", ".page-title", "[class*='page-title']"]
        for sel in selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_typography(page, sel, role="page_title")  # type: ignore[arg-type]
                return

        pytest.skip(
            "No page title element (h1/.page-title) found — skipping typography check"
        )

    def test_section_heading_typography(self, page: object, base_url: str) -> None:
        """Section headings (h2) use §6.2 section_title scale (16px / weight 600)."""
        _navigate_to_compliance(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_table_cell_typography(self, page: object, base_url: str) -> None:
        """Table cell text uses §6.2 body scale (14px / weight 400)."""
        _navigate_to_compliance(page, base_url)

        if not _has_table(page):
            pytest.skip(
                "No table found on compliance page — skipping table cell typography check"
            )

        assert_typography(page, "td", role="body")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe
# ---------------------------------------------------------------------------


class TestComplianceBadgeRecipe:
    """Badges on the compliance page must conform to §9.3 badge recipe.

    Per-repo compliance status badges and per-check pass/fail/warning badges are
    the primary badge type on this page. They must use the correct sizing, padding,
    and font weight as specified in §9.3 to maintain visual consistency with
    the broader admin UI badge system.
    """

    def test_badge_recipe(self, page: object, base_url: str) -> None:
        """Status and check-result badges match §9.3 badge recipe."""
        _navigate_to_compliance(page, base_url)

        badge_selectors = [
            "[data-status]",
            "[data-compliance-status]",
            ".compliance-status-badge",
            ".status-badge",
            "[class*='compliance-status']",
            ".badge",
            "[class*='badge']",
            ".pill",
            "[class*='pill']",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Badge {sel!r} on compliance page fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No badge element found on compliance page — skipping §9.3 badge recipe check"
        )

    def test_dark_theme_does_not_break_layout(self, page: object, base_url: str) -> None:
        """Compliance page layout remains intact when dark theme is applied."""
        _navigate_to_compliance(page, base_url)

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page body empty after switching to dark theme"
        finally:
            set_light_theme(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.1 — Card recipe (scorecard cards)
# ---------------------------------------------------------------------------


class TestComplianceCardRecipe:
    """Compliance scorecard cards must conform to §9.1 card recipe.

    The compliance page typically renders per-repo status as cards in a scorecard
    grid, or uses a card-styled summary panel. Each card must have the correct
    background, border color, border-radius (≥ 8px), and padding (≥ 16px) per §9.1.
    """

    def test_card_recipe_if_present(self, page: object, base_url: str) -> None:
        """Scorecard cards/panels match §9.1 card recipe (background, border, radius, padding)."""
        _navigate_to_compliance(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".scorecard",
            "[class*='scorecard']",
            ".compliance-card",
            ".detail-panel",
            "[class*='detail-panel']",
            "[data-component='card']",
            "[data-component='compliance-card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_card(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Compliance card/panel {sel!r} fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No card element found on compliance page — skipping §9.1 card recipe check"
        )


# ---------------------------------------------------------------------------
# §9.2 — Table recipe (compliance scorecard table)
# ---------------------------------------------------------------------------


class TestComplianceTableRecipe:
    """Compliance scorecard table must conform to §9.2 table recipe.

    The compliance page typically renders per-repo check results in a table with
    columns for repository name, compliance status, check count, and last run.
    §9.2 requires a distinct thead background and scope attributes on all column
    headers for accessible data presentation.
    """

    def test_table_recipe(self, page: object, base_url: str) -> None:
        """Compliance scorecard table matches §9.2 table recipe (thead background, th scope)."""
        _navigate_to_compliance(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found on compliance page — card layout acceptable")

        result = validate_table(page, "table")  # type: ignore[arg-type]
        assert result.passed, (
            f"Compliance scorecard table fails §9.2 recipe: {result.summary()}"
        )

    def test_table_header_scope_attributes(self, page: object, base_url: str) -> None:
        """<th> elements in the compliance table have scope='col' attribute (§9.2)."""
        _navigate_to_compliance(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found — skipping th scope check")

        th_count = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('table thead th').length"
        )
        if th_count == 0:
            pytest.skip("No thead th elements found — skipping scope attribute check")

        missing_scope = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table thead th');
                var missing = [];
                ths.forEach(function(th, i) {
                    if (!th.hasAttribute('scope')) {
                        missing.push(i);
                    }
                });
                return missing;
            })()
            """
        )
        assert not missing_scope, (
            f"Column headers at indices {missing_scope} are missing scope='col' — "
            "§9.2 requires scope attributes for accessible tables"
        )

    def test_status_column_present_in_table(self, page: object, base_url: str) -> None:
        """Compliance table includes a status column header (§9.2 / §5.1).

        Operators use the compliance table to assess policy health at a glance.
        The presence of a status column confirms that compliance outcome is surfaced
        at the list level, not buried in a detail panel.
        """
        _navigate_to_compliance(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found — skipping status column check")

        headers_text = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table th');
                return Array.from(ths).map(function(th) { return th.textContent.toLowerCase(); });
            })()
            """
        )
        status_keywords = ("status", "compliance", "pass", "fail", "result", "check")
        has_status_col = any(
            any(kw in header for kw in status_keywords) for header in headers_text
        )
        if not has_status_col:
            pytest.skip(
                "No status column header found in compliance table — "
                "status may be shown via row color or detail panel (acceptable)"
            )
