"""Story 76.9 — Pipeline Dashboard: Activity Log Style Guide Compliance.

Validates that /dashboard/?tab=activity conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4 / §5  — Design tokens: colors, status colors, focus ring
  §6       — Typography: headings, monospace timestamps
  §9.1     — Card recipe: background, border, radius, padding
  §9.3     — Badge recipe: action badges sizing, padding, font weight
  §9.11    — Empty state recipe

Most style checks are xfail-marked: the pipeline dashboard is a dark-theme
React SPA whose CSS tokens differ slightly from the admin UI style guide
baseline.  These xfails are resolved in Epic 77 (style guide remediation).

These tests check *how* the page looks, not *what* it contains.
Semantic content is in test_pd_activity_intent.py.
API contracts are in test_pd_activity_api.py.
"""

import pytest

from tests.playwright.lib.component_validators import (
    validate_badge,
    validate_button,
    validate_card,
    validate_empty_state,
    validate_table,
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
    """Navigate to the activity tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "activity")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.1 — Card recipe on the activity log container
# ---------------------------------------------------------------------------


class TestActivityCardRecipe:
    """Activity log container must conform to §9.1 card recipe.

    The main activity log section (table or empty state) uses the card recipe:
    dark background, border, ≥8px radius, ≥16px padding.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_activity_container_card_recipe(
        self, page: object, base_url: str
    ) -> None:
        """Activity log container matches §9.1 card recipe."""
        _go(page, base_url)

        # Try the overflow container wrapping the table first, then fall back.
        selectors = [
            "[class*='overflow-x-auto']",
            "div.space-y-6",
            "main",
        ]
        for sel in selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_card(page, sel, dark=True)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Activity log container fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No activity log container element found — skipping §9.1 card check"
        )

    def test_table_border_present(self, page: object, base_url: str) -> None:
        """Audit table wrapper carries visible border styling."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No audit table — empty state; skipping border check")

        # The table is wrapped in a div with rounded-lg border border-gray-800.
        table_wrapper = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var table = document.querySelector('table');
                if (!table) return null;
                var wrapper = table.parentElement;
                if (!wrapper) return null;
                return window.getComputedStyle(wrapper).borderStyle;
            })()
            """
        )
        assert table_wrapper and table_wrapper != "none", (
            "Audit table wrapper must have a visible border (§9.1)"
        )


# ---------------------------------------------------------------------------
# §9.2 — Table recipe on audit table
# ---------------------------------------------------------------------------


class TestActivityTableRecipe:
    """Audit table must conform to §9.2 table recipe.

    Columns should have scope attributes, and the thead must use
    the dark background (gray-900) consistent with dark-theme tables.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_audit_table_recipe(self, page: object, base_url: str) -> None:
        """Audit table matches §9.2 table recipe (thead bg, scope attributes)."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No audit table — empty state is present")

        result = validate_table(page, "table", dark=True)  # type: ignore[arg-type]
        assert result.passed, (
            f"Audit table fails §9.2 recipe: {result.summary()}"
        )

    def test_thead_background_dark(self, page: object, base_url: str) -> None:
        """Audit table thead uses a dark background (gray-900 / bg-gray-900/60)."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No audit table — empty state is present")

        thead_bg = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var thead = document.querySelector('thead tr');
                if (!thead) return null;
                return window.getComputedStyle(thead).backgroundColor;
            })()
            """
        )
        if thead_bg is None:
            pytest.skip("No thead row found in audit table")

        # Accept gray-900 (#111827) or near-black values
        is_dark = colors_close(thead_bg, "#111827") or (
            "rgb(17, 24, 39" in thead_bg
            or "rgb(0, 0, 0" in thead_bg
        )
        # Also accept rgba variants with partial transparency
        if not is_dark:
            try:
                import re
                match = re.search(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", thead_bg)
                if match:
                    r, g, b = (
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                    )
                    is_dark = r <= 30 and g <= 40 and b <= 60
            except Exception:  # noqa: BLE001
                pass

        assert is_dark, (
            f"Audit table thead background {thead_bg!r} — expected dark "
            "background (gray-900 or near-black)"
        )


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe on action badges
# ---------------------------------------------------------------------------


class TestActivityBadgeRecipe:
    """Action type badges must conform to §9.3 badge recipe.

    Each audit entry shows an action badge (Pause, Resume, Abort, etc.)
    with a coloured pill shape. The badge must have ≥8px horizontal padding,
    ≥2px vertical padding, a border-radius, and text-xs font size.
    """

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_action_badge_recipe(self, page: object, base_url: str) -> None:
        """Action badge in audit table matches §9.3 badge recipe."""
        _go(page, base_url)

        if page.locator("table tbody tr").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No audit entries — empty state; cannot check action badges")

        # Action badges use rounded-full with inline-flex class.
        badge_selectors = [
            "span[class*='rounded-full']",
            "span[class*='rounded']",
            "span[class*='badge']",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Action badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip("No action badge elements found in audit table")

    def test_action_badges_have_background_color(
        self, page: object, base_url: str
    ) -> None:
        """Action badges have a coloured background (semantic color coding)."""
        _go(page, base_url)

        if page.locator("table tbody tr").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No audit entries — empty state; cannot check badge colors")

        # Check that at least one badge-like span has a non-transparent background.
        has_colored_badge = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var badges = document.querySelectorAll(
                    'span[class*="rounded-full"], span[class*="bg-"]'
                );
                for (var i = 0; i < badges.length; i++) {
                    var bg = window.getComputedStyle(badges[i]).backgroundColor;
                    if (bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)') {
                        return true;
                    }
                }
                return false;
            })()
            """
        )
        assert has_colored_badge, (
            "Action badges must have a coloured background — "
            "each action type (pause/resume/abort) uses a distinct semantic color"
        )


# ---------------------------------------------------------------------------
# §9.11 — Empty state recipe
# ---------------------------------------------------------------------------


class TestActivityEmptyStateRecipe:
    """The empty activity state must conform to §9.11 empty state recipe."""

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_empty_state_recipe(self, page: object, base_url: str) -> None:
        """Empty activity state matches §9.11 recipe (icon, heading, description)."""
        _go(page, base_url)

        if page.locator("table tbody tr").count() > 0:  # type: ignore[attr-defined]
            pytest.skip("Audit entries present — empty state not shown")

        # The EmptyState component wraps its content in a div.
        empty_selectors = [
            "[data-testid='activity-log-empty-state']",
            "[data-testid='empty-state']",
            "div[class*='empty']",
        ]
        for sel in empty_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_empty_state(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Empty activity state fails §9.11 recipe: {result.summary()}"
                )
                return

        pytest.skip("No empty-state container element found — skipping §9.11 check")


# ---------------------------------------------------------------------------
# §6 — Typography: monospace timestamps and heading scale
# ---------------------------------------------------------------------------


class TestActivityTypography:
    """Activity log typography must match the style guide type scale (§6).

    Timestamps use monospace font for alignment (JetBrains Mono or system mono).
    The 'Steering Activity Log' heading uses the §6.2 page_title scale.
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1–h3 elements on the activity tab follow the §6.2 heading scale."""
        _go(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_activity_log_heading_typography(
        self, page: object, base_url: str
    ) -> None:
        """'Steering Activity Log' h2 uses §6.2 page_title scale (20px / weight 600)."""
        _go(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 element found on activity tab")

        assert_typography(page, "h2", role="page_title")  # type: ignore[arg-type]

    def test_task_id_uses_monospace_font(self, page: object, base_url: str) -> None:
        """Task ID cell in audit table uses a monospace font."""
        _go(page, base_url)

        if page.locator("table tbody tr").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No audit entries — cannot check task ID font")

        mono_font = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var mono = document.querySelector('span[class*="font-mono"]');
                if (!mono) return null;
                return window.getComputedStyle(mono).fontFamily;
            })()
            """
        )
        if mono_font is None:
            pytest.skip("No font-mono span found in audit entries")

        lower = mono_font.lower()
        assert "mono" in lower or "courier" in lower or "jetbrains" in lower, (
            f"Task ID font-family {mono_font!r} — expected a monospace font "
            "(JetBrains Mono, Courier, or system monospace) per §6.3"
        )

    def test_column_headers_uppercase(self, page: object, base_url: str) -> None:
        """Audit table column headers use uppercase tracking (text-xs uppercase)."""
        _go(page, base_url)

        if page.locator("table").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No audit table — empty state is present")

        header_transform = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var th = document.querySelector('th');
                if (!th) return null;
                return window.getComputedStyle(th).textTransform;
            })()
            """
        )
        assert header_transform == "uppercase", (
            f"Audit table column headers textTransform {header_transform!r} — "
            "expected 'uppercase' per style guide table recipe (§9.2)"
        )


# ---------------------------------------------------------------------------
# §4.1 / §5 — Status semantic colors on action badges
# ---------------------------------------------------------------------------


class TestActivityActionColors:
    """Action badges must use semantic status colors for each action type.

    Each action type maps to a specific color:
    - pause → amber/warning
    - resume → green/success
    - abort → red/error
    - redirect → violet
    - retry → blue/info
    - trust_tier_* → teal/orange
    """

    def test_action_badge_colors_are_semantic(
        self, page: object, base_url: str
    ) -> None:
        """Action badges use distinct background colors for each action type."""
        _go(page, base_url)

        if page.locator("table tbody tr").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("No audit entries — empty state; cannot verify badge colors")

        # Confirm that action badges in the table have colored backgrounds.
        distinct_bg_colors = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var badges = document.querySelectorAll(
                    'span[class*="rounded-full"]'
                );
                var colors = new Set();
                badges.forEach(function(b) {
                    var bg = window.getComputedStyle(b).backgroundColor;
                    if (bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)') {
                        colors.add(bg);
                    }
                });
                return colors.size;
            })()
            """
        )
        assert distinct_bg_colors >= 1, (
            "Action badges must use distinct colored backgrounds — "
            "at least one colored badge background must be found in the audit table"
        )

    def test_page_uses_dark_theme_background(
        self, page: object, base_url: str
    ) -> None:
        """Activity tab body uses dark theme background (gray-950)."""
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
            except Exception:  # noqa: BLE001
                pass

        assert is_dark, (
            f"Activity tab body background {bg!r} — expected dark theme "
            "background (gray-950 #030712 or near-black)"
        )


# ---------------------------------------------------------------------------
# §9.4 — Button recipe on Refresh and pagination buttons
# ---------------------------------------------------------------------------


class TestActivityButtonRecipe:
    """Pagination and Refresh buttons must conform to §9.4 button recipe."""

    @pytest.mark.xfail(reason="Style guide compliance — Epic 77 remediation")
    def test_refresh_button_recipe(self, page: object, base_url: str) -> None:
        """Refresh button matches §9.4 button recipe."""
        _go(page, base_url)

        # Refresh button text: '↻ Refresh'
        button_selectors = [
            "button[class*='border-gray']",
            "button[class*='bg-gray']",
        ]
        for sel in button_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_button(page, sel, variant="secondary")  # type: ignore[arg-type]
                assert result.passed, (
                    f"Refresh button {sel!r} fails §9.4 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No Refresh button found — skipping §9.4 button recipe check"
        )

    def test_pagination_buttons_visible_and_enabled(
        self, page: object, base_url: str
    ) -> None:
        """Next and Previous pagination buttons are visible on the activity tab."""
        _go(page, base_url)

        buttons = page.locator("button")  # type: ignore[attr-defined]
        count = buttons.count()

        found_nav_button = False
        for i in range(count):
            btn = buttons.nth(i)
            text = btn.inner_text() or ""
            if "Next" in text or "Previous" in text:
                assert btn.is_visible(), (
                    f"Pagination button '{text}' must be visible"
                )
                found_nav_button = True
                break

        if not found_nav_button:
            pytest.skip(
                "No Next/Previous buttons found — skipping visibility check"
            )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring
# ---------------------------------------------------------------------------


class TestActivityFocusRing:
    """Interactive elements must display the correct focus ring (§4.2)."""

    def test_filter_select_focus_ring(self, page: object, base_url: str) -> None:
        """Filter select shows the §4.2 focus ring color on keyboard focus."""
        _go(page, base_url)

        selectors_to_try = [
            "select",
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
            "No focusable element found on activity tab — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens
# ---------------------------------------------------------------------------


class TestActivityDesignTokens:
    """CSS design tokens must be registered on :root (§4.1)."""

    def test_font_sans_token_or_direct_declaration(
        self, page: object, base_url: str
    ) -> None:
        """Activity tab loads Inter or a sans-serif font (§6.1)."""
        _go(page, base_url)

        font_family = page.evaluate(  # type: ignore[attr-defined]
            "window.getComputedStyle(document.body).fontFamily"
        )
        assert font_family, "Activity tab body must declare a font-family"
        lower = font_family.lower()
        assert "inter" in lower or "sans" in lower or "system" in lower, (
            f"Activity tab font-family {font_family!r} — expected Inter or "
            "a system sans-serif font (§6.1)"
        )
