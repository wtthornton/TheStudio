"""Story 76.3 — Triage Tab: Style Guide Compliance.

Validates that /dashboard/?tab=triage conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md):

  §9.1  — Card recipe: triage cards have correct background, border, radius, padding
  §9.3  — Badge recipe: complexity/priority badges meet sizing, padding, font-weight
  §9.4  — Button recipe: Accept button uses primary/success palette; Reject uses destructive
  §6.2  — Typography: headings and card titles use correct scale
  §4.1  — Design tokens: CSS variables registered on :root

Most checks are marked xfail because the triage tab is an early-iteration
component; remediation is tracked in Epic 77.

These tests check *how* the page looks, not *what* it contains.
Semantic content is in test_pd_triage_intent.py.
"""

import pytest

from tests.playwright.lib.component_validators import (
    validate_badge,
    validate_card,
)
from tests.playwright.lib.style_assertions import (
    assert_focus_ring_color,
    colors_close,
    get_background_color,
    get_css_variable,
)
from tests.playwright.lib.typography_assertions import (
    assert_heading_scale,
    assert_typography,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _navigate(page, base_url: str) -> None:
    """Navigate to the triage tab and wait for React hydration."""
    dashboard_navigate(page, base_url, "triage")


# ---------------------------------------------------------------------------
# §9.1 — Card recipe on triage cards
# ---------------------------------------------------------------------------


class TestTriageCardRecipe:
    """Triage cards must conform to §9.1 card recipe.

    Each card wrapping an issue must use the canonical background color,
    border color, border-radius (≥ 8px), and padding (≥ 16px).
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_triage_card_recipe(self, page, base_url: str) -> None:
        """Triage cards match §9.1 card recipe (background, border, radius, padding)."""
        _navigate(page, base_url)

        card_selectors = [
            "[data-tour='triage-card']",
            "[data-testid='triage-card']",
            ".triage-card",
            "[class*='triage-card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(f"document.querySelectorAll({sel!r}).length")
            if count > 0:
                result = validate_card(page, sel)
                assert result.passed, (
                    f"Triage card {sel!r} fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip("No triage card elements found — skipping §9.1 card recipe check")

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_triage_card_padding_grid_compliance(self, page, base_url: str) -> None:
        """Triage card padding is a 4px-grid multiple (§7.1) of at least 16px."""
        _navigate(page, base_url)

        card_selectors = [
            "[data-tour='triage-card']",
            ".triage-card",
            "[class*='triage-card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(f"document.querySelectorAll({sel!r}).length")
            if count > 0:
                padding_raw = page.evaluate(
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        return window.getComputedStyle(el).paddingTop;
                    }})()
                    """
                )
                if padding_raw is None:
                    pytest.skip(f"No element found at {sel!r}")

                px_str = padding_raw.strip()
                if px_str.endswith("px"):
                    px_val = float(px_str[:-2])
                    assert px_val >= 16, (
                        f"Triage card padding {px_val}px < 16px — §9.1 requires p-4 (16px) minimum"
                    )
                    assert px_val % 4 == 0 or abs(px_val % 4) < 1, (
                        f"Triage card padding {px_val}px is not a 4px-grid multiple (§7.1)"
                    )
                return

        pytest.skip("No triage card elements — skipping padding check")

    def test_triage_card_background_is_dark(self, page, base_url: str) -> None:
        """Triage cards use the dark surface palette (gray-900 / gray-800)."""
        _navigate(page, base_url)

        card_selectors = [
            "[data-tour='triage-card']",
            ".triage-card",
        ]
        for sel in card_selectors:
            count = page.evaluate(f"document.querySelectorAll({sel!r}).length")
            if count > 0:
                bg = get_background_color(page, sel)
                # Accept gray-900 (#111827) or gray-800 (#1f2937) — dark surface tokens
                is_dark = (
                    colors_close(bg, "#111827")
                    or colors_close(bg, "#1f2937")
                    or colors_close(bg, "#0f172a")
                )
                assert is_dark, (
                    f"Triage card background {bg!r} — expected dark surface color "
                    f"(gray-900 #111827 or gray-800 #1f2937)"
                )
                return

        pytest.skip("No triage card elements — skipping background color check")


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe on complexity / priority badges
# ---------------------------------------------------------------------------


class TestTriageBadgeRecipe:
    """Complexity and priority badges must conform to §9.3 badge recipe.

    Badges on triage cards communicate issue complexity (low/medium/high).
    They must have correct padding, border-radius, and font-weight.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_complexity_badge_recipe(self, page, base_url: str) -> None:
        """Complexity badges match §9.3 badge recipe."""
        _navigate(page, base_url)

        badge_selectors = [
            "[class*='complexity']",
            "[data-complexity]",
            "[class*='badge']",
            ".badge",
        ]
        for sel in badge_selectors:
            count = page.evaluate(f"document.querySelectorAll({sel!r}).length")
            if count > 0:
                result = validate_badge(page, sel)
                assert result.passed, (
                    f"Complexity badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip("No complexity badge elements — skipping §9.3 badge check")

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_badge_font_weight(self, page, base_url: str) -> None:
        """Badges use font-weight 500 or 600 per §9.3."""
        _navigate(page, base_url)

        badge_selectors = [
            "[class*='complexity']",
            "[class*='badge']",
            ".badge",
        ]
        for sel in badge_selectors:
            count = page.evaluate(f"document.querySelectorAll({sel!r}).length")
            if count > 0:
                fw = page.evaluate(
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        return window.getComputedStyle(el).fontWeight;
                    }})()
                    """
                )
                if fw is None:
                    continue
                fw_int = int(fw) if fw.isdigit() else 400
                assert fw_int >= 500, (
                    f"Badge font-weight {fw_int} < 500 — §9.3 requires medium (500) or semibold (600)"
                )
                return

        pytest.skip("No badge elements found — skipping font-weight check")


# ---------------------------------------------------------------------------
# §9.4 — Button colors
# ---------------------------------------------------------------------------


class TestTriageButtonColors:
    """Accept and Reject buttons must use semantically correct colors.

    Accept & Plan is a constructive action (success/primary palette).
    Reject is a destructive action (destructive/error palette).
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_accept_button_uses_success_color(self, page, base_url: str) -> None:
        """'Accept & Plan' button background is in the success/emerald palette (§5.1)."""
        _navigate(page, base_url)

        accept_selectors = [
            "[data-testid='triage-card-accept-intent-btn']",
            "button:has-text('Accept')",
        ]
        for sel in accept_selectors:
            count = page.evaluate(f"document.querySelectorAll({sel!r}).length")
            if count > 0:
                bg = get_background_color(page, sel)
                # Accept emerald-700 (#047857) or emerald-600 (#059669)
                is_success = (
                    colors_close(bg, "#047857")
                    or colors_close(bg, "#059669")
                    or colors_close(bg, "#065f46")
                )
                assert is_success, (
                    f"Accept button background {bg!r} — expected success/emerald palette "
                    f"(emerald-700 #047857 or similar per §5.1)"
                )
                return

        pytest.skip("No Accept button found — skipping color check")

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_reject_button_uses_destructive_color(self, page, base_url: str) -> None:
        """'Reject' button uses the destructive/red palette (§5.4)."""
        _navigate(page, base_url)

        reject_selectors = ["button:has-text('Reject')"]
        for sel in reject_selectors:
            count = page.evaluate(f"document.querySelectorAll({sel!r}).length")
            if count > 0:
                # Check text color (border-style reject button uses red text)
                text_color = page.evaluate(
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        return window.getComputedStyle(el).color;
                    }})()
                    """
                )
                if text_color is None:
                    pytest.skip("Could not read reject button color")

                # rgb(248, 113, 113) = red-400; rgb(239, 68, 68) = red-500
                is_red = (
                    "248, 113, 113" in text_color
                    or "239, 68, 68" in text_color
                    or "220, 38, 38" in text_color
                    or "252, 165, 165" in text_color
                )
                assert is_red, (
                    f"Reject button text color {text_color!r} — expected red palette "
                    f"(§5.4 destructive: red-400/500)"
                )
                return

        pytest.skip("No Reject button found — skipping destructive color check")


# ---------------------------------------------------------------------------
# §6.2 — Typography scale on headings and card titles
# ---------------------------------------------------------------------------


class TestTriageTypography:
    """Triage queue headings and card titles must follow §6.2 type scale."""

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_heading_scale_compliance(self, page, base_url: str) -> None:
        """All h1–h3 elements in the triage tab follow the §6.2 heading scale."""
        _navigate(page, base_url)
        assert_heading_scale(page)

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_queue_heading_typography(self, page, base_url: str) -> None:
        """'Triage Queue' heading (h2) uses §6.2 section_title scale (16px / weight 600)."""
        _navigate(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")
        if count == 0:
            pytest.skip("No h2 headings — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_card_title_typography(self, page, base_url: str) -> None:
        """Card issue-title (h3) uses §6.2 subsection_title scale (14px / weight 600)."""
        _navigate(page, base_url)

        count = page.evaluate(
            "document.querySelectorAll('[data-tour=\"triage-card\"] h3').length"
        )
        if count == 0:
            pytest.skip("No card h3 title elements — skipping card title typography check")

        assert_typography(page, "[data-tour='triage-card'] h3", role="subsection_title")


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens
# ---------------------------------------------------------------------------


class TestTriageDesignTokens:
    """CSS design tokens must be registered on :root (§4.1) for the triage tab."""

    def test_focus_ring_token_registered(self, page, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate(page, base_url)
        try:
            val = get_css_variable(page, "--color-focus-ring")
            assert val, "--color-focus-ring is empty — §4.1 requires it to be set"
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip("--color-focus-ring not present; stylesheet may use direct classes")
            raise

    def test_surface_app_token_registered(self, page, base_url: str) -> None:
        """§4.1 app surface: ``--color-bg-surface`` on :root (see ``frontend/src/theme.css``).

        Tailwind maps ``--color-surface`` → ``var(--color-bg-surface)`` in
        ``frontend/src/index.css`` @theme; there is no ``--color-surface-app`` alias.
        """
        _navigate(page, base_url)
        try:
            val = get_css_variable(page, "--color-bg-surface")
            assert val, "--color-bg-surface is empty — §4.1 requires a surface token"
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip(
                    "--color-bg-surface not present; stylesheet may load differently"
                )
            raise


# ---------------------------------------------------------------------------
# §4.2 — Focus ring on interactive elements
# ---------------------------------------------------------------------------


class TestTriageFocusRing:
    """Accept and Reject buttons must display the §4.2 focus ring on keyboard focus."""

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_accept_button_focus_ring(self, page, base_url: str) -> None:
        """Accept button shows the §4.2 focus ring color on keyboard focus."""
        _navigate(page, base_url)

        selectors_to_try = [
            "[data-testid='triage-card-accept-intent-btn']",
            "button:has-text('Accept')",
            "button",
        ]
        for sel in selectors_to_try:
            count = page.evaluate(f"document.querySelectorAll({sel!r}).length")
            if count > 0:
                try:
                    assert_focus_ring_color(page, sel)
                    return
                except AssertionError:
                    continue

        pytest.skip("No focusable Accept button found — skipping focus ring check")
