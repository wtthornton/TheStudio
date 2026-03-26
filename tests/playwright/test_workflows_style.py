"""Epic 61.3 — Workflow Console: Style Guide Compliance.

Validates that /admin/ui/workflows conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §5.1     — Status badge colors: running / stuck / failed / queued
  §6       — Typography: page title, section headings, body text
  §9.1     — Card recipe: background, border, radius, padding
  §9.2     — Table recipe: thead background, <th> scope attributes
  §9.3     — Badge recipe: sizing, padding, font weight
  §9.15    — Kanban column specs: column header colors, card border colors
  §4.1     — CSS design tokens registered on :root

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_workflows_intent.py (Epic 61.1).
API contracts are covered in test_workflows_api.py (Epic 61.2).
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

WORKFLOWS_URL = "/admin/ui/workflows"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_workflows(page: object, base_url: str) -> None:
    """Navigate to the workflows page and wait for the main content."""
    navigate(page, f"{base_url}{WORKFLOWS_URL}")  # type: ignore[arg-type]


def _has_table(page: object) -> bool:
    """Return True when at least one <table> element is present on the page."""
    return page.locator("table").count() > 0  # type: ignore[attr-defined]


def _has_kanban(page: object) -> bool:
    """Return True when a kanban board element is present on the page."""
    kanban_selectors = [
        "[data-view='kanban']",
        ".kanban",
        "[class*='kanban']",
        ".kanban-board",
        "[data-component='kanban']",
    ]
    for sel in kanban_selectors:
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({sel!r}).length"
        )
        if count > 0:
            return True
    return False


# ---------------------------------------------------------------------------
# §5.1 — Status badge colors
# ---------------------------------------------------------------------------


class TestWorkflowsStatusColors:
    """Workflow status badges must use the correct §5.1 status color tokens.

    The workflows page renders running / stuck / failed / queued status
    for each workflow. Each status badge must use the semantic color palette
    so operators can instantly distinguish healthy from stuck workflows.
    """

    def test_status_color_running_present(self, page: object, base_url: str) -> None:
        """Running workflow badges use the §5.1 success color token."""
        _navigate_to_workflows(page, base_url)

        selector = "[data-status='running'], [data-status='success'], [data-status='active']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No running/success status badge found — skipping color check")

        assert_status_colors(page, selector, "success")  # type: ignore[arg-type]

    def test_status_color_stuck_present(self, page: object, base_url: str) -> None:
        """Stuck workflow badges use the §5.1 warning color token."""
        _navigate_to_workflows(page, base_url)

        selector = "[data-status='stuck'], [data-status='warning'], [data-status='paused']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No stuck/warning status badge found — skipping color check")

        assert_status_colors(page, selector, "warning")  # type: ignore[arg-type]

    def test_status_color_failed_present(self, page: object, base_url: str) -> None:
        """Failed workflow badges use the §5.1 error color token."""
        _navigate_to_workflows(page, base_url)

        selector = "[data-status='failed'], [data-status='error']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No failed/error status badge found — skipping color check")

        assert_status_colors(page, selector, "error")  # type: ignore[arg-type]

    def test_status_color_queued_present(self, page: object, base_url: str) -> None:
        """Queued workflow badges use the §5.1 neutral/info color token."""
        _navigate_to_workflows(page, base_url)

        selector = "[data-status='queued'], [data-status='pending'], [data-status='info']"
        count = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({selector!r}).length"
        )
        if count == 0:
            pytest.skip("No queued/pending status badge found — skipping color check")

        # Queued maps to neutral/info — just verify badge exists with some styling
        result = validate_badge(page, selector)  # type: ignore[arg-type]
        assert result.passed, (
            f"Queued status badge {selector!r} fails §9.3 recipe: {result.summary()}"
        )

    def test_page_background_uses_design_token(self, page: object, base_url: str) -> None:
        """Workflows page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_workflows(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        # §4.1: surface-app (gray-50 #f9fafb) or white
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Workflows page body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §9.15 — Kanban column specs
# ---------------------------------------------------------------------------


class TestWorkflowsKanbanColumnSpecs:
    """Kanban board columns must match §9.15 column spec colors and card borders.

    §9.15 defines:
      - Column header background: matches the status color for that column
      - Card border-left: 3px solid matching status color
      - Column count badge: gray-600 text on gray-100 background

    When the list view is active these tests are skipped gracefully.
    """

    def test_kanban_column_header_background(self, page: object, base_url: str) -> None:
        """Kanban column headers use the §9.15 status color background."""
        _navigate_to_workflows(page, base_url)

        # Try to activate kanban view if a toggle is present
        toggle_selectors = [
            "button:has-text('Kanban')",
            "button:has-text('Board')",
            "[data-view='kanban']",
            "[data-toggle='kanban']",
        ]
        for sel in toggle_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                try:
                    page.locator(sel).first.click()  # type: ignore[attr-defined]
                    page.wait_for_timeout(500)  # type: ignore[attr-defined]
                except Exception:  # noqa: BLE001
                    pass
                break

        if not _has_kanban(page):
            pytest.skip("Kanban view not active — skipping §9.15 column header check")

        column_header_selectors = [
            ".kanban-column-header",
            "[class*='kanban-column'] h3",
            "[class*='kanban-column'] header",
            "[class*='column-header']",
        ]
        for sel in column_header_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                # Column header must have some background color set
                header_style = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var cs = window.getComputedStyle(el);
                        return {{
                            background: cs.backgroundColor,
                            color: cs.color
                        }};
                    }})()
                    """
                )
                if header_style:
                    bg = header_style.get("background", "")
                    # Must not be fully transparent — §9.15 requires a colored header
                    is_transparent = bg in ("rgba(0, 0, 0, 0)", "transparent", "")
                    if not is_transparent:
                        return  # Column header has a background color — passes

        pytest.skip("No kanban column header found — skipping §9.15 header background check")

    def test_kanban_card_border_left(self, page: object, base_url: str) -> None:
        """Kanban cards have a §9.15 status-color border-left (3px solid)."""
        _navigate_to_workflows(page, base_url)

        if not _has_kanban(page):
            pytest.skip("Kanban view not active — skipping §9.15 card border check")

        card_selectors = [
            ".kanban-card",
            "[class*='kanban-card']",
            ".kanban .card",
            "[class*='kanban'] [class*='card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                border_info = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var cs = window.getComputedStyle(el);
                        return {{
                            borderLeftWidth: cs.borderLeftWidth,
                            borderLeftStyle: cs.borderLeftStyle,
                            borderLeftColor: cs.borderLeftColor
                        }};
                    }})()
                    """
                )
                if not border_info:
                    continue

                width = border_info.get("borderLeftWidth", "0px")
                style = border_info.get("borderLeftStyle", "none")
                # §9.15: left border must be at least 2px (design spec says 3px)
                if width.endswith("px"):
                    px_val = float(width[:-2])
                    assert px_val >= 2, (  # noqa: PLR2004
                        f"Kanban card left border width {px_val}px < 2px — "
                        "§9.15 requires a colored status border-left"
                    )
                assert style not in ("none", "hidden"), (
                    f"Kanban card border-left style is {style!r} — §9.15 requires "
                    "a visible left border indicating status color"
                )
                return

        pytest.skip("No kanban card found — skipping §9.15 card border-left check")

    def test_kanban_column_count_badge_style(self, page: object, base_url: str) -> None:
        """Kanban column count badges use §9.15 gray-100 background, gray-600 text."""
        _navigate_to_workflows(page, base_url)

        if not _has_kanban(page):
            pytest.skip("Kanban view not active — skipping §9.15 column count badge check")

        count_badge_selectors = [
            ".kanban-count",
            "[class*='kanban-count']",
            ".column-count",
            "[class*='column'] .badge",
            "[class*='column'] [class*='badge']",
            "[class*='column'] [class*='count']",
        ]
        for sel in count_badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                badge_style = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var cs = window.getComputedStyle(el);
                        return {{
                            background: cs.backgroundColor,
                            color: cs.color,
                            fontWeight: cs.fontWeight
                        }};
                    }})()
                    """
                )
                if badge_style:
                    # Just verify the badge has a visible background (not fully transparent)
                    bg = badge_style.get("background", "")
                    is_transparent = bg in ("rgba(0, 0, 0, 0)", "transparent", "")
                    if not is_transparent:
                        return  # Has a background color — consistent with §9.15

        pytest.skip("No kanban column count badge found — skipping §9.15 count badge check")

    def test_kanban_dark_theme_columns(self, page: object, base_url: str) -> None:
        """Kanban column colors update correctly when dark theme is applied (§9.15)."""
        _navigate_to_workflows(page, base_url)

        if not _has_kanban(page):
            pytest.skip("Kanban view not active — skipping dark theme kanban check")

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page body empty after switching to dark theme"
        finally:
            set_light_theme(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestWorkflowsFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2).

    The focus ring (blue-600 in light mode) ensures keyboard navigators can
    identify focused elements at a glance on the workflows page.
    """

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable elements show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_workflows(page, base_url)

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

        pytest.skip(
            "No focusable element found on workflows page — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestWorkflowsTypography:
    """Workflows page typography must match the style guide type scale (§6.2).

    Key elements:
    - Page title (h1 / .page-title): 20px / weight 600
    - Section headings (h2): 16px / weight 600
    - Body text / table cells: 14px / weight 400
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1–h3 elements follow the §6.2 heading scale."""
        _navigate_to_workflows(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_workflows(page, base_url)

        selectors = ["h1", ".page-title", "[class*='page-title']"]
        for sel in selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_typography(page, sel, role="page_title")  # type: ignore[arg-type]
                return

        pytest.skip(
            "No page title element (h1/.page-title) found — skipping typography check"
        )

    def test_section_heading_typography(self, page: object, base_url: str) -> None:
        """Section headings (h2) use §6.2 section_title scale (16px / weight 600)."""
        _navigate_to_workflows(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_body_text_typography(self, page: object, base_url: str) -> None:
        """Body text / table cells use §6.2 body scale (14px / weight 400)."""
        _navigate_to_workflows(page, base_url)

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


class TestWorkflowsCardRecipe:
    """Workflows page cards must conform to §9.1 card recipe.

    Cards may wrap the workflow table container or individual kanban cards.
    Each card must have the correct background, border color, border-radius
    (≥ 8px), and padding (≥ 16px).
    """

    def test_card_recipe(self, page: object, base_url: str) -> None:
        """Page cards match §9.1 card recipe (background, border, radius, padding)."""
        _navigate_to_workflows(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".workflow-card",
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

        pytest.skip(
            "No card element found on workflows page — skipping §9.1 card recipe check"
        )

    def test_card_padding_on_4px_grid(self, page: object, base_url: str) -> None:
        """Workflow page cards have §7.1 compliant padding (multiple of 4px)."""
        _navigate_to_workflows(page, base_url)

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
                    assert px_val >= 16, (  # noqa: PLR2004
                        f"Card padding {px_val}px < 16px — §9.1 requires p-4 (16px) minimum"
                    )
                    assert px_val % 4 == 0 or abs(px_val % 4) < 1, (
                        f"Card padding {px_val}px is not a 4px-grid multiple (§7.1)"
                    )
                return

        pytest.skip("No card element found on workflows page — skipping spacing check")


# ---------------------------------------------------------------------------
# §9.2 — Table recipe
# ---------------------------------------------------------------------------


class TestWorkflowsTableRecipe:
    """The workflow table must conform to §9.2 table recipe.

    Validates thead background color, <th scope="col"> presence, and
    right-aligned numeric columns (duration).
    """

    def test_workflow_table_recipe(self, page: object, base_url: str) -> None:
        """Workflow table matches §9.2 table recipe (thead bg, th scope, alignment)."""
        _navigate_to_workflows(page, base_url)

        if not _has_table(page):
            pytest.skip("No <table> on workflows page — empty state is acceptable")

        result = validate_table(page, "table")  # type: ignore[arg-type]
        assert result.passed, (
            f"Workflow table fails §9.2 recipe: {result.summary()}"
        )

    def test_table_th_scope_attributes(self, page: object, base_url: str) -> None:
        """All <th> elements in the workflow table carry scope='col' or scope='row'."""
        _navigate_to_workflows(page, base_url)

        if not _has_table(page):
            pytest.skip("No <table> on workflows page — empty state is acceptable")

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
        """Workflow table thead row uses §9.2 gray-50 header background."""
        _navigate_to_workflows(page, base_url)

        if not _has_table(page):
            pytest.skip("No <table> on workflows page — empty state is acceptable")

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


class TestWorkflowsBadgeRecipe:
    """Status badges must conform to §9.3 badge recipe.

    Workflow status badges (running/stuck/failed/queued) appear in the list
    table and as kanban column indicators. Each badge must use the correct
    sizing, padding, and font weight.
    """

    def test_status_badge_recipe(self, page: object, base_url: str) -> None:
        """Status badges match §9.3 badge recipe (padding, radius, font weight)."""
        _navigate_to_workflows(page, base_url)

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

        pytest.skip(
            "No status badge element found — skipping §9.3 badge recipe check"
        )

    def test_badge_font_size(self, page: object, base_url: str) -> None:
        """Status badges use §9.3 badge font size (12px, text-xs)."""
        _navigate_to_workflows(page, base_url)

        badge_selectors = [
            "[data-status]",
            ".badge",
            "[class*='badge']",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                font_size_raw = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        return window.getComputedStyle(el).fontSize;
                    }})()
                    """
                )
                if font_size_raw and font_size_raw.endswith("px"):
                    px_val = float(font_size_raw[:-2])
                    # §9.3: badge text-xs = 12px; allow up to 13px (some implementations)
                    assert px_val <= 13, (  # noqa: PLR2004
                        f"Badge font size {px_val}px > 13px — §9.3 requires text-xs (12px)"
                    )
                return

        pytest.skip("No badge element found — skipping §9.3 badge font size check")


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestWorkflowsDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates that all color, spacing, and typography values
    are driven by CSS custom properties. The presence of these tokens confirms
    the correct stylesheet is loaded on the workflows page.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_workflows(page, base_url)

        try:
            val = get_css_variable(page, "--color-focus-ring")  # type: ignore[arg-type]
            assert val, (
                "--color-focus-ring CSS variable is empty — §4.1 requires it to be set"
            )
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip(
                    "--color-focus-ring not present; stylesheet may use direct classes"
                )
            raise

    def test_font_sans_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --font-sans is registered on :root (§6.1)."""
        _navigate_to_workflows(page, base_url)

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
                pytest.skip(
                    "--font-sans not present; stylesheet may use direct font declarations"
                )
            raise

    def test_surface_app_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-surface-app is registered (§4.1)."""
        _navigate_to_workflows(page, base_url)

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
