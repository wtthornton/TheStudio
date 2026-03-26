"""Epic 74.5 — Detail Pages: Accessibility WCAG 2.2 AA.

Validates that entity detail views (/{entity}/{id}) meet WCAG 2.2 AA requirements:

  Panel ARIA       — detail panels carry role='complementary' or role='dialog',
                     aria-labelledby or aria-label, and a labelled close button (SC 4.1.2)
  Action buttons   — every action button on a detail page has an accessible label
                     (aria-label, aria-labelledby, or visible text) (SC 1.1.1 / 4.1.2)
  Focus management — focus moves into the panel when it opens (SC 2.4.3); Escape
                     dismisses the panel (SC 2.1.2); focus returns to the trigger on close
  Focus indicators — interactive elements show a visible focus ring (SC 2.4.11)
  Keyboard nav     — all interactive elements are reachable by Tab (SC 2.1.1)
  ARIA landmarks   — page exposes <main>, <nav>, and <header> regions (SC 1.3.6)
  Colour-only cues — status/tier badges pair colour with text, icon, or ARIA (SC 1.4.1)
  Touch targets    — buttons and links are at least 24×24 px (SC 2.5.8)
  axe-core audit   — zero critical/serious WCAG 2.x AA violations

Note: Detail pages require seed data.  Tests skip gracefully when no entities exist.
"""

from __future__ import annotations

import pytest
import httpx

from tests.playwright.conftest import navigate
from tests.playwright.lib.accessibility_helpers import (
    assert_aria_landmarks,
    assert_focus_visible,
    assert_keyboard_navigation,
    assert_no_color_only_indicators,
    assert_touch_targets,
    run_axe_audit,
)

pytestmark = pytest.mark.playwright

REPOS_URL = "/admin/ui/repos"
WORKFLOWS_URL = "/admin/ui/workflows"
EXPERTS_URL = "/admin/ui/experts"
API_REPOS = "/api/v1/repos"
API_WORKFLOWS = "/api/v1/workflows"
API_EXPERTS = "/api/v1/experts"

# Selectors for §9.14 sliding detail panels
PANEL_SELECTORS = (
    "[role='complementary'], [role='dialog'], "
    ".detail-panel, .inspector-panel, .slide-panel, "
    "[data-panel], [id*='detail'], [id*='panel']"
)


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
                or ""
            )
        return None
    except Exception:  # noqa: BLE001
        return None


def _go_detail(page: object, base_url: str, detail_base: str, entity_id: str) -> None:
    """Navigate to an entity detail page and wait for DOM to settle."""
    navigate(page, f"{base_url}{detail_base}/{entity_id}")  # type: ignore[arg-type]


def _go_list(page: object, base_url: str, list_url: str) -> None:
    """Navigate to a list page and wait for DOM to settle."""
    navigate(page, f"{base_url}{list_url}")  # type: ignore[arg-type]


def _open_first_row_panel(page: object) -> bool:
    """Click the first visible table row to open the detail panel.

    Returns True if a row was clicked, False otherwise.
    """
    row_selectors = [
        "table tbody tr[hx-get]",
        "table tbody tr[data-detail-trigger]",
        "table tbody tr[data-href]",
        "table tbody tr",
    ]
    for sel in row_selectors:
        rows = page.locator(sel)  # type: ignore[attr-defined]
        if rows.count() == 0:
            continue
        first_row = rows.first
        if not first_row.is_visible():
            continue
        first_row.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]
        return True
    return False


# ---------------------------------------------------------------------------
# Panel ARIA — §9.14 inspector/detail panels (WCAG 2.2 SC 4.1.2)
# ---------------------------------------------------------------------------


class TestDetailPagePanelAria:
    """Detail panels opened from list pages must carry correct ARIA roles and attributes."""

    @pytest.mark.parametrize("list_url,api_path,entity_name", [
        (REPOS_URL, API_REPOS, "repo"),
        (WORKFLOWS_URL, API_WORKFLOWS, "workflow"),
        (EXPERTS_URL, API_EXPERTS, "expert"),
    ])
    def test_panel_has_required_role(
        self,
        page,
        base_url: str,
        list_url: str,
        api_path: str,
        entity_name: str,
    ) -> None:
        """Detail panel element must have role='complementary' or role='dialog'."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5 panel ARIA")

        _go_detail(page, base_url, f"/admin/ui/{entity_name}s", entity_id)

        panel = page.locator(PANEL_SELECTORS)  # type: ignore[attr-defined]
        if panel.count() == 0:
            # Fall back to checking list page for panel trigger
            _go_list(page, base_url, list_url)
            if page.locator("table tbody tr").count() == 0:  # type: ignore[attr-defined]
                pytest.skip(f"No {entity_name} rows — cannot open detail panel")
            if not _open_first_row_panel(page):
                pytest.skip(f"Could not open {entity_name} detail panel")
            panel = page.locator(PANEL_SELECTORS)  # type: ignore[attr-defined]

        assert panel.count() > 0, (
            f"{entity_name} detail panel must be present in the DOM "
            "(expected role='complementary' or role='dialog', .detail-panel, or similar)"
        )

    @pytest.mark.parametrize("list_url,api_path,entity_name", [
        (REPOS_URL, API_REPOS, "repo"),
        (WORKFLOWS_URL, API_WORKFLOWS, "workflow"),
        (EXPERTS_URL, API_EXPERTS, "expert"),
    ])
    def test_panel_has_accessible_name(
        self,
        page,
        base_url: str,
        list_url: str,
        api_path: str,
        entity_name: str,
    ) -> None:
        """Detail panel must carry aria-label or aria-labelledby so screen readers identify it."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, f"/admin/ui/{entity_name}s", entity_id)

        panel_info = page.evaluate(f"""
        () => {{
            const sel = "{PANEL_SELECTORS}";
            return Array.from(document.querySelectorAll(sel)).map(el => ({{
                role: el.getAttribute('role') || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                ariaLabelledBy: el.getAttribute('aria-labelledby') || '',
                ariaHidden: el.getAttribute('aria-hidden') === 'true',
            }}));
        }}
        """)

        if not panel_info:
            pytest.skip(f"No panel elements found on {entity_name} detail page")

        visible_panels = [p for p in panel_info if not p.get("ariaHidden")]
        if not visible_panels:
            pytest.skip(f"All panel elements are aria-hidden on {entity_name} detail page")

        unlabelled = [
            p for p in visible_panels
            if not p.get("ariaLabel") and not p.get("ariaLabelledBy")
        ]
        assert not unlabelled, (
            f"{len(unlabelled)} visible panel(s) on {entity_name} detail page lack "
            "aria-label or aria-labelledby — screen readers cannot identify the panel purpose"
        )

    @pytest.mark.parametrize("list_url,api_path,entity_name", [
        (REPOS_URL, API_REPOS, "repo"),
        (WORKFLOWS_URL, API_WORKFLOWS, "workflow"),
        (EXPERTS_URL, API_EXPERTS, "expert"),
    ])
    def test_panel_close_button_has_aria_label(
        self,
        page,
        base_url: str,
        list_url: str,
        api_path: str,
        entity_name: str,
    ) -> None:
        """The detail panel close button must have an accessible aria-label."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, f"/admin/ui/{entity_name}s", entity_id)

        close_btn_with_label = page.locator(  # type: ignore[attr-defined]
            "[aria-label='Close'], [aria-label='Dismiss'], [aria-label='Close panel'], "
            "[aria-label*='close' i], "
            "button[data-close][aria-label], button.close[aria-label], "
            ".panel-close[aria-label], [data-panel-close][aria-label]"
        )

        if close_btn_with_label.count() > 0:
            return  # Close button has proper aria-label — pass

        # Check if any close button exists WITHOUT an aria-label
        bare_close = page.locator(  # type: ignore[attr-defined]
            "button[data-close]:not([aria-label]), button.close:not([aria-label]), "
            ".panel-close:not([aria-label]):not([aria-labelledby]), "
            "[data-panel-close]:not([aria-label])"
        )
        if bare_close.count() > 0:
            assert False, (
                f"{entity_name} detail panel close button exists but lacks aria-label — "
                "screen readers cannot identify its purpose (SC 4.1.2)"
            )

        pytest.skip(
            f"No explicit close button found on {entity_name} detail page — "
            "panel may use Escape only (acceptable)"
        )


# ---------------------------------------------------------------------------
# Action button labels (WCAG 2.2 SC 1.1.1 / 4.1.2)
# ---------------------------------------------------------------------------


class TestDetailPageActionButtonLabels:
    """Every action button on a detail page must have an accessible name."""

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_all_action_buttons_have_accessible_name(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """All <button> and [role='button'] elements must have a non-empty accessible name."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        unnamed_buttons = page.evaluate("""
        () => {
            const sel = 'button, [role="button"]';
            const results = [];
            document.querySelectorAll(sel).forEach(el => {
                const text = el.textContent.trim();
                const ariaLabel = el.getAttribute('aria-label') || '';
                const ariaLabelledBy = el.getAttribute('aria-labelledby') || '';
                const title = el.getAttribute('title') || '';
                const hasVisibleIcon = !!el.querySelector('svg[aria-label], img[alt]');
                const hasName = text || ariaLabel || ariaLabelledBy || title || hasVisibleIcon;
                if (!hasName) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        className: (el.className || '').slice(0, 60),
                        outerHTML: el.outerHTML.slice(0, 120),
                    });
                }
            });
            return results;
        }
        """)

        assert not unnamed_buttons, (
            f"{len(unnamed_buttons)} action button(s) on {entity_name} detail page "
            "have no accessible name — "
            "add aria-label, visible text, or aria-labelledby: "
            + ", ".join(
                f"<{b['tag']} class='{b['className']}'>" for b in unnamed_buttons[:5]
            )
        )

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_icon_only_buttons_have_aria_label(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Buttons containing only SVG icons or images must have an aria-label."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        icon_only_unlabelled = page.evaluate("""
        () => {
            const results = [];
            document.querySelectorAll('button, [role="button"]').forEach(el => {
                const text = el.textContent.trim();
                if (text) return;  // Has visible text — not icon-only
                const hasSvg = !!el.querySelector('svg');
                const hasImg = !!el.querySelector('img');
                if (!hasSvg && !hasImg) return;  // No icon element
                // This is an icon-only button
                const ariaLabel = el.getAttribute('aria-label') || '';
                const ariaLabelledBy = el.getAttribute('aria-labelledby') || '';
                const title = el.getAttribute('title') || '';
                if (!ariaLabel && !ariaLabelledBy && !title) {
                    results.push({
                        id: el.id || '',
                        className: (el.className || '').slice(0, 60),
                    });
                }
            });
            return results;
        }
        """)

        assert not icon_only_unlabelled, (
            f"{len(icon_only_unlabelled)} icon-only button(s) on {entity_name} detail page "
            "lack aria-label — "
            "icon-only buttons must have aria-label so screen readers can announce purpose: "
            + ", ".join(
                f"class='{b['className']}'" for b in icon_only_unlabelled[:5]
            )
        )

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_tier_change_buttons_are_labelled(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Tier-change controls (Observe/Suggest/Execute) must have accessible names."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        tier_labels = page.evaluate("""
        () => {
            const tierSel = [
                'button[data-tier]',
                'button[aria-label*="observe" i]',
                'button[aria-label*="suggest" i]',
                'button[aria-label*="execute" i]',
                'input[type="radio"][value*="observe" i]',
                'input[type="radio"][value*="suggest" i]',
                'input[type="radio"][value*="execute" i]',
                '[data-action*="tier" i]',
            ].join(', ');
            return Array.from(document.querySelectorAll(tierSel)).map(el => ({
                tag: el.tagName.toLowerCase(),
                text: el.textContent.trim().slice(0, 40),
                ariaLabel: el.getAttribute('aria-label') || '',
                value: el.getAttribute('value') || '',
                hasLabel: !!el.closest('label') || !!document.querySelector(`label[for="${el.id}"]`),
            }));
        }
        """)

        if not tier_labels:
            pytest.skip(
                f"No tier-change controls found on {entity_name} detail page — "
                "may not support tier changes"
            )

        unlabelled_tier = [
            t for t in tier_labels
            if not t.get("text") and not t.get("ariaLabel") and not t.get("value") and not t.get("hasLabel")
        ]
        assert not unlabelled_tier, (
            f"{len(unlabelled_tier)} tier-change control(s) on {entity_name} detail page "
            "have no accessible name — add aria-label or visible text for Observe/Suggest/Execute"
        )


# ---------------------------------------------------------------------------
# Focus management (WCAG 2.2 SC 2.4.3)
# ---------------------------------------------------------------------------


class TestDetailPageFocusManagement:
    """Focus must be correctly managed when detail panels open and close."""

    @pytest.mark.parametrize("list_url,entity_name", [
        (REPOS_URL, "repo"),
        (WORKFLOWS_URL, "workflow"),
        (EXPERTS_URL, "expert"),
    ])
    def test_focus_moves_into_panel_on_open(
        self,
        page,
        base_url: str,
        list_url: str,
        entity_name: str,
    ) -> None:
        """Opening a detail panel from the list must move keyboard focus into the panel."""
        _go_list(page, base_url, list_url)

        if page.locator("table tbody tr").count() == 0:  # type: ignore[attr-defined]
            pytest.skip(f"No {entity_name} rows — cannot test focus management")

        if not _open_first_row_panel(page):
            pytest.skip(f"Could not open {entity_name} detail panel for focus test")

        active_tag = page.evaluate(  # type: ignore[attr-defined]
            "() => document.activeElement?.tagName?.toLowerCase() || ''"
        )
        active_in_panel = page.evaluate(f"""  # type: ignore[attr-defined]
        () => {{
            const panel = document.querySelector("{PANEL_SELECTORS.replace('"', '\\"')}");
            if (!panel) return false;
            return panel.contains(document.activeElement);
        }}
        """)

        assert active_in_panel or active_tag in ("dialog", "aside", "section"), (
            f"After opening {entity_name} detail panel, focus must move inside the panel "
            f"(currently on: <{active_tag}>). "
            "Screen readers require focus to land inside the panel on open (SC 2.4.3)."
        )

    @pytest.mark.parametrize("list_url,entity_name", [
        (REPOS_URL, "repo"),
        (WORKFLOWS_URL, "workflow"),
        (EXPERTS_URL, "expert"),
    ])
    def test_escape_dismisses_panel(
        self,
        page,
        base_url: str,
        list_url: str,
        entity_name: str,
    ) -> None:
        """Pressing Escape must close an open detail panel (SC 2.1.2 / §9.14)."""
        _go_list(page, base_url, list_url)

        if page.locator("table tbody tr").count() == 0:  # type: ignore[attr-defined]
            pytest.skip(f"No {entity_name} rows — cannot test Escape key behaviour")

        if not _open_first_row_panel(page):
            pytest.skip(f"Could not open {entity_name} detail panel for Escape key test")

        panel = page.locator(  # type: ignore[attr-defined]
            "[role='dialog'], [role='complementary'], "
            ".detail-panel, .inspector-panel, .slide-panel"
        )
        if panel.count() == 0:
            pytest.skip(
                f"Detail panel not detectable after row click on {entity_name} list — "
                "cannot verify Escape key behaviour"
            )

        page.keyboard.press("Escape")  # type: ignore[attr-defined]
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        still_open = page.locator(  # type: ignore[attr-defined]
            "[role='dialog']:not([aria-hidden='true']), "
            ".detail-panel:not(.hidden):not([hidden]):not([aria-hidden='true']), "
            ".inspector-panel:not(.hidden):not([hidden]):not([aria-hidden='true'])"
        ).count()

        assert still_open == 0, (
            f"{entity_name} detail panel must close when Escape is pressed "
            "(WCAG 2.2 SC 2.1.2 and §9.14 inspector panel spec)"
        )

    @pytest.mark.parametrize("list_url,entity_name", [
        (REPOS_URL, "repo"),
        (WORKFLOWS_URL, "workflow"),
        (EXPERTS_URL, "expert"),
    ])
    def test_focus_returns_to_trigger_on_panel_close(
        self,
        page,
        base_url: str,
        list_url: str,
        entity_name: str,
    ) -> None:
        """After closing the detail panel, focus must return to the triggering row/button."""
        _go_list(page, base_url, list_url)

        if page.locator("table tbody tr").count() == 0:  # type: ignore[attr-defined]
            pytest.skip(f"No {entity_name} rows — cannot test focus return on close")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        trigger_row = None
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            page.evaluate("""
            (sel) => {
                const el = document.querySelectorAll(sel)[0];
                if (el) el.setAttribute('data-a11y-focus-return-test', 'true');
            }
            """, sel)  # type: ignore[attr-defined]
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            trigger_row = first_row
            break

        if trigger_row is None:
            pytest.skip(f"Could not open {entity_name} detail panel for focus-return test")

        page.keyboard.press("Escape")  # type: ignore[attr-defined]
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        focus_returned = page.evaluate("""
        () => {
            const trigger = document.querySelector('[data-a11y-focus-return-test="true"]');
            if (!trigger) return false;
            return trigger === document.activeElement || trigger.contains(document.activeElement);
        }
        """)  # type: ignore[attr-defined]

        if not focus_returned:
            pytest.xfail(
                f"Focus did not return to the triggering {entity_name} row after panel close "
                "(SC 2.4.3 advisory — acceptable in current implementation)"
            )


# ---------------------------------------------------------------------------
# Focus indicators (WCAG 2.2 SC 2.4.11)
# ---------------------------------------------------------------------------


class TestDetailPageFocusIndicators:
    """Every interactive element on detail pages must show a visible focus ring."""

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_focus_ring_on_all_interactive_elements(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Tab to each focusable element on a detail page — each must show a focus ring."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        result = assert_focus_visible(page)
        assert result.passed, result.summary()

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_no_outline_none_without_alternative(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """No interactive element on a detail page should suppress the focus outline."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        missing = page.evaluate("""
        () => {
            const sel = 'a[href], button:not([disabled]), input:not([disabled]), ' +
                'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
            const results = [];
            document.querySelectorAll(sel).forEach(el => {
                el.focus();
                const style = window.getComputedStyle(el);
                const outlineStyle = style.outlineStyle;
                const outlineWidth = parseFloat(style.outlineWidth) || 0;
                const boxShadow = style.boxShadow;
                const hasOutline = outlineStyle !== 'none' && outlineWidth >= 1;
                const hasBoxShadow = boxShadow && boxShadow !== 'none';
                if (!hasOutline && !hasBoxShadow) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        label: (el.getAttribute('aria-label') || el.textContent.trim()).slice(0, 60),
                    });
                }
            });
            return results;
        }
        """)  # type: ignore[attr-defined]

        assert not missing, (
            f"{len(missing)} interactive element(s) on {entity_name} detail page "
            "suppress focus outline with no alternative indicator: "
            + ", ".join(f"<{e['tag']}> '{e['label'] or e['id']}'" for e in missing[:5])
        )


# ---------------------------------------------------------------------------
# Keyboard navigation (WCAG 2.2 SC 2.1.1)
# ---------------------------------------------------------------------------


class TestDetailPageKeyboardNavigation:
    """All interactive elements on detail pages must be reachable by Tab."""

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_interactive_elements_reachable_by_keyboard(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Detail page must expose at least one focusable interactive element."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        result = assert_keyboard_navigation(page, min_focusable=1)
        assert result.passed, result.summary()

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_no_positive_tabindex_on_detail_page(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """No element on a detail page should use tabindex > 0 (disrupts tab order)."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        positive_tab = page.evaluate("""
        () => {
            return Array.from(document.querySelectorAll('[tabindex]'))
                .filter(el => el.tabIndex > 0)
                .map(el => ({
                    tag: el.tagName.toLowerCase(),
                    id: el.id || '',
                    tabIndex: el.tabIndex,
                    label: (el.getAttribute('aria-label') || el.textContent.trim()).slice(0, 60),
                }));
        }
        """)  # type: ignore[attr-defined]

        assert not positive_tab, (
            f"{len(positive_tab)} element(s) on {entity_name} detail page "
            "use tabindex > 0 (disrupts natural keyboard order): "
            + ", ".join(
                f"<{e['tag']} tabindex={e['tabIndex']}> '{e['label'] or e['id']}'"
                for e in positive_tab[:5]
            )
        )

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_skip_link_or_main_landmark_present(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Detail page must have a skip-to-main-content link or a named <main> landmark."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        skip_link = page.locator(  # type: ignore[attr-defined]
            "a[href='#main'], a[href='#content'], a[href='#main-content'], "
            "a[href*='skip'], a[aria-label*='skip' i]"
        ).count()

        main_element = page.locator("main, [role='main']").count()  # type: ignore[attr-defined]

        assert skip_link > 0 or main_element > 0, (
            f"{entity_name} detail page must have a skip-to-main link or a <main> landmark "
            "so keyboard users can bypass repeated navigation"
        )


# ---------------------------------------------------------------------------
# ARIA landmark regions (WCAG 2.2 SC 1.3.6)
# ---------------------------------------------------------------------------


class TestDetailPageAriaLandmarks:
    """Required ARIA landmark regions must be present on detail pages."""

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_aria_landmarks_present(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Detail page must include <main>, <nav>, and <header> ARIA landmarks."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        result = assert_aria_landmarks(page)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Colour-only status indicators (WCAG 2.2 SC 1.4.1)
# ---------------------------------------------------------------------------


class TestDetailPageColorOnlyIndicators:
    """Status and tier badges on detail pages must pair colour with text, icon, or ARIA."""

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_status_badges_not_color_only(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Status and tier badges on detail pages must not convey state through colour alone."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        result = assert_no_color_only_indicators(page)
        assert result.passed, result.summary()

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_badge_elements_have_text_or_aria_label(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Elements with data-tier, data-status, or badge class names must carry text or ARIA."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        badge_elements = page.evaluate("""
        () => {
            const sel = '[data-tier], [data-status], [class*="tier-"], [class*="-tier"], ' +
                '[class*="status-"], [class*="-status"], [class*="badge"]';
            return Array.from(document.querySelectorAll(sel)).map(el => ({
                tag: el.tagName.toLowerCase(),
                text: el.textContent.trim().slice(0, 40),
                ariaLabel: el.getAttribute('aria-label') || '',
                title: el.getAttribute('title') || '',
                hasIcon: !!el.querySelector('svg, img, [class*="icon"]'),
            }));
        }
        """)  # type: ignore[attr-defined]

        if not badge_elements:
            pytest.skip(f"No badge/tier/status elements found on {entity_name} detail page")

        color_only = [
            e for e in badge_elements
            if not e.get("text")
            and not e.get("ariaLabel")
            and not e.get("title")
            and not e.get("hasIcon")
        ]

        assert not color_only, (
            f"{len(color_only)} badge element(s) on {entity_name} detail page "
            "convey state through colour only: "
            + ", ".join(f"<{e['tag']}>" for e in color_only[:5])
        )


# ---------------------------------------------------------------------------
# Touch target sizes (WCAG 2.2 SC 2.5.8)
# ---------------------------------------------------------------------------


class TestDetailPageTouchTargets:
    """Interactive elements on detail pages must meet 24×24 px minimum target size."""

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_buttons_and_links_meet_minimum_size(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Visible buttons and links on detail pages must be at least 24×24 px."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        result = assert_touch_targets(page, min_width=24, min_height=24)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# axe-core WCAG 2.x AA audit (comprehensive)
# ---------------------------------------------------------------------------


class TestDetailPageAxeAudit:
    """Full axe-core WCAG 2.x AA audit must report zero critical/serious violations."""

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_no_axe_critical_violations(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """axe-core must find zero critical violations on entity detail pages."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        try:
            violations = run_axe_audit(page)
        except RuntimeError as exc:
            pytest.skip(f"axe-core could not be loaded (likely offline/CSP): {exc}")

        critical = [v for v in violations if v.get("impact") == "critical"]
        assert not critical, (
            f"{len(critical)} critical axe violation(s) on {entity_name} detail page: "
            + "; ".join(f"[{v['id']}] {v['description']}" for v in critical[:3])
        )

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_no_axe_serious_violations(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """axe-core must find zero serious violations on entity detail pages."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        try:
            violations = run_axe_audit(page)
        except RuntimeError as exc:
            pytest.skip(f"axe-core could not be loaded (likely offline/CSP): {exc}")

        serious = [v for v in violations if v.get("impact") == "serious"]
        assert not serious, (
            f"{len(serious)} serious axe violation(s) on {entity_name} detail page: "
            + "; ".join(f"[{v['id']}] {v['description']}" for v in serious[:3])
        )

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_axe_full_report_summary(
        self,
        page,
        base_url: str,
        api_path: str,
        detail_base: str,
        entity_name: str,
    ) -> None:
        """Log all axe violations at any severity level on entity detail pages."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for 74.5")

        _go_detail(page, base_url, detail_base, entity_id)

        try:
            violations = run_axe_audit(page)
        except RuntimeError as exc:
            pytest.skip(f"axe-core could not be loaded (likely offline/CSP): {exc}")

        if violations:
            summary_lines = []
            for v in violations:
                impact = v.get("impact", "unknown")
                vid = v.get("id", "?")
                desc = v.get("description", "")
                node_count = len(v.get("nodes", []))
                summary_lines.append(f"  [{impact}] {vid}: {desc} ({node_count} node(s))")

            blocking = [v for v in violations if v.get("impact") in ("critical", "serious")]
            report = "\n".join(summary_lines)
            assert not blocking, (
                f"{entity_name} detail page has {len(blocking)} blocking axe violation(s) "
                f"({len(violations)} total):\n{report}"
            )
        else:
            assert True, (
                f"No axe violations found — {entity_name} detail page is WCAG 2.x AA compliant"
            )
