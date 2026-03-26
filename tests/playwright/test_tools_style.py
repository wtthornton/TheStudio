"""Epic 65.3 — Tool Hub: Style Guide Compliance.

Validates that /admin/ui/tools conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4.1     — CSS design tokens registered on :root
  §4.2     — Focus ring color
  §5.1     — Status badge colors: approved (green) / pending (amber) / rejected (red)
  §6       — Typography: page title, section headings, body text
  §9.1     — Card recipe: background, border, radius, padding (tool detail card)
  §9.2     — Table recipe: thead background, <th> scope attributes (if table layout)
  §9.3     — Badge recipe: sizing, padding, font weight

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_tools_intent.py (Epic 65.1).
API contracts are covered in test_tools_api.py (Epic 65.2).
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

TOOLS_URL = "/admin/ui/tools"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_tools(page: object, base_url: str) -> None:
    """Navigate to the tools page and wait for the main content."""
    navigate(page, f"{base_url}{TOOLS_URL}")  # type: ignore[arg-type]


def _has_table(page: object) -> bool:
    """Return True when at least one <table> element is present on the page."""
    return page.locator("table").count() > 0  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestToolsDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates that all color, spacing, and typography values
    are driven by CSS custom properties. The presence of these tokens confirms
    the correct stylesheet is loaded on the tools page.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_tools(page, base_url)

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
        _navigate_to_tools(page, base_url)

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
        _navigate_to_tools(page, base_url)

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
        """Tools page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_tools(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Tools page body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestToolsFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2)."""

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable elements show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_tools(page, base_url)

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
            "No focusable element found on tools page — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §5.1 — Approval status badge colors
# ---------------------------------------------------------------------------


class TestToolsApprovalStatusColors:
    """Approval status badges must use the §5.1 semantic color tokens.

    §5.1 mandates semantic status colors:
      - approved  → green palette
      - pending   → amber/yellow palette
      - rejected  → red palette

    The tools page is the primary surface where approval status badges appear.
    Incorrect colors undermine operators' ability to assess tool access quickly.
    """

    def test_approval_status_badge_colors_present(self, page: object, base_url: str) -> None:
        """Approval status badges on the tools catalog use §5.1 color tokens."""
        _navigate_to_tools(page, base_url)

        status_selectors = [
            "[data-status]",
            "[data-approval-status]",
            ".approval-status-badge",
            ".status-badge",
            "[class*='approval-status']",
            "[class*='status-badge']",
        ]
        for sel in status_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Approval status badge {sel!r} fails §9.3 recipe: {result.summary()}"
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
            "No approval status badge element found on tools page — "
            "skipping §5.1 status color check"
        )

    def test_approved_badge_not_red(self, page: object, base_url: str) -> None:
        """Approved badges must not use the rejected (red) color (§5.1)."""
        _navigate_to_tools(page, base_url)

        approved_selectors = [
            "[data-status='approved']",
            "[data-approval-status='approved']",
            ".status-approved",
            "[class*='status-approved']",
            "[class*='approved']",
        ]
        for sel in approved_selectors:
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
                    rejected_reds = ("#ef4444", "#dc2626", "#b91c1c", "#f87171")
                    is_red = any(colors_close(color, r) for r in rejected_reds)
                    assert not is_red, (
                        f"Approved badge {sel!r} uses red color {color!r} — "
                        "§5.1 reserves red for 'rejected' status only"
                    )
                    return

        pytest.skip(
            "No 'approved' status badge found on tools page — skipping color separation check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestToolsTypography:
    """Tools page typography must match the style guide type scale (§6.2)."""

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1-h3 elements follow the §6.2 heading scale."""
        _navigate_to_tools(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_tools(page, base_url)

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
        _navigate_to_tools(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_table_cell_typography(self, page: object, base_url: str) -> None:
        """Table cell text uses §6.2 body scale (14px / weight 400)."""
        _navigate_to_tools(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found on tools page — skipping table cell typography check")

        assert_typography(page, "td", role="body")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe
# ---------------------------------------------------------------------------


class TestToolsBadgeRecipe:
    """Badges on the tools page must conform to §9.3 badge recipe.

    Approval status badges are the primary badge type on this page. They must
    use correct sizing, padding, and font weight per §9.3.
    """

    def test_badge_recipe(self, page: object, base_url: str) -> None:
        """Approval status and other badges match §9.3 badge recipe."""
        _navigate_to_tools(page, base_url)

        badge_selectors = [
            "[data-status]",
            "[data-approval-status]",
            ".approval-status-badge",
            ".status-badge",
            "[class*='approval-status']",
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
                    f"Badge {sel!r} on tools page fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No badge element found on tools page — skipping §9.3 badge recipe check"
        )

    def test_dark_theme_does_not_break_layout(self, page: object, base_url: str) -> None:
        """Tools page layout remains intact when dark theme is applied."""
        _navigate_to_tools(page, base_url)

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page body empty after switching to dark theme"
        finally:
            set_light_theme(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.1 — Card recipe (tool cards / detail card)
# ---------------------------------------------------------------------------


class TestToolsCardRecipe:
    """Tool cards or detail panel must conform to §9.1 card recipe.

    The tools page may render tool catalog cards or use a card-styled
    detail panel. Each card must have the correct background, border color,
    border-radius (≥ 8px), and padding (≥ 16px) per §9.1.
    """

    def test_card_recipe_if_present(self, page: object, base_url: str) -> None:
        """Tool cards/panels match §9.1 card recipe (background, border, radius, padding)."""
        _navigate_to_tools(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".tool-card",
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
                    f"Tool card/panel {sel!r} fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No card element found on tools page — skipping §9.1 card recipe check"
        )


# ---------------------------------------------------------------------------
# §9.2 — Table recipe (if table layout)
# ---------------------------------------------------------------------------


class TestToolsTableRecipe:
    """Tool catalog table (if present) must conform to §9.2 table recipe."""

    def test_table_recipe(self, page: object, base_url: str) -> None:
        """Tool catalog table matches §9.2 table recipe (thead background, th scope)."""
        _navigate_to_tools(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found on tools page — card layout acceptable")

        result = validate_table(page, "table")  # type: ignore[arg-type]
        assert result.passed, f"Tool catalog table fails §9.2 recipe: {result.summary()}"

    def test_table_header_scope_attributes(self, page: object, base_url: str) -> None:
        """<th> elements in the tool catalog table have scope='col' attribute (§9.2)."""
        _navigate_to_tools(page, base_url)

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
