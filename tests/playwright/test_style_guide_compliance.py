"""Style Guide Compliance Tests — enforce docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md.

These tests call the lib helpers against LIVE rendered pages on the Docker stack.
Failures mean the UI violates the style guide and needs fixing.

Sections tested:
- Section 6: Typography (heading scale, font families, type roles)
- Section 7: Spacing and density (4px grid)
- Section 9: Component recipes (cards, tables, badges, buttons, forms, empty states)
- Section 11: Accessibility (focus visible, landmarks, keyboard nav, touch targets,
  table headers, form labels, color-only indicators)
"""

import pytest

from tests.playwright.conftest import navigate

# --- Lib helpers (built in Epic 58, now wired to live pages) ---
from tests.playwright.lib.accessibility_helpers import (
    assert_aria_landmarks,
    assert_focus_visible,
    assert_form_accessibility,
    assert_keyboard_navigation as a11y_keyboard_navigation,
    assert_no_color_only_indicators,
    assert_table_accessibility,
    assert_touch_targets,
)
from tests.playwright.lib.component_validators import (
    validate_badge,
    validate_button,
    validate_card,
    validate_empty_state,
    validate_form_input,
    validate_table,
)
from tests.playwright.lib.typography_assertions import (
    assert_font_family,
    assert_heading_scale,
    assert_typography,
)

pytestmark = pytest.mark.playwright

# ---------------------------------------------------------------------------
# Page registry — all admin UI pages
# ---------------------------------------------------------------------------
ALL_PAGES = [
    "/admin/ui/dashboard",
    "/admin/ui/repos",
    "/admin/ui/workflows",
    "/admin/ui/audit",
    "/admin/ui/metrics",
    "/admin/ui/experts",
    "/admin/ui/tools",
    "/admin/ui/models",
    "/admin/ui/compliance",
    "/admin/ui/quarantine",
    "/admin/ui/dead-letters",
    "/admin/ui/planes",
    "/admin/ui/settings",
]

# Pages known to contain specific elements
PAGES_WITH_TABLES = [
    "/admin/ui/workflows",
    "/admin/ui/audit",
    "/admin/ui/experts",
    "/admin/ui/tools",
    "/admin/ui/models",
]

PAGES_WITH_FORMS = [
    "/admin/ui/repos",
    "/admin/ui/planes",
    "/admin/ui/settings",
]


# ===========================================================================
# SECTION 6 — Typography
# ===========================================================================


class TestTypographyScale:
    """Style guide Section 6.2: heading hierarchy must follow the type scale."""

    @pytest.mark.parametrize(
        "path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES]
    )
    def test_heading_scale(self, page, base_url: str, path: str) -> None:
        """All h1-h3 elements must follow the type scale (h1=20px/600, h2=16px/600, h3=14px/600)."""
        navigate(page, f"{base_url}{path}")
        assert_heading_scale(page)


class TestFontFamily:
    """Style guide Section 6.1: Inter for UI text, JetBrains Mono for code."""

    @pytest.mark.parametrize(
        "path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES]
    )
    def test_body_uses_sans_font(self, page, base_url: str, path: str) -> None:
        """Body text must use Inter (sans) font family."""
        navigate(page, f"{base_url}{path}")
        # Check body-level font family
        has_body = page.evaluate(
            "() => document.querySelector('body') !== null"
        )
        if has_body:
            assert_font_family(page, "body", expected="sans")

    @pytest.mark.parametrize(
        "path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES]
    )
    def test_code_elements_use_mono_font(self, page, base_url: str, path: str) -> None:
        """<code> elements must use JetBrains Mono (mono) font family."""
        navigate(page, f"{base_url}{path}")
        has_code = page.evaluate(
            "() => document.querySelectorAll('code, .font-mono').length"
        )
        if has_code == 0:
            pytest.skip(f"No code/mono elements on {path}")
        assert_font_family(page, "code, .font-mono", expected="mono")


# ===========================================================================
# SECTION 9 — Component Recipes
# ===========================================================================


class TestCardComponents:
    """Style guide Section 9.1: cards have correct bg, border, radius, padding."""

    @pytest.mark.parametrize(
        "path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES]
    )
    def test_cards_meet_style_guide(self, page, base_url: str, path: str) -> None:
        """All card elements must meet §9.1 specs (bg, border, radius >= 8px, padding >= 16px)."""
        navigate(page, f"{base_url}{path}")
        card_count = page.evaluate(
            """() => document.querySelectorAll(
                '.bg-white.rounded-lg.border, .card, [class*="rounded-lg"][class*="border"]'
            ).length"""
        )
        if card_count == 0:
            pytest.skip(f"No card elements found on {path}")

        result = validate_card(
            page,
            '.bg-white.rounded-lg.border, .card, [class*="rounded-lg"][class*="border"]',
        )
        assert result.passed, result.summary()


class TestTableComponents:
    """Style guide Section 9.2: table headers, scope attrs, mono numeric columns."""

    @pytest.mark.parametrize(
        "path", PAGES_WITH_TABLES, ids=[p.split("/")[-1] for p in PAGES_WITH_TABLES]
    )
    def test_tables_meet_style_guide(self, page, base_url: str, path: str) -> None:
        """Tables must have correct header bg, <th scope>, and mono numeric columns."""
        navigate(page, f"{base_url}{path}")
        table_count = page.evaluate("() => document.querySelectorAll('table').length")
        if table_count == 0:
            pytest.skip(f"No tables on {path}")

        result = validate_table(page, "table")
        assert result.passed, result.summary()


class TestButtonComponents:
    """Style guide Section 9.4: buttons have correct radius, padding, touch target."""

    @pytest.mark.parametrize(
        "path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES]
    )
    def test_buttons_meet_style_guide(self, page, base_url: str, path: str) -> None:
        """All buttons must have radius >= 6px, proper padding, font, and touch target >= 24x24."""
        navigate(page, f"{base_url}{path}")
        btn_count = page.evaluate("() => document.querySelectorAll('button').length")
        if btn_count == 0:
            pytest.skip(f"No buttons on {path}")

        result = validate_button(page, "button")
        assert result.passed, result.summary()


class TestBadgeComponents:
    """Style guide Section 9.3: badges are compact pills with correct sizing."""

    def test_dashboard_badges(self, page, base_url: str) -> None:
        """Dashboard status badges must meet §9.3 specs."""
        navigate(page, f"{base_url}/admin/ui/dashboard")
        badge_count = page.evaluate(
            """() => document.querySelectorAll(
                '.badge, [class*="rounded"][class*="text-xs"][class*="font-semibold"], '
                + 'span[class*="px-2"][class*="py-"]'
            ).length"""
        )
        if badge_count == 0:
            pytest.skip("No badges found on dashboard")

        result = validate_badge(
            page,
            '.badge, [class*="rounded"][class*="text-xs"][class*="font-semibold"], '
            + 'span[class*="px-2"][class*="py-"]',
        )
        assert result.passed, result.summary()


class TestFormInputComponents:
    """Style guide Section 9.8: form inputs have labels, borders, aria-describedby."""

    @pytest.mark.parametrize(
        "path", PAGES_WITH_FORMS, ids=[p.split("/")[-1] for p in PAGES_WITH_FORMS]
    )
    def test_form_inputs_meet_style_guide(self, page, base_url: str, path: str) -> None:
        """Form inputs must have associated labels and visible borders."""
        navigate(page, f"{base_url}{path}")

        # For repos page, click Register to expose the form
        if path == "/admin/ui/repos":
            register_btn = page.get_by_role("button", name="Register Repo")
            if register_btn.count() > 0:
                register_btn.click()
                page.wait_for_load_state("networkidle")

        input_count = page.evaluate(
            "() => document.querySelectorAll('input[type=\"text\"], input[type=\"number\"], "
            + "input[type=\"email\"], input[type=\"password\"], select, textarea').length"
        )
        if input_count == 0:
            pytest.skip(f"No form inputs on {path}")

        result = validate_form_input(
            page,
            'input[type="text"], input[type="number"], input[type="email"], '
            + 'input[type="password"], select, textarea',
        )
        assert result.passed, result.summary()


class TestEmptyStateComponents:
    """Style guide Section 9.11: empty states have heading, description, and CTA."""

    def test_repos_empty_state(self, page, base_url: str) -> None:
        """Empty repos page must show a proper empty state (heading + description + CTA)."""
        navigate(page, f"{base_url}/admin/ui/repos")
        # Check if page is in empty state (no repo table rows)
        has_rows = page.evaluate(
            "() => document.querySelectorAll('table tbody tr').length > 0"
        )
        if has_rows:
            pytest.skip("Repos page has data — not in empty state")

        empty_el = page.evaluate(
            """() => {
                const el = document.querySelector('.empty-state, [class*="empty"], [class*="text-center"][class*="py-"]');
                return el !== null;
            }"""
        )
        if not empty_el:
            pytest.skip("No empty state container found")

        result = validate_empty_state(
            page,
            '.empty-state, [class*="empty"], [class*="text-center"][class*="py-"]',
        )
        assert result.passed, result.summary()


# ===========================================================================
# SECTION 11 — Accessibility
# ===========================================================================


class TestAccessibilityLandmarks:
    """Style guide Section 11.5: every page needs <main>, <nav>, <header> landmarks."""

    @pytest.mark.parametrize(
        "path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES]
    )
    def test_aria_landmarks_present(self, page, base_url: str, path: str) -> None:
        """Every page must have <main>, <nav>, and <header> landmarks (§11.5.7)."""
        navigate(page, f"{base_url}{path}")
        result = assert_aria_landmarks(page)
        assert result.passed, f"{path}: {result.summary()}"


class TestAccessibilityFocusVisible:
    """Style guide Section 11.1: all interactive elements must have visible focus indicators."""

    @pytest.mark.parametrize(
        "path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES]
    )
    def test_focus_visible_on_interactive_elements(
        self, page, base_url: str, path: str
    ) -> None:
        """All interactive elements must have a visible focus ring (§11.1)."""
        navigate(page, f"{base_url}{path}")
        result = assert_focus_visible(page)
        assert result.passed, f"{path}: {result.summary()}"


class TestAccessibilityTouchTargets:
    """Style guide Section 11.2: all buttons/links must be >= 24x24px minimum."""

    @pytest.mark.parametrize(
        "path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES]
    )
    def test_touch_targets_meet_minimum(self, page, base_url: str, path: str) -> None:
        """All interactive elements must be >= 24x24px (WCAG 2.2 SC 2.5.8)."""
        navigate(page, f"{base_url}{path}")
        result = assert_touch_targets(page)
        assert result.passed, f"{path}: {result.summary()}"


class TestAccessibilityColorOnly:
    """Style guide Section 5.5 / 11.3: never use color as the sole indicator of state."""

    @pytest.mark.parametrize(
        "path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES]
    )
    def test_no_color_only_indicators(self, page, base_url: str, path: str) -> None:
        """Status badges must pair color with text, icon, or title (§5.5, §11.3)."""
        navigate(page, f"{base_url}{path}")
        result = assert_no_color_only_indicators(page)
        assert result.passed, f"{path}: {result.summary()}"


class TestAccessibilityKeyboardNavigation:
    """Style guide Section 11.4: all interactive elements reachable via Tab."""

    @pytest.mark.parametrize(
        "path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES]
    )
    def test_keyboard_navigation(self, page, base_url: str, path: str) -> None:
        """Each page must have keyboard-navigable elements with no tabindex > 0 (§11.4)."""
        navigate(page, f"{base_url}{path}")
        result = a11y_keyboard_navigation(page, min_focusable=1)
        assert result.passed, f"{path}: {result.summary()}"


class TestAccessibilityTableHeaders:
    """Style guide Section 9.2 / 11.5.6: all <th> must have scope="col" or scope="row"."""

    @pytest.mark.parametrize(
        "path", PAGES_WITH_TABLES, ids=[p.split("/")[-1] for p in PAGES_WITH_TABLES]
    )
    def test_table_headers_have_scope(self, page, base_url: str, path: str) -> None:
        """Every <th> in tables must have scope attribute for screen readers."""
        navigate(page, f"{base_url}{path}")
        table_count = page.evaluate("() => document.querySelectorAll('table').length")
        if table_count == 0:
            pytest.skip(f"No tables on {path}")

        result = assert_table_accessibility(page, "table")
        assert result.passed, f"{path}: {result.summary()}"


class TestAccessibilityFormLabels:
    """Style guide Section 9.8 / 11.5.5: every input must have an associated <label>."""

    @pytest.mark.parametrize(
        "path", PAGES_WITH_FORMS, ids=[p.split("/")[-1] for p in PAGES_WITH_FORMS]
    )
    def test_form_controls_have_labels(self, page, base_url: str, path: str) -> None:
        """Every form input/select/textarea must have an associated label (§11.5.5)."""
        navigate(page, f"{base_url}{path}")

        # For repos page, click Register to expose the form
        if path == "/admin/ui/repos":
            register_btn = page.get_by_role("button", name="Register Repo")
            if register_btn.count() > 0:
                register_btn.click()
                page.wait_for_load_state("networkidle")

        # For settings page, click first tab to expose form content
        if path == "/admin/ui/settings":
            tab_link = page.locator('[hx-get*="api-keys"]')
            if tab_link.count() > 0:
                tab_link.first.click()
                page.wait_for_load_state("networkidle")

        result = assert_form_accessibility(page)
        assert result.passed, f"{path}: {result.summary()}"
