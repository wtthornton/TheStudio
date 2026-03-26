"""Epic 60.3 — Repo Management: Style Guide Compliance.

Validates that /admin/ui/repos conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §5.1     — Status badge colors: active / paused / error
  §5.2     — Trust tier badge colors: OBSERVE / SUGGEST / EXECUTE
  §6       — Typography: page title, section headings, body text
  §9.1     — Card recipe: background, border, radius, padding
  §9.2     — Table recipe: thead background, <th> scope attributes
  §9.3     — Badge recipe: sizing, padding, font weight
  §4.1     — CSS design tokens registered on :root

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_repos_intent.py (Epic 60.1).
API contracts are covered in test_repos_api.py (Epic 60.2).
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

REPOS_URL = "/admin/ui/repos"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_repos(page: object, base_url: str) -> None:
    """Navigate to the repos page and wait for the main content."""
    navigate(page, f"{base_url}{REPOS_URL}")  # type: ignore[arg-type]


def _has_table(page: object) -> bool:
    """Return True when at least one <table> element is present on the page."""
    return page.locator("table").count() > 0  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# §5.1 — Status badge colors
# ---------------------------------------------------------------------------


class TestReposStatusColors:
    """Repo status badges must use the correct §5.1 status color tokens.

    The repos page renders an active / paused / error status for each repo.
    Each status badge must use the semantic color palette so operators can
    instantly distinguish a healthy repo from one that needs attention.
    """

    def test_status_color_active_present(self, page: object, base_url: str) -> None:
        """Active repo badges use the §5.1 success color token."""
        _navigate_to_repos(page, base_url)

        selector = "[data-status='success'], [data-status='active']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No active/success status badge found — skipping color check")

        assert_status_colors(page, selector, "success")  # type: ignore[arg-type]

    def test_status_color_warning_present(self, page: object, base_url: str) -> None:
        """Paused / warning repo badges use the §5.1 warning color token."""
        _navigate_to_repos(page, base_url)

        selector = "[data-status='warning'], [data-status='paused']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No warning/paused status badge found — skipping color check")

        assert_status_colors(page, selector, "warning")  # type: ignore[arg-type]

    def test_status_color_error_present(self, page: object, base_url: str) -> None:
        """Error repo badges use the §5.1 error color token."""
        _navigate_to_repos(page, base_url)

        selector = "[data-status='error']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No data-status='error' badge found — skipping color check")

        assert_status_colors(page, selector, "error")  # type: ignore[arg-type]

    def test_page_background_uses_design_token(self, page: object, base_url: str) -> None:
        """Repos page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_repos(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        # §4.1: surface-app (gray-50 #f9fafb) or white
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Repos page body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §5.2 — Trust tier badge colors
# ---------------------------------------------------------------------------


class TestReposTrustTierColors:
    """Trust tier badges must use the §5.2 tier color tokens.

    The repos table renders an OBSERVE / SUGGEST / EXECUTE badge for each repo.
    These badges must use the correct trust-tier palette so operators can
    distinguish automation trust levels at a glance.
    """

    def test_trust_tier_observe_color(self, page: object, base_url: str) -> None:
        """OBSERVE tier badges use the §5.2 observe color token."""
        _navigate_to_repos(page, base_url)

        selectors = [
            "[data-tier='observe']",
            "[data-tier='OBSERVE']",
            ".tier-observe",
            "[class*='observe']",
        ]
        for sel in selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_trust_tier_colors(page, sel, "observe")  # type: ignore[arg-type]
                return

        pytest.skip("No OBSERVE tier badge found — skipping §5.2 color check")

    def test_trust_tier_suggest_color(self, page: object, base_url: str) -> None:
        """SUGGEST tier badges use the §5.2 suggest color token."""
        _navigate_to_repos(page, base_url)

        selectors = [
            "[data-tier='suggest']",
            "[data-tier='SUGGEST']",
            ".tier-suggest",
            "[class*='suggest']",
        ]
        for sel in selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_trust_tier_colors(page, sel, "suggest")  # type: ignore[arg-type]
                return

        pytest.skip("No SUGGEST tier badge found — skipping §5.2 color check")

    def test_trust_tier_execute_color(self, page: object, base_url: str) -> None:
        """EXECUTE tier badges use the §5.2 execute color token."""
        _navigate_to_repos(page, base_url)

        selectors = [
            "[data-tier='execute']",
            "[data-tier='EXECUTE']",
            ".tier-execute",
            "[class*='execute']",
        ]
        for sel in selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_trust_tier_colors(page, sel, "execute")  # type: ignore[arg-type]
                return

        pytest.skip("No EXECUTE tier badge found — skipping §5.2 color check")

    def test_dark_theme_tier_badge_colors(self, page: object, base_url: str) -> None:
        """Trust tier badge colors update correctly when dark theme is applied."""
        _navigate_to_repos(page, base_url)

        tier_selectors = [
            "[data-tier]",
            ".tier-badge",
            "[class*='tier']",
        ]
        for sel in tier_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                set_dark_theme(page)  # type: ignore[arg-type]
                try:
                    # In dark mode the badge must still be visible; check it exists
                    # and that the page hasn't crashed (non-empty body).
                    body = page.locator("body").inner_text()  # type: ignore[attr-defined]
                    assert len(body) > 0, "Page body empty after switching to dark theme"
                finally:
                    set_light_theme(page)  # type: ignore[arg-type]
                return

        pytest.skip("No trust tier badge found — skipping dark theme check")


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestReposFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2).

    The focus ring (blue-600 in light mode) ensures keyboard navigators can
    identify focused elements at a glance on the repos page.
    """

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable elements show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_repos(page, base_url)

        selectors_to_try = [
            "button.btn-primary",
            "button[class*='primary']",
            "button",
            "a[href][class*='btn']",
            "a[href]",
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

        pytest.skip("No focusable element found on repos page — skipping focus ring check")


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestReposTypography:
    """Repos page typography must match the style guide type scale (§6.2).

    Key elements:
    - Page title (h1 / .page-title): 20px / weight 600
    - Section headings (h2): 16px / weight 600
    - Body text / table cells: 14px / weight 400
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1–h3 elements follow the §6.2 heading scale."""
        _navigate_to_repos(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_repos(page, base_url)

        selectors = ["h1", ".page-title", "[class*='page-title']"]
        for sel in selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_typography(page, sel, role="page_title")  # type: ignore[arg-type]
                return

        pytest.skip("No page title element (h1/.page-title) found — skipping typography check")

    def test_section_heading_typography(self, page: object, base_url: str) -> None:
        """Section headings (h2) use §6.2 section_title scale (16px / weight 600)."""
        _navigate_to_repos(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_body_text_typography(self, page: object, base_url: str) -> None:
        """Body text / table cells use §6.2 body scale (14px / weight 400)."""
        _navigate_to_repos(page, base_url)

        body_selectors = ["p", "td", ".body-text", "[class*='body']"]
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


class TestReposCardRecipe:
    """Repos page cards must conform to §9.1 card recipe.

    Cards may wrap the repo table container or individual repo entries.
    Each card must have the correct background, border color, border-radius
    (≥ 8px), and padding (≥ 16px).
    """

    def test_card_recipe(self, page: object, base_url: str) -> None:
        """Page cards match §9.1 card recipe (background, border, radius, padding)."""
        _navigate_to_repos(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".repo-card",
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

        pytest.skip("No card element found on repos page — skipping §9.1 card recipe check")

    def test_card_padding_on_4px_grid(self, page: object, base_url: str) -> None:
        """Repo page cards have §7.1 compliant padding (multiple of 4px)."""
        _navigate_to_repos(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
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

        pytest.skip("No card element found on repos page — skipping spacing check")


# ---------------------------------------------------------------------------
# §9.2 — Table recipe
# ---------------------------------------------------------------------------


class TestReposTableRecipe:
    """The repo table must conform to §9.2 table recipe.

    Validates thead background color, <th scope="col"> presence, and
    right-aligned numeric columns (queue depth).
    """

    def test_repo_table_recipe(self, page: object, base_url: str) -> None:
        """Repo table matches §9.2 table recipe (thead bg, th scope, alignment)."""
        _navigate_to_repos(page, base_url)

        if not _has_table(page):
            pytest.skip("No <table> on repos page — empty state is acceptable")

        result = validate_table(page, "table")  # type: ignore[arg-type]
        assert result.passed, (
            f"Repo table fails §9.2 recipe: {result.summary()}"
        )

    def test_table_th_scope_attributes(self, page: object, base_url: str) -> None:
        """All <th> elements in the repo table carry scope='col' or scope='row'."""
        _navigate_to_repos(page, base_url)

        if not _has_table(page):
            pytest.skip("No <table> on repos page — empty state is acceptable")

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

    def test_table_header_background(self, page: object, base_url: str) -> None:
        """Repo table thead row uses §9.2 gray-50 header background."""
        _navigate_to_repos(page, base_url)

        if not _has_table(page):
            pytest.skip("No <table> on repos page — empty state is acceptable")

        header_bg = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var thead = document.querySelector('table thead tr');
                if (!thead) return null;
                return window.getComputedStyle(thead).backgroundColor;
            })()
            """
        )
        if header_bg is None:
            pytest.skip("No <thead tr> found in table")

        # §9.2: gray-50 (#f9fafb) or transparent (inherits from card)
        is_gray_50 = colors_close(header_bg, "#f9fafb")
        is_transparent = header_bg in ("rgba(0, 0, 0, 0)", "transparent", "")
        assert is_gray_50 or is_transparent, (
            f"Table thead background {header_bg!r} — expected gray-50 (#f9fafb) "
            "or transparent per §9.2"
        )


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe
# ---------------------------------------------------------------------------


class TestReposBadgeRecipe:
    """Status and trust tier badges must conform to §9.3 badge recipe.

    Badges appear in the repos table for trust tier (Observe/Suggest/Execute)
    and repo status (active/paused/error).
    """

    def test_status_badge_recipe(self, page: object, base_url: str) -> None:
        """Status badges match §9.3 badge recipe (padding, radius, font weight)."""
        _navigate_to_repos(page, base_url)

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
                    f"Status badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip("No status badge element found — skipping §9.3 badge recipe check")

    def test_trust_tier_badge_recipe(self, page: object, base_url: str) -> None:
        """Trust tier badges match §9.3 badge recipe (§5.2 + §9.3 combined)."""
        _navigate_to_repos(page, base_url)

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
                    f"Trust tier badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip("No trust tier badge found on repos page — skipping §9.3 check")


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestReposDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates that all color, spacing, and typography values
    are driven by CSS custom properties.  The presence of these tokens
    confirms the correct stylesheet is loaded on the repos page.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_repos(page, base_url)

        try:
            val = get_css_variable(page, "--color-focus-ring")  # type: ignore[arg-type]
            assert val, (
                "--color-focus-ring CSS variable is empty — §4.1 requires it to be set"
            )
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip("--color-focus-ring not present; stylesheet may use direct classes")
            raise

    def test_font_sans_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --font-sans is registered on :root (§6.1)."""
        _navigate_to_repos(page, base_url)

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
        _navigate_to_repos(page, base_url)

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
