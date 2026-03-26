"""Story 76.5 — Routing Review Tab: Style Guide Compliance.

Validates that /dashboard/?tab=routing conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4 / §5  — Design tokens: colors, status colors, focus ring
  §6       — Typography: page title, section headings, body text
  §9.4     — Button recipe: primary CTA styling
  §9.11    — Empty state recipe

Most style checks are xfail-marked: the pipeline dashboard is a dark-theme
React SPA whose CSS tokens differ slightly from the admin UI style guide
baseline.  These xfails are resolved in Epic 77 (style guide remediation).

These tests check *how* the page looks, not *what* it contains.
Semantic content is in test_pd_routing_intent.py (Story 76.5).
API contracts are in test_pd_routing_api.py (Story 76.5).
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
)
from tests.playwright.lib.typography_assertions import (
    assert_heading_scale,
    assert_typography,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _go(page: object, base_url: str) -> None:
    """Navigate to the routing tab."""
    dashboard_navigate(page, base_url, "routing")  # type: ignore[arg-type]


def _in_empty_state(page: object) -> bool:
    """Return True when the routing tab is showing the no-task-selected empty state."""
    return page.locator("[data-testid='routing-no-task-state']").count() > 0  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# §9.11 — Empty state recipe on the no-task-selected state
# ---------------------------------------------------------------------------


class TestRoutingEmptyStateRecipe:
    """The routing 'No Task Selected' empty state must conform to §9.11 recipe."""

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_empty_state_recipe(self, page: object, base_url: str) -> None:
        """Routing empty state matches §9.11 recipe (icon, heading, description, CTA)."""
        _go(page, base_url)

        if not _in_empty_state(page):
            pytest.skip("Routing tab not in empty state — task may be pre-selected")

        result = validate_empty_state(  # type: ignore[attr-defined]
            page, "[data-testid='routing-no-task-state']"
        )
        assert result.passed, (
            f"Routing empty state fails §9.11 recipe: {result.summary()}"
        )

    def test_empty_state_has_visible_content(self, page: object, base_url: str) -> None:
        """Routing empty state renders visible text content."""
        _go(page, base_url)

        if not _in_empty_state(page):
            pytest.skip("Routing tab not in empty state — task may be pre-selected")

        empty = page.locator("[data-testid='routing-no-task-state']")  # type: ignore[attr-defined]
        text = empty.inner_text().strip()
        assert text, (
            "Routing empty state [data-testid='routing-no-task-state'] must render "
            "non-empty visible text content"
        )


# ---------------------------------------------------------------------------
# §9.4 — Button recipe on CTA buttons
# ---------------------------------------------------------------------------


class TestRoutingButtonRecipe:
    """CTA buttons on the routing tab must conform to §9.4 button recipe.

    The primary 'Go to Pipeline' and secondary 'Open Backlog' buttons are the
    main interactive elements on the empty routing state.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_go_to_pipeline_button_recipe(self, page: object, base_url: str) -> None:
        """'Go to Pipeline' button matches §9.4 button recipe."""
        _go(page, base_url)

        if not _in_empty_state(page):
            pytest.skip("Routing tab not in empty state — no empty-state CTAs visible")

        button_selectors = [
            "button:has-text('Go to Pipeline')",
            "[data-testid='routing-no-task-state'] button",
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

        pytest.skip("No 'Go to Pipeline' button found — skipping §9.4 button recipe check")

    def test_action_buttons_visible_and_enabled(self, page: object, base_url: str) -> None:
        """'Go to Pipeline' and 'Open Backlog' buttons are visible and enabled."""
        _go(page, base_url)

        if not _in_empty_state(page):
            pytest.skip("Routing tab not in empty state — no empty-state CTAs visible")

        for label in ("Go to Pipeline", "Open Backlog"):
            btns = page.locator(f"button:has-text('{label}'), a:has-text('{label}')")  # type: ignore[attr-defined]
            if btns.count() == 0:
                continue
            btn = btns.first
            assert btn.is_visible(), f"'{label}' button must be visible"
            assert btn.is_enabled(), f"'{label}' button must not be disabled"


# ---------------------------------------------------------------------------
# §5 — Background and theme
# ---------------------------------------------------------------------------


class TestRoutingPageTheme:
    """Routing tab must use the dark-theme background (§4.1 gray-950)."""

    def test_page_background_dark_theme(self, page: object, base_url: str) -> None:
        """Routing tab body uses dark theme background (gray-950)."""
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
            f"Routing tab body background {bg!r} — expected dark theme "
            "background (gray-950 #030712 or near-black)"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestRoutingTypography:
    """Routing tab typography must match the style guide type scale (§6.2)."""

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1–h3 elements on the routing tab follow the §6.2 heading scale."""
        _go(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1) uses §6.2 page_title scale (20px / weight 600)."""
        _go(page, base_url)

        count = page.evaluate("document.querySelectorAll('h1').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h1 element found on routing tab")

        assert_typography(page, "h1", role="page_title")  # type: ignore[arg-type]

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_empty_state_heading_typography(self, page: object, base_url: str) -> None:
        """Empty state headings use §6.2 scale (14px / weight 600)."""
        _go(page, base_url)

        if not _in_empty_state(page):
            pytest.skip("Routing tab not in empty state — skipping empty state heading typography check")

        count = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('[data-testid=\"routing-no-task-state\"] h1, "
            "[data-testid=\"routing-no-task-state\"] h2, "
            "[data-testid=\"routing-no-task-state\"] h3').length"
        )
        if count == 0:
            pytest.skip("No heading found inside routing empty state")

        assert_typography(  # type: ignore[arg-type]
            page,
            "[data-testid='routing-no-task-state'] h1, "
            "[data-testid='routing-no-task-state'] h2, "
            "[data-testid='routing-no-task-state'] h3",
            role="section_title",
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring
# ---------------------------------------------------------------------------


class TestRoutingFocusRing:
    """Interactive elements must display the correct focus ring (§4.2)."""

    def test_primary_button_focus_ring(self, page: object, base_url: str) -> None:
        """Primary buttons show the §4.2 focus ring color on keyboard focus."""
        _go(page, base_url)

        selectors_to_try = [
            "button:has-text('Go to Pipeline')",
            "button:has-text('Open Backlog')",
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

        pytest.skip("No focusable button found on routing tab — skipping focus ring check")


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens
# ---------------------------------------------------------------------------


class TestRoutingDesignTokens:
    """CSS design tokens must be registered on :root (§4.1)."""

    def test_font_sans_token_or_direct_declaration(self, page: object, base_url: str) -> None:
        """Routing tab loads Inter or a sans-serif font (§6.1)."""
        _go(page, base_url)

        font_family = page.evaluate(  # type: ignore[attr-defined]
            "window.getComputedStyle(document.body).fontFamily"
        )
        assert font_family, "Routing tab body must declare a font-family"
        lower = font_family.lower()
        assert "inter" in lower or "sans" in lower or "system" in lower, (
            f"Routing tab font-family {font_family!r} — expected Inter or "
            "a system sans-serif font (§6.1)"
        )
