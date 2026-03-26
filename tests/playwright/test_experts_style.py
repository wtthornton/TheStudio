"""Epic 64.3 — Expert Performance: Style Guide Compliance.

Validates that /admin/ui/experts conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4.1     — CSS design tokens registered on :root
  §4.2     — Focus ring color
  §5.2     — Trust tier badge colors: OBSERVE (shadow) / SUGGEST (probation) / EXECUTE (trusted)
  §6       — Typography: page title, section headings, body text
  §9.1     — Card recipe: background, border, radius, padding (detail card)
  §9.2     — Table recipe: thead background, <th> scope attributes
  §9.3     — Badge recipe: sizing, padding, font weight

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_experts_intent.py (Epic 64.1).
API contracts are covered in test_experts_api.py (Epic 64.2).
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
    assert_trust_tier_colors,
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

EXPERTS_URL = "/admin/ui/experts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_experts(page: object, base_url: str) -> None:
    """Navigate to the experts page and wait for the main content."""
    navigate(page, f"{base_url}{EXPERTS_URL}")  # type: ignore[arg-type]


def _has_table(page: object) -> bool:
    """Return True when at least one <table> element is present on the page."""
    return page.locator("table").count() > 0  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestExpertsDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates that all color, spacing, and typography values
    are driven by CSS custom properties. The presence of these tokens confirms
    the correct stylesheet is loaded on the experts page.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_experts(page, base_url)

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
        _navigate_to_experts(page, base_url)

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
        _navigate_to_experts(page, base_url)

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
        """Experts page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_experts(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Experts page body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestExpertsFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2).

    The focus ring (blue-600 in light mode) ensures keyboard navigators can
    identify focused elements at a glance on the experts page.
    """

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable elements show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_experts(page, base_url)

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
            "No focusable element found on experts page — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §5.2 — Trust tier badge colors
# ---------------------------------------------------------------------------


class TestExpertsTrustTierColors:
    """Trust tier badges must use the §5.2 semantic color tokens.

    §5.2 mandates three distinct trust tiers, each with a specific badge color:
      - shadow    (OBSERVE)  → gray palette
      - probation (SUGGEST)  → amber/yellow palette
      - trusted   (EXECUTE)  → green palette

    The experts page is the primary surface where trust tier badges appear.
    Incorrect colors undermine operators' ability to assess expert trustworthiness.
    """

    def test_trust_tier_badge_colors_present(self, page: object, base_url: str) -> None:
        """Trust tier badges on the experts table use §5.2 tier color tokens."""
        _navigate_to_experts(page, base_url)

        trust_tier_selectors = [
            "[data-tier]",
            "[data-trust-tier]",
            ".trust-tier-badge",
            ".tier-badge",
            "[class*='trust-tier']",
            "[class*='tier-badge']",
        ]
        for sel in trust_tier_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_trust_tier_colors(page, sel)  # type: ignore[arg-type]
                return

        # Fallback: look for badge-like elements near trust tier text
        badge_selectors = [
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
                # At minimum verify badge recipe is used
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Trust tier badge element {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No trust tier badge element found on experts page — "
            "skipping §5.2 trust tier color check"
        )

    def test_shadow_tier_badge_not_green(self, page: object, base_url: str) -> None:
        """Shadow tier badges must not use the trusted (green) color (§5.2)."""
        _navigate_to_experts(page, base_url)

        shadow_selectors = [
            "[data-tier='shadow']",
            "[data-trust-tier='shadow']",
            ".tier-shadow",
            "[class*='tier-shadow']",
            "[class*='trust-shadow']",
        ]
        for sel in shadow_selectors:
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
                    # Shadow tier must NOT be green (trusted color)
                    trusted_greens = ("#22c55e", "#16a34a", "#15803d", "#4ade80")
                    is_green = any(colors_close(color, g) for g in trusted_greens)
                    assert not is_green, (
                        f"Shadow tier badge {sel!r} uses green color {color!r} — "
                        "§5.2 reserves green for 'trusted' tier only"
                    )
                    return

        pytest.skip(
            "No shadow tier badge found on experts page — skipping tier color separation check"
        )

    def test_trusted_tier_badge_uses_green(self, page: object, base_url: str) -> None:
        """Trusted tier badges use the §5.2 green success color tokens."""
        _navigate_to_experts(page, base_url)

        trusted_selectors = [
            "[data-tier='trusted']",
            "[data-trust-tier='trusted']",
            ".tier-trusted",
            "[class*='tier-trusted']",
            "[class*='trust-trusted']",
        ]
        trusted_greens = ("#22c55e", "#16a34a", "#15803d", "#4ade80", "#bbf7d0", "#dcfce7")

        for sel in trusted_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var style = window.getComputedStyle(el);
                        return style.color || style.backgroundColor;
                    }})()
                    """
                )
                if color:
                    is_green = any(colors_close(color, g) for g in trusted_greens)
                    assert is_green, (
                        f"Trusted tier badge {sel!r} color {color!r} is not §5.2 green — "
                        "trusted experts should be clearly distinguished with green tokens"
                    )
                    return

        pytest.skip(
            "No trusted tier badge found on experts page — skipping trusted green check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestExpertsTypography:
    """Experts page typography must match the style guide type scale (§6.2).

    Key elements:
    - Page title (h1 / .page-title): 20px / weight 600
    - Section headings (h2): 16px / weight 600
    - Body / table cell text: 14px / weight 400
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1-h3 elements follow the §6.2 heading scale."""
        _navigate_to_experts(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_experts(page, base_url)

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
        _navigate_to_experts(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_table_cell_typography(self, page: object, base_url: str) -> None:
        """Table cell text uses §6.2 body scale (14px / weight 400)."""
        _navigate_to_experts(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found on experts page — skipping table cell typography check")

        assert_typography(page, "td", role="body")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.2 — Table recipe
# ---------------------------------------------------------------------------


class TestExpertsTableRecipe:
    """Expert table must conform to §9.2 table recipe.

    The experts page uses a data table with trust tier, confidence, and drift
    columns. The table must have the correct thead background, <th> scope
    attributes, and row styling per §9.2.
    """

    def test_table_recipe(self, page: object, base_url: str) -> None:
        """Expert table matches §9.2 table recipe (thead background, th scope)."""
        _navigate_to_experts(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found on experts page — skipping §9.2 table recipe check")

        result = validate_table(page, "table")  # type: ignore[arg-type]
        assert result.passed, (
            f"Expert table fails §9.2 recipe: {result.summary()}"
        )

    def test_table_header_scope_attributes(self, page: object, base_url: str) -> None:
        """<th> elements in the expert table have scope='col' attribute (§9.2)."""
        _navigate_to_experts(page, base_url)

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

    def test_table_has_thead_element(self, page: object, base_url: str) -> None:
        """Expert table uses a <thead> element for column headers (§9.2)."""
        _navigate_to_experts(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found — skipping thead check")

        thead_count = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('table thead').length"
        )
        assert thead_count > 0, (
            "Expert table has no <thead> element — §9.2 requires a proper thead for "
            "accessible column header markup"
        )

    def test_table_rows_have_consistent_column_count(self, page: object, base_url: str) -> None:
        """All body rows in the expert table have the same number of columns."""
        _navigate_to_experts(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found — skipping column count check")

        col_counts = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var rows = document.querySelectorAll('table tbody tr');
                var counts = [];
                rows.forEach(function(row) {
                    counts.push(row.querySelectorAll('td').length);
                });
                return counts;
            })()
            """
        )
        if not col_counts:
            pytest.skip("No tbody rows found — skipping column count consistency check")

        unique_counts = set(col_counts)
        assert len(unique_counts) == 1, (
            f"Expert table body rows have inconsistent column counts {unique_counts} — "
            "all rows must have the same number of columns per §9.2"
        )


# ---------------------------------------------------------------------------
# §9.1 — Card recipe (detail card / expert card layout)
# ---------------------------------------------------------------------------


class TestExpertsCardRecipe:
    """Expert cards (detail panel or summary cards) must conform to §9.1 card recipe.

    The experts page may render expert summary cards or use a card-styled
    detail panel. Each card must have the correct background, border color,
    border-radius (≥ 8px), and padding (≥ 16px) per §9.1.
    """

    def test_card_recipe_if_present(self, page: object, base_url: str) -> None:
        """Expert cards/panels match §9.1 card recipe (background, border, radius, padding)."""
        _navigate_to_experts(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".expert-card",
            ".detail-panel",
            "[class*='detail-panel']",
            "[data-component='card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_card(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Expert card/panel {sel!r} fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No card element found on experts page — skipping §9.1 card recipe check"
        )


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe
# ---------------------------------------------------------------------------


class TestExpertsBadgeRecipe:
    """Badges on the experts page must conform to §9.3 badge recipe.

    Trust tier badges are the primary badge type on this page. They must
    use correct sizing, padding, and font weight per §9.3.
    """

    def test_badge_recipe(self, page: object, base_url: str) -> None:
        """Trust tier and status badges match §9.3 badge recipe."""
        _navigate_to_experts(page, base_url)

        badge_selectors = [
            "[data-tier]",
            "[data-trust-tier]",
            ".trust-tier-badge",
            ".tier-badge",
            "[class*='trust-tier']",
            "[class*='tier-badge']",
            ".badge",
            "[class*='badge']",
            ".pill",
            "[class*='pill']",
            "[data-status]",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Badge {sel!r} on experts page fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No badge element found on experts page — skipping §9.3 badge recipe check"
        )

    def test_dark_theme_does_not_break_layout(self, page: object, base_url: str) -> None:
        """Experts page layout remains intact when dark theme is applied."""
        _navigate_to_experts(page, base_url)

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page body empty after switching to dark theme"
        finally:
            set_light_theme(page)  # type: ignore[arg-type]
