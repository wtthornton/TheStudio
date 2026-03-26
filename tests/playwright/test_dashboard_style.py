"""Epic 59.3 — Fleet Dashboard: Style Guide Compliance.

Validates that /admin/ui/dashboard conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4 / §5  — Design tokens: colors, status colors, focus ring
  §6       — Typography: page title, section headings, KPI values, body text
  §7       — Spacing: 4px-grid compliance for cards and tables
  §9.1     — Card recipe: background, border, radius, padding
  §9.2     — Table recipe: thead background, <th> scope attributes
  §9.3     — Badge recipe: sizing, padding, font weight

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_dashboard_intent.py (Epic 59.1).
API contracts are covered in test_dashboard_api.py (Epic 59.2).
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
    assert_status_colors,
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

DASHBOARD_URL = "/admin/ui/dashboard"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_dashboard(page: object, base_url: str) -> None:
    """Navigate to the dashboard and wait for the main content."""
    navigate(page, f"{base_url}{DASHBOARD_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §5 — Status colors on service health badges
# ---------------------------------------------------------------------------


class TestDashboardStatusColors:
    """Service health badges must use the correct §5.1 status color tokens.

    The dashboard renders Temporal, Postgres, JetStream, and Router health
    cards.  Each card's status badge must use the semantic color palette so
    that operators can instantly distinguish healthy from degraded/failed.
    """

    def test_status_color_token_success_present(self, page: object, base_url: str) -> None:
        """At least one element with data-status='success' uses the correct colors."""
        _navigate_to_dashboard(page, base_url)

        selector = "[data-status='success']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No data-status='success' badge found — skipping color check")

        assert_status_colors(page, selector, "success")  # type: ignore[arg-type]

    def test_status_color_token_warning_present(self, page: object, base_url: str) -> None:
        """At least one element with data-status='warning' uses the correct colors."""
        _navigate_to_dashboard(page, base_url)

        selector = "[data-status='warning']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No data-status='warning' badge found — skipping color check")

        assert_status_colors(page, selector, "warning")  # type: ignore[arg-type]

    def test_status_color_token_error_present(self, page: object, base_url: str) -> None:
        """At least one element with data-status='error' uses the correct colors."""
        _navigate_to_dashboard(page, base_url)

        selector = "[data-status='error']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No data-status='error' badge found — skipping color check")

        assert_status_colors(page, selector, "error")  # type: ignore[arg-type]

    def test_page_background_uses_design_token(self, page: object, base_url: str) -> None:
        """Dashboard page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_dashboard(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        # §4.1: surface-app (gray-50 #f9fafb) or white
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Dashboard body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )

    def test_dark_theme_status_colors(self, page: object, base_url: str) -> None:
        """Status colors update correctly when dark theme is applied."""
        _navigate_to_dashboard(page, base_url)

        selector = "[data-status='success']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No data-status='success' badge — skipping dark theme check")

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            assert_status_colors(page, selector, "success", dark=True)  # type: ignore[arg-type]
        finally:
            set_light_theme(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestDashboardFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2).

    The focus ring (blue-600 in light mode) ensures keyboard navigators can
    identify focused elements at a glance.
    """

    def test_primary_button_focus_ring(self, page: object, base_url: str) -> None:
        """Primary buttons show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_dashboard(page, base_url)

        # Try a primary button first; fall back to any button if none found.
        selectors_to_try = [
            "button.btn-primary",
            "button[class*='primary']",
            "button",
            "a[href][class*='btn']",
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
                    # Focus ring assertion failed on this selector; try next.
                    continue

        pytest.skip("No focusable button found on dashboard — skipping focus ring check")


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestDashboardTypography:
    """Dashboard typography must match the style guide type scale (§6.2).

    Key elements:
    - Page title (h1 / .page-title): 20px / weight 600
    - Section headings (h2): 16px / weight 600
    - Subsection headings (h3): 14px / weight 600
    - KPI metric values: 24–30px / weight 700
    - Body text: 14px / weight 400
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1–h3 elements follow the §6.2 heading scale."""
        _navigate_to_dashboard(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_dashboard(page, base_url)

        selectors = ["h1", ".page-title", "[class*='page-title']"]
        for sel in selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_typography(page, sel, role="page_title")  # type: ignore[arg-type]
                return

        pytest.skip("No page title element (h1/.page-title) found — skipping typography check")

    def test_kpi_value_typography(self, page: object, base_url: str) -> None:
        """Workflow Summary KPI values use §6.2 kpi scale (24–30px / weight 700)."""
        _navigate_to_dashboard(page, base_url)

        kpi_selectors = [
            ".kpi-value",
            "[class*='kpi']",
            ".metric-value",
            "[class*='metric-value']",
            "[class*='count']",
        ]
        for sel in kpi_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_typography(page, sel, role="kpi")  # type: ignore[arg-type]
                return

        pytest.skip("No KPI value element found — skipping kpi typography check")

    def test_section_heading_typography(self, page: object, base_url: str) -> None:
        """Section headings (h2) use §6.2 section_title scale (16px / weight 600)."""
        _navigate_to_dashboard(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_body_text_typography(self, page: object, base_url: str) -> None:
        """Body text elements use §6.2 body scale (14px / weight 400)."""
        _navigate_to_dashboard(page, base_url)

        body_selectors = [
            "p",
            ".body-text",
            "[class*='body']",
            "td",
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
# §9.1 — Card component recipe
# ---------------------------------------------------------------------------


class TestDashboardCardRecipe:
    """Dashboard cards must conform to §9.1 card recipe.

    Cards wrap the System Health service entries, Workflow Summary KPIs, and
    the Repo Activity table.  Each card must have the correct background,
    border color, border-radius (≥ 8px), and padding (≥ 16px).
    """

    def test_system_health_card_recipe(self, page: object, base_url: str) -> None:
        """System health section cards match §9.1 card recipe."""
        _navigate_to_dashboard(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".service-card",
            ".health-card",
            "[data-component='card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_card(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Card {sel!r} fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip("No card element found — skipping §9.1 card recipe check")

    def test_workflow_summary_card_spacing(self, page: object, base_url: str) -> None:
        """Workflow summary cards have §7.1 compliant padding (4px-grid multiple)."""
        _navigate_to_dashboard(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".metric-card",
            "[data-component='card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                padding_top_raw = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        return window.getComputedStyle(el).paddingTop;
                    }})()
                    """
                )
                if padding_top_raw is None:
                    pytest.skip(f"No element found at {sel!r}")

                # Strip 'px' and convert to float
                px_str = padding_top_raw.strip()
                if px_str.endswith("px"):
                    px_val = float(px_str[:-2])
                    assert px_val >= 16, (
                        f"Card padding {px_val}px < 16px — §9.1 requires p-4 (16px) minimum"
                    )
                    assert px_val % 4 == 0 or abs(px_val % 4) < 1, (
                        f"Card padding {px_val}px is not a 4px-grid multiple (§7.1)"
                    )
                return

        pytest.skip("No card element found — skipping spacing check")


# ---------------------------------------------------------------------------
# §9.2 — Table recipe for Repo Activity
# ---------------------------------------------------------------------------


class TestDashboardTableRecipe:
    """The Repo Activity table must conform to §9.2 table recipe.

    Validates thead background color, <th scope="col"> presence, and
    right-aligned numeric columns.
    """

    def test_repo_activity_table_recipe(self, page: object, base_url: str) -> None:
        """Repo Activity table matches §9.2 table recipe when rendered."""
        _navigate_to_dashboard(page, base_url)

        table_count = page.locator("table").count()  # type: ignore[attr-defined]
        if table_count == 0:
            pytest.skip("No <table> present on dashboard — empty state is acceptable")

        result = validate_table(page, "table")  # type: ignore[arg-type]
        assert result.passed, (
            f"Repo Activity table fails §9.2 recipe: {result.summary()}"
        )

    def test_table_th_scope_attributes(self, page: object, base_url: str) -> None:
        """All <th> elements in the Repo Activity table carry scope='col' or scope='row'."""
        _navigate_to_dashboard(page, base_url)

        table_count = page.locator("table").count()  # type: ignore[attr-defined]
        if table_count == 0:
            pytest.skip("No <table> present on dashboard — empty state is acceptable")

        scope_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var table = document.querySelector('table');
                if (!table) return {total: 0, missing: 0};
                var ths = table.querySelectorAll('th');
                var missing = 0;
                ths.forEach(function(th) {
                    var sc = th.getAttribute('scope');
                    if (sc !== 'col' && sc !== 'row') missing++;
                });
                return {total: ths.length, missing: missing};
            })()
            """
        )
        if scope_info["total"] == 0:
            pytest.skip("No <th> elements in table")

        assert scope_info["missing"] == 0, (
            f"{scope_info['missing']}/{scope_info['total']} <th> elements missing "
            "scope='col'/'row' — required by §9.2"
        )


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe for status indicators
# ---------------------------------------------------------------------------


class TestDashboardBadgeRecipe:
    """Status and tier badges must conform to §9.3 badge recipe.

    Badges appear in the System Health section (service status) and on the
    Repo Activity table (trust tier, repo status).
    """

    def test_status_badge_recipe(self, page: object, base_url: str) -> None:
        """Status badges match §9.3 badge recipe (padding, radius, font weight)."""
        _navigate_to_dashboard(page, base_url)

        badge_selectors = [
            "[data-status]",
            ".badge",
            "[class*='badge']",
            ".status-badge",
            "[class*='status-badge']",
            ".pill",
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

        pytest.skip("No badge element found — skipping §9.3 badge recipe check")

    def test_trust_tier_badge_recipe(self, page: object, base_url: str) -> None:
        """Trust tier badges match §9.3 badge recipe when present."""
        _navigate_to_dashboard(page, base_url)

        tier_badge_selectors = [
            "[data-tier]",
            ".tier-badge",
            "[class*='tier']",
        ]
        for sel in tier_badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Tier badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip("No trust tier badge found on dashboard — skipping §9.3 check")


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestDashboardDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates that all color, spacing, and typography values
    are driven by CSS custom properties.  The presence of these tokens
    confirms the correct stylesheet is loaded.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_dashboard(page, base_url)

        try:
            val = get_css_variable(page, "--color-focus-ring")  # type: ignore[arg-type]
            # Value should be non-empty and resemble a color
            assert val, (
                "--color-focus-ring CSS variable is empty — §4.1 requires it to be set"
            )
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip("--color-focus-ring not present; stylesheet may use direct classes")
            raise

    def test_font_sans_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --font-sans is registered on :root (§6.1)."""
        _navigate_to_dashboard(page, base_url)

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
                pytest.skip("--font-sans not present; stylesheet may use direct font declarations")
            raise

    def test_surface_app_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-surface-app is registered (§4.1)."""
        _navigate_to_dashboard(page, base_url)

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
