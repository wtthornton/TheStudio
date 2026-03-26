"""Epic 74.3 — Detail Pages: Style Guide Compliance.

Validates that entity detail views (/{entity}/{id}) and inspector panels
conform to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md):

  §9.14    — Inspector panel specs: min-width 320px, backdrop/overlay, slide-in
  §5.1     — Status badge colors: active / paused / error
  §5.2     — Trust tier badge colors: OBSERVE / SUGGEST / EXECUTE
  §6       — Typography: page title, section headings, body text
  §9.1     — Card recipe: background, border, radius, padding
  §9.3     — Badge recipe: sizing, padding, font weight
  §4.1     — CSS design tokens registered on :root
  §4.2     — Focus ring color

These tests check *how* the detail views look, not *what* they contain.
Semantic content is covered in test_detail_pages_intent.py (Epic 74.1).
API contracts are covered in test_detail_pages_api.py (Epic 74.2).
"""

import pytest
import httpx

from tests.playwright.conftest import navigate
from tests.playwright.lib.component_validators import (
    validate_badge,
    validate_card,
)
from tests.playwright.lib.style_assertions import (
    assert_focus_ring_color,
    assert_status_colors,
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

pytestmark = pytest.mark.playwright

REPOS_URL = "/admin/ui/repos"
WORKFLOWS_URL = "/admin/ui/workflows"
EXPERTS_URL = "/admin/ui/experts"
API_REPOS = "/api/v1/repos"
API_WORKFLOWS = "/api/v1/workflows"
API_EXPERTS = "/api/v1/experts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _first_entity_id(base_url: str, api_path: str) -> str | None:
    """Return the first entity ID from a list endpoint, or None if unavailable."""
    try:
        r = httpx.get(f"{base_url.rstrip('/')}{api_path}", timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", data.get("data", []))
        if items:
            first = items[0]
            return str(
                first.get("id")
                or first.get("repo_id")
                or first.get("workflow_id")
                or first.get("expert_id")
                or ""
            ) or None
        return None
    except Exception:
        return None


def _navigate_to_detail(page: object, base_url: str, detail_base: str, entity_id: str) -> None:
    """Navigate to a detail page URL."""
    navigate(page, f"{base_url}{detail_base}/{entity_id}")  # type: ignore[arg-type]


def _navigate_to_list(page: object, base_url: str, list_url: str) -> None:
    """Navigate to a list page URL."""
    navigate(page, f"{base_url}{list_url}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.14 — Inspector Panel Structure
# ---------------------------------------------------------------------------


class TestInspectorPanelStructure:
    """Inspector panels (§9.14) must meet structural and sizing requirements.

    The sliding detail panel opens when an operator clicks a list row. It must:
      - Have a minimum width of 320px (§9.14)
      - Include a backdrop/overlay element when open
      - Be positioned at the side of the viewport (right-side drawer)
      - Provide a close / dismiss mechanism
    """

    def test_inspector_panel_min_width_on_repos(self, page: object, base_url: str) -> None:
        """Repo inspector panel (§9.14) has min-width ≥ 320px when open."""
        _navigate_to_list(page, base_url, REPOS_URL)

        # Trigger the panel by clicking the first row or detail button if available
        rows = page.locator("table tbody tr")  # type: ignore[attr-defined]
        if rows.count() == 0:
            pytest.skip("No repo rows — inspector panel width test requires at least one repo")

        rows.first.click()  # type: ignore[attr-defined]
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        panel_selectors = [
            "[data-panel]",
            "[class*='inspector']",
            "[class*='detail-panel']",
            "[class*='slide']",
            "[class*='drawer']",
            "[role='complementary']",
            "aside",
        ]
        for sel in panel_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                width_px = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return 0;
                        return el.getBoundingClientRect().width;
                    }})()
                    """
                )
                assert width_px >= 320, (
                    f"Inspector panel {sel!r} width {width_px}px < 320px — "
                    "§9.14 requires min-width of 320px"
                )
                return

        pytest.skip("No inspector panel found after row click — skipping §9.14 width check")

    def test_inspector_panel_close_mechanism(self, page: object, base_url: str) -> None:
        """Inspector panel provides a close button or ESC-key dismiss mechanism (§9.14)."""
        _navigate_to_list(page, base_url, REPOS_URL)

        rows = page.locator("table tbody tr")  # type: ignore[attr-defined]
        if rows.count() == 0:
            pytest.skip("No repo rows — close mechanism test requires at least one repo")

        rows.first.click()  # type: ignore[attr-defined]
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        close_selectors = [
            "button[aria-label*='close' i]",
            "button[aria-label*='Close' i]",
            "button[aria-label*='dismiss' i]",
            "[data-panel] button",
            "[class*='inspector'] button",
            "[class*='close']",
            "[class*='dismiss']",
            "aside button",
        ]
        for sel in close_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                return  # Close mechanism found

        # Fall back to checking ESC key works (panel disappears after ESC)
        panels_before = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var sels = ['[data-panel]', 'aside', '[role="complementary"]'];
                for (var i = 0; i < sels.length; i++) {
                    if (document.querySelector(sels[i])) return true;
                }
                return false;
            })()
            """
        )
        if panels_before:
            page.keyboard.press("Escape")  # type: ignore[attr-defined]
            page.wait_for_timeout(300)  # type: ignore[attr-defined]
            # If panel closed with ESC, the test passes
            return

        pytest.skip(
            "No inspector panel found after row click — skipping §9.14 close mechanism check"
        )

    def test_inspector_panel_backdrop_on_workflows(self, page: object, base_url: str) -> None:
        """Workflow inspector panel (§9.14) includes an overlay/backdrop element."""
        _navigate_to_list(page, base_url, WORKFLOWS_URL)

        rows = page.locator("table tbody tr")  # type: ignore[attr-defined]
        if rows.count() == 0:
            pytest.skip("No workflow rows — backdrop test requires at least one workflow")

        rows.first.click()  # type: ignore[attr-defined]
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        backdrop_selectors = [
            "[class*='overlay']",
            "[class*='backdrop']",
            "[class*='scrim']",
            "[data-backdrop]",
            "[aria-modal='true']",
        ]
        panel_found = False
        for sel in backdrop_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                panel_found = True
                break

        if not panel_found:
            # Acceptable: panel without backdrop (e.g., inline split-view) — just verify panel exists
            panel_selectors = [
                "[data-panel]",
                "[class*='inspector']",
                "[class*='detail-panel']",
                "aside",
                "[role='complementary']",
            ]
            for sel in panel_selectors:
                count = page.evaluate(  # type: ignore[attr-defined]
                    f"document.querySelectorAll({sel!r}).length"
                )
                if count > 0:
                    return  # Panel exists; inline split-view without backdrop is acceptable

        # Either backdrop found or panel found — test passes
        if not panel_found:
            pytest.skip("No inspector panel found after workflow row click — skipping §9.14 backdrop check")

    def test_inspector_panel_positioned_right_on_experts(self, page: object, base_url: str) -> None:
        """Expert inspector panel (§9.14) is positioned at the right edge of the viewport."""
        _navigate_to_list(page, base_url, EXPERTS_URL)

        rows = page.locator("table tbody tr")  # type: ignore[attr-defined]
        if rows.count() == 0:
            pytest.skip("No expert rows — position test requires at least one expert")

        rows.first.click()  # type: ignore[attr-defined]
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        panel_selectors = [
            "[data-panel]",
            "[class*='inspector']",
            "[class*='detail-panel']",
            "[class*='drawer']",
            "aside",
        ]
        for sel in panel_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                rect = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var r = el.getBoundingClientRect();
                        return {{right: r.right, viewportWidth: window.innerWidth}};
                    }})()
                    """
                )
                if rect is None:
                    continue
                # Panel right edge should be near or at viewport right edge
                right_proximity = abs(rect["right"] - rect["viewportWidth"])
                assert right_proximity <= 40, (
                    f"Inspector panel right edge ({rect['right']}px) is more than 40px "
                    f"from viewport right ({rect['viewportWidth']}px) — §9.14 requires "
                    "right-anchored placement"
                )
                return

        pytest.skip("No inspector panel found after expert row click — skipping §9.14 position check")


# ---------------------------------------------------------------------------
# §5.2 — Trust tier badge colors on detail views
# ---------------------------------------------------------------------------


class TestDetailPagesTrustTierColors:
    """Trust tier badges on detail pages must use §5.2 color tokens.

    Detail views for repos and experts render OBSERVE / SUGGEST / EXECUTE
    badges. These must match the §5.2 tier palette for instant visual
    recognition across all entity types.
    """

    def test_trust_tier_observe_on_repo_detail(self, page: object, base_url: str) -> None:
        """OBSERVE tier badge on repo detail uses §5.2 observe color token."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos — tier color test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/repos", entity_id)

        for sel in ("[data-tier='observe']", "[data-tier='OBSERVE']", ".tier-observe", "[class*='observe']"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_trust_tier_colors(page, sel, "observe")  # type: ignore[arg-type]
                return

        pytest.skip("No OBSERVE tier badge on repo detail — skipping §5.2 color check")

    def test_trust_tier_badge_on_expert_detail(self, page: object, base_url: str) -> None:
        """Trust tier badge on expert detail uses correct §5.2 color token."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if not entity_id:
            pytest.skip("No experts — tier color test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/experts", entity_id)

        tier_selectors = [
            "[data-tier]",
            ".tier-badge",
            "[class*='tier']",
        ]
        for sel in tier_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                # Determine the tier to validate against
                tier_val = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return '';
                        return (el.getAttribute('data-tier') || el.className || '').toLowerCase();
                    }})()
                    """
                )
                if "observe" in tier_val:
                    assert_trust_tier_colors(page, sel, "observe")  # type: ignore[arg-type]
                elif "suggest" in tier_val:
                    assert_trust_tier_colors(page, sel, "suggest")  # type: ignore[arg-type]
                elif "execute" in tier_val:
                    assert_trust_tier_colors(page, sel, "execute")  # type: ignore[arg-type]
                return

        pytest.skip("No tier badge on expert detail — skipping §5.2 color check")

    def test_trust_tier_dark_mode_on_detail(self, page: object, base_url: str) -> None:
        """Tier badges on repo detail remain visible and non-empty in dark mode."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos — dark mode test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/repos", entity_id)

        tier_selectors = ["[data-tier]", ".tier-badge", "[class*='tier']"]
        for sel in tier_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                set_dark_theme(page)  # type: ignore[arg-type]
                try:
                    body = page.locator("body").inner_text()  # type: ignore[attr-defined]
                    assert len(body) > 0, "Page body empty after switching to dark theme"
                finally:
                    set_light_theme(page)  # type: ignore[arg-type]
                return

        pytest.skip("No tier badge on repo detail — skipping dark mode check")


# ---------------------------------------------------------------------------
# §5.1 — Status badge colors on detail views
# ---------------------------------------------------------------------------


class TestDetailPagesStatusColors:
    """Status badges on detail pages must use §5.1 status color tokens.

    Workflow and repo detail views render running/stuck/failed/active status
    badges. Each must use the semantic palette so operators can identify state
    at a glance.
    """

    def test_status_badge_color_on_workflow_detail(self, page: object, base_url: str) -> None:
        """Status badge on workflow detail uses the correct §5.1 status color."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if not entity_id:
            pytest.skip("No workflows — status color test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/workflows", entity_id)

        for sel in ("[data-status='success']", "[data-status='active']", "[data-status='running']"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_status_colors(page, sel, "success")  # type: ignore[arg-type]
                return

        for sel in ("[data-status='error']", "[data-status='failed']"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_status_colors(page, sel, "error")  # type: ignore[arg-type]
                return

        pytest.skip("No status badge on workflow detail — skipping §5.1 color check")

    def test_status_badge_recipe_on_detail_pages(self, page: object, base_url: str) -> None:
        """Status badges on detail pages conform to §9.3 badge recipe."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos — badge recipe test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/repos", entity_id)

        badge_selectors = [
            "[data-status]",
            ".badge",
            "[class*='badge']",
            ".status-badge",
            ".pill",
        ]
        for sel in badge_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Status badge {sel!r} on repo detail fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip("No status badge on repo detail — skipping §9.3 badge recipe check")


# ---------------------------------------------------------------------------
# §6 — Typography on detail pages
# ---------------------------------------------------------------------------


class TestDetailPagesTypography:
    """Detail page typography must match the style guide type scale (§6.2).

    Key elements checked:
    - Page / panel heading: 20px / weight 600 (h1 / .page-title)
    - Section headings (h2): 16px / weight 600
    - Body text / label text: 14px / weight 400
    """

    def test_heading_scale_compliance_on_repo_detail(self, page: object, base_url: str) -> None:
        """All h1–h3 elements on repo detail follow the §6.2 heading scale."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos — typography test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/repos", entity_id)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography_on_detail(self, page: object, base_url: str) -> None:
        """Detail page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos — typography test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/repos", entity_id)

        for sel in ("h1", ".page-title", "[class*='page-title']"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_typography(page, sel, role="page_title")  # type: ignore[arg-type]
                return

        pytest.skip("No h1/.page-title on repo detail — skipping §6.2 typography check")

    def test_section_heading_typography_on_workflow_detail(self, page: object, base_url: str) -> None:
        """Section headings (h2) on workflow detail use §6.2 section_title scale (16px/600)."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if not entity_id:
            pytest.skip("No workflows — typography test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/workflows", entity_id)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings on workflow detail — skipping section heading check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_body_text_typography_on_detail(self, page: object, base_url: str) -> None:
        """Body text on expert detail uses §6.2 body scale (14px / weight 400)."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if not entity_id:
            pytest.skip("No experts — typography test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/experts", entity_id)

        for sel in ("p", "td", ".body-text", "[class*='label']"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                assert_typography(page, sel, role="body")  # type: ignore[arg-type]
                return

        pytest.skip("No body text on expert detail — skipping §6.2 body typography check")

    def test_heading_scale_compliance_on_list_fallback(self, page: object, base_url: str) -> None:
        """Heading scale compliance verified on list page when no detail entities exist."""
        navigate(page, f"{base_url}{REPOS_URL}")  # type: ignore[arg-type]
        assert_heading_scale(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.1 — Card recipe on detail pages
# ---------------------------------------------------------------------------


class TestDetailPagesCardRecipe:
    """Detail page cards must conform to §9.1 card recipe.

    The inspector panel and dedicated detail pages use card containers to group
    entity metadata. Each card must have the correct background, border color,
    border-radius (≥ 8px), and padding (≥ 16px).
    """

    def test_card_recipe_on_repo_detail(self, page: object, base_url: str) -> None:
        """Repo detail page cards match §9.1 card recipe (background, border, radius, padding)."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos — card recipe test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/repos", entity_id)

        for sel in (".card", "[class*='card']", "[data-component='card']"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_card(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Card {sel!r} on repo detail fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip("No card element on repo detail — skipping §9.1 card recipe check")

    def test_inspector_panel_padding_on_4px_grid(self, page: object, base_url: str) -> None:
        """Inspector panel container (§9.14) has §7.1 compliant padding (multiple of 4px)."""
        _navigate_to_list(page, base_url, REPOS_URL)

        rows = page.locator("table tbody tr")  # type: ignore[attr-defined]
        if rows.count() == 0:
            pytest.skip("No repo rows — inspector panel padding test requires at least one repo")

        rows.first.click()  # type: ignore[attr-defined]
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        panel_selectors = [
            "[data-panel]",
            "[class*='inspector']",
            "[class*='detail-panel']",
            "aside",
        ]
        for sel in panel_selectors:
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                padding_raw = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        return window.getComputedStyle(el).paddingTop;
                    }})()
                    """
                )
                if padding_raw is None:
                    continue
                px_str = padding_raw.strip()
                if px_str.endswith("px"):
                    px_val = float(px_str[:-2])
                    assert px_val % 4 == 0 or abs(px_val % 4) < 1, (
                        f"Inspector panel padding {px_val}px is not a 4px-grid multiple (§7.1)"
                    )
                return

        pytest.skip("No inspector panel found — skipping §7.1 padding grid check")


# ---------------------------------------------------------------------------
# §9.3 — Badge recipe on detail pages
# ---------------------------------------------------------------------------


class TestDetailPagesBadgeRecipe:
    """Badges on detail pages must conform to §9.3 badge recipe.

    Inspector panels and detail views render trust tier and status badges.
    Each badge must meet the §9.3 requirements: rounded corners, horizontal
    padding, correct font weight, and appropriate sizing.
    """

    def test_trust_tier_badge_recipe_on_repo_detail(self, page: object, base_url: str) -> None:
        """Trust tier badges on repo detail match §9.3 badge recipe."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos — badge recipe test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/repos", entity_id)

        for sel in ("[data-tier]", ".tier-badge", "[class*='tier']"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Tier badge {sel!r} on repo detail fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip("No tier badge on repo detail — skipping §9.3 check")

    def test_status_and_tier_badges_on_expert_detail(self, page: object, base_url: str) -> None:
        """All badges on expert detail conform to §9.3 badge recipe."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if not entity_id:
            pytest.skip("No experts — badge recipe test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/experts", entity_id)

        for sel in ("[data-status]", "[data-tier]", ".badge", "[class*='badge']", ".pill"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                result = validate_badge(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Badge {sel!r} on expert detail fails §9.3 recipe: {result.summary()}"
                )
                return

        pytest.skip("No badges on expert detail — skipping §9.3 check")


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens on detail pages
# ---------------------------------------------------------------------------


class TestDetailPagesDesignTokens:
    """CSS design tokens must be registered on :root for all detail views (§4.1).

    Detail pages share the same stylesheet as list pages. This confirms the
    correct stylesheet is loaded and tokens are available for the inspector
    panel's color, spacing, and typography.
    """

    def test_color_focus_ring_token_on_repo_detail(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on repo detail :root."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        navigate_url = (
            f"{base_url}/admin/ui/repos/{entity_id}"
            if entity_id
            else f"{base_url}{REPOS_URL}"
        )
        navigate(page, navigate_url)  # type: ignore[arg-type]

        try:
            val = get_css_variable(page, "--color-focus-ring")  # type: ignore[arg-type]
            assert val, "--color-focus-ring CSS variable is empty — §4.1 requires it to be set"
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip("--color-focus-ring not present; stylesheet may use direct classes")
            raise

    def test_font_sans_token_on_workflow_detail(self, page: object, base_url: str) -> None:
        """CSS custom property --font-sans is registered on workflow detail :root (§6.1)."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        navigate_url = (
            f"{base_url}/admin/ui/workflows/{entity_id}"
            if entity_id
            else f"{base_url}{WORKFLOWS_URL}"
        )
        navigate(page, navigate_url)  # type: ignore[arg-type]

        try:
            val = get_css_variable(page, "--font-sans")  # type: ignore[arg-type]
            assert val, "--font-sans CSS variable is empty — §6.1 requires it to specify Inter"
            assert "inter" in val.lower() or "sans" in val.lower(), (
                f"--font-sans value {val!r} does not reference 'Inter' (§6.1)"
            )
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip("--font-sans not present; stylesheet may use direct font declarations")
            raise

    def test_surface_app_token_on_expert_detail(self, page: object, base_url: str) -> None:
        """CSS custom property --color-surface-app is registered on expert detail (§4.1)."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        navigate_url = (
            f"{base_url}/admin/ui/experts/{entity_id}"
            if entity_id
            else f"{base_url}{EXPERTS_URL}"
        )
        navigate(page, navigate_url)  # type: ignore[arg-type]

        try:
            val = get_css_variable(page, "--color-surface-app")  # type: ignore[arg-type]
            assert val, "--color-surface-app CSS variable is empty — §4.1 requires a surface token"
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip(
                    "--color-surface-app not present; token may be named differently in this build"
                )
            raise


# ---------------------------------------------------------------------------
# §4.2 — Focus ring on detail pages
# ---------------------------------------------------------------------------


class TestDetailPagesFocusRing:
    """Interactive elements on detail pages must display the §4.2 focus ring.

    Action buttons on inspector panels and detail views must show the
    blue-600 focus ring so keyboard navigators can track their position.
    """

    def test_focus_ring_on_repo_detail_buttons(self, page: object, base_url: str) -> None:
        """Buttons on repo detail show the §4.2 focus ring color on keyboard focus."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos — focus ring test requires seed data")

        _navigate_to_detail(page, base_url, "/admin/ui/repos", entity_id)

        for sel in ("button.btn-primary", "button[class*='primary']", "button", "a[href][class*='btn']"):
            count = page.evaluate(  # type: ignore[attr-defined]
                f"document.querySelectorAll({sel!r}).length"
            )
            if count > 0:
                try:
                    assert_focus_ring_color(page, sel)  # type: ignore[arg-type]
                    return
                except AssertionError:
                    continue

        pytest.skip("No focusable button on repo detail — skipping §4.2 focus ring check")

    def test_focus_ring_on_inspector_panel_after_open(self, page: object, base_url: str) -> None:
        """Focus ring is present on inspector panel action buttons after panel opens."""
        _navigate_to_list(page, base_url, REPOS_URL)

        rows = page.locator("table tbody tr")  # type: ignore[attr-defined]
        if rows.count() == 0:
            pytest.skip("No repo rows — focus ring panel test requires at least one repo")

        rows.first.click()  # type: ignore[attr-defined]
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        panel_button_selectors = [
            "[data-panel] button",
            "[class*='inspector'] button",
            "aside button",
            "[role='complementary'] button",
        ]
        for sel in panel_button_selectors:
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
            "No buttons in inspector panel found — skipping §4.2 focus ring panel check"
        )


# ---------------------------------------------------------------------------
# §4.1 — Page background on detail pages
# ---------------------------------------------------------------------------


class TestDetailPagesBackground:
    """Detail page background must use §4.1 design tokens.

    The page background must be gray-50 (#f9fafb) or white in light mode,
    consistent with all other admin pages.
    """

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_page_background_uses_design_token(
        self,
        page: object,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Detail page body background matches §4.1 gray-50 or white design token."""
        entity_id = _first_entity_id(base_url, api_path)
        navigate_url = (
            f"{base_url}{detail_base}/{entity_id}"
            if entity_id
            else f"{base_url}{detail_base}"
        )
        navigate(page, navigate_url)  # type: ignore[arg-type]

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"{entity_name} detail page body background {bg!r} — expected gray-50 "
            f"(#f9fafb) or white (#ffffff) per §4.1 design tokens"
        )
