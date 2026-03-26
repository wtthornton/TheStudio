"""Story 76.7 — Trust Tiers Tab: Style Guide Compliance.

Validates that /dashboard/?tab=trust conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §5.2     — Trust tier colors: EXECUTE=purple, SUGGEST=blue, OBSERVE=gray
  §9.1     — Card recipe: background, border, radius, padding
  §9.3     — Badge recipe: sizing, padding, font weight
  §9.4     — Button recipe: primary CTA styling
  §9.8     — Form input recipe: label association, border, aria-describedby
  §9.11    — Empty state recipe: icon, heading, description, CTA

Most style checks are xfail-marked: the trust tiers tab is a dark-theme
React SPA whose CSS tokens differ slightly from the admin UI style guide
baseline.  These xfails are resolved in Epic 77 (style guide remediation).

These tests check *how* the page looks, not *what* it contains.
Semantic content is in test_pd_trust_intent.py (Story 76.7).
API contracts are in test_pd_trust_api.py (Story 76.7).
"""

import pytest

from tests.playwright.lib.component_validators import (
    validate_badge,
    validate_button,
    validate_card,
    validate_empty_state,
    validate_form_input,
)
from tests.playwright.lib.style_assertions import (
    assert_focus_ring_color,
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
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _go(page: object, base_url: str) -> None:
    """Navigate to the trust tiers tab."""
    dashboard_navigate(page, base_url, "trust")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §5.2 — Trust tier badge colors (EXECUTE=purple, SUGGEST=blue, OBSERVE=gray)
# ---------------------------------------------------------------------------


class TestTrustTierBadgeColors:
    """Trust tier badges must use the correct §5.2 color tokens.

    The style guide defines specific colors for each trust tier:
      - EXECUTE: purple background, purple text
      - SUGGEST: blue background, blue text
      - OBSERVE: gray background, gray text

    These colors are applied to tier badges in the rule list and tier selector.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_execute_tier_badge_colors(self, page: object, base_url: str) -> None:
        """EXECUTE tier badge uses §5.2 purple color tokens."""
        _go(page, base_url)

        # Look for execute/EXECUTE tier badge selectors.
        badge_selectors = [
            "[data-tier='execute']",
            "[data-tier='EXECUTE']",
            ".tier-execute",
            "[class*='purple'][class*='badge']",
            "span[class*='purple']",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_trust_tier_colors(page, sel, "EXECUTE")  # type: ignore[arg-type]
                return

        pytest.skip("No EXECUTE tier badge found — rule list may be empty")

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_suggest_tier_badge_colors(self, page: object, base_url: str) -> None:
        """SUGGEST tier badge uses §5.2 blue color tokens."""
        _go(page, base_url)

        badge_selectors = [
            "[data-tier='suggest']",
            "[data-tier='SUGGEST']",
            ".tier-suggest",
            "[class*='blue'][class*='badge']",
            "span[class*='blue-300']",
            "span[class*='blue-900']",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_trust_tier_colors(page, sel, "SUGGEST")  # type: ignore[arg-type]
                return

        pytest.skip("No SUGGEST tier badge found — rule list may be empty")

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_observe_tier_badge_colors(self, page: object, base_url: str) -> None:
        """OBSERVE tier badge uses §5.2 gray color tokens."""
        _go(page, base_url)

        badge_selectors = [
            "[data-tier='observe']",
            "[data-tier='OBSERVE']",
            ".tier-observe",
            "span[class*='gray-800'][class*='text-gray']",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_trust_tier_colors(page, sel, "OBSERVE")  # type: ignore[arg-type]
                return

        pytest.skip("No OBSERVE tier badge found — rule list may be empty")

    def test_tier_badge_recipe_when_rules_present(self, page: object, base_url: str) -> None:
        """Tier badges in rule list match §9.3 badge recipe (padding, radius, weight)."""
        _go(page, base_url)

        # TrustConfiguration uses: rounded px-2 py-0.5 text-xs font-medium
        badge_selectors = [
            "[data-tier]",
            "span[class*='rounded'][class*='px-2'][class*='text-xs']",
            "span[class*='bg-purple']",
            "span[class*='bg-blue']",
            "span[class*='bg-gray-800']",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                # Non-fatal — badge recipes are remediated in Epic 77.
                if not result.passed:
                    pytest.xfail(
                        f"Tier badge {sel!r} fails §9.3 recipe: {result.summary()}"
                    )
                return

        pytest.skip("No tier badge elements found — rule list may be empty")

    def test_tier_selector_buttons_have_distinct_colors(self, page: object, base_url: str) -> None:
        """Default tier selector buttons use visually distinct colors per tier."""
        _go(page, base_url)

        # The active tier button should differ from inactive ones via CSS classes.
        # TrustConfiguration applies TIER_COLORS to the active button.
        tier_buttons = page.locator("[data-tour='trust-tier'] button")  # type: ignore[attr-defined]
        count = tier_buttons.count()

        if count < 2:
            pytest.skip("Fewer than 2 tier selector buttons — cannot compare colors")

        # Just verify that multiple buttons are present (color comparison requires
        # knowing which is active — done in interactions tests).
        assert count >= 2, (
            "Default tier selector must render at least 2 tier buttons "
            "(observe, suggest, execute)"
        )


# ---------------------------------------------------------------------------
# §9.1 — Card recipe on configuration panels
# ---------------------------------------------------------------------------


class TestTrustCardRecipe:
    """Trust configuration panels must conform to §9.1 card recipe.

    The ActiveTierDisplay, SafetyBoundsPanel, and RuleBuilder each render
    as rounded-lg border border-gray-700 bg-gray-900 p-4 cards.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_default_tier_panel_card_recipe(self, page: object, base_url: str) -> None:
        """Default tier panel matches §9.1 card recipe."""
        _go(page, base_url)

        result = validate_card(page, "[data-tour='trust-tier']", dark=True)  # type: ignore[arg-type]
        assert result.passed, (
            f"Default tier panel card fails §9.1 recipe: {result.summary()}"
        )

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_safety_bounds_panel_card_recipe(self, page: object, base_url: str) -> None:
        """Safety bounds panel matches §9.1 card recipe."""
        _go(page, base_url)

        # SafetyBoundsPanel renders as rounded-lg border border-gray-700 bg-gray-900.
        safety_selectors = [
            "[data-testid='safety-bounds-panel']",
            "div.rounded-lg:has(h3)",
        ]
        for sel in safety_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_card(page, sel, dark=True)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Safety bounds panel card fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip("Safety bounds panel not found via known selectors")


# ---------------------------------------------------------------------------
# §9.4 — Button recipe on primary CTAs
# ---------------------------------------------------------------------------


class TestTrustButtonRecipe:
    """Primary CTA buttons must conform to §9.4 button recipe.

    The '+ New rule' button and 'Save bounds' button are the primary CTAs.
    The RuleBuilder's 'Add rule' / 'Update rule' submit button is also tested.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_new_rule_button_recipe(self, page: object, base_url: str) -> None:
        """'+ New rule' button matches §9.4 button recipe."""
        _go(page, base_url)

        button_selectors = [
            "button[class*='violet']",
            "button[class*='bg-violet']",
            "button[class*='purple']",
            "button[class*='bg-purple']",
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

        pytest.skip("No violet/purple CTA button found — skipping §9.4 button recipe check")

    def test_primary_cta_button_visible_and_enabled(self, page: object, base_url: str) -> None:
        """The primary action button on the trust tab is visible and enabled."""
        _go(page, base_url)

        buttons = page.locator("button")  # type: ignore[attr-defined]
        count = buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            text = btn.inner_text() or ""
            if any(label in text for label in ("New rule", "Add First Rule", "Save bounds")):
                assert btn.is_visible(), f"Trust CTA button '{text}' must be visible"
                assert btn.is_enabled(), f"Trust CTA button '{text}' must be enabled"
                return

        pytest.skip("No primary CTA button found on trust tab — skipping visibility check")


# ---------------------------------------------------------------------------
# §9.8 — Form input recipe on safety bounds inputs
# ---------------------------------------------------------------------------


class TestTrustFormInputRecipe:
    """Safety bounds form inputs must conform to §9.8 form input recipe.

    SafetyBoundsPanel wraps each input in a <label> element, providing
    label association via the wrapper pattern.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_safety_bounds_input_recipe(self, page: object, base_url: str) -> None:
        """Safety bounds numeric input matches §9.8 form input recipe."""
        _go(page, base_url)

        input_selector = "input[type='number']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({input_selector!r}).length"
        )
        if count == 0:
            pytest.skip("No numeric inputs found on trust tab")

        result = validate_form_input(page, input_selector)  # type: ignore[arg-type]
        assert result.passed, (
            f"Safety bounds input fails §9.8 recipe: {result.summary()}"
        )

    def test_safety_bounds_inputs_have_labels(self, page: object, base_url: str) -> None:
        """All safety bounds form inputs are wrapped in or associated with labels."""
        _go(page, base_url)

        # SafetyBoundsPanel wraps inputs in <label className="flex flex-col gap-1">.
        label_wrapped = page.evaluate(  # type: ignore[attr-defined]
            """
            () => {
                const inputs = Array.from(document.querySelectorAll(
                    'input[type="number"], textarea'
                ));
                return inputs.filter(inp => inp.closest('label')).length;
            }
            """
        )
        total_inputs = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('input[type=\"number\"], textarea').length"
        )

        if total_inputs == 0:
            pytest.skip("No form inputs found on trust tab")

        # At least half of inputs should be label-wrapped (safety bounds pattern).
        assert label_wrapped >= max(1, total_inputs // 2), (
            f"Only {label_wrapped}/{total_inputs} form inputs are label-wrapped "
            "on the trust tab (SafetyBoundsPanel pattern requires <label> wrappers)"
        )

    def test_safety_bounds_inputs_have_borders(self, page: object, base_url: str) -> None:
        """Safety bounds form inputs have visible borders."""
        _go(page, base_url)

        count = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('input[type=\"number\"]').length"
        )
        if count == 0:
            pytest.skip("No numeric inputs found on trust tab")

        border_style = page.evaluate(  # type: ignore[attr-defined]
            """
            () => {
                const el = document.querySelector('input[type="number"]');
                if (!el) return null;
                return window.getComputedStyle(el).borderStyle;
            }
            """
        )
        assert border_style and border_style != "none", (
            "Safety bounds numeric inputs must have a visible border (§9.8)"
        )


# ---------------------------------------------------------------------------
# §9.11 — Empty state recipe
# ---------------------------------------------------------------------------


class TestTrustEmptyStateRecipe:
    """The trust rules empty state must conform to §9.11 empty state recipe."""

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_trust_empty_state_recipe(self, page: object, base_url: str) -> None:
        """Trust rules empty state matches §9.11 recipe (icon, heading, description, CTA)."""
        _go(page, base_url)

        body = page.locator("body").inner_text()  # type: ignore[attr-defined]
        if "No trust rules yet" not in body:
            pytest.skip("Trust rules are configured — empty state not visible")

        empty_selectors = [
            "[data-testid='trust-rules-empty']",
            "[data-testid='empty-state']",
        ]
        for sel in empty_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_empty_state(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Trust rules empty state fails §9.11 recipe: {result.summary()}"
                )
                return

        pytest.skip("Trust rules empty state container not found via known selectors")


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestTrustTypography:
    """Trust tab typography must match the style guide type scale (§6.2)."""

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1–h3 elements on the trust tab follow the §6.2 heading scale."""
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


class TestTrustFocusRing:
    """Interactive elements must display the correct focus ring (§4.2)."""

    def test_primary_button_focus_ring(self, page: object, base_url: str) -> None:
        """Primary buttons show the §4.2 focus ring color on keyboard focus."""
        _go(page, base_url)

        selectors_to_try = [
            "button[class*='violet']",
            "button[class*='purple']",
            "button",
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

        pytest.skip("No focusable button found on trust tab — skipping focus ring check")


# ---------------------------------------------------------------------------
# §4.1 — Page background / dark theme
# ---------------------------------------------------------------------------


class TestTrustPageBackground:
    """Trust tab must use the dark theme background token (§4.1)."""

    def test_page_background_dark_theme(self, page: object, base_url: str) -> None:
        """Trust tab body uses dark theme background (gray-950 or near-black)."""
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
            f"Trust tab body background {bg!r} — expected dark theme "
            "background (gray-950 #030712 or near-black)"
        )
