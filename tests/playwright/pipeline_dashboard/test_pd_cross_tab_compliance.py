"""Cross-Tab Style Guide Compliance — Pipeline Dashboard (Story 76.14).

Validates style guide compliance across ALL 12 pipeline dashboard tabs using a
single parametrized suite.  Tests are organised into five compliance dimensions:

1. Typography   — headings present, body/code font families (§6.1, §6.2)
2. Spacing      — 4px-grid-compliant card padding (§7.1)
3. Components   — cards, buttons, and badges validated via shared recipes (§9.1–9.4)
4. Dark theme   — body background near-black, text light (§4.1, §5)
5. Focus rings  — first interactive element has blue-500 focus ring (§4.2, §11.1)

Patterns followed from tests/playwright/test_style_guide_compliance.py (Admin UI
equivalent).  All assertions use the shared lib helpers — computed styles, not
class names.

Epic 77 remediation: style-sensitive tests that are expected to fail while
remediation is in progress are decorated with @pytest.mark.xfail.
"""

from __future__ import annotations

import pytest

from tests.playwright.pipeline_dashboard.conftest import (
    ALL_TAB_IDS,
    DASHBOARD_TABS,
    dashboard_navigate,
)
from tests.playwright.lib.component_validators import (
    validate_badge,
    validate_button,
    validate_card,
)
from tests.playwright.lib.style_assertions import (
    colors_close,
    get_background_color,
    get_text_color,
    parse_css_color,
    set_dark_theme,
)
from tests.playwright.lib.typography_assertions import (
    assert_font_family,
    assert_heading_scale,
)

pytestmark = pytest.mark.playwright

# ---------------------------------------------------------------------------
# Selectors shared across dimensions
# ---------------------------------------------------------------------------

# Card: any element that looks like a dashboard card
_CARD_SEL = (
    '.bg-white.rounded-lg.border, '
    '.card, '
    '[class*="rounded-lg"][class*="border"]'
)

# Badge: pill-shaped status indicator
_BADGE_SEL = (
    '.badge, '
    '[class*="rounded"][class*="text-xs"][class*="font-semibold"], '
    'span[class*="px-2"][class*="py-"]'
)

# Dark-theme color thresholds (gray-950 = #030712, i.e. r≤10, g≤10, b≤20)
# We accept any near-black background (each channel < 30) as "dark enough".
_DARK_BG_MAX_CHANNEL = 30

# Light text — gray-50 (#f9fafb), gray-100 (#f3f4f6), gray-200 (#e5e7eb).
# We accept text where the minimum channel value is > 190 (clearly light).
_LIGHT_TEXT_MIN_CHANNEL = 190


# ===========================================================================
# Dimension 1 — Typography
# ===========================================================================


@pytest.mark.parametrize("tab", ALL_TAB_IDS, ids=ALL_TAB_IDS)
class TestCrossTabTypography:
    """Typography compliance across all 12 dashboard tabs (§6.1, §6.2)."""

    def test_heading_present(self, page: object, base_url: str, tab: str) -> None:
        """Each tab must render at least one h1/h2/h3 heading."""
        dashboard_navigate(page, base_url, tab)  # type: ignore[arg-type]
        headings = page.locator("h1, h2, h3")  # type: ignore[attr-defined]
        count = headings.count()
        assert count > 0, (
            f"Tab '{tab}' ({DASHBOARD_TABS[tab]['label']}): "
            f"no h1/h2/h3 heading found — every tab must have at least one heading"
        )

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_heading_scale(self, page: object, base_url: str, tab: str) -> None:
        """All h1–h3 elements must follow the type scale (h1=20px/600, h2=16px/600, h3=14px/600)."""
        dashboard_navigate(page, base_url, tab)  # type: ignore[arg-type]
        assert_heading_scale(page)

    def test_font_family_sans(self, page: object, base_url: str, tab: str) -> None:
        """Body text must use Inter (sans-serif) as first font in the family stack."""
        dashboard_navigate(page, base_url, tab)  # type: ignore[arg-type]
        has_body: bool = page.evaluate(  # type: ignore[attr-defined]
            "() => document.querySelector('body') !== null"
        )
        if not has_body:
            pytest.skip(f"Tab '{tab}': no <body> element found")
        assert_font_family(page, "body", expected="sans")

    def test_code_elements_use_mono_font(
        self, page: object, base_url: str, tab: str
    ) -> None:
        """<code> and .font-mono elements must use JetBrains Mono."""
        dashboard_navigate(page, base_url, tab)  # type: ignore[arg-type]
        has_code: int = page.evaluate(  # type: ignore[attr-defined]
            "() => document.querySelectorAll('code, .font-mono').length"
        )
        if has_code == 0:
            pytest.skip(f"Tab '{tab}': no code/mono elements — skipping mono font check")
        assert_font_family(page, "code, .font-mono", expected="mono")


# ===========================================================================
# Dimension 2 — Spacing (4px grid)
# ===========================================================================


@pytest.mark.parametrize("tab", ALL_TAB_IDS, ids=ALL_TAB_IDS)
class TestCrossTabSpacing:
    """Spacing compliance — card/container padding must be on the 4px grid (§7.1)."""

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_card_padding_on_grid(
        self, page: object, base_url: str, tab: str
    ) -> None:
        """First card's paddingTop must be ≥ 16px and a multiple of 4 (p-4 or p-6)."""
        dashboard_navigate(page, base_url, tab)  # type: ignore[arg-type]
        card_count: int = page.evaluate(  # type: ignore[attr-defined]
            f"() => document.querySelectorAll({_CARD_SEL!r}).length"
        )
        if card_count == 0:
            pytest.skip(f"Tab '{tab}': no card elements found — skipping spacing check")

        # Read paddingTop of first matching card
        padding_raw: str | None = page.evaluate(  # type: ignore[attr-defined]
            f"""() => {{
                const el = document.querySelector({_CARD_SEL!r});
                if (!el) return null;
                return window.getComputedStyle(el).paddingTop;
            }}"""
        )
        if padding_raw is None:
            pytest.skip(f"Tab '{tab}': could not read card padding")

        padding_px = float(padding_raw.replace("px", "").strip()) if padding_raw.endswith("px") else -1.0

        assert padding_px >= 16.0, (
            f"Tab '{tab}': card paddingTop {padding_raw!r} < 16px (p-4 minimum per §7.1)"
        )
        assert int(padding_px) % 4 == 0, (
            f"Tab '{tab}': card paddingTop {padding_raw!r} is not a 4px-grid multiple (§7.1)"
        )


# ===========================================================================
# Dimension 3 — Component Recipes
# ===========================================================================


@pytest.mark.parametrize("tab", ALL_TAB_IDS, ids=ALL_TAB_IDS)
class TestCrossTabComponentRecipes:
    """Component recipe compliance across all 12 tabs (§9.1–9.4)."""

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_first_card_validates(
        self, page: object, base_url: str, tab: str
    ) -> None:
        """First matching card must pass the §9.1 card validator."""
        dashboard_navigate(page, base_url, tab)  # type: ignore[arg-type]
        card_count: int = page.evaluate(  # type: ignore[attr-defined]
            f"() => document.querySelectorAll({_CARD_SEL!r}).length"
        )
        if card_count == 0:
            pytest.skip(f"Tab '{tab}': no card elements — skipping card recipe check")

        result = validate_card(page, _CARD_SEL)
        assert result.passed, (
            f"Tab '{tab}' — {result.summary()}"
        )

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_first_button_validates(
        self, page: object, base_url: str, tab: str
    ) -> None:
        """First <button> must pass the §9.4 button validator."""
        dashboard_navigate(page, base_url, tab)  # type: ignore[arg-type]
        btn_count: int = page.evaluate(  # type: ignore[attr-defined]
            "() => document.querySelectorAll('button').length"
        )
        if btn_count == 0:
            pytest.skip(f"Tab '{tab}': no buttons found — skipping button recipe check")

        result = validate_button(page, "button")
        assert result.passed, (
            f"Tab '{tab}' — {result.summary()}"
        )

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_first_badge_validates(
        self, page: object, base_url: str, tab: str
    ) -> None:
        """First matching badge must pass the §9.3 badge validator.

        Many tabs carry no badge elements — those are skipped, not failed.
        """
        dashboard_navigate(page, base_url, tab)  # type: ignore[arg-type]
        badge_count: int = page.evaluate(  # type: ignore[attr-defined]
            f"() => document.querySelectorAll({_BADGE_SEL!r}).length"
        )
        if badge_count == 0:
            pytest.skip(
                f"Tab '{tab}': no badge elements found — skipping badge recipe check"
            )

        result = validate_badge(page, _BADGE_SEL)
        assert result.passed, (
            f"Tab '{tab}' — {result.summary()}"
        )


# ===========================================================================
# Dimension 4 — Dark Theme Colors
# ===========================================================================


@pytest.mark.parametrize("tab", ALL_TAB_IDS, ids=ALL_TAB_IDS)
class TestCrossTabDarkTheme:
    """Dark theme color compliance across all 12 tabs (§4.1, §5).

    The dashboard SPA uses data-theme="dark" on the root element.  These tests
    activate dark mode via JavaScript and then validate computed colors.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_body_background_is_near_black(
        self, page: object, base_url: str, tab: str
    ) -> None:
        """In dark theme, <body> background must be near-black (gray-950 or equivalent)."""
        dashboard_navigate(page, base_url, tab)  # type: ignore[arg-type]
        set_dark_theme(page)

        bg_css: str = get_background_color(page, "body")  # type: ignore[arg-type]
        try:
            r, g, b, _a = parse_css_color(bg_css)
        except ValueError:
            pytest.skip(
                f"Tab '{tab}': cannot parse body background color {bg_css!r}"
            )

        assert r <= _DARK_BG_MAX_CHANNEL and g <= _DARK_BG_MAX_CHANNEL and b <= _DARK_BG_MAX_CHANNEL, (
            f"Tab '{tab}': dark theme body background {bg_css!r} is not near-black — "
            f"each channel must be ≤ {_DARK_BG_MAX_CHANNEL} (gray-950 spec)"
        )

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_body_text_is_light(
        self, page: object, base_url: str, tab: str
    ) -> None:
        """In dark theme, <body> text color must be light (gray-50/100/200)."""
        dashboard_navigate(page, base_url, tab)  # type: ignore[arg-type]
        set_dark_theme(page)

        text_css: str = get_text_color(page, "body")  # type: ignore[arg-type]
        try:
            r, g, b, _a = parse_css_color(text_css)
        except ValueError:
            pytest.skip(
                f"Tab '{tab}': cannot parse body text color {text_css!r}"
            )

        assert (
            r >= _LIGHT_TEXT_MIN_CHANNEL
            and g >= _LIGHT_TEXT_MIN_CHANNEL
            and b >= _LIGHT_TEXT_MIN_CHANNEL
        ), (
            f"Tab '{tab}': dark theme body text {text_css!r} is not light — "
            f"each channel must be ≥ {_LIGHT_TEXT_MIN_CHANNEL} "
            f"(gray-50/100/200 expected per §4.1)"
        )


# ===========================================================================
# Dimension 5 — Focus Rings
# ===========================================================================


@pytest.mark.parametrize("tab", ALL_TAB_IDS, ids=ALL_TAB_IDS)
class TestCrossTabFocusRings:
    """Focus ring compliance across all 12 tabs (§4.2, §11.1).

    Every interactive element must show a visible focus ring using blue-500
    (#3b82f6) as the outline color in dark mode, or blue-600 (#2563eb) in
    light mode.
    """

    # blue-500 hex — the dark-mode focus ring color per §4.2
    _BLUE_500 = "#3b82f6"
    # blue-600 hex — the light-mode focus ring color per §4.2
    _BLUE_600 = "#2563eb"
    # Per-channel tolerance for rendering differences
    _TOLERANCE = 8

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_first_interactive_has_focus_ring(
        self, page: object, base_url: str, tab: str
    ) -> None:
        """First focusable interactive element must reveal a blue focus ring on focus."""
        dashboard_navigate(page, base_url, tab)  # type: ignore[arg-type]

        # Find the first button or link
        first_selector: str | None = page.evaluate(  # type: ignore[attr-defined]
            """() => {
                const candidates = ['button', 'a[href]', '[role="button"]', 'input', 'select'];
                for (const sel of candidates) {
                    const el = document.querySelector(sel);
                    if (el) return sel;
                }
                return null;
            }"""
        )
        if first_selector is None:
            pytest.skip(
                f"Tab '{tab}': no focusable interactive element found — "
                "skipping focus ring check"
            )

        # Focus the element and read its outline color
        page.focus(first_selector)  # type: ignore[attr-defined]

        outline_css: str | None = page.evaluate(  # type: ignore[attr-defined]
            f"""() => {{
                const el = document.querySelector({first_selector!r});
                if (!el) return null;
                const s = window.getComputedStyle(el);
                return s.outlineColor || s.getPropertyValue('--tw-ring-color') || null;
            }}"""
        )
        if not outline_css:
            pytest.skip(
                f"Tab '{tab}': could not read outline color on {first_selector!r} "
                "after focus — element may not receive focus in this context"
            )

        # Accept either blue-600 (light) or blue-500 (dark)
        try:
            matches_light = colors_close(outline_css, self._BLUE_600, self._TOLERANCE)
            matches_dark = colors_close(outline_css, self._BLUE_500, self._TOLERANCE)
        except ValueError:
            pytest.skip(
                f"Tab '{tab}': cannot parse outline color {outline_css!r}"
            )
            return  # unreachable; satisfies type checker

        assert matches_light or matches_dark, (
            f"Tab '{tab}': focus ring on {first_selector!r} is {outline_css!r} — "
            f"expected blue-600 ({self._BLUE_600}) or blue-500 ({self._BLUE_500}) "
            f"within ±{self._TOLERANCE} per channel (§4.2, §11.1)"
        )
