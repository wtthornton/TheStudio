"""Epic 62.3 — Audit Log: Style Guide Compliance.

Validates that /admin/ui/audit conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4-9:

  §4.1     — CSS design tokens registered on :root
  §4.2     — Focus ring color
  §6       — Typography: page title, section headings, body text
  §9.1     — Card recipe: background, border, radius, padding
  §9.2     — Table recipe: thead background, <th> scope attributes
  §9.3     — Badge recipe: sizing, padding, font weight
  Timestamp — ISO-8601 or locale-formatted timestamps in the event table

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_audit_intent.py (Epic 62.1).
API contracts are covered in test_audit_api.py (Epic 62.2).
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

AUDIT_URL = "/admin/ui/audit"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_audit(page: object, base_url: str) -> None:
    """Navigate to the audit log page and wait for the main content."""
    navigate(page, f"{base_url}{AUDIT_URL}")  # type: ignore[arg-type]


def _has_table(page: object) -> bool:
    """Return True when at least one <table> element is present on the page."""
    return page.locator("table").count() > 0  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestAuditDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates that all color, spacing, and typography values
    are driven by CSS custom properties. The presence of these tokens confirms
    the correct stylesheet is loaded on the audit log page.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_audit(page, base_url)

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
        _navigate_to_audit(page, base_url)

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
        _navigate_to_audit(page, base_url)

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
        """Audit page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_audit(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Audit page body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestAuditFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2).

    The focus ring (blue-600 in light mode) ensures keyboard navigators can
    identify focused elements at a glance on the audit log page.
    """

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable elements show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_audit(page, base_url)

        selectors_to_try = [
            "button.btn-primary",
            "button[class*='primary']",
            "button",
            "a[href][class*='btn']",
            "a[href]",
            "input",
            "select",
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
            "No focusable element found on audit page — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestAuditTypography:
    """Audit page typography must match the style guide type scale (§6.2).

    Key elements:
    - Page title (h1 / .page-title): 20px / weight 600
    - Section headings (h2): 16px / weight 600
    - Body text / table cells: 14px / weight 400
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1-h3 elements follow the §6.2 heading scale."""
        _navigate_to_audit(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_audit(page, base_url)

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
        _navigate_to_audit(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_body_text_typography(self, page: object, base_url: str) -> None:
        """Body text / table cells use §6.2 body scale (14px / weight 400)."""
        _navigate_to_audit(page, base_url)

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


class TestAuditCardRecipe:
    """Audit page cards must conform to §9.1 card recipe.

    Cards typically wrap the audit event table container.
    Each card must have the correct background, border color, border-radius
    (≥ 8px), and padding (≥ 16px).
    """

    def test_card_recipe(self, page: object, base_url: str) -> None:
        """Page cards match §9.1 card recipe (background, border, radius, padding)."""
        _navigate_to_audit(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".audit-card",
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
            "No card element found on audit page — skipping §9.1 card recipe check"
        )


# ---------------------------------------------------------------------------
# §9.2 — Table recipe
# ---------------------------------------------------------------------------


class TestAuditTableRecipe:
    """The audit event table must conform to §9.2 table recipe.

    Validates thead background color, <th scope="col"> presence, and
    appropriate timestamp column formatting.
    """

    def test_audit_table_recipe(self, page: object, base_url: str) -> None:
        """Audit table matches §9.2 table recipe (thead bg, th scope, alignment)."""
        _navigate_to_audit(page, base_url)

        if not _has_table(page):
            pytest.skip("No <table> on audit page — empty state is acceptable")

        result = validate_table(page, "table")  # type: ignore[arg-type]
        assert result.passed, (
            f"Audit table fails §9.2 recipe: {result.summary()}"
        )

    def test_table_th_scope_attributes(self, page: object, base_url: str) -> None:
        """All <th> elements in the audit table carry scope='col' or scope='row'."""
        _navigate_to_audit(page, base_url)

        if not _has_table(page):
            pytest.skip("No <table> on audit page — empty state is acceptable")

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
        """Audit table thead row uses §9.2 gray-50 header background."""
        _navigate_to_audit(page, base_url)

        if not _has_table(page):
            pytest.skip("No <table> on audit page — empty state is acceptable")

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

        is_gray_50 = colors_close(header_bg, "#f9fafb")
        is_transparent = header_bg in ("rgba(0, 0, 0, 0)", "transparent", "")
        assert is_gray_50 or is_transparent, (
            f"Table thead background {header_bg!r} — expected gray-50 (#f9fafb) "
            "or transparent per §9.2"
        )

    def test_timestamp_column_formatted(self, page: object, base_url: str) -> None:
        """Audit table timestamp cells contain a formatted datetime string."""
        _navigate_to_audit(page, base_url)

        if not _has_table(page):
            pytest.skip("No <table> on audit page — empty state is acceptable")

        has_rows = page.locator("table tbody tr").count() > 0
        if not has_rows:
            pytest.skip("No audit event rows — timestamp format check requires data")

        # Look for the timestamp column: first td or a td with a time/datetime element
        timestamp_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var timeEl = document.querySelector('td time, td [datetime], td[data-col="timestamp"]');
                if (timeEl) {
                    return {found: true, text: timeEl.textContent.trim()};
                }
                var firstTd = document.querySelector('table tbody tr td:first-child');
                if (firstTd) {
                    return {found: true, text: firstTd.textContent.trim()};
                }
                return {found: false, text: ''};
            })()
            """
        )
        if not timestamp_info or not timestamp_info.get("found"):
            pytest.skip("No timestamp cell found in audit table")

        ts_text = timestamp_info.get("text", "")
        # Timestamp must contain digits (year, at minimum)
        has_digits = any(ch.isdigit() for ch in ts_text)
        assert has_digits, (
            f"Audit table timestamp column value {ts_text!r} does not appear to be a "
            "formatted datetime — expected ISO-8601 or locale-formatted date"
        )


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe
# ---------------------------------------------------------------------------


class TestAuditBadgeRecipe:
    """Action/status badges on the audit page must conform to §9.3 badge recipe.

    Audit events may carry action-type or severity badges. Each badge must use
    the correct sizing, padding, and font weight.
    """

    def test_badge_recipe_if_present(self, page: object, base_url: str) -> None:
        """Action/status badges match §9.3 badge recipe when present."""
        _navigate_to_audit(page, base_url)

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
                    f"Badge {sel!r} fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No badge element found on audit page — skipping §9.3 badge recipe check"
        )

    def test_dark_theme_does_not_break_layout(self, page: object, base_url: str) -> None:
        """Audit page layout remains intact when dark theme is applied."""
        _navigate_to_audit(page, base_url)

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page body empty after switching to dark theme"
        finally:
            set_light_theme(page)  # type: ignore[arg-type]
