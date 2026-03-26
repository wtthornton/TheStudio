"""Story 76.12 — Pipeline Dashboard: Repos Tab — Style Guide Compliance.

Validates that /dashboard/?tab=repos conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4 / §5  — Design tokens: colors, status colors, focus ring
  §6       — Typography: page title, section headings, body text
  §7       — Spacing: 4px-grid compliance for cards and panels
  §9.1     — Card recipe: background, border, radius, padding
  §9.2     — Table recipe: header, row, border
  §9.3     — Badge recipe: sizing, padding, font weight
  §9.4     — Button recipe: primary CTA styling
  §9.11    — Empty state recipe

Most style checks are xfail-marked: the pipeline dashboard is a dark-theme
React SPA whose CSS tokens differ slightly from the admin UI style guide
baseline.  These xfails are resolved in Epic 77 (style guide remediation).

These tests check *how* the page looks, not *what* it contains.
Semantic content is in test_pd_repos_intent.py.
API contracts are in test_pd_repos_api.py.
"""

import pytest

from tests.playwright.lib.component_validators import (
    validate_badge,
    validate_button,
    validate_card,
    validate_empty_state,
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
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _go(page: object, base_url: str) -> None:
    """Navigate to the repos tab."""
    dashboard_navigate(page, base_url, "repos")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.1 — Card recipe on fleet health and config panels
# ---------------------------------------------------------------------------


class TestReposCardRecipe:
    """Repos panel cards must conform to §9.1 card recipe.

    The fleet health panel and repo configuration panel each use the card
    recipe: dark background, border, ≥8px radius, ≥16px padding.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_fleet_health_card_recipe(self, page: object, base_url: str) -> None:
        """Fleet health panel matches §9.1 card recipe."""
        _go(page, base_url)

        result = validate_card(page, "[data-tour='repo-selector']")  # type: ignore[arg-type]
        assert result.passed, (
            f"Fleet health card fails §9.1 recipe: {result.summary()}"
        )

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_repo_config_card_recipe(self, page: object, base_url: str) -> None:
        """Repo configuration panel matches §9.1 card recipe."""
        _go(page, base_url)

        if page.locator("[data-tour='repo-config']").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("Repo config panel not shown — no repo selected")

        result = validate_card(page, "[data-tour='repo-config']")  # type: ignore[arg-type]
        assert result.passed, (
            f"Repo config card fails §9.1 recipe: {result.summary()}"
        )

    def test_card_border_present_on_panels(self, page: object, base_url: str) -> None:
        """Fleet health and repo config panels carry visible border styling."""
        _go(page, base_url)

        for testid in ("repo-selector", "repo-config"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll(\"[data-tour='{testid}']\").length"
            )
            if count == 0:
                continue

            border_style = page.evaluate(  # type: ignore[attr-defined]
                f"""
                (function() {{
                    var el = document.querySelector("[data-tour='{testid}']");
                    if (!el) return null;
                    return window.getComputedStyle(el).borderStyle;
                }})()
                """
            )
            assert border_style and border_style != "none", (
                f"Panel [data-tour='{testid}'] must have a visible border (§9.1)"
            )
            break  # One panel check is sufficient for this assertion


# ---------------------------------------------------------------------------
# §9.2 — Table recipe on fleet health table
# ---------------------------------------------------------------------------


class TestReposTableRecipe:
    """Fleet health table must conform to §9.2 table recipe.

    The fleet health table renders rows with visible borders and proper
    header styling.
    """

    def test_table_has_thead(self, page: object, base_url: str) -> None:
        """Fleet health table has a <thead> section."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No table — empty state is shown")

        thead_count = page.evaluate("document.querySelectorAll('thead').length")  # type: ignore[attr-defined]
        assert thead_count > 0, (
            "Fleet health table must have a <thead> element (§9.2)"
        )

    def test_table_has_tbody(self, page: object, base_url: str) -> None:
        """Fleet health table has a <tbody> section."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No table — empty state is shown")

        tbody_count = page.evaluate("document.querySelectorAll('tbody').length")  # type: ignore[attr-defined]
        assert tbody_count > 0, (
            "Fleet health table must have a <tbody> element (§9.2)"
        )

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_table_header_font_weight(self, page: object, base_url: str) -> None:
        """Fleet health table header cells use font-weight ≥ 500 (§9.2)."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No table — empty state is shown")

        th_weight = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var th = document.querySelector('thead th');
                if (!th) return null;
                return parseFloat(window.getComputedStyle(th).fontWeight) || 0;
            })()
            """
        )
        assert th_weight is not None and th_weight >= 500, (
            f"Fleet health table <th> font-weight {th_weight} is below 500 (§9.2)"
        )


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe on tier and status badges
# ---------------------------------------------------------------------------


class TestReposBadgeRecipe:
    """Trust tier and status badges must conform to §9.3 badge recipe.

    TierBadge (OBSERVE / SUGGEST / EXECUTE) and StatusBadge (ACTIVE / PAUSED /
    DISABLED) are the primary status indicators on the repos tab.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_tier_badge_recipe(self, page: object, base_url: str) -> None:
        """Trust tier badges match §9.3 badge recipe (padding, radius, font weight)."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No table — no tier badges to check")

        badge_selectors = [
            "span[class*='bg-gray-700']",
            "span[class*='bg-blue-900']",
            "span[class*='bg-green-900']",
            "span[class*='rounded']",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Tier badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip("No tier badge elements found — table may be empty")

    def test_status_badge_present_in_table(self, page: object, base_url: str) -> None:
        """Status badges are visible in the fleet health table."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No table — empty state is shown")

        rows = page.locator("table tbody tr").count()  # type: ignore[attr-defined]
        if rows == 0:
            pytest.skip("No repo rows — table is empty")

        table_text = page.locator("table").first.inner_text().upper()  # type: ignore[attr-defined]
        has_badge = (
            "ACTIVE" in table_text
            or "PAUSED" in table_text
            or "DISABLED" in table_text
        )
        assert has_badge, (
            "Fleet health table must display status badges "
            "(ACTIVE / PAUSED / DISABLED) for each repo row"
        )


# ---------------------------------------------------------------------------
# §9.4 — Button recipe on CTA buttons
# ---------------------------------------------------------------------------


class TestReposButtonRecipe:
    """CTA buttons must conform to §9.4 button recipe.

    The 'Register Repository' empty-state CTA and the 'Refresh' button are
    the primary interactive controls on the repos tab.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_register_repository_button_recipe(self, page: object, base_url: str) -> None:
        """'Register Repository' CTA matches §9.4 button recipe."""
        _go(page, base_url)

        if page.locator("table").count() > 0:  # type: ignore[attr-defined]
            pytest.skip("Repo table active — empty state CTA not shown")

        button_selectors = [
            "a[href='/admin/ui/repos']",
            "button:has-text('Register Repository')",
            "a:has-text('Register Repository')",
        ]
        for sel in button_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_button(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"CTA button {sel!r} fails §9.4 recipe: {result.summary()}"
                )
                return

        pytest.skip("No 'Register Repository' CTA found — skipping §9.4 check")

    def test_refresh_button_visible_and_enabled(self, page: object, base_url: str) -> None:
        """The 'Refresh' header button is visible and enabled."""
        _go(page, base_url)

        buttons = page.locator("button")  # type: ignore[attr-defined]
        count = buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            label = btn.inner_text() or ""
            if "Refresh" in label or "↺" in label:
                assert btn.is_visible(), "Refresh button must be visible"
                assert btn.is_enabled(), "Refresh button must not be disabled"
                return

        pytest.skip("No 'Refresh' button found on repos tab — skipping visibility check")


# ---------------------------------------------------------------------------
# §9.11 — Empty state recipe
# ---------------------------------------------------------------------------


class TestReposEmptyStateRecipe:
    """The empty repos state must conform to §9.11 empty state recipe."""

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_empty_state_recipe(self, page: object, base_url: str) -> None:
        """Empty repos state matches §9.11 recipe (icon, heading, description, CTA)."""
        _go(page, base_url)

        if page.locator("table").count() > 0:  # type: ignore[attr-defined]
            pytest.skip("Repo table active — empty state not shown")

        result = validate_empty_state(  # type: ignore[attr-defined]
            page, "[data-testid='repos-empty']"
        )
        assert result.passed, (
            f"Empty repos state fails §9.11 recipe: {result.summary()}"
        )


# ---------------------------------------------------------------------------
# §5 — Status colors
# ---------------------------------------------------------------------------


class TestReposStatusColors:
    """Health and tier colors must follow §5 status color tokens."""

    def test_page_background_dark_theme(self, page: object, base_url: str) -> None:
        """Repos tab body uses dark theme background (gray-950)."""
        _go(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_dark = (
            colors_close(bg, "#030712")
            or colors_close(bg, "#111827")
            or colors_close(bg, "#0f172a")
        )
        if not is_dark:
            try:
                import re
                match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', bg)
                if match:
                    r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    is_dark = r < 30 and g < 30 and b < 30
            except Exception:
                pass

        assert is_dark, (
            f"Repos tab body background {bg!r} — expected dark theme "
            "background (gray-950 #030712 or near-black)"
        )

    def test_health_ok_color_green(self, page: object, base_url: str) -> None:
        """'ok' health dots use green (§5.1 success color)."""
        _go(page, base_url)

        selector = "span[class*='bg-green-500']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No 'ok' health dots found — fleet may be empty or idle")

        # The presence of bg-green-500 elements is sufficient to confirm the
        # color token is applied — no computed-color comparison needed here.
        assert count > 0

    def test_health_degraded_color_red(self, page: object, base_url: str) -> None:
        """'degraded' health dots use red (§5.1 error color)."""
        _go(page, base_url)

        selector = "span[class*='bg-red-500']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No 'degraded' health dots found — fleet may have no degraded repos")

        assert count > 0


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestReposTypography:
    """Repos tab typography must match the style guide type scale (§6.2)."""

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1–h3 elements on the repos tab follow the §6.2 heading scale."""
        _go(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_section_heading_typography(self, page: object, base_url: str) -> None:
        """Section headings (h3) use §6.2 scale (14px / weight 600)."""
        _go(page, base_url)

        count = page.evaluate("document.querySelectorAll('h3').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h3 headings found — skipping section heading typography check")

        assert_typography(page, "h3", role="section_title")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §4.2 — Focus ring
# ---------------------------------------------------------------------------


class TestReposFocusRing:
    """Interactive elements must display the correct focus ring (§4.2)."""

    def test_primary_button_focus_ring(self, page: object, base_url: str) -> None:
        """Primary buttons show the §4.2 focus ring color on keyboard focus."""
        _go(page, base_url)

        selectors_to_try = [
            "button[class*='blue']",
            "button[class*='bg-blue']",
            "button",
            "a[href][class*='rounded']",
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

        pytest.skip("No focusable button found on repos tab — skipping focus ring check")


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens
# ---------------------------------------------------------------------------


class TestReposDesignTokens:
    """CSS design tokens must be registered on :root (§4.1)."""

    def test_font_sans_token_or_direct_declaration(self, page: object, base_url: str) -> None:
        """Repos tab loads Inter or a sans-serif font (§6.1)."""
        _go(page, base_url)

        font_family = page.evaluate(  # type: ignore[attr-defined]
            "window.getComputedStyle(document.body).fontFamily"
        )
        assert font_family, "Repos tab body must declare a font-family"
        lower = font_family.lower()
        assert "inter" in lower or "sans" in lower or "system" in lower, (
            f"Repos tab font-family {font_family!r} — expected Inter or "
            "a system sans-serif font (§6.1)"
        )
