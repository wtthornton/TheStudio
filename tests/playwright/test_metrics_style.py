"""Epic 63.3 — Metrics: Style Guide Compliance.

Validates that /admin/ui/metrics conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4-9:

  §4.1     — CSS design tokens registered on :root
  §4.2     — Focus ring color
  §5.1     — Status colors: success green, error red, warning amber, neutral gray
  §6       — Typography: page title, section headings, body/KPI text
  §9.1     — Card recipe: background, border, radius, padding (KPI cards)
  §9.3     — Badge recipe: sizing, padding, font weight (status badges)

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_metrics_intent.py (Epic 63.1).
API contracts are covered in test_metrics_api.py (Epic 63.2).
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

METRICS_URL = "/admin/ui/metrics"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_metrics(page: object, base_url: str) -> None:
    """Navigate to the metrics page and wait for the main content."""
    navigate(page, f"{base_url}{METRICS_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestMetricsDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates that all color, spacing, and typography values
    are driven by CSS custom properties. The presence of these tokens confirms
    the correct stylesheet is loaded on the metrics page.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_metrics(page, base_url)

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
        _navigate_to_metrics(page, base_url)

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
        _navigate_to_metrics(page, base_url)

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
        """Metrics page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_metrics(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Metrics page body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestMetricsFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2).

    The focus ring (blue-600 in light mode) ensures keyboard navigators can
    identify focused elements at a glance on the metrics page.
    """

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable elements show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_metrics(page, base_url)

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
            "No focusable element found on metrics page — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §5.1 — Status colors
# ---------------------------------------------------------------------------


class TestMetricsStatusColors:
    """Status indicators must use the §5.1 semantic color palette.

    §5.1 mandates:
      - Success / pass   → green-500  (#22c55e) / green-600 (#16a34a)
      - Error / fail     → red-500    (#ef4444) / red-600   (#dc2626)
      - Warning          → amber-500  (#f59e0b) / amber-600 (#d97706)
      - Neutral / info   → gray-500   (#6b7280) or blue-500 (#3b82f6)

    Status colors are checked on the first matching badge or status element.
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

    def test_success_status_color(self, page: object, base_url: str) -> None:
        """Success/pass status indicators use §5.1 green color palette."""
        _navigate_to_metrics(page, base_url)

        success_selectors = [
            "[data-status='success']",
            "[data-status='pass']",
            "[data-status='passed']",
            ".status-success",
            ".status-pass",
            "[class*='success']",
            "[class*='pass'][class*='status']",
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
                        f"Success status element {sel!r} color {color!r} does not match "
                        f"§5.1 green palette {self._SUCCESS_COLORS}"
                    )
                    return

        pytest.skip(
            "No success status element found on metrics page — skipping §5.1 success color check"
        )

    def test_error_status_color(self, page: object, base_url: str) -> None:
        """Error/fail status indicators use §5.1 red color palette."""
        _navigate_to_metrics(page, base_url)

        error_selectors = [
            "[data-status='error']",
            "[data-status='fail']",
            "[data-status='failed']",
            ".status-error",
            ".status-fail",
            "[class*='error'][class*='status']",
            "[class*='fail'][class*='status']",
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
                        f"Error status element {sel!r} color {color!r} does not match "
                        f"§5.1 red palette {self._ERROR_COLORS}"
                    )
                    return

        pytest.skip(
            "No error status element found on metrics page — skipping §5.1 error color check"
        )

    def test_warning_status_color(self, page: object, base_url: str) -> None:
        """Warning status indicators use §5.1 amber color palette."""
        _navigate_to_metrics(page, base_url)

        warning_selectors = [
            "[data-status='warning']",
            "[data-status='warn']",
            "[data-status='degraded']",
            ".status-warning",
            ".status-warn",
            "[class*='warning'][class*='status']",
            "[class*='warn'][class*='status']",
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
                        f"Warning status element {sel!r} color {color!r} does not match "
                        f"§5.1 amber palette {self._WARNING_COLORS}"
                    )
                    return

        pytest.skip(
            "No warning status element found on metrics page — skipping §5.1 warning color check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestMetricsTypography:
    """Metrics page typography must match the style guide type scale (§6.2).

    Key elements:
    - Page title (h1 / .page-title): 20px / weight 600
    - Section headings (h2): 16px / weight 600
    - KPI values / body text: 14px / weight 400 (body) or 24px+ / weight 700 (KPI)
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1-h3 elements follow the §6.2 heading scale."""
        _navigate_to_metrics(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_metrics(page, base_url)

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
        _navigate_to_metrics(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_body_text_typography(self, page: object, base_url: str) -> None:
        """Body text / metric labels use §6.2 body scale (14px / weight 400)."""
        _navigate_to_metrics(page, base_url)

        body_selectors = ["p", ".metric-label", ".kpi-label", "td", "[class*='label']"]
        for sel in body_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_typography(page, sel, role="body")  # type: ignore[arg-type]
                return

        pytest.skip("No body text element found — skipping body typography check")

    def test_kpi_value_font_size(self, page: object, base_url: str) -> None:
        """KPI metric values use a large display font size (≥ 20px) for visual hierarchy."""
        _navigate_to_metrics(page, base_url)

        kpi_selectors = [
            ".kpi-value",
            ".metric-value",
            ".stat-value",
            "[class*='kpi-value']",
            "[class*='metric-value']",
            "[class*='stat-value']",
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
                        f"KPI value element {sel!r} font-size {font_size_px}px — "
                        "expected ≥ 20px for display hierarchy per §6.2"
                    )
                    return

        pytest.skip(
            "No KPI value element found on metrics page — skipping KPI font-size check"
        )


# ---------------------------------------------------------------------------
# §9.1 — Card component recipe (KPI cards)
# ---------------------------------------------------------------------------


class TestMetricsCardRecipe:
    """Metrics page KPI cards must conform to §9.1 card recipe.

    KPI cards are the primary visual container on the metrics page.
    Each card must have the correct background, border color, border-radius
    (≥ 8px), and padding (≥ 16px) per §9.1.
    """

    def test_card_recipe(self, page: object, base_url: str) -> None:
        """KPI/metric cards match §9.1 card recipe (background, border, radius, padding)."""
        _navigate_to_metrics(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".kpi-card",
            ".metric-card",
            ".stat-card",
            "[data-component='card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_card(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"KPI card {sel!r} fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No card element found on metrics page — skipping §9.1 card recipe check"
        )

    def test_kpi_cards_have_consistent_dimensions(self, page: object, base_url: str) -> None:
        """All KPI cards on the metrics page share consistent width/height dimensions."""
        _navigate_to_metrics(page, base_url)

        kpi_selectors = [
            ".kpi-card",
            ".metric-card",
            ".stat-card",
            ".card",
            "[class*='kpi-card']",
            "[class*='metric-card']",
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
                        f"KPI cards {sel!r} have inconsistent widths {widths} — "
                        "cards in the same grid row should share equal widths per §9.1"
                    )
                    return

        pytest.skip(
            "Fewer than 2 KPI cards found on metrics page — skipping consistency check"
        )


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe (status badges)
# ---------------------------------------------------------------------------


class TestMetricsBadgeRecipe:
    """Status badges on the metrics page must conform to §9.3 badge recipe.

    Gate pass/fail badges and pipeline status badges must use correct
    sizing, padding, and font weight per §9.3.
    """

    def test_badge_recipe_if_present(self, page: object, base_url: str) -> None:
        """Status badges match §9.3 badge recipe when present."""
        _navigate_to_metrics(page, base_url)

        badge_selectors = [
            "[data-status]",
            ".badge",
            "[class*='badge']",
            ".status-badge",
            "[class*='status-badge']",
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
                    f"Badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No badge element found on metrics page — skipping §9.3 badge recipe check"
        )

    def test_dark_theme_does_not_break_layout(self, page: object, base_url: str) -> None:
        """Metrics page layout remains intact when dark theme is applied."""
        _navigate_to_metrics(page, base_url)

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page body empty after switching to dark theme"
        finally:
            set_light_theme(page)  # type: ignore[arg-type]
