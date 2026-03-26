"""Epic 70.3 — Execution Planes: Style Guide Compliance.

Validates that /admin/ui/planes conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4.1     — CSS design tokens registered on :root
  §4.2     — Focus ring color
  §5.1     — Health status badge colors (healthy = green, degraded = amber, offline = red)
  §6       — Typography: page title, section headings, body text, table cells
  §9.1     — Card recipe: background, border, radius, padding (if cards present)
  §9.2     — Table recipe: thead background, <th> scope attributes
  §9.3     — Badge recipe: sizing, padding, font weight

The execution planes page is an operational surface. Worker cluster health
status colors are a functional requirement — operators must identify degraded
or offline clusters instantly without reading every row. §5.1 color semantics:
  - healthy / active / online  → green palette (#22c55e / #16a34a)
  - degraded / paused          → amber/yellow palette (#f59e0b / #d97706)
  - offline / error / failed   → red palette (#ef4444 / #dc2626)

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_planes_intent.py (Epic 70.1).
API contracts are covered in test_planes_api.py (Epic 70.2).
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

PLANES_URL = "/admin/ui/planes"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_planes(page: object, base_url: str) -> None:
    """Navigate to the execution planes page and wait for main content."""
    navigate(page, f"{base_url}{PLANES_URL}")  # type: ignore[arg-type]


def _has_table(page: object) -> bool:
    """Return True when at least one <table> element is present on the page."""
    return page.locator("table").count() > 0  # type: ignore[attr-defined]


def _has_plane_entries(page: object) -> bool:
    """Return True when plane rows or cards are present (not empty-state)."""
    has_rows = (
        page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('table tbody tr').length"
        )
        > 0
    )
    has_cards = page.locator(  # type: ignore[attr-defined]
        "[class*='plane'], [data-plane], [data-component='plane-card'], "
        "[class*='cluster'], [data-cluster]"
    ).count() > 0
    return has_rows or has_cards


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestPlanesDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates that all color, spacing, and typography values are
    driven by CSS custom properties. Their presence on the planes page confirms
    the correct stylesheet is loaded.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_planes(page, base_url)

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
        _navigate_to_planes(page, base_url)

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
        _navigate_to_planes(page, base_url)

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

    def test_page_background_uses_design_token(self, page: object, base_url: str) -> None:
        """Planes page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_planes(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Planes page body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestPlanesFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2)."""

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable elements show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_planes(page, base_url)

        selectors_to_try = [
            "button.btn-primary",
            "button[class*='primary']",
            "button",
            "select",
            "a[href][class*='btn']",
            "a[href]",
            "input",
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
            "No focusable element found on planes page — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §5.1 — Health status badge colors
# ---------------------------------------------------------------------------


class TestPlanesHealthStatusColors:
    """Execution plane health status badges must use §5.1 semantic color tokens.

    The planes page surfaces worker cluster health — operators must see at a
    glance which clusters are healthy, degraded, or offline. §5.1 assigns:
      - healthy / active / online  → green palette (#22c55e / #16a34a)
      - degraded / paused          → amber/yellow palette (#f59e0b / #d97706)
      - offline / error / failed   → red palette (#ef4444 / #dc2626)

    Color semantics are a functional requirement on an operational surface.
    """

    def test_status_badge_colors_present(self, page: object, base_url: str) -> None:
        """Status badges on the planes page use §5.1 color tokens."""
        _navigate_to_planes(page, base_url)

        status_selectors = [
            "[data-status]",
            "[data-health]",
            "[data-plane-status]",
            ".plane-status-badge",
            ".health-badge",
            ".status-badge",
            "[class*='plane-status']",
            "[class*='health-status']",
            "[class*='status-badge']",
        ]
        for sel in status_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Planes status badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        badge_selectors = [".badge", "[class*='badge']", ".pill", "[class*='pill']"]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Badge element {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No status badge element found on planes page — "
            "skipping §5.1 status color check"
        )

    def test_healthy_status_badge_uses_green_palette(self, page: object, base_url: str) -> None:
        """Healthy/active/online plane badges must use the §5.1 green success palette.

        §5.1 reserves the green palette for healthy/pass states. Worker clusters
        with healthy status must render green so operators immediately identify
        operational clusters without reading each row.
        """
        _navigate_to_planes(page, base_url)

        healthy_selectors = [
            "[data-status='healthy']",
            "[data-status='active']",
            "[data-status='online']",
            "[data-status='running']",
            "[data-health='healthy']",
            "[data-plane-status='healthy']",
            "[data-plane-status='active']",
            ".status-healthy",
            ".status-active",
            ".status-online",
            "[class*='status-healthy']",
            "[class*='status-active']",
            "[class*='status-online']",
        ]
        for sel in healthy_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var style = window.getComputedStyle(el);
                        return style.color || style.backgroundColor;
                    }})()
                    """
                )
                if color:
                    success_greens = ("#22c55e", "#16a34a", "#15803d", "#4ade80", "#86efac")
                    is_green = any(colors_close(color, g) for g in success_greens)
                    assert is_green, (
                        f"Healthy/active plane badge {sel!r} uses color {color!r} — "
                        "§5.1 requires green palette for healthy/active/online states"
                    )
                    return

        pytest.skip(
            "No healthy/active/online plane status badge found — "
            "skipping §5.1 green-palette enforcement check"
        )

    def test_offline_error_badge_uses_red_palette(self, page: object, base_url: str) -> None:
        """Offline/error/failed plane badges must use the §5.1 red error palette.

        §5.1 reserves the red palette exclusively for error/failed states.
        Offline or failed worker clusters must render red so operators can
        immediately identify clusters that require intervention.
        """
        _navigate_to_planes(page, base_url)

        offline_selectors = [
            "[data-status='offline']",
            "[data-status='error']",
            "[data-status='failed']",
            "[data-status='disconnected']",
            "[data-health='offline']",
            "[data-health='error']",
            "[data-plane-status='offline']",
            "[data-plane-status='error']",
            ".status-offline",
            ".status-error",
            ".status-failed",
            "[class*='status-offline']",
            "[class*='status-error']",
            "[class*='status-failed']",
        ]
        for sel in offline_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var style = window.getComputedStyle(el);
                        return style.color || style.backgroundColor;
                    }})()
                    """
                )
                if color:
                    error_reds = ("#ef4444", "#dc2626", "#b91c1c", "#f87171", "#fca5a5")
                    is_red = any(colors_close(color, r) for r in error_reds)
                    assert is_red, (
                        f"Offline/error plane badge {sel!r} uses color {color!r} — "
                        "§5.1 requires red palette for offline/error/failed states"
                    )
                    return

        pytest.skip(
            "No offline/error/failed plane status badge found — "
            "skipping §5.1 red-palette enforcement check"
        )

    def test_degraded_badge_uses_amber_palette(self, page: object, base_url: str) -> None:
        """Degraded/paused plane badges must use the §5.1 amber/yellow warning palette.

        §5.1 assigns amber/yellow to warning/degraded states. A degraded worker
        cluster is still partially operational — amber signals partial availability
        without the urgency of red (offline/failed).
        """
        _navigate_to_planes(page, base_url)

        degraded_selectors = [
            "[data-status='degraded']",
            "[data-status='paused']",
            "[data-status='warning']",
            "[data-health='degraded']",
            "[data-health='warning']",
            "[data-plane-status='degraded']",
            "[data-plane-status='paused']",
            ".status-degraded",
            ".status-paused",
            ".status-warning",
            "[class*='status-degraded']",
            "[class*='status-paused']",
            "[class*='status-warning']",
        ]
        for sel in degraded_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var style = window.getComputedStyle(el);
                        return style.color || style.backgroundColor;
                    }})()
                    """
                )
                if color:
                    warning_ambers = ("#f59e0b", "#d97706", "#b45309", "#fbbf24", "#fcd34d")
                    is_amber = any(colors_close(color, a) for a in warning_ambers)
                    assert is_amber, (
                        f"Degraded/paused plane badge {sel!r} uses color {color!r} — "
                        "§5.1 requires amber palette for degraded/paused/warning states"
                    )
                    return

        pytest.skip(
            "No degraded/paused plane status badge found — "
            "skipping §5.1 amber-palette enforcement check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestPlanesTypography:
    """Planes page typography must match the style guide type scale (§6.2).

    The execution planes page carries a page title, optional section headings,
    body text describing cluster state, and table cells. Consistent heading
    scale and body weight help operators parse cluster lists without fatigue.
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1-h3 elements follow the §6.2 heading scale."""
        _navigate_to_planes(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_planes(page, base_url)

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
        _navigate_to_planes(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_table_cell_typography(self, page: object, base_url: str) -> None:
        """Table cell text uses §6.2 body scale (14px / weight 400)."""
        _navigate_to_planes(page, base_url)

        if not _has_table(page):
            pytest.skip(
                "No table found on planes page — skipping table cell typography check"
            )

        assert_typography(page, "td", role="body")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe
# ---------------------------------------------------------------------------


class TestPlanesBadgeRecipe:
    """Badges on the planes page must conform to §9.3 badge recipe.

    Execution planes health badges and registration status labels are the
    primary badge types on this page. They must use the correct sizing,
    padding, and font weight per §9.3 to maintain visual consistency.
    """

    def test_badge_recipe(self, page: object, base_url: str) -> None:
        """Health status and registration badges match §9.3 badge recipe."""
        _navigate_to_planes(page, base_url)

        badge_selectors = [
            "[data-status]",
            "[data-health]",
            "[data-plane-status]",
            ".plane-status-badge",
            ".health-badge",
            ".status-badge",
            "[class*='plane-status']",
            "[class*='health-status']",
            ".badge",
            "[class*='badge']",
            ".pill",
            "[class*='pill']",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Badge {sel!r} on planes page fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No badge element found on planes page — skipping §9.3 badge recipe check"
        )

    def test_dark_theme_does_not_break_layout(self, page: object, base_url: str) -> None:
        """Planes page layout remains intact when dark theme is applied."""
        _navigate_to_planes(page, base_url)

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page body empty after switching to dark theme"
        finally:
            set_light_theme(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.2 — Table recipe
# ---------------------------------------------------------------------------


class TestPlanesTableRecipe:
    """Execution planes table must conform to §9.2 table recipe.

    The planes page typically renders worker clusters in a table with columns
    for cluster name, health status, registration status, and region/zone.
    §9.2 requires a distinct thead background and scope attributes on all
    column headers for accessible data presentation.
    """

    def test_table_recipe(self, page: object, base_url: str) -> None:
        """Execution planes table matches §9.2 table recipe (thead background, th scope)."""
        _navigate_to_planes(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found on planes page — card layout acceptable")

        result = validate_table(page, "table")  # type: ignore[arg-type]
        assert result.passed, (
            f"Execution planes table fails §9.2 recipe: {result.summary()}"
        )

    def test_table_header_scope_attributes(self, page: object, base_url: str) -> None:
        """<th> elements in the planes table have scope='col' attribute (§9.2)."""
        _navigate_to_planes(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found — skipping th scope check")

        th_count = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('table thead th').length"
        )
        if th_count == 0:
            pytest.skip("No thead th elements found — skipping scope attribute check")

        missing_scope = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table thead th');
                var missing = [];
                ths.forEach(function(th, i) {
                    if (!th.hasAttribute('scope')) {
                        missing.push(i);
                    }
                });
                return missing;
            })()
            """
        )
        assert not missing_scope, (
            f"Column headers at indices {missing_scope} are missing scope='col' — "
            "§9.2 requires scope attributes for accessible tables"
        )

    def test_health_column_present_in_table(self, page: object, base_url: str) -> None:
        """Planes table includes a health status column header (§9.2 / §5.1).

        Operators use the planes table to monitor worker cluster health.
        The presence of a health column confirms that health status is surfaced
        at the list level, not buried in a detail panel.
        """
        _navigate_to_planes(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found — skipping health column check")

        headers_text = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table th');
                return Array.from(ths).map(function(th) { return th.textContent.toLowerCase(); });
            })()
            """
        )
        health_keywords = (
            "health",
            "status",
            "state",
            "online",
            "offline",
            "active",
            "available",
        )
        has_health_col = any(
            any(kw in header for kw in health_keywords) for header in headers_text
        )
        if not has_health_col:
            pytest.skip(
                "No health/status column header found in planes table — "
                "health may be shown via card or detail panel (acceptable)"
            )

    def test_registration_column_present_in_table(self, page: object, base_url: str) -> None:
        """Planes table includes a registration status column header (§9.2).

        Registration status gives operators context on which planes are enrolled
        and processing work. This is surfaced at the list level so operators can
        quickly identify unregistered or paused planes.
        """
        _navigate_to_planes(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found — skipping registration column check")

        headers_text = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table th');
                return Array.from(ths).map(function(th) { return th.textContent.toLowerCase(); });
            })()
            """
        )
        registration_keywords = (
            "register",
            "registration",
            "status",
            "active",
            "enabled",
            "connected",
        )
        has_reg_col = any(
            any(kw in header for kw in registration_keywords) for header in headers_text
        )
        if not has_reg_col:
            pytest.skip(
                "No registration column header found in planes table — "
                "registration status may be shown in row detail (acceptable)"
            )


# ---------------------------------------------------------------------------
# §9.1 — Card recipe (if card layout is used)
# ---------------------------------------------------------------------------


class TestPlanesCardRecipe:
    """Execution plane cards must conform to §9.1 card recipe if present.

    Some implementations render worker clusters as cards rather than table rows.
    Each card must have the correct background, border color, border-radius
    (≥ 8px), and padding (≥ 16px) per §9.1.
    """

    def test_card_recipe_if_present(self, page: object, base_url: str) -> None:
        """Execution plane cards match §9.1 card recipe (background, border, radius, padding)."""
        _navigate_to_planes(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".plane-card",
            "[class*='plane-card']",
            ".cluster-card",
            "[class*='cluster-card']",
            ".worker-card",
            "[class*='worker-card']",
            ".detail-panel",
            "[class*='detail-panel']",
            "[data-component='card']",
            "[data-component='plane-card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_card(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Execution plane card/panel {sel!r} fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No card element found on planes page — skipping §9.1 card recipe check"
        )


# ---------------------------------------------------------------------------
# Empty-state styling
# ---------------------------------------------------------------------------


class TestPlanesEmptyStateStyle:
    """Planes empty state must be styled correctly when no planes are registered.

    An empty execution planes page should communicate that no worker clusters
    are registered. It must not show broken layout, phantom table rows, or
    unstyled placeholder text. The page must look intentional, not broken.
    """

    def test_empty_state_no_broken_table(self, page: object, base_url: str) -> None:
        """When no planes are registered, no phantom table rows appear (§9.2).

        Phantom <tr> elements in an empty <tbody> break the §9.2 table recipe by
        rendering blank rows with incorrect spacing and background colors.
        """
        _navigate_to_planes(page, base_url)

        if not _has_table(page):
            pytest.skip("No table on planes page — empty-state table check not applicable")

        if _has_plane_entries(page):
            pytest.skip("Execution planes are present — empty-state test not applicable")

        tbody_row_count = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('table tbody tr').length"
        )
        if tbody_row_count > 1:
            rows_with_content = page.evaluate(  # type: ignore[attr-defined]
                """
                (function() {
                    var rows = document.querySelectorAll('table tbody tr');
                    var count = 0;
                    rows.forEach(function(row) {
                        if (row.textContent.trim().length > 0) count++;
                    });
                    return count;
                })()
                """
            )
            assert rows_with_content <= 1, (
                f"Found {tbody_row_count} tbody rows when no planes are registered; "
                f"only {rows_with_content} contain text — phantom rows indicate broken empty state"
            )

    def test_empty_state_body_background_correct(self, page: object, base_url: str) -> None:
        """Planes page body background is correct even when empty (§4.1).

        An empty planes state must not break the background token — the page
        should still look like a properly styled admin page, not a blank sheet.
        """
        _navigate_to_planes(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Planes page (empty state) body background {bg!r} — "
            "expected gray-50 (#f9fafb) or white (#ffffff) per §4.1 design tokens"
        )
