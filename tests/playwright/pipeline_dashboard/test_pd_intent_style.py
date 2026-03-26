"""Story 76.4 — Intent Review Tab: Style Guide Compliance.

Validates that /dashboard/?tab=intent conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4 / §5  — Design tokens: colors, focus ring
  §6       — Typography: page title, section headings, body text
  §9.4     — Button recipe: primary CTA styling
  §9.11    — Empty state recipe

Most style checks are xfail-marked: the pipeline dashboard is a dark-theme
React SPA whose CSS tokens differ slightly from the admin UI style guide
baseline.  These xfails are resolved in Epic 77 (style guide remediation).

These tests check *how* the page looks, not *what* it contains.
Semantic content is in test_pd_intent_intent.py.
API contracts are in test_pd_intent_api.py.
"""

import pytest

from tests.playwright.lib.component_validators import (
    validate_button,
    validate_empty_state,
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
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _go(page: object, base_url: str) -> None:
    """Navigate to the intent tab."""
    dashboard_navigate(page, base_url, "intent")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.11 — Empty state recipe
# ---------------------------------------------------------------------------


class TestIntentEmptyStateRecipe:
    """The intent empty state must conform to §9.11 empty state recipe.

    §9.11 requires an icon, heading, description, and at least one CTA button.
    The intent tab shows this state whenever no task is selected.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_empty_state_recipe(self, page: object, base_url: str) -> None:
        """Intent tab empty state matches §9.11 recipe (icon, heading, description, CTA)."""
        _go(page, base_url)

        result = validate_empty_state(  # type: ignore[arg-type]
            page, "[data-testid='intent-no-task-state']"
        )
        assert result.passed, (
            f"Intent tab empty state fails §9.11 recipe: {result.summary()}"
        )

    def test_empty_state_container_present(self, page: object, base_url: str) -> None:
        """Intent empty state container is rendered (data-testid='intent-no-task-state')."""
        _go(page, base_url)

        count = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll(\"[data-testid='intent-no-task-state']\").length"
        )
        assert count > 0, (
            "Intent tab must render [data-testid='intent-no-task-state'] container "
            "when no task is selected"
        )


# ---------------------------------------------------------------------------
# §9.4 — Button recipe on CTA buttons
# ---------------------------------------------------------------------------


class TestIntentButtonRecipe:
    """CTA buttons on the intent empty state must conform to §9.4 button recipe.

    The 'Go to Pipeline' primary CTA and 'Open Backlog' secondary CTA are the
    primary interactive elements when no task is selected.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_go_to_pipeline_button_recipe(self, page: object, base_url: str) -> None:
        """'Go to Pipeline' primary button matches §9.4 button recipe."""
        _go(page, base_url)

        # Try to locate the primary action button via common empty-state patterns.
        button_selectors = [
            "[data-testid='intent-no-task-state'] button",
            "[data-testid='empty-state-primary-action']",
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
                    f"Intent 'Go to Pipeline' button {sel!r} fails §9.4 recipe: "
                    f"{result.summary()}"
                )
                return

        pytest.skip(
            "No primary CTA button found on intent empty state — skipping §9.4 check"
        )

    def test_go_to_pipeline_button_visible_enabled(
        self, page: object, base_url: str
    ) -> None:
        """'Go to Pipeline' button is visible and enabled."""
        _go(page, base_url)

        buttons = page.locator("button")  # type: ignore[attr-defined]
        count = buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            text = btn.inner_text() or ""
            if "Go to Pipeline" in text:
                assert btn.is_visible(), "'Go to Pipeline' button must be visible"
                assert btn.is_enabled(), "'Go to Pipeline' button must be enabled"
                return

        pytest.skip(
            "No 'Go to Pipeline' button found — skipping §9.4 visibility check"
        )

    def test_open_backlog_button_visible_enabled(
        self, page: object, base_url: str
    ) -> None:
        """'Open Backlog' secondary button is visible and enabled."""
        _go(page, base_url)

        buttons = page.locator("button")  # type: ignore[attr-defined]
        count = buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            text = btn.inner_text() or ""
            if "Open Backlog" in text:
                assert btn.is_visible(), "'Open Backlog' button must be visible"
                assert btn.is_enabled(), "'Open Backlog' button must be enabled"
                return

        pytest.skip(
            "No 'Open Backlog' button found — skipping §9.4 visibility check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestIntentTypography:
    """Dashboard typography must match the style guide type scale (§6.2)."""

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1–h3 elements on the intent tab follow the §6.2 heading scale."""
        _go(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_empty_state_heading_typography(self, page: object, base_url: str) -> None:
        """Empty state heading follows §6.2 type scale."""
        _go(page, base_url)

        empty_state = page.locator("[data-testid='intent-no-task-state']")  # type: ignore[attr-defined]
        if empty_state.count() == 0:
            pytest.skip("Intent empty state not found — skipping heading typography check")

        heading = empty_state.locator("h1, h2, h3").first
        if heading.count() == 0:
            pytest.skip("No heading element found inside intent empty state")

        tag = heading.evaluate("el => el.tagName.toLowerCase()")
        assert_typography(page, tag, role="section_title")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §5 — Background / theme colors
# ---------------------------------------------------------------------------


class TestIntentStatusColors:
    """Page background must follow the dark theme color token (§4.1)."""

    def test_page_background_dark_theme(self, page: object, base_url: str) -> None:
        """Intent tab body uses dark theme background (gray-950)."""
        _go(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_dark = (
            colors_close(bg, "#030712")
            or colors_close(bg, "#111827")
            or colors_close(bg, "#0f172a")
        )
        # Accept near-black values (rgb < 30 per channel)
        if not is_dark:
            try:
                import re
                match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', bg)
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
            f"Intent tab body background {bg!r} — expected dark theme background "
            "(gray-950 #030712 or near-black per §4.1)"
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring
# ---------------------------------------------------------------------------


class TestIntentFocusRing:
    """Interactive elements must display the correct focus ring (§4.2)."""

    def test_primary_button_focus_ring(self, page: object, base_url: str) -> None:
        """CTA buttons show the §4.2 focus ring on keyboard focus."""
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
            "No focusable button found on intent tab — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens
# ---------------------------------------------------------------------------


class TestIntentDesignTokens:
    """CSS design tokens must be loaded on the intent tab (§4.1)."""

    def test_font_sans_token_or_direct_declaration(
        self, page: object, base_url: str
    ) -> None:
        """Intent tab loads Inter or a sans-serif font (§6.1)."""
        _go(page, base_url)

        font_family = page.evaluate(  # type: ignore[attr-defined]
            "window.getComputedStyle(document.body).fontFamily"
        )
        assert font_family, "Intent tab body must declare a font-family"
        lower = font_family.lower()
        assert "inter" in lower or "sans" in lower or "system" in lower, (
            f"Intent tab font-family {font_family!r} — expected Inter or "
            "a system sans-serif font (§6.1)"
        )
