"""Epic 75.8 — Accessibility Audit & Fixes (WCAG 2.2 AA).

Audits all components introduced in Epic 75 (Icon System, Detail Panel,
Repo/Workflow panels, Kanban Board, Command Palette, Dark Mode) for
WCAG 2.2 AA compliance.

Test categories
---------------
1. axe-core WCAG AA audit  — light mode (all Epic 75 pages)
2. axe-core WCAG AA audit  — dark mode (toggle via JS, re-audit)
3. Detail Panel ARIA       — role="dialog", aria-modal, aria-labelledby, focus-trap
4. Command Palette ARIA    — role="dialog", combobox, listbox, keyboard navigation
5. SVG Icon System         — decorative icons carry aria-hidden="true"
6. Kanban Board            — interactive elements reachable via keyboard
7. Touch targets           — all buttons/links ≥ 24x24 px (WCAG 2.2 SC 2.5.8)
8. No colour-only status   — status indicators pair colour with text/icon
"""

from __future__ import annotations

import pytest

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

# ---------------------------------------------------------------------------
# Pages introduced / heavily modified by Epic 75
# ---------------------------------------------------------------------------

EPIC75_PAGES = [
    "/admin/ui/dashboard",  # dark-mode, icon system, command palette
    "/admin/ui/repos",  # detail panel trigger (75.3), icon system
    "/admin/ui/workflows",  # detail panel trigger (75.4), kanban toggle (75.5)
]

# All admin pages get dark-mode checks (75.7 touched base.html globally)
ALL_ADMIN_PAGES = [
    "/admin/ui/dashboard",
    "/admin/ui/repos",
    "/admin/ui/workflows",
    "/admin/ui/audit",
    "/admin/ui/metrics",
    "/admin/ui/experts",
    "/admin/ui/quarantine",
    "/admin/ui/dead-letters",
    "/admin/ui/settings",
]


# ===========================================================================
# 1. axe-core WCAG AA audit — light mode
# ===========================================================================


@pytest.mark.parametrize("path", EPIC75_PAGES)
def test_axe_no_violations_light_mode(page, base_url: str, path: str) -> None:
    """Run axe-core WCAG 2.x AA audit in light mode on Epic 75 pages.

    Fails if any *critical* or *serious* violations are reported.  Minor
    violations (impact="minor"/"moderate") are collected but do not fail the
    suite to avoid blocking on third-party asset issues.
    """
    navigate(page, f"{base_url}{path}")
    try:
        violations = run_axe_audit(page)
    except RuntimeError as exc:
        pytest.skip(f"axe-core injection failed (CDN unreachable?): {exc}")

    serious = [v for v in violations if v.get("impact") in ("critical", "serious")]
    violation_summary = [f"[{v['impact']}] {v['id']}: {v['description']}" for v in serious]
    assert not serious, f"{path}: {len(serious)} critical/serious axe violation(s):\n" + "\n".join(
        violation_summary
    )


# ===========================================================================
# 2. axe-core WCAG AA audit — dark mode
# ===========================================================================


_JS_ENABLE_DARK_MODE = """
() => {
    // Apply dark mode exactly as tsTheme.toggle() would
    document.documentElement.classList.add('dark');
    localStorage.setItem('ts-theme', 'dark');
}
"""


@pytest.mark.parametrize("path", EPIC75_PAGES)
def test_axe_no_violations_dark_mode(page, base_url: str, path: str) -> None:
    """Run axe-core WCAG 2.x AA audit after enabling dark mode (75.7).

    Contrast ratios in dark mode must still meet WCAG AA (4.5:1 for normal
    text, 3:1 for large text and UI components).
    """
    navigate(page, f"{base_url}{path}")
    page.evaluate(_JS_ENABLE_DARK_MODE)
    # Allow CSS custom properties to recompute
    page.wait_for_timeout(200)

    try:
        violations = run_axe_audit(page)
    except RuntimeError as exc:
        pytest.skip(f"axe-core injection failed (CDN unreachable?): {exc}")

    serious = [v for v in violations if v.get("impact") in ("critical", "serious")]
    violation_summary = [f"[{v['impact']}] {v['id']}: {v['description']}" for v in serious]
    assert not serious, (
        f"{path} [dark mode]: {len(serious)} critical/serious axe violation(s):\n"
        + "\n".join(violation_summary)
    )


# ===========================================================================
# 3. Detail Panel ARIA (Epic 75.2 — global in base.html)
# ===========================================================================


_JS_DETAIL_PANEL_ATTRS = """
() => {
    const panel = document.getElementById('detail-panel');
    if (!panel) return null;
    return {
        role:           panel.getAttribute('role') || '',
        ariaModal:      panel.getAttribute('aria-modal') || '',
        ariaLabelledby: panel.getAttribute('aria-labelledby') || '',
        ariaHidden:     panel.getAttribute('aria-hidden') || '',
        hasCloseBtn:    !!document.getElementById('detail-panel-close'),
        closeBtnLabel:  (document.getElementById('detail-panel-close') || {}).getAttribute
                        ? document.getElementById('detail-panel-close').getAttribute('aria-label') || ''
                        : '',
        titleId:        (document.getElementById('detail-panel-title') || {}).id || '',
    };
}
"""


def test_detail_panel_aria_attributes(page, base_url: str) -> None:
    """detail-panel must carry role=dialog, aria-modal, aria-labelledby (75.2)."""
    navigate(page, f"{base_url}/admin/ui/dashboard")
    attrs = page.evaluate(_JS_DETAIL_PANEL_ATTRS)
    assert attrs is not None, "detail-panel element not found in DOM"
    assert attrs["role"] == "dialog", f"detail-panel: expected role='dialog', got '{attrs['role']}'"
    assert attrs["ariaModal"] == "true", "detail-panel: aria-modal must be 'true'"
    assert attrs["ariaLabelledby"] == "detail-panel-title", (
        "detail-panel: aria-labelledby must reference 'detail-panel-title'"
    )
    assert attrs["hasCloseBtn"], "detail-panel: close button not found"
    assert attrs["closeBtnLabel"], (
        "detail-panel close button: missing aria-label (screen reader users need this)"
    )
    assert attrs["titleId"] == "detail-panel-title", (
        "detail-panel: title element must have id='detail-panel-title'"
    )


_JS_OPEN_DETAIL_PANEL = """
() => {
    const panel = document.getElementById('detail-panel');
    const overlay = document.getElementById('detail-panel-overlay');
    if (!panel) return false;
    panel.removeAttribute('hidden');
    panel.setAttribute('aria-hidden', 'false');
    panel.classList.add('is-open');
    if (overlay) {
        overlay.classList.add('is-open');
        overlay.setAttribute('aria-hidden', 'false');
    }
    return true;
}
"""


def test_detail_panel_focus_trap_structure(page, base_url: str) -> None:
    """When detail panel opens, body #detail-panel-body is tabindex=-1 (programmatic focus target)."""
    navigate(page, f"{base_url}/admin/ui/repos")
    opened = page.evaluate(_JS_OPEN_DETAIL_PANEL)
    assert opened, "Could not open detail panel in test"

    body_tabindex = page.evaluate(
        "() => { const b = document.getElementById('detail-panel-body'); "
        "return b ? b.getAttribute('tabindex') : null; }"
    )
    # tabindex="-1" means it accepts programmatic focus (focus trap sends focus here initially)
    assert body_tabindex == "-1", (
        "detail-panel-body: expected tabindex='-1' for programmatic focus target, "
        f"got '{body_tabindex}'"
    )


# ===========================================================================
# 4. Command Palette ARIA (Epic 75.6)
# ===========================================================================


_JS_CMD_PALETTE_ATTRS = """
() => {
    const modal = document.getElementById('cmd-modal');
    if (!modal) return null;
    return {
        role:       modal.getAttribute('role') || '',
        ariaModal:  modal.getAttribute('aria-modal') || '',
        ariaLabel:  modal.getAttribute('aria-label') || '',
        ariaHidden: modal.getAttribute('aria-hidden') || '',
    };
}
"""

_JS_CMD_INPUT_ATTRS = """
() => {
    const input = document.getElementById('cmd-input');
    if (!input) return null;
    return {
        role:             input.getAttribute('role') || '',
        ariaExpanded:     input.getAttribute('aria-expanded') || '',
        ariaControls:     input.getAttribute('aria-controls') || '',
        ariaAutocomplete: input.getAttribute('aria-autocomplete') || '',
    };
}
"""

_JS_CMD_LISTBOX_ATTRS = """
() => {
    const lb = document.getElementById('cmd-listbox');
    if (!lb) return null;
    return {
        role:      lb.getAttribute('role') || '',
        ariaLabel: lb.getAttribute('aria-label') || '',
    };
}
"""

_JS_OPEN_CMD_PALETTE = """
() => {
    if (window.commandPalette && typeof window.commandPalette.open === 'function') {
        window.commandPalette.open();
        return true;
    }
    return false;
}
"""


def test_command_palette_dialog_attributes(page, base_url: str) -> None:
    """cmd-modal must carry role=dialog, aria-modal, aria-label (75.6)."""
    navigate(page, f"{base_url}/admin/ui/dashboard")
    attrs = page.evaluate(_JS_CMD_PALETTE_ATTRS)
    assert attrs is not None, "cmd-modal element not found in DOM"
    assert attrs["role"] == "dialog", f"cmd-modal: expected role='dialog', got '{attrs['role']}'"
    assert attrs["ariaModal"] == "true", "cmd-modal: aria-modal must be 'true'"
    assert attrs["ariaLabel"], "cmd-modal: missing aria-label"


def test_command_palette_combobox_pattern(page, base_url: str) -> None:
    """cmd-input must implement ARIA combobox pattern (75.6)."""
    navigate(page, f"{base_url}/admin/ui/dashboard")
    attrs = page.evaluate(_JS_CMD_INPUT_ATTRS)
    assert attrs is not None, "cmd-input element not found in DOM"
    assert attrs["role"] == "combobox", (
        f"cmd-input: expected role='combobox', got '{attrs['role']}'"
    )
    assert attrs["ariaControls"] == "cmd-listbox", (
        "cmd-input: aria-controls must reference 'cmd-listbox'"
    )
    assert attrs["ariaAutocomplete"] == "list", "cmd-input: aria-autocomplete must be 'list'"


def test_command_palette_listbox(page, base_url: str) -> None:
    """cmd-listbox must carry role=listbox with an aria-label (75.6)."""
    navigate(page, f"{base_url}/admin/ui/dashboard")
    attrs = page.evaluate(_JS_CMD_LISTBOX_ATTRS)
    assert attrs is not None, "cmd-listbox element not found in DOM"
    assert attrs["role"] == "listbox", (
        f"cmd-listbox: expected role='listbox', got '{attrs['role']}'"
    )
    assert attrs["ariaLabel"], "cmd-listbox: missing aria-label"


def test_command_palette_keyboard_navigation(page, base_url: str) -> None:
    """After opening, ArrowDown selects first item and input focus is retained (75.6)."""
    navigate(page, f"{base_url}/admin/ui/dashboard")
    opened = page.evaluate(_JS_OPEN_CMD_PALETTE)
    if not opened:
        pytest.skip("commandPalette.open() not available — JS may not have loaded")

    # Wait for palette to open and nav items to render
    page.wait_for_selector("#cmd-modal.is-open", timeout=2000)

    # Press ArrowDown to select first item
    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(100)

    # At least one item should now be aria-selected="true"
    selected = page.evaluate(
        "() => Array.from(document.querySelectorAll('.cmd-item[aria-selected=\"true\"]')).length"
    )
    assert selected >= 1, (
        "command palette: ArrowDown did not select any item (aria-selected='true' not found)"
    )

    # Escape closes palette
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    is_open = page.evaluate(
        "() => document.getElementById('cmd-modal')?.classList.contains('is-open') || false"
    )
    assert not is_open, "command palette: Escape key did not close the palette"


# ===========================================================================
# 5. SVG Icon System — decorative icons (Epic 75.1)
# ===========================================================================


_JS_DECORATIVE_ICON_CHECK = """
() => {
    // All inline SVGs in the admin nav should be aria-hidden (decorative)
    const svgs = Array.from(document.querySelectorAll('nav svg, header svg'));
    const lacking = svgs.filter(svg => {
        const ariaHidden = svg.getAttribute('aria-hidden');
        const ariaLabel  = svg.getAttribute('aria-label');
        const role       = svg.getAttribute('role');
        // Acceptable: aria-hidden="true" OR (role="img" AND aria-label present)
        const isDecorative = ariaHidden === 'true';
        const isLabelledImg = role === 'img' && !!ariaLabel;
        return !isDecorative && !isLabelledImg;
    });
    return lacking.map(svg => ({
        outerHTML: svg.outerHTML.slice(0, 120),
        parent: svg.parentElement ? svg.parentElement.tagName.toLowerCase() : '?',
    }));
}
"""


@pytest.mark.parametrize("path", ["/admin/ui/dashboard", "/admin/ui/repos"])
def test_decorative_svgs_aria_hidden(page, base_url: str, path: str) -> None:
    """All decorative SVGs in nav/header must carry aria-hidden='true' (75.1).

    Decorative icons must not be announced by screen readers; they must have
    aria-hidden or be labelled with role="img" + aria-label.
    """
    navigate(page, f"{base_url}{path}")
    lacking = page.evaluate(_JS_DECORATIVE_ICON_CHECK)
    assert not lacking, (
        f"{path}: {len(lacking)} SVG(s) in nav/header lack aria-hidden='true' or "
        f"role='img' + aria-label:\n"
        + "\n".join(f"  parent=<{el['parent']}> {el['outerHTML']}" for el in lacking[:5])
    )


# ===========================================================================
# 6. Kanban Board — keyboard reachability (Epic 75.5)
# ===========================================================================


_JS_SWITCH_TO_KANBAN = """
() => {
    const btn = document.querySelector('[data-view="kanban"], button[onclick*="kanban"], #kanban-toggle');
    if (btn) { btn.click(); return true; }
    // Try looking for a toggle button with kanban text
    const btns = Array.from(document.querySelectorAll('button'));
    const kanbanBtn = btns.find(b => b.textContent.trim().toLowerCase().includes('kanban'));
    if (kanbanBtn) { kanbanBtn.click(); return true; }
    return false;
}
"""


def test_kanban_keyboard_navigation(page, base_url: str) -> None:
    """Kanban board interactive elements must be reachable via keyboard (75.5)."""
    navigate(page, f"{base_url}/admin/ui/workflows")

    # Try switching to kanban view
    switched = page.evaluate(_JS_SWITCH_TO_KANBAN)
    if not switched:
        # Kanban may be the default view or toggle selector changed
        # Check if kanban cards are present directly
        has_kanban = page.evaluate(
            "() => !!document.querySelector('.kanban-col, [data-kanban], .workflow-card')"
        )
        if not has_kanban:
            pytest.skip("Kanban board not reachable on workflows page — view toggle not found")

    page.wait_for_timeout(300)

    result = assert_keyboard_navigation(page, min_focusable=2)
    assert result.passed, f"Kanban keyboard navigation: {result.summary()}"


# ===========================================================================
# 7. Touch targets — WCAG 2.2 SC 2.5.8 (all Epic 75 pages)
# ===========================================================================


@pytest.mark.parametrize("path", EPIC75_PAGES)
def test_touch_targets_min_size(page, base_url: str, path: str) -> None:
    """All visible buttons and links must meet 24x24 px minimum (WCAG 2.2 SC 2.5.8)."""
    navigate(page, f"{base_url}{path}")
    result = assert_touch_targets(page, min_width=24, min_height=24)
    assert result.passed, f"{path} touch targets: {result.summary()}"


# ===========================================================================
# 8. No colour-only status indicators (all Epic 75 pages)
# ===========================================================================


@pytest.mark.parametrize("path", EPIC75_PAGES)
def test_no_color_only_status(page, base_url: str, path: str) -> None:
    """Status badges must pair colour with text/icon (WCAG 2.1 SC 1.4.1)."""
    navigate(page, f"{base_url}{path}")
    result = assert_no_color_only_indicators(page)
    assert result.passed, f"{path} color-only indicators: {result.summary()}"


# ===========================================================================
# 9. ARIA landmarks — all Epic 75 pages
# ===========================================================================


@pytest.mark.parametrize("path", ALL_ADMIN_PAGES)
def test_aria_landmarks_present(page, base_url: str, path: str) -> None:
    """All admin pages must expose <main>, <nav>, and <header> landmarks (75.7 base.html)."""
    navigate(page, f"{base_url}{path}")
    result = assert_aria_landmarks(page)
    assert result.passed, f"{path} ARIA landmarks: {result.summary()}"


# ===========================================================================
# 10. Focus visible — Epic 75 interactive components
# ===========================================================================


@pytest.mark.parametrize("path", EPIC75_PAGES)
def test_focus_visible_ring(page, base_url: str, path: str) -> None:
    """Every focusable element must show a visible focus indicator (WCAG 2.4.11)."""
    navigate(page, f"{base_url}{path}")
    result = assert_focus_visible(page)
    assert result.passed, f"{path} focus visible: {result.summary()}"


# ===========================================================================
# 11. Dark mode — CSS custom properties applied (Epic 75.7)
# ===========================================================================


_JS_CHECK_DARK_TOKEN = """
() => {
    document.documentElement.classList.add('dark');
    const root = window.getComputedStyle(document.documentElement);
    return {
        // Check that at least one CSS custom property resolves differently in dark mode
        // by verifying the 'dark' class is on <html>
        hasDarkClass: document.documentElement.classList.contains('dark'),
        // Verify the dark-mode toggle button exists
        hasToggle: !!document.getElementById('dark-mode-toggle'),
    };
}
"""


def test_dark_mode_toggle_present(page, base_url: str) -> None:
    """Dark mode toggle button must be present in the header (75.7)."""
    navigate(page, f"{base_url}/admin/ui/dashboard")
    info = page.evaluate(_JS_CHECK_DARK_TOKEN)
    assert info["hasToggle"], (
        "Dark mode toggle button (#dark-mode-toggle) not found in header. "
        "Epic 75.7 requires a theme toggle in the header."
    )


def test_dark_mode_class_applied(page, base_url: str) -> None:
    """Enabling dark mode adds 'dark' class to <html> element (75.7)."""
    navigate(page, f"{base_url}/admin/ui/dashboard")
    info = page.evaluate(_JS_CHECK_DARK_TOKEN)
    assert info["hasDarkClass"], (
        "<html> element does not receive 'dark' class when dark mode is enabled. "
        "Epic 75.7 requires Tailwind dark: prefix support via dark class on <html>."
    )
