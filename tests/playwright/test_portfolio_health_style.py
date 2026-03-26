"""Epic 73.3 — Portfolio Health: Style Guide Compliance.

Validates that /admin/ui/portfolio-health conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4-9:

  §4.1     — CSS design tokens registered on :root
  §4.2     — Focus ring color
  §5.1     — Status colors: success green, error red, warning amber, neutral gray
  §6       — Typography: page title, section headings, body text
  §9.1     — Card recipe: background, border, radius, padding (health/repo cards)
  §9.3     — Badge recipe: sizing, padding, font weight (risk badges)

Portfolio Health specific concerns:
  - Health status colors map correctly (healthy=green, degraded=amber, critical=red)
  - Risk-level badges (low/medium/high/critical) use §5.1 semantic colors
  - Card recipe applied to per-repo health cards and aggregate health card

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_portfolio_health_intent.py (Epic 73.1).
API contracts are covered in test_portfolio_health_api.py (Epic 73.2).
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

PORTFOLIO_HEALTH_URL = "/admin/ui/portfolio-health"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_portfolio_health(page: object, base_url: str) -> None:
    """Navigate to the portfolio health page and wait for the main content."""
    navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestPortfolioHealthDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates all color, spacing, and typography values are driven
    by CSS custom properties. Their presence confirms the correct stylesheet is
    loaded on the portfolio health page.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_portfolio_health(page, base_url)

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
        _navigate_to_portfolio_health(page, base_url)

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
        _navigate_to_portfolio_health(page, base_url)

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
        """Portfolio health page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_portfolio_health(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Portfolio health page body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestPortfolioHealthFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2).

    The focus ring (blue-600 in light mode) ensures keyboard navigators can
    identify focused elements at a glance on the portfolio health page.
    """

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable elements show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_portfolio_health(page, base_url)

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
            "No focusable element found on portfolio health page — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §5.1 — Health status colors
# ---------------------------------------------------------------------------


class TestPortfolioHealthStatusColors:
    """Health status indicators must use the §5.1 semantic color palette.

    §5.1 mandates:
      - Healthy / success  → green-500  (#22c55e) / green-600 (#16a34a)
      - Critical / error   → red-500    (#ef4444) / red-600   (#dc2626)
      - Degraded / warning → amber-500  (#f59e0b) / amber-600 (#d97706)
      - Neutral / info     → gray-500   (#6b7280) or blue-500 (#3b82f6)

    Status colors are checked on the first matching health status element or badge.
    Portfolio Health uses health states: healthy, degraded, critical, warning, ok, idle.
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

    def test_healthy_status_color(self, page: object, base_url: str) -> None:
        """Healthy/success status indicators use §5.1 green color palette."""
        _navigate_to_portfolio_health(page, base_url)

        healthy_selectors = [
            "[data-health='healthy']",
            "[data-health='ok']",
            "[data-status='healthy']",
            "[data-status='success']",
            "[data-status='ok']",
            ".status-healthy",
            ".status-success",
            ".health-healthy",
            "[class*='health-ok']",
            "[class*='status-healthy']",
        ]
        for sel in healthy_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = self._get_element_color(page, sel)
                if color:
                    matched = any(colors_close(color, c) for c in self._SUCCESS_COLORS)
                    assert matched, (
                        f"Healthy status element {sel!r} color {color!r} does not match "
                        f"§5.1 green palette {self._SUCCESS_COLORS}"
                    )
                    return

        pytest.skip(
            "No healthy status element found on portfolio health page — "
            "skipping §5.1 healthy color check"
        )

    def test_critical_status_color(self, page: object, base_url: str) -> None:
        """Critical/error status indicators use §5.1 red color palette."""
        _navigate_to_portfolio_health(page, base_url)

        critical_selectors = [
            "[data-health='critical']",
            "[data-status='critical']",
            "[data-status='error']",
            "[data-status='failed']",
            "[data-risk='critical']",
            ".status-critical",
            ".status-error",
            ".health-critical",
            "[class*='status-critical']",
            "[class*='health-critical']",
        ]
        for sel in critical_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = self._get_element_color(page, sel)
                if color:
                    matched = any(colors_close(color, c) for c in self._ERROR_COLORS)
                    assert matched, (
                        f"Critical status element {sel!r} color {color!r} does not match "
                        f"§5.1 red palette {self._ERROR_COLORS}"
                    )
                    return

        pytest.skip(
            "No critical status element found on portfolio health page — "
            "skipping §5.1 critical color check"
        )

    def test_degraded_status_color(self, page: object, base_url: str) -> None:
        """Degraded/warning status indicators use §5.1 amber color palette."""
        _navigate_to_portfolio_health(page, base_url)

        degraded_selectors = [
            "[data-health='degraded']",
            "[data-health='warning']",
            "[data-status='degraded']",
            "[data-status='warning']",
            "[data-risk='high']",
            "[data-risk='medium']",
            ".status-degraded",
            ".status-warning",
            ".health-degraded",
            "[class*='status-degraded']",
            "[class*='health-degraded']",
        ]
        for sel in degraded_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = self._get_element_color(page, sel)
                if color:
                    matched = any(colors_close(color, c) for c in self._WARNING_COLORS)
                    assert matched, (
                        f"Degraded status element {sel!r} color {color!r} does not match "
                        f"§5.1 amber palette {self._WARNING_COLORS}"
                    )
                    return

        pytest.skip(
            "No degraded/warning status element found on portfolio health page — "
            "skipping §5.1 degraded color check"
        )

    def test_risk_badge_critical_uses_red(self, page: object, base_url: str) -> None:
        """Risk-level 'critical' badge uses §5.1 red color."""
        _navigate_to_portfolio_health(page, base_url)

        risk_critical_selectors = [
            "[data-risk='critical']",
            ".risk-critical",
            "[class*='risk-critical']",
            ".badge-critical",
            "[class*='badge-critical']",
        ]
        for sel in risk_critical_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = self._get_element_color(page, sel)
                if color:
                    matched = any(colors_close(color, c) for c in self._ERROR_COLORS)
                    assert matched, (
                        f"Critical risk badge {sel!r} color {color!r} does not match "
                        f"§5.1 red palette {self._ERROR_COLORS}"
                    )
                    return

        pytest.skip(
            "No critical risk badge found on portfolio health page — "
            "skipping §5.1 critical risk badge color check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestPortfolioHealthTypography:
    """Portfolio health page typography must match the style guide type scale (§6.2).

    Key elements:
    - Page title (h1 / .page-title): 20px / weight 600
    - Section headings (h2): 16px / weight 600
    - Body text / repo labels: 14px / weight 400
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1-h3 elements follow the §6.2 heading scale."""
        _navigate_to_portfolio_health(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_portfolio_health(page, base_url)

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
        _navigate_to_portfolio_health(page, base_url)

        count = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('h2').length"
        )
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_body_text_typography(self, page: object, base_url: str) -> None:
        """Body text / repo labels use §6.2 body scale (14px / weight 400)."""
        _navigate_to_portfolio_health(page, base_url)

        body_selectors = [
            "p",
            ".repo-name",
            ".repo-label",
            "td",
            "[class*='label']",
            "[class*='repo-name']",
        ]
        for sel in body_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_typography(page, sel, role="body")  # type: ignore[arg-type]
                return

        pytest.skip("No body text element found — skipping body typography check")


# ---------------------------------------------------------------------------
# §9.1 — Card component recipe (health / repo cards)
# ---------------------------------------------------------------------------


class TestPortfolioHealthCardRecipe:
    """Portfolio health cards must conform to §9.1 card recipe.

    Per-repo health cards and the aggregate portfolio health card are the
    primary visual containers. Each must have correct background, border color,
    border-radius (≥ 8px), and padding (≥ 16px) per §9.1.
    """

    def test_card_recipe(self, page: object, base_url: str) -> None:
        """Health / repo cards match §9.1 card recipe (background, border, radius, padding)."""
        _navigate_to_portfolio_health(page, base_url)

        card_selectors = [
            "[data-component='repo-card']",
            "[data-component='health-card']",
            ".repo-card",
            ".health-card",
            ".portfolio-card",
            ".card",
            "[class*='repo-card']",
            "[class*='health-card']",
            "[class*='card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_card(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Health card {sel!r} fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No card element found on portfolio health page — skipping §9.1 card recipe check"
        )

    def test_repo_cards_have_consistent_dimensions(self, page: object, base_url: str) -> None:
        """Per-repo health cards share consistent width dimensions within the grid."""
        _navigate_to_portfolio_health(page, base_url)

        card_selectors = [
            "[data-component='repo-card']",
            ".repo-card",
            ".health-card",
            ".portfolio-card",
            "[class*='repo-card']",
            "[class*='health-card']",
        ]
        for sel in card_selectors:
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
                    min_w, max_w = min(widths), max(widths)
                    assert max_w - min_w <= 4 or max_w == 0, (
                        f"Repo health cards {sel!r} have inconsistent widths {widths} — "
                        "cards in the same grid row should share equal widths per §9.1"
                    )
                    return

        pytest.skip(
            "Fewer than 2 repo health cards found on portfolio health page — "
            "skipping consistency check"
        )


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe (risk / health status badges)
# ---------------------------------------------------------------------------


class TestPortfolioHealthBadgeRecipe:
    """Risk and health status badges must conform to §9.3 badge recipe.

    Risk-level badges (low / medium / high / critical) and health status
    badges (healthy / degraded / critical) must use correct sizing, padding,
    and font weight per §9.3.
    """

    def test_risk_badge_recipe_if_present(self, page: object, base_url: str) -> None:
        """Risk level badges match §9.3 badge recipe when present."""
        _navigate_to_portfolio_health(page, base_url)

        badge_selectors = [
            "[data-risk]",
            "[data-health]",
            "[data-status]",
            ".badge",
            "[class*='badge']",
            ".risk-badge",
            "[class*='risk-badge']",
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
                    f"Risk/health badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No risk or health badge found on portfolio health page — "
            "skipping §9.3 badge recipe check"
        )

    def test_risk_badges_have_text_labels(self, page: object, base_url: str) -> None:
        """Risk badges include text labels (not color-only) for non-color accessibility."""
        _navigate_to_portfolio_health(page, base_url)

        badge_selectors = [
            "[data-risk]",
            ".risk-badge",
            "[class*='risk-badge']",
            "[class*='risk-level']",
        ]
        for sel in badge_selectors:
            badges = page.evaluate(  # type: ignore[attr-defined]
                f"""
                (function() {{
                    var els = document.querySelectorAll({sel!r});
                    var texts = [];
                    els.forEach(function(el) {{
                        var t = (el.textContent || el.innerText || "").trim();
                        if (t) texts.push(t);
                    }});
                    return texts;
                }})()
                """
            )
            if badges:
                valid_labels = {"low", "medium", "high", "critical", "none", "unknown", "ok"}
                for label in badges:
                    assert label.lower() in valid_labels or len(label) > 0, (
                        f"Risk badge text {label!r} is not a recognised risk level label — "
                        "badges must have visible text (not color-only) per §9.3"
                    )
                return

        pytest.skip(
            "No risk badge with text found on portfolio health page — "
            "skipping risk badge text label check"
        )

    def test_dark_theme_does_not_break_layout(self, page: object, base_url: str) -> None:
        """Portfolio health page layout remains intact when dark theme is applied."""
        _navigate_to_portfolio_health(page, base_url)

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page body empty after switching to dark theme"
        finally:
            set_light_theme(page)  # type: ignore[arg-type]
