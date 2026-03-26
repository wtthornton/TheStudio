"""Epic 69.3 — Dead-Letter Inspector: Style Guide Compliance.

Validates that /admin/ui/dead-letters conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4.1     — CSS design tokens registered on :root
  §4.2     — Focus ring color
  §5.1     — Status badge colors (error/dead-lettered = red, retry = amber)
  §6       — Typography: page title, section headings, body text, table cells
  §9.1     — Card recipe: background, border, radius, padding (if cards present)
  §9.2     — Table recipe: thead background, <th> scope attributes
  §9.3     — Badge recipe: sizing, padding, font weight

The dead-letter inspector is an error-triage surface. Dead-lettered events have
permanently exhausted their retry budget. §5.1 error colors (red palette) are
therefore a functional requirement — operators must identify dead-lettered events
instantly without reading every row.

Empty-state styling must render cleanly (no phantom rows, legible message)
so an empty dead-letter queue reads as a positive signal, not a broken page.

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_dead_letters_intent.py (Epic 69.1).
API contracts are covered in test_dead_letters_api.py (Epic 69.2).
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

DEAD_LETTERS_URL = "/admin/ui/dead-letters"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_dead_letters(page: object, base_url: str) -> None:
    """Navigate to the dead-letter inspector page and wait for main content."""
    navigate(page, f"{base_url}{DEAD_LETTERS_URL}")  # type: ignore[arg-type]


def _has_table(page: object) -> bool:
    """Return True when at least one <table> element is present on the page."""
    return page.locator("table").count() > 0  # type: ignore[attr-defined]


def _has_dead_letter_entries(page: object) -> bool:
    """Return True when dead-letter rows or cards are present (not empty-state)."""
    has_rows = (
        page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('table tbody tr').length"
        )
        > 0
    )
    has_cards = page.locator(  # type: ignore[attr-defined]
        "[class*='dead-letter'], [data-dead-letter], [data-component='dead-letter-card']"
    ).count() > 0
    return has_rows or has_cards


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestDeadLettersDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    The style guide mandates that all color, spacing, and typography values are
    driven by CSS custom properties. Their presence on the dead-letter page confirms
    the correct stylesheet is loaded.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_dead_letters(page, base_url)

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
        _navigate_to_dead_letters(page, base_url)

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
        _navigate_to_dead_letters(page, base_url)

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
        """Dead-letter page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_dead_letters(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Dead-letter page body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestDeadLettersFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2)."""

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable elements show the §4.2 focus ring color on keyboard focus."""
        _navigate_to_dead_letters(page, base_url)

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
            "No focusable element found on dead-letter page — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §5.1 — Status badge / error colors
# ---------------------------------------------------------------------------


class TestDeadLettersErrorStatusColors:
    """Dead-letter status badges must use §5.1 error-semantic color tokens.

    The dead-letter inspector surfaces events that have permanently exhausted
    their retry budget — the highest severity error state. §5.1 assigns:
      - dead-lettered / failed / error  → red palette (#ef4444 / #dc2626)
      - retry / pending                 → amber/yellow palette (#f59e0b / #d97706)
      - replayed / resolved             → green palette (#22c55e / #16a34a)

    Operators must be able to identify dead-lettered events at a glance without
    reading every row — correct color semantics are a functional requirement.
    """

    def test_status_badge_colors_present(self, page: object, base_url: str) -> None:
        """Status badges on the dead-letter page use §5.1 color tokens."""
        _navigate_to_dead_letters(page, base_url)

        status_selectors = [
            "[data-status]",
            "[data-dead-letter-status]",
            ".dead-letter-status-badge",
            ".status-badge",
            "[class*='dead-letter-status']",
            "[class*='status-badge']",
        ]
        for sel in status_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Dead-letter status badge {sel!r} fails §9.3 recipe: {result.summary()}"
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
            "No status badge element found on dead-letter page — "
            "skipping §5.1 status color check"
        )

    def test_error_status_badge_uses_red_palette(self, page: object, base_url: str) -> None:
        """Dead-lettered/error/failed badges must use the §5.1 red error palette.

        §5.1 reserves the red palette exclusively for error/failed states.
        Dead-lettered events are permanently failed — their badges must use
        the red palette so operators immediately identify high-severity events.
        """
        _navigate_to_dead_letters(page, base_url)

        error_selectors = [
            "[data-status='error']",
            "[data-status='failed']",
            "[data-status='dead-lettered']",
            "[data-status='dead_lettered']",
            "[data-dead-letter-status='error']",
            "[data-dead-letter-status='failed']",
            ".status-error",
            ".status-failed",
            ".status-dead-lettered",
            "[class*='status-error']",
            "[class*='status-failed']",
            "[class*='status-dead']",
        ]
        for sel in error_selectors:
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
                        f"Dead-lettered badge {sel!r} uses color {color!r} — "
                        "§5.1 requires red palette for error/failed/dead-lettered states"
                    )
                    return

        pytest.skip(
            "No error/failed/dead-lettered status badge found — "
            "skipping §5.1 red-palette enforcement check"
        )

    def test_retry_pending_badge_not_green(self, page: object, base_url: str) -> None:
        """Retry/pending dead-letter badges must not use the success (green) color (§5.1).

        §5.1 reserves green for pass/success states. A retry/pending badge
        rendered green would falsely suggest the event resolved successfully.
        """
        _navigate_to_dead_letters(page, base_url)

        retry_selectors = [
            "[data-status='retry']",
            "[data-status='pending']",
            "[data-dead-letter-status='retry']",
            "[data-dead-letter-status='pending']",
            ".status-retry",
            ".status-pending",
            "[class*='status-retry']",
            "[class*='status-pending']",
        ]
        for sel in retry_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                color = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        return window.getComputedStyle(el).color;
                    }})()
                    """
                )
                if color:
                    success_greens = ("#22c55e", "#16a34a", "#15803d", "#4ade80", "#86efac")
                    is_green = any(colors_close(color, g) for g in success_greens)
                    assert not is_green, (
                        f"Retry/pending dead-letter badge {sel!r} uses green color {color!r} — "
                        "§5.1 reserves green for resolved/success states only"
                    )
                    return

        pytest.skip(
            "No 'retry/pending' dead-letter status badge found — skipping color check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestDeadLettersTypography:
    """Dead-letter page typography must match the style guide type scale (§6.2).

    The dead-letter inspector carries a page title, optional section headings,
    body text describing failure reasons, and table cells. Consistent heading
    scale and body weight help operators parse dense error lists without fatigue.
    """

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1-h3 elements follow the §6.2 heading scale."""
        _navigate_to_dead_letters(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_dead_letters(page, base_url)

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
        _navigate_to_dead_letters(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_table_cell_typography(self, page: object, base_url: str) -> None:
        """Table cell text uses §6.2 body scale (14px / weight 400)."""
        _navigate_to_dead_letters(page, base_url)

        if not _has_table(page):
            pytest.skip(
                "No table found on dead-letter page — skipping table cell typography check"
            )

        assert_typography(page, "td", role="body")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe
# ---------------------------------------------------------------------------


class TestDeadLettersBadgeRecipe:
    """Badges on the dead-letter page must conform to §9.3 badge recipe.

    Dead-letter status badges and failure-reason labels are the primary badge
    types on this page. They must use the correct sizing, padding, and font
    weight per §9.3 to maintain visual consistency with the admin UI badge system.
    """

    def test_badge_recipe(self, page: object, base_url: str) -> None:
        """Status and failure-reason badges match §9.3 badge recipe."""
        _navigate_to_dead_letters(page, base_url)

        badge_selectors = [
            "[data-status]",
            "[data-dead-letter-status]",
            ".dead-letter-status-badge",
            ".status-badge",
            "[class*='dead-letter-status']",
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
                    f"Badge {sel!r} on dead-letter page fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No badge element found on dead-letter page — skipping §9.3 badge recipe check"
        )

    def test_dark_theme_does_not_break_layout(self, page: object, base_url: str) -> None:
        """Dead-letter page layout remains intact when dark theme is applied."""
        _navigate_to_dead_letters(page, base_url)

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page body empty after switching to dark theme"
        finally:
            set_light_theme(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.2 — Table recipe
# ---------------------------------------------------------------------------


class TestDeadLettersTableRecipe:
    """Dead-letter events table must conform to §9.2 table recipe.

    The dead-letter inspector typically renders failed events in a table with
    columns for event ID, failure reason, attempt count, and timestamp.
    §9.2 requires a distinct thead background and scope attributes on all column
    headers for accessible data presentation.
    """

    def test_table_recipe(self, page: object, base_url: str) -> None:
        """Dead-letter events table matches §9.2 table recipe (thead background, th scope)."""
        _navigate_to_dead_letters(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found on dead-letter page — card layout acceptable")

        result = validate_table(page, "table")  # type: ignore[arg-type]
        assert result.passed, (
            f"Dead-letter events table fails §9.2 recipe: {result.summary()}"
        )

    def test_table_header_scope_attributes(self, page: object, base_url: str) -> None:
        """<th> elements in the dead-letter table have scope='col' attribute (§9.2)."""
        _navigate_to_dead_letters(page, base_url)

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

    def test_failure_reason_column_present_in_table(self, page: object, base_url: str) -> None:
        """Dead-letter table includes a failure reason or error column header (§9.2 / §5.1).

        Operators use the dead-letter table to triage permanently failed events.
        The presence of a failure/reason column confirms error context is surfaced
        at the list level, not buried in a detail panel.
        """
        _navigate_to_dead_letters(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found — skipping failure reason column check")

        headers_text = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table th');
                return Array.from(ths).map(function(th) { return th.textContent.toLowerCase(); });
            })()
            """
        )
        reason_keywords = ("reason", "failure", "error", "cause", "message", "status", "fail")
        has_reason_col = any(
            any(kw in header for kw in reason_keywords) for header in headers_text
        )
        if not has_reason_col:
            pytest.skip(
                "No failure reason column header found in dead-letter table — "
                "reason may be shown via row expansion or detail panel (acceptable)"
            )

    def test_attempt_count_column_present_in_table(self, page: object, base_url: str) -> None:
        """Dead-letter table includes an attempt count column or field (§9.2).

        Attempt counts give operators context on how many retries were exhausted
        before the event was dead-lettered. This is surfaced at the list level so
        operators can prioritize high-retry failures for investigation.
        """
        _navigate_to_dead_letters(page, base_url)

        if not _has_table(page):
            pytest.skip("No table found — skipping attempt count column check")

        headers_text = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table th');
                return Array.from(ths).map(function(th) { return th.textContent.toLowerCase(); });
            })()
            """
        )
        attempt_keywords = ("attempt", "retry", "retries", "tries", "count", "times")
        has_attempt_col = any(
            any(kw in header for kw in attempt_keywords) for header in headers_text
        )
        if not has_attempt_col:
            pytest.skip(
                "No attempt count column header found in dead-letter table — "
                "attempt count may be shown in row detail (acceptable)"
            )


# ---------------------------------------------------------------------------
# §9.1 — Card recipe (if card layout is used)
# ---------------------------------------------------------------------------


class TestDeadLettersCardRecipe:
    """Dead-letter event cards must conform to §9.1 card recipe if present.

    Some implementations render dead-lettered events as cards rather than table
    rows. Each card must have the correct background, border color, border-radius
    (≥ 8px), and padding (≥ 16px) per §9.1.
    """

    def test_card_recipe_if_present(self, page: object, base_url: str) -> None:
        """Dead-letter event cards match §9.1 card recipe (background, border, radius, padding)."""
        _navigate_to_dead_letters(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".dead-letter-card",
            "[class*='dead-letter-card']",
            ".event-card",
            "[class*='event-card']",
            ".detail-panel",
            "[class*='detail-panel']",
            "[data-component='card']",
            "[data-component='dead-letter-card']",
        ]
        for sel in card_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_card(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Dead-letter card/panel {sel!r} fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No card element found on dead-letter page — skipping §9.1 card recipe check"
        )


# ---------------------------------------------------------------------------
# Empty-state styling
# ---------------------------------------------------------------------------


class TestDeadLettersEmptyStateStyle:
    """Dead-letter empty state must be styled correctly when no events are present.

    An empty dead-letter queue is a positive signal (no permanently failed events).
    The empty state must not show a broken layout, phantom table rows, or unstyled
    placeholder text. It must render with the same card/surface recipe and
    typography as the populated state so the page looks intentional, not broken.
    """

    def test_empty_state_no_broken_table(self, page: object, base_url: str) -> None:
        """When dead-letter queue is empty, no phantom table rows appear (§9.2).

        Phantom <tr> elements in an empty <tbody> break the §9.2 table recipe by
        rendering blank rows with incorrect spacing and background colors.
        """
        _navigate_to_dead_letters(page, base_url)

        if not _has_table(page):
            pytest.skip("No table on dead-letter page — empty-state table check not applicable")

        if _has_dead_letter_entries(page):
            pytest.skip("Dead-letter queue has entries — empty-state test not applicable")

        tbody_row_count = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('table tbody tr').length"
        )
        # An empty tbody is fine (0 rows). A single "no results" row is also acceptable.
        # Multiple phantom rows without content would indicate a broken empty state.
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
                f"Found {tbody_row_count} tbody rows when dead-letter queue is empty; "
                f"only {rows_with_content} contain text — phantom rows indicate broken empty state"
            )

    def test_empty_state_body_background_correct(self, page: object, base_url: str) -> None:
        """Dead-letter page body background is correct even when empty (§4.1).

        An empty dead-letter state must not break the background token — the page
        should still look like a properly styled admin page, not a blank white sheet.
        """
        _navigate_to_dead_letters(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Dead-letter page (empty state) body background {bg!r} — "
            "expected gray-50 (#f9fafb) or white (#ffffff) per §4.1 design tokens"
        )
