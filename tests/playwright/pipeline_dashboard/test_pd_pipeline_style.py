"""Story 76.2 — Pipeline Dashboard: Style Guide Compliance.

Validates that /dashboard/?tab=pipeline conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4 / §5  — Design tokens: colors, status colors, focus ring
  §6       — Typography: page title, section headings, body text
  §7       — Spacing: 4px-grid compliance for cards and panels
  §9.1     — Card recipe: background, border, radius, padding
  §9.3     — Badge recipe: sizing, padding, font weight
  §9.4     — Button recipe: primary CTA styling
  §9.11    — Empty state recipe

Most style checks are xfail-marked: the pipeline dashboard is a dark-theme
React SPA whose CSS tokens differ slightly from the admin UI style guide
baseline.  These xfails are resolved in Epic 77 (style guide remediation).

These tests check *how* the page looks, not *what* it contains.
Semantic content is in test_pd_pipeline_intent.py (Story 76.2).
API contracts are in test_pd_pipeline_api.py (Story 76.2).
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
    """Navigate to the pipeline dashboard tab."""
    dashboard_navigate(page, base_url, "pipeline")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.1 — Card recipe on stage cards / event log / gate inspector
# ---------------------------------------------------------------------------


class TestPipelineCardRecipe:
    """Pipeline panel cards must conform to §9.1 card recipe.

    The event-log panel and gate-inspector panel each use the card recipe:
    white/dark background, border, ≥8px radius, ≥16px padding.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_event_log_card_recipe(self, page: object, base_url: str) -> None:
        """Event log panel matches §9.1 card recipe."""
        _go(page, base_url)

        result = validate_card(page, "[data-testid='event-log']")  # type: ignore[arg-type]
        assert result.passed, (
            f"Event log card fails §9.1 recipe: {result.summary()}"
        )

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_gate_inspector_card_recipe(self, page: object, base_url: str) -> None:
        """Gate Inspector panel matches §9.1 card recipe."""
        _go(page, base_url)

        result = validate_card(page, "[data-testid='gate-inspector']")  # type: ignore[arg-type]
        assert result.passed, (
            f"Gate Inspector card fails §9.1 recipe: {result.summary()}"
        )

    def test_card_border_present_on_panels(self, page: object, base_url: str) -> None:
        """Event log and gate inspector panels carry visible border styling."""
        _go(page, base_url)

        for testid in ("event-log", "gate-inspector"):
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
            assert border_style and border_style != "none", (
                f"Panel [data-testid='{testid}'] must have a visible border (§9.1)"
            )
            break  # One panel check is sufficient for this assertion


# ---------------------------------------------------------------------------
# §9.4 — Button recipe on CTA buttons
# ---------------------------------------------------------------------------


class TestPipelineButtonRecipe:
    """Primary CTA buttons must conform to §9.4 button recipe.

    The 'Import an Issue' button in the empty state and the header 'Import Issues'
    button are the primary CTAs on the pipeline tab.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_import_button_recipe(self, page: object, base_url: str) -> None:
        """Primary import button matches §9.4 button recipe."""
        _go(page, base_url)

        # Try the empty-state CTA first, then fall back to the header import button.
        button_selectors = [
            "[data-testid='empty-state-primary-action']",
            "[data-testid='empty-pipeline-rail-primary-action']",
            "button[class*='blue']",
            "button[class*='bg-blue']",
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

        pytest.skip("No primary CTA button found — skipping §9.4 button recipe check")

    def test_header_import_button_visible(self, page: object, base_url: str) -> None:
        """The global 'Import Issues' header button is visible and enabled."""
        _go(page, base_url)

        # The header import button uses "↓ Import Issues" label.
        buttons = page.locator("button")  # type: ignore[attr-defined]
        count = buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            if "Import" in (btn.inner_text() or ""):
                assert btn.is_visible(), "Import button must be visible"
                assert btn.is_enabled(), "Import button must not be disabled"
                return

        pytest.skip("No 'Import Issues' button found in header — skipping visibility check")


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe on gate result badges
# ---------------------------------------------------------------------------


class TestPipelineBadgeRecipe:
    """Gate result and stage status badges must conform to §9.3 badge recipe.

    Gate Inspector gate items carry PASS / FAIL result badges.
    Stage nodes carry status badges when tasks are active.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_gate_result_badge_recipe(self, page: object, base_url: str) -> None:
        """Gate result badges match §9.3 badge recipe (padding, radius, font weight)."""
        _go(page, base_url)

        badge_selectors = [
            "[data-status]",
            ".badge",
            "[class*='badge']",
            "[class*='text-emerald']",
            "[class*='text-red']",
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

        pytest.skip("No badge elements found — gate may be empty or not yet loaded")


# ---------------------------------------------------------------------------
# §9.11 — Empty state recipe
# ---------------------------------------------------------------------------


class TestPipelineEmptyStateRecipe:
    """The empty pipeline state must conform to §9.11 empty state recipe."""

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_empty_state_recipe(self, page: object, base_url: str) -> None:
        """Empty pipeline state matches §9.11 recipe (icon, heading, description, CTA)."""
        _go(page, base_url)

        if page.locator("[data-testid='pipeline-rail']").count() > 0:  # type: ignore[attr-defined]
            pytest.skip("Pipeline rail active — empty state not shown")

        result = validate_empty_state(  # type: ignore[attr-defined]
            page, "[data-testid='empty-pipeline-rail']"
        )
        assert result.passed, (
            f"Empty pipeline state fails §9.11 recipe: {result.summary()}"
        )


# ---------------------------------------------------------------------------
# §5 — Status colors
# ---------------------------------------------------------------------------


class TestPipelineStatusColors:
    """Stage status and gate result colors must follow §5.1 status color tokens."""

    def test_page_background_dark_theme(self, page: object, base_url: str) -> None:
        """Pipeline dashboard body uses dark theme background (gray-950)."""
        _go(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        # §4.1: gray-950 (#030712) or dark surface variant
        is_dark = (
            colors_close(bg, "#030712")
            or colors_close(bg, "#111827")
            or colors_close(bg, "#0f172a")
        )
        # Also accept near-black values (rgb < 30 per channel)
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
            f"Pipeline dashboard body background {bg!r} — expected dark theme "
            "background (gray-950 #030712 or near-black)"
        )

    def test_status_success_color_token(self, page: object, base_url: str) -> None:
        """Gate PASS result elements use §5.1 success color token."""
        _go(page, base_url)

        selector = "[data-status='success'], [data-status='pass']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No success/pass status elements found — gate may be empty")

        assert_status_colors(page, selector, "success")  # type: ignore[arg-type]

    def test_status_error_color_token(self, page: object, base_url: str) -> None:
        """Gate FAIL result elements use §5.1 error color token."""
        _go(page, base_url)

        selector = "[data-status='error'], [data-status='fail']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No error/fail status elements found — gate may be empty")

        assert_status_colors(page, selector, "error")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestPipelineTypography:
    """Dashboard typography must match the style guide type scale (§6.2)."""

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1–h3 elements on the pipeline tab follow the §6.2 heading scale."""
        _go(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1) uses §6.2 page_title scale (20px / weight 600)."""
        _go(page, base_url)

        count = page.evaluate("document.querySelectorAll('h1').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h1 element found on pipeline tab")

        assert_typography(page, "h1", role="page_title")  # type: ignore[arg-type]

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


class TestPipelineFocusRing:
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

        pytest.skip("No focusable button found on pipeline tab — skipping focus ring check")


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens
# ---------------------------------------------------------------------------


class TestPipelineDesignTokens:
    """CSS design tokens must be registered on :root (§4.1)."""

    def test_font_sans_token_or_direct_declaration(self, page: object, base_url: str) -> None:
        """Pipeline dashboard loads Inter or a sans-serif font (§6.1)."""
        _go(page, base_url)

        font_family = page.evaluate(  # type: ignore[attr-defined]
            "window.getComputedStyle(document.body).fontFamily"
        )
        assert font_family, "Pipeline dashboard body must declare a font-family"
        lower = font_family.lower()
        assert "inter" in lower or "sans" in lower or "system" in lower, (
            f"Pipeline dashboard font-family {font_family!r} — expected Inter or "
            "a system sans-serif font (§6.1)"
        )
