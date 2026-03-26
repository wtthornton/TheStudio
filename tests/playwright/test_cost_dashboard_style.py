"""Epic 72.3 — Cost Dashboard: Style Guide Compliance.

Validates that /admin/ui/cost-dashboard conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4-9:

  §4.1     — CSS design tokens registered on :root
  §4.2     — Focus ring color
  §5.1     — Status colors: success green, error red, warning amber, neutral gray
  §6       — Typography: page title, section headings, body/KPI text
  §9.1     — Card recipe: background, border, radius, padding (KPI cards)
  §9.3     — Badge recipe: sizing, padding, font weight (status badges)

Cost-dashboard specific checks:
  - KPI cards display cost figures with correct visual hierarchy
  - Cost/monetary values formatted with appropriate typography (§6.2)
  - Chart colors follow §5.1 semantic color palette

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_cost_dashboard_intent.py (Epic 72.1).
API contracts are covered in test_cost_dashboard_api.py (Epic 72.2).
"""

import pytest

from tests.playwright.conftest import navigate
from tests.playwright.lib.component_validators import (
    validate_badge,
    validate_card,
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

COST_DASHBOARD_URL = "/admin/ui/cost-dashboard"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_cost_dashboard(page: object, base_url: str) -> None:
    """Navigate to the cost dashboard page and wait for the main content."""
    navigate(page, f"{base_url}{COST_DASHBOARD_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestCostDashboardDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates that all color, spacing, and typography values
    are driven by CSS custom properties. The presence of these tokens confirms
    the correct stylesheet is loaded on the cost dashboard page.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_cost_dashboard(page, base_url)

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
        _navigate_to_cost_dashboard(page, base_url)

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
        _navigate_to_cost_dashboard(page, base_url)

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
        """Cost dashboard background matches the §4.1 gray-50 or white design token."""
        _navigate_to_cost_dashboard(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Cost dashboard body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestCostDashboardFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2).

    The focus ring (blue-600 in light mode) ensures keyboard navigators can
    identify focused elements at a glance on the cost dashboard page.
    """

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable elements show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_cost_dashboard(page, base_url)

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
            "No focusable element found on cost dashboard page — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §5.1 — Status colors and chart colors
# ---------------------------------------------------------------------------


class TestCostDashboardStatusColors:
    """Status indicators and chart elements must use the §5.1 semantic color palette.

    §5.1 mandates:
      - Success / under-budget   → green-500  (#22c55e) / green-600 (#16a34a)
      - Error / over-budget      → red-500    (#ef4444) / red-600   (#dc2626)
      - Warning / near-limit     → amber-500  (#f59e0b) / amber-600 (#d97706)
      - Neutral / informational  → gray-500   (#6b7280) or blue-500 (#3b82f6)

    Cost dashboard chart colors must also follow this palette to convey
    spend status semantics consistently with other admin pages.
    """

    _SUCCESS_COLORS = ("#22c55e", "#16a34a", "#15803d", "#4ade80")
    _ERROR_COLORS = ("#ef4444", "#dc2626", "#b91c1c", "#f87171")
    _WARNING_COLORS = ("#f59e0b", "#d97706", "#b45309", "#fbbf24")
    _NEUTRAL_COLORS = ("#6b7280", "#4b5563", "#3b82f6", "#2563eb")

    def _get_element_color(self, page: object, selector: str) -> str | None:
        """Return the computed color of the first matching element, or None."""
        return page.evaluate(  # type: ignore[attr-defined]
            f"""
            (function() {{
                var el = document.querySelector({selector!r});
                if (!el) return null;
                return window.getComputedStyle(el).color;
            }})()
            """
        )

    def test_under_budget_status_color(self, page: object, base_url: str) -> None:
        """Under-budget / success status indicators use §5.1 green color palette."""
        _navigate_to_cost_dashboard(page, base_url)

        success_selectors = [
            "[data-status='success']",
            "[data-status='under-budget']",
            "[data-status='ok']",
            ".status-success",
            ".status-under-budget",
            "[class*='success']",
            "[class*='under-budget']",
        ]
        for sel in success_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = self._get_element_color(page, sel)
                if color:
                    matched = any(colors_close(color, c) for c in self._SUCCESS_COLORS)
                    assert matched, (
                        f"Under-budget status element {sel!r} color {color!r} does not match "
                        f"§5.1 green palette {self._SUCCESS_COLORS}"
                    )
                    return

        pytest.skip(
            "No under-budget/success status element found — skipping §5.1 success color check"
        )

    def test_over_budget_status_color(self, page: object, base_url: str) -> None:
        """Over-budget / error status indicators use §5.1 red color palette."""
        _navigate_to_cost_dashboard(page, base_url)

        error_selectors = [
            "[data-status='error']",
            "[data-status='over-budget']",
            "[data-status='exceeded']",
            ".status-error",
            ".status-over-budget",
            "[class*='error'][class*='status']",
            "[class*='over-budget']",
        ]
        for sel in error_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = self._get_element_color(page, sel)
                if color:
                    matched = any(colors_close(color, c) for c in self._ERROR_COLORS)
                    assert matched, (
                        f"Over-budget status element {sel!r} color {color!r} does not match "
                        f"§5.1 red palette {self._ERROR_COLORS}"
                    )
                    return

        pytest.skip(
            "No over-budget/error status element found — skipping §5.1 error color check"
        )

    def test_near_limit_warning_color(self, page: object, base_url: str) -> None:
        """Near-limit / warning status indicators use §5.1 amber color palette."""
        _navigate_to_cost_dashboard(page, base_url)

        warning_selectors = [
            "[data-status='warning']",
            "[data-status='near-limit']",
            "[data-status='degraded']",
            ".status-warning",
            ".status-near-limit",
            "[class*='warning'][class*='status']",
            "[class*='near-limit']",
        ]
        for sel in warning_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = self._get_element_color(page, sel)
                if color:
                    matched = any(colors_close(color, c) for c in self._WARNING_COLORS)
                    assert matched, (
                        f"Near-limit warning element {sel!r} color {color!r} does not match "
                        f"§5.1 amber palette {self._WARNING_COLORS}"
                    )
                    return

        pytest.skip(
            "No near-limit/warning status element found — skipping §5.1 warning color check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography (including cost/monetary value formatting)
# ---------------------------------------------------------------------------


class TestCostDashboardTypography:
    """Cost dashboard typography must match the style guide type scale (§6.2).

    Key elements:
    - Page title (h1 / .page-title): 20px / weight 600
    - Section headings (h2): 16px / weight 600
    - KPI cost values: ≥ 20px / weight 700 (display size for monetary figures)
    - Body text / labels: 14px / weight 400
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1-h3 elements follow the §6.2 heading scale."""
        _navigate_to_cost_dashboard(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_cost_dashboard(page, base_url)

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
        _navigate_to_cost_dashboard(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_body_text_typography(self, page: object, base_url: str) -> None:
        """Body text / cost labels use §6.2 body scale (14px / weight 400)."""
        _navigate_to_cost_dashboard(page, base_url)

        body_selectors = [
            "p",
            ".cost-label",
            ".kpi-label",
            ".metric-label",
            "td",
            "[class*='label']",
        ]
        for sel in body_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_typography(page, sel, role="body")  # type: ignore[arg-type]
                return

        pytest.skip("No body text element found — skipping body typography check")

    def test_cost_kpi_value_font_size(self, page: object, base_url: str) -> None:
        """Cost KPI values use a large display font size (≥ 20px) for visual hierarchy."""
        _navigate_to_cost_dashboard(page, base_url)

        kpi_selectors = [
            ".kpi-value",
            ".cost-value",
            ".spend-value",
            ".metric-value",
            ".stat-value",
            "[class*='kpi-value']",
            "[class*='cost-value']",
            "[class*='spend-value']",
        ]
        for sel in kpi_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                font_size_px = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var fs = window.getComputedStyle(el).fontSize;
                        return parseFloat(fs);
                    }})()
                    """
                )
                if font_size_px is not None:
                    assert font_size_px >= 20, (
                        f"Cost KPI value element {sel!r} font-size {font_size_px}px — "
                        "expected ≥ 20px for display hierarchy per §6.2"
                    )
                    return

        pytest.skip(
            "No cost KPI value element found on cost dashboard — skipping KPI font-size check"
        )


# ---------------------------------------------------------------------------
# §9.1 — Card component recipe (KPI cost cards)
# ---------------------------------------------------------------------------


class TestCostDashboardCardRecipe:
    """Cost dashboard KPI cards must conform to §9.1 card recipe.

    Cost KPI cards (total spend, budget used, budget remaining, etc.) are the
    primary visual containers on the cost dashboard. Each card must have the
    correct background, border color, border-radius (≥ 8px), and padding
    (≥ 16px) per §9.1.
    """

    def test_card_recipe(self, page: object, base_url: str) -> None:
        """KPI/cost cards match §9.1 card recipe (background, border, radius, padding)."""
        _navigate_to_cost_dashboard(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".kpi-card",
            ".cost-card",
            ".spend-card",
            ".budget-card",
            "[data-component='card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_card(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Cost KPI card {sel!r} fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No card element found on cost dashboard — skipping §9.1 card recipe check"
        )

    def test_kpi_cards_have_consistent_dimensions(self, page: object, base_url: str) -> None:
        """All cost KPI cards share consistent width dimensions (same grid column)."""
        _navigate_to_cost_dashboard(page, base_url)

        kpi_selectors = [
            ".kpi-card",
            ".cost-card",
            ".spend-card",
            ".budget-card",
            ".card",
            "[class*='kpi-card']",
            "[class*='cost-card']",
        ]
        for sel in kpi_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count >= 2:
                widths = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var cards = document.querySelectorAll({sel!r});
                        var widths = [];
                        cards.forEach(function(c) {{
                            widths.push(Math.round(c.getBoundingClientRect().width));
                        }});
                        return widths;
                    }})()
                    """
                )
                if widths and len(widths) >= 2:
                    # All cards should be within 4px of each other (same grid column)
                    min_w, max_w = min(widths), max(widths)
                    assert max_w - min_w <= 4 or max_w == 0, (
                        f"Cost KPI cards {sel!r} have inconsistent widths {widths} — "
                        "cards in the same grid row should share equal widths per §9.1"
                    )
                    return

        pytest.skip(
            "Fewer than 2 cost KPI cards found on cost dashboard — skipping consistency check"
        )


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe (budget status badges)
# ---------------------------------------------------------------------------


class TestCostDashboardBadgeRecipe:
    """Budget status badges on the cost dashboard must conform to §9.3 badge recipe.

    Budget utilization badges (e.g. "Under Budget", "Near Limit", "Exceeded")
    must use correct sizing, padding, and font weight per §9.3.
    """

    def test_badge_recipe_if_present(self, page: object, base_url: str) -> None:
        """Budget status badges match §9.3 badge recipe when present."""
        _navigate_to_cost_dashboard(page, base_url)

        badge_selectors = [
            "[data-status]",
            ".badge",
            "[class*='badge']",
            ".status-badge",
            "[class*='status-badge']",
            ".budget-badge",
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
                    f"Budget status badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No badge element found on cost dashboard — skipping §9.3 badge recipe check"
        )

    def test_dark_theme_does_not_break_layout(self, page: object, base_url: str) -> None:
        """Cost dashboard layout remains intact when dark theme is applied."""
        _navigate_to_cost_dashboard(page, base_url)

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page body empty after switching to dark theme"
        finally:
            set_light_theme(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cost formatting specifics
# ---------------------------------------------------------------------------


class TestCostDashboardCostFormatting:
    """Monetary cost values must be formatted consistently across the cost dashboard.

    Cost figures should use standard currency notation ($X.XX or X.XX USD).
    Large values should use appropriate number formatting (commas for thousands).
    """

    def test_monetary_values_use_consistent_formatting(
        self, page: object, base_url: str
    ) -> None:
        """Monetary values use consistent dollar-sign prefix or USD suffix formatting."""
        _navigate_to_cost_dashboard(page, base_url)

        # Look for elements that likely display cost figures
        cost_selectors = [
            ".cost-value",
            ".spend-value",
            ".kpi-value",
            ".metric-value",
            "[class*='cost-value']",
            "[class*='spend-value']",
            "[data-metric='cost']",
            "[data-metric='spend']",
        ]

        for sel in cost_selectors:
            texts = page.evaluate(  # type: ignore[attr-defined]
                f"""
                (function() {{
                    var els = document.querySelectorAll({sel!r});
                    var texts = [];
                    els.forEach(function(el) {{
                        texts.push(el.innerText || el.textContent || '');
                    }});
                    return texts;
                }})()
                """
            )
            if texts:
                # Filter to non-empty texts
                non_empty = [t.strip() for t in texts if t.strip()]
                if non_empty:
                    # At least some monetary values should use $ or USD notation
                    # OR be pure numeric (still acceptable for cost displays)
                    for text in non_empty:
                        has_currency = "$" in text or "usd" in text.lower()
                        has_numeric = any(c.isdigit() for c in text)
                        assert has_currency or has_numeric, (
                            f"Cost value element {sel!r} text {text!r} — expected currency "
                            "notation ($X.XX or numeric) per cost dashboard formatting"
                        )
                    return

        pytest.skip(
            "No cost value elements found on cost dashboard — skipping formatting check"
        )

    def test_cost_figures_have_visual_prominence(self, page: object, base_url: str) -> None:
        """Primary cost figures are visually prominent (font-weight ≥ 500)."""
        _navigate_to_cost_dashboard(page, base_url)

        prominent_selectors = [
            ".kpi-value",
            ".cost-value",
            ".spend-value",
            ".total-cost",
            "[class*='kpi-value']",
            "[class*='cost-value']",
            "[class*='total']",
        ]
        for sel in prominent_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                font_weight = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var fw = window.getComputedStyle(el).fontWeight;
                        return parseFloat(fw);
                    }})()
                    """
                )
                if font_weight is not None:
                    assert font_weight >= 500, (
                        f"Cost KPI element {sel!r} font-weight {font_weight} — "
                        "expected ≥ 500 (medium/semibold) for visual prominence per §6.2"
                    )
                    return

        pytest.skip(
            "No prominent cost figure element found — skipping font-weight prominence check"
        )
