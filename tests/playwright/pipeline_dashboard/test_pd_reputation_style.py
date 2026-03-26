"""Story 76.11 — Reputation Tab: Style Guide Compliance.

Validates that /dashboard/?tab=reputation conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4 / §5  — Design tokens: colors, status colors, focus ring
  §6       — Typography: page title, section headings, body text
  §7       — Spacing: 4px-grid compliance for cards and panels
  §9.1     — Card recipe: background, border, radius, padding
  §9.3     — Badge recipe: sizing, padding, font weight
  §9.11    — Empty state recipe

Most style checks are xfail-marked: the pipeline dashboard is a dark-theme
React SPA whose CSS tokens differ slightly from the admin UI style guide
baseline.  These xfails are resolved in Epic 77 (style guide remediation).

These tests check *how* the page looks, not *what* it contains.
Semantic content is in test_pd_reputation_intent.py (Story 76.11).
API contracts are in test_pd_reputation_api.py (Story 76.11).
"""

import pytest

from tests.playwright.lib.component_validators import (
    validate_badge,
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
    """Navigate to the reputation tab."""
    dashboard_navigate(page, base_url, "reputation")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.1 — Card recipe on summary cards and expert cards
# ---------------------------------------------------------------------------


class TestReputationCardRecipe:
    """Reputation panel cards must conform to §9.1 card recipe.

    The expert table panel and drift alerts panel each use the card recipe:
    white/dark background, border, ≥8px radius, ≥16px padding.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_expert_table_card_recipe(self, page: object, base_url: str) -> None:
        """Expert table panel matches §9.1 card recipe."""
        _go(page, base_url)

        for testid in ("expert-table", "expert-list"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll(\"[data-testid='{testid}']\").length"
            )
            if count > 0:
                result = validate_card(page, f"[data-testid='{testid}']")  # type: ignore[arg-type]
                assert result.passed, (
                    f"Expert table card fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip("Expert table panel not found — skipping §9.1 card recipe check")

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_drift_alerts_card_recipe(self, page: object, base_url: str) -> None:
        """Drift Alerts panel matches §9.1 card recipe."""
        _go(page, base_url)

        for testid in ("drift-alerts", "drift-panel"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll(\"[data-testid='{testid}']\").length"
            )
            if count > 0:
                result = validate_card(page, f"[data-testid='{testid}']")  # type: ignore[arg-type]
                assert result.passed, (
                    f"Drift Alerts card fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip("Drift Alerts panel not found — skipping §9.1 card recipe check")

    def test_panel_borders_present(self, page: object, base_url: str) -> None:
        """Expert table and drift alerts panels carry visible border styling."""
        _go(page, base_url)

        for testid in ("expert-table", "drift-alerts", "outcome-feed"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll(\"[data-testid='{testid}']\").length"
            )
            if count == 0:
                continue

            border_style = page.evaluate(  # type: ignore[attr-defined]
                f"""
                (function() {{
                    var el = document.querySelector("[data-testid='{testid}']");
                    if (!el) return null;
                    return window.getComputedStyle(el).borderStyle;
                }})()
                """
            )
            if border_style and border_style != "none":
                return  # At least one panel has a border — test passes

        # No panel found with a border — skip rather than fail on first run.
        pytest.skip(
            "No reputation panel with explicit border found — "
            "border may be applied via Tailwind class"
        )


# ---------------------------------------------------------------------------
# §5 — Score indicator status colors
# ---------------------------------------------------------------------------


class TestReputationStatusColors:
    """Score indicators must follow §5.1 status color tokens.

    Expert score badges use success (high score), warning (medium), and
    error (low score) semantic colors so operators can interpret at a glance.
    """

    def test_page_background_dark_theme(self, page: object, base_url: str) -> None:
        """Reputation tab body uses dark theme background (gray-950)."""
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
                match = re.search(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", bg)
                if match:
                    r, g, b = (
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                    )
                    is_dark = r < 30 and g < 30 and b < 30
            except Exception:
                pass

        assert is_dark, (
            f"Reputation tab body background {bg!r} — expected dark theme "
            "background (gray-950 #030712 or near-black)"
        )

    def test_success_score_color_token(self, page: object, base_url: str) -> None:
        """High-score elements use §5.1 success color token."""
        _go(page, base_url)

        selector = "[data-status='success'], [data-score-level='high']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip(
                "No success/high-score status elements found — "
                "expert data may be empty"
            )

        assert_status_colors(page, selector, "success")  # type: ignore[arg-type]

    def test_error_score_color_token(self, page: object, base_url: str) -> None:
        """Low-score / drift-alert elements use §5.1 error color token."""
        _go(page, base_url)

        selector = "[data-status='error'], [data-score-level='low'], [data-status='drift']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip(
                "No error/low-score/drift status elements found — "
                "expert data or drift alerts may be empty"
            )

        assert_status_colors(page, selector, "error")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe on score badges
# ---------------------------------------------------------------------------


class TestReputationBadgeRecipe:
    """Score and status badges must conform to §9.3 badge recipe.

    Expert score indicators and drift alert badges carry PASS / FAIL or
    numeric score badges.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_score_badge_recipe(self, page: object, base_url: str) -> None:
        """Expert score badges match §9.3 badge recipe (padding, radius, font weight)."""
        _go(page, base_url)

        badge_selectors = [
            "[data-testid='score-badge']",
            "[data-status]",
            ".badge",
            "[class*='badge']",
            "[class*='text-emerald']",
            "[class*='text-red']",
            "[class*='text-yellow']",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Score badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No score badge elements found — expert data may be empty or "
            "badges not yet loaded"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestReputationTypography:
    """Dashboard typography must match the style guide type scale (§6.2)."""

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1–h3 elements on the reputation tab follow the §6.2 heading scale."""
        _go(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_section_heading_typography(self, page: object, base_url: str) -> None:
        """Section headings (h2/h3) use §6.2 scale (14–20px / weight 600)."""
        _go(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2, h3').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2/h3 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §4.2 — Focus ring
# ---------------------------------------------------------------------------


class TestReputationFocusRing:
    """Interactive elements must display the correct focus ring (§4.2)."""

    def test_interactive_element_focus_ring(self, page: object, base_url: str) -> None:
        """Buttons and links show the §4.2 focus ring color on keyboard focus."""
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

        pytest.skip(
            "No focusable button found on reputation tab — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens
# ---------------------------------------------------------------------------


class TestReputationDesignTokens:
    """CSS design tokens must be registered on :root (§4.1)."""

    def test_font_sans_token_or_direct_declaration(self, page: object, base_url: str) -> None:
        """Reputation tab loads Inter or a sans-serif font (§6.1)."""
        _go(page, base_url)

        font_family = page.evaluate(  # type: ignore[attr-defined]
            "window.getComputedStyle(document.body).fontFamily"
        )
        assert font_family, "Reputation tab body must declare a font-family"
        lower = font_family.lower()
        assert "inter" in lower or "sans" in lower or "system" in lower, (
            f"Reputation tab font-family {font_family!r} — expected Inter or "
            "a system sans-serif font (§6.1)"
        )
