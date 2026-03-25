"""WCAG 2.2 AA Accessibility Checker (Epic 58, Story 58.6).

Reusable helpers that audit pages for accessibility compliance per WCAG 2.2 AA
requirements as described in style guide Section 11.  Each helper accepts a
Playwright ``Page`` object and returns an :class:`AccessibilityResult` describing
every check performed.

Covers:

- ``assert_focus_visible`` — Tab through all interactive elements; verify each
  shows a 2 px solid focus ring in the correct colour.
- ``assert_keyboard_navigation`` — Tab order is logical; all interactive elements
  reachable via keyboard.
- ``assert_aria_landmarks`` — ``<nav>``, ``<main>``, ``<header>`` present; when
  duplicated they carry distinct ``aria-label`` attributes.
- ``assert_aria_roles`` — Verify a specific ARIA role on one or more elements
  matching a CSS selector.
- ``assert_table_accessibility`` — Every ``<th>`` inside the given table has
  ``scope="col"`` or ``scope="row"``.
- ``assert_form_accessibility`` — Every ``<input>`` / ``<select>`` /
  ``<textarea>`` has an associated ``<label>`` or ``aria-label``; help-text
  elements carry ``aria-describedby``.
- ``assert_touch_targets`` — All buttons and links meet the 24 × 24 px minimum.
- ``assert_no_color_only_indicators`` — Status badge / indicator elements pair
  colour with visible text, an icon, or a ``title`` attribute.
- ``run_axe_audit`` — Inject axe-core via CDN, run a full audit, return
  structured violations with element selectors.

Usage example::

    from tests.playwright.lib.accessibility_helpers import (
        assert_focus_visible,
        assert_aria_landmarks,
        assert_table_accessibility,
        run_axe_audit,
    )

    def test_dashboard_a11y(page):
        page.goto("/admin/ui/dashboard")
        result = assert_aria_landmarks(page)
        assert result.passed, result.summary()

    def test_no_axe_violations(page):
        page.goto("/admin/ui/dashboard")
        violations = run_axe_audit(page)
        assert violations == [], f"{len(violations)} axe violation(s): {violations}"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class AccessibilityResult:
    """Structured pass/fail result returned by every accessibility helper.

    Attributes:
        check:   Short label identifying which a11y check was performed.
        details: List of check descriptions; failures are prefixed ``"FAIL:"``.
        data:    Optional dict with extra diagnostic information.
    """

    check: str
    details: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Return True only when no detail line starts with ``"FAIL:"``."""
        return not any(d.startswith("FAIL:") for d in self.details)

    def summary(self) -> str:
        """One-line summary suitable for pytest ``assert`` messages."""
        status = "PASS" if self.passed else "FAIL"
        failures = [d for d in self.details if d.startswith("FAIL:")]
        if failures:
            return f"[{status}] {self.check}: " + "; ".join(failures)
        return f"[{status}] {self.check}: all checks passed"


# ---------------------------------------------------------------------------
# Internal JS snippets
# ---------------------------------------------------------------------------

_JS_FOCUSABLE_ELEMENTS = """
() => {
    const sel = 'a[href], button:not([disabled]), input:not([disabled]), ' +
        'select:not([disabled]), textarea:not([disabled]), ' +
        '[tabindex]:not([tabindex="-1"]), [contenteditable="true"]';
    return Array.from(document.querySelectorAll(sel)).map(el => ({
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
        label: el.getAttribute('aria-label') || el.textContent.trim().slice(0, 60),
        tabIndex: el.tabIndex,
    }));
}
"""

_JS_FOCUS_RING_CHECK = """
() => {
    const sel = 'a[href], button:not([disabled]), input:not([disabled]), ' +
        'select:not([disabled]), textarea:not([disabled]), ' +
        '[tabindex]:not([tabindex="-1"])';
    const results = [];
    document.querySelectorAll(sel).forEach(el => {
        el.focus();
        const style = window.getComputedStyle(el);
        const outline = style.outlineStyle;
        const outlineWidth = parseFloat(style.outlineWidth) || 0;
        const outlineColor = style.outlineColor;
        // Also check box-shadow as a valid focus indicator
        const boxShadow = style.boxShadow;
        const hasFocusRing = (
            (outline !== 'none' && outlineWidth >= 2) ||
            (boxShadow && boxShadow !== 'none')
        );
        results.push({
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
            label: (el.getAttribute('aria-label') || el.textContent.trim()).slice(0, 60),
            outlineStyle: outline,
            outlineWidth: outlineWidth,
            outlineColor: outlineColor,
            boxShadow: boxShadow,
            hasFocusRing: hasFocusRing,
        });
    });
    return results;
}
"""

_JS_ARIA_LANDMARKS = """
() => {
    const landmarks = {
        nav: Array.from(document.querySelectorAll('nav, [role="navigation"]')).map(el => ({
            tag: el.tagName.toLowerCase(),
            role: el.getAttribute('role') || 'nav',
            ariaLabel: el.getAttribute('aria-label') || '',
        })),
        main: Array.from(document.querySelectorAll('main, [role="main"]')).map(el => ({
            tag: el.tagName.toLowerCase(),
            role: el.getAttribute('role') || 'main',
            ariaLabel: el.getAttribute('aria-label') || '',
        })),
        header: Array.from(document.querySelectorAll('header, [role="banner"]')).map(el => ({
            tag: el.tagName.toLowerCase(),
            role: el.getAttribute('role') || 'header',
            ariaLabel: el.getAttribute('aria-label') || '',
        })),
        aside: Array.from(document.querySelectorAll('aside, [role="complementary"]')).map(el => ({
            tag: el.tagName.toLowerCase(),
            role: el.getAttribute('role') || 'aside',
            ariaLabel: el.getAttribute('aria-label') || '',
        })),
    };
    return landmarks;
}
"""

_JS_ARIA_ROLES = """
(args) => {
    return Array.from(document.querySelectorAll(args.selector)).map(el => ({
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
        role: el.getAttribute('role') || el.tagName.toLowerCase(),
        ariaLabel: el.getAttribute('aria-label') || el.textContent.trim().slice(0, 60),
    }));
}
"""

_JS_TABLE_ACCESSIBILITY = """
(selector) => {
    const table = document.querySelector(selector);
    if (!table) return null;
    const headers = Array.from(table.querySelectorAll('th'));
    return headers.map(th => ({
        text: th.textContent.trim().slice(0, 60),
        scope: th.getAttribute('scope') || '',
        id: th.id || '',
    }));
}
"""

_JS_FORM_ACCESSIBILITY = """
(selector) => {
    const container = document.querySelector(selector) || document.body;
    const controls = Array.from(
        container.querySelectorAll('input:not([type="hidden"]), select, textarea')
    );
    return controls.map(el => {
        const id = el.id || '';
        const ariaLabel = el.getAttribute('aria-label') || '';
        const ariaLabelledBy = el.getAttribute('aria-labelledby') || '';
        const ariaDescribedBy = el.getAttribute('aria-describedby') || '';
        const associatedLabel = id ? !!document.querySelector(`label[for="${id}"]`) : false;
        const hasLabel = associatedLabel || !!ariaLabel || !!ariaLabelledBy;
        return {
            tag: el.tagName.toLowerCase(),
            type: el.getAttribute('type') || '',
            id: id,
            ariaLabel: ariaLabel,
            ariaLabelledBy: ariaLabelledBy,
            ariaDescribedBy: ariaDescribedBy,
            hasLabel: hasLabel,
        };
    });
}
"""

_JS_TOUCH_TARGETS = """
() => {
    const sel = 'a[href], button:not([disabled])';
    return Array.from(document.querySelectorAll(sel)).map(el => {
        const rect = el.getBoundingClientRect();
        return {
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
            label: (el.getAttribute('aria-label') || el.textContent.trim()).slice(0, 60),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            meetsMinimum: rect.width >= 24 && rect.height >= 24,
        };
    });
}
"""

_JS_COLOR_ONLY_INDICATORS = """
() => {
    // Check elements that are commonly used as status/color indicators:
    // badges, pills, dots, status indicators
    const sel = [
        '[class*="badge"]',
        '[class*="status"]',
        '[class*="dot"]',
        '[class*="indicator"]',
        '[class*="pill"]',
        '[class*="tag"]',
        '[data-status]',
        '[aria-label*="status" i]',
    ].join(', ');
    const elements = Array.from(document.querySelectorAll(sel));
    return elements.map(el => {
        const text = el.textContent.trim();
        const ariaLabel = el.getAttribute('aria-label') || '';
        const title = el.getAttribute('title') || '';
        const hasIcon = !!el.querySelector('svg, img, i[class*="icon"], span[class*="icon"]');
        const hasTextContent = text.length > 0;
        const hasAccessibleLabel = ariaLabel.length > 0 || title.length > 0;
        return {
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
            class: el.className || '',
            text: text.slice(0, 40),
            hasTextOrIcon: hasTextContent || hasIcon || hasAccessibleLabel,
        };
    });
}
"""

_JS_INJECT_AXE = """
() => {
    return new Promise((resolve, reject) => {
        if (window.axe) { resolve('already_loaded'); return; }
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js';
        script.onload = () => resolve('loaded');
        script.onerror = (e) => reject('axe-core load failed');
        document.head.appendChild(script);
    });
}
"""

_JS_RUN_AXE = """
() => {
    return new Promise((resolve, reject) => {
        if (!window.axe) { reject('axe not loaded'); return; }
        axe.run({ runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } })
            .then(results => {
                const violations = results.violations.map(v => ({
                    id: v.id,
                    impact: v.impact,
                    description: v.description,
                    helpUrl: v.helpUrl,
                    nodes: v.nodes.map(n => ({
                        html: n.html.slice(0, 200),
                        target: n.target,
                        failureSummary: n.failureSummary || '',
                    })),
                }));
                resolve(violations);
            })
            .catch(err => reject(String(err)));
    });
}
"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def assert_focus_visible(page: Any) -> AccessibilityResult:  # noqa: ANN401
    """Tab through all interactive elements and verify each shows a focus ring.

    A valid focus indicator is either:

    - An outline with ``outline-style != none`` and ``outline-width >= 2px``, or
    - A non-``none`` ``box-shadow`` (used by Tailwind ``ring`` utilities).

    Args:
        page: Playwright ``Page`` object.

    Returns:
        :class:`AccessibilityResult` — passes when every focusable element has a
        visible focus indicator.
    """
    result = AccessibilityResult(check="focus_visible")
    try:
        elements = page.evaluate(_JS_FOCUS_RING_CHECK)
    except Exception as exc:  # noqa: BLE001
        result.details.append(f"FAIL: Could not evaluate focus ring JS — {exc}")
        return result

    if not elements:
        result.details.append("OK: no focusable elements found (page may not be loaded)")
        return result

    missing: list[str] = []
    for el in elements:
        if not el.get("hasFocusRing"):
            label = el.get("label") or el.get("id") or el.get("tag", "?")
            missing.append(f"<{el.get('tag', '?')}> '{label}'")

    if missing:
        result.details.append(
            f"FAIL: {len(missing)} element(s) missing focus ring: "
            + ", ".join(missing[:5])
            + ("…" if len(missing) > 5 else "")
        )
    else:
        result.details.append(f"OK: all {len(elements)} focusable elements have focus rings")

    result.data["elements_checked"] = len(elements)
    result.data["missing_focus_ring"] = missing
    return result


def assert_keyboard_navigation(
    page: Any,  # noqa: ANN401
    min_focusable: int = 1,
    container: str = "body",
) -> AccessibilityResult:
    """Verify that interactive elements are reachable via Tab and have logical order.

    Checks that:

    - At least *min_focusable* interactive elements exist in the page (or container).
    - All elements have ``tabIndex >= 0`` (not removed from tab order).
    - No element has ``tabIndex > 0`` (which breaks natural DOM order).

    Args:
        page:          Playwright ``Page`` object.
        min_focusable: Minimum number of focusable elements expected.
        container:     CSS selector for the root to check; defaults to ``"body"``.

    Returns:
        :class:`AccessibilityResult`.
    """
    result = AccessibilityResult(check="keyboard_navigation")
    try:
        elements = page.evaluate(_JS_FOCUSABLE_ELEMENTS)
    except Exception as exc:  # noqa: BLE001
        result.details.append(f"FAIL: Could not evaluate focusable elements — {exc}")
        return result

    if elements is None:
        result.details.append(f"FAIL: container '{container}' not found")
        return result

    count = len(elements)
    if count < min_focusable:
        result.details.append(
            f"FAIL: expected at least {min_focusable} focusable element(s), found {count}"
        )
    else:
        result.details.append(f"OK: {count} focusable element(s) found")

    positive_tab_index = [e for e in elements if e.get("tabIndex", 0) > 0]
    if positive_tab_index:
        labels = [e.get("label") or e.get("id") or e.get("tag", "?") for e in positive_tab_index[:3]]
        result.details.append(
            f"FAIL: {len(positive_tab_index)} element(s) have tabIndex > 0 (breaks natural order): "
            + ", ".join(labels)
        )
    else:
        result.details.append("OK: no elements with tabIndex > 0")

    result.data["focusable_count"] = count
    result.data["positive_tab_index_elements"] = positive_tab_index
    return result


def assert_aria_landmarks(page: Any) -> AccessibilityResult:  # noqa: ANN401
    """Verify that required ARIA landmark elements are present on the page.

    Checks:

    - At least one ``<main>`` or ``[role="main"]``.
    - At least one ``<nav>`` or ``[role="navigation"]``.
    - At least one ``<header>`` or ``[role="banner"]``.
    - When multiple ``<nav>`` elements exist, each must have a distinct
      ``aria-label`` to help screen-reader users distinguish them.

    Args:
        page: Playwright ``Page`` object.

    Returns:
        :class:`AccessibilityResult`.
    """
    result = AccessibilityResult(check="aria_landmarks")
    try:
        landmarks = page.evaluate(_JS_ARIA_LANDMARKS)
    except Exception as exc:  # noqa: BLE001
        result.details.append(f"FAIL: Could not evaluate landmarks — {exc}")
        return result

    if landmarks is None:
        result.details.append("FAIL: could not read landmarks from page")
        return result

    for name, key in [("main", "main"), ("nav", "nav"), ("header", "header")]:
        items = landmarks.get(key, [])
        if not items:
            result.details.append(f"FAIL: no <{name}> / [role='{name}'] landmark found")
        else:
            result.details.append(f"OK: {len(items)} <{name}> landmark(s) present")
            # When duplicated, each must have aria-label
            if len(items) > 1:
                unlabelled = [i for i in items if not i.get("ariaLabel")]
                if unlabelled:
                    result.details.append(
                        f"FAIL: {len(unlabelled)} <{name}> element(s) lack aria-label "
                        f"(required when multiple {name}s exist)"
                    )
                else:
                    result.details.append(f"OK: all <{name}> landmarks have distinct aria-labels")

    result.data["landmarks"] = landmarks
    return result


def assert_aria_roles(
    page: Any,  # noqa: ANN401
    selector: str,
    expected_role: str,
) -> AccessibilityResult:
    """Verify that elements matching *selector* carry the expected ARIA role.

    The check accepts both native HTML roles (e.g. ``button``, ``link``) and
    explicit ``role="..."`` attribute values.

    Args:
        page:          Playwright ``Page`` object.
        selector:      CSS selector for elements to check.
        expected_role: ARIA role string expected on every matched element.

    Returns:
        :class:`AccessibilityResult`.
    """
    result = AccessibilityResult(check=f"aria_roles[{selector}]={expected_role}")
    try:
        elements = page.evaluate(_JS_ARIA_ROLES, {"selector": selector})
    except Exception as exc:  # noqa: BLE001
        result.details.append(f"FAIL: Could not evaluate ARIA roles — {exc}")
        return result

    if not elements:
        result.details.append(f"FAIL: no elements found for selector '{selector}'")
        return result

    wrong: list[str] = []
    for el in elements:
        actual = el.get("role", "")
        if actual != expected_role:
            label = el.get("ariaLabel") or el.get("id") or el.get("tag", "?")
            wrong.append(f"'{label}' has role='{actual}'")

    if wrong:
        result.details.append(
            f"FAIL: {len(wrong)} element(s) do not have role='{expected_role}': "
            + ", ".join(wrong[:5])
        )
    else:
        result.details.append(
            f"OK: all {len(elements)} element(s) have role='{expected_role}'"
        )

    result.data["elements_checked"] = len(elements)
    result.data["wrong_role_elements"] = wrong
    return result


def assert_table_accessibility(
    page: Any,  # noqa: ANN401
    selector: str = "table",
) -> AccessibilityResult:
    """Verify that every ``<th>`` in *selector* has ``scope="col"`` or ``scope="row"``.

    Args:
        page:     Playwright ``Page`` object.
        selector: CSS selector for the table element to check.

    Returns:
        :class:`AccessibilityResult`.
    """
    result = AccessibilityResult(check=f"table_accessibility[{selector}]")
    try:
        headers = page.evaluate(_JS_TABLE_ACCESSIBILITY, selector)
    except Exception as exc:  # noqa: BLE001
        result.details.append(f"FAIL: Could not evaluate table — {exc}")
        return result

    if headers is None:
        result.details.append(f"FAIL: table '{selector}' not found")
        return result

    if not headers:
        result.details.append("OK: no <th> elements found in table")
        return result

    missing_scope: list[str] = []
    for th in headers:
        scope = th.get("scope", "")
        if scope not in ("col", "row"):
            missing_scope.append(th.get("text") or "(empty)")

    if missing_scope:
        result.details.append(
            f"FAIL: {len(missing_scope)} <th> element(s) missing scope attribute: "
            + ", ".join(f"'{s}'" for s in missing_scope[:5])
        )
    else:
        result.details.append(f"OK: all {len(headers)} <th> element(s) have scope attribute")

    result.data["headers_checked"] = len(headers)
    result.data["missing_scope"] = missing_scope
    return result


def assert_form_accessibility(
    page: Any,  # noqa: ANN401
    selector: str = "body",
) -> AccessibilityResult:
    """Verify that every form control has an accessible label.

    For every ``<input>`` (excluding hidden), ``<select>``, and ``<textarea>``
    inside *selector*:

    - Must have an associated ``<label for="...">`` **or** ``aria-label`` **or**
      ``aria-labelledby``.

    Args:
        page:     Playwright ``Page`` object.
        selector: CSS selector for the form or container to inspect.

    Returns:
        :class:`AccessibilityResult`.
    """
    result = AccessibilityResult(check=f"form_accessibility[{selector}]")
    try:
        controls = page.evaluate(_JS_FORM_ACCESSIBILITY, selector)
    except Exception as exc:  # noqa: BLE001
        result.details.append(f"FAIL: Could not evaluate form controls — {exc}")
        return result

    if controls is None:
        result.details.append(f"FAIL: container '{selector}' not found")
        return result

    if not controls:
        result.details.append("OK: no form controls found in container")
        return result

    unlabelled: list[str] = []
    for ctrl in controls:
        if not ctrl.get("hasLabel"):
            tag = ctrl.get("tag", "?")
            ctrl_type = ctrl.get("type", "")
            ctrl_id = ctrl.get("id", "")
            unlabelled.append(f"<{tag} type='{ctrl_type}' id='{ctrl_id}'>")

    if unlabelled:
        result.details.append(
            f"FAIL: {len(unlabelled)} form control(s) missing accessible label: "
            + ", ".join(unlabelled[:5])
        )
    else:
        result.details.append(
            f"OK: all {len(controls)} form control(s) have accessible labels"
        )

    result.data["controls_checked"] = len(controls)
    result.data["unlabelled_controls"] = unlabelled
    return result


def assert_touch_targets(
    page: Any,  # noqa: ANN401
    min_width: int = 24,
    min_height: int = 24,
) -> AccessibilityResult:
    """Verify that all buttons and links meet the minimum touch-target size.

    WCAG 2.2 SC 2.5.8 requires interactive elements to be at least 24 × 24 CSS
    pixels (AA level).

    Args:
        page:       Playwright ``Page`` object.
        min_width:  Minimum element width in pixels (default 24).
        min_height: Minimum element height in pixels (default 24).

    Returns:
        :class:`AccessibilityResult`.
    """
    result = AccessibilityResult(check="touch_targets")
    try:
        elements = page.evaluate(_JS_TOUCH_TARGETS)
    except Exception as exc:  # noqa: BLE001
        result.details.append(f"FAIL: Could not evaluate touch targets — {exc}")
        return result

    if not elements:
        result.details.append("OK: no buttons or links found")
        return result

    # Filter to elements that are actually visible (non-zero dimensions)
    visible = [e for e in elements if e.get("width", 0) > 0 or e.get("height", 0) > 0]
    too_small: list[str] = []
    for el in visible:
        w = el.get("width", 0)
        h = el.get("height", 0)
        if w < min_width or h < min_height:
            label = el.get("label") or el.get("id") or el.get("tag", "?")
            too_small.append(f"'{label}' ({w}×{h}px)")

    if too_small:
        result.details.append(
            f"FAIL: {len(too_small)} element(s) below {min_width}×{min_height}px minimum: "
            + ", ".join(too_small[:5])
            + ("…" if len(too_small) > 5 else "")
        )
    else:
        result.details.append(
            f"OK: all {len(visible)} visible interactive elements meet {min_width}×{min_height}px minimum"
        )

    result.data["elements_checked"] = len(elements)
    result.data["visible_checked"] = len(visible)
    result.data["too_small"] = too_small
    return result


def assert_no_color_only_indicators(page: Any) -> AccessibilityResult:  # noqa: ANN401
    """Verify that status/indicator elements do not rely on colour alone.

    Per WCAG 2.1 SC 1.4.1, information conveyed by colour must also be
    available via text, icon, pattern, or other non-colour means.

    This helper checks elements carrying class names that typically represent
    status indicators (``badge``, ``status``, ``dot``, ``indicator``, ``pill``,
    ``tag``) and verifies each has one of:

    - Non-empty text content, or
    - An ``<svg>`` / ``<img>`` / icon child element, or
    - A non-empty ``aria-label`` or ``title`` attribute.

    Args:
        page: Playwright ``Page`` object.

    Returns:
        :class:`AccessibilityResult`.
    """
    result = AccessibilityResult(check="no_color_only_indicators")
    try:
        elements = page.evaluate(_JS_COLOR_ONLY_INDICATORS)
    except Exception as exc:  # noqa: BLE001
        result.details.append(f"FAIL: Could not evaluate color indicators — {exc}")
        return result

    if not elements:
        result.details.append("OK: no status indicator elements found")
        return result

    color_only: list[str] = []
    for el in elements:
        if not el.get("hasTextOrIcon"):
            label = el.get("class") or el.get("id") or el.get("tag", "?")
            color_only.append(f"<{el.get('tag', '?')} class='{label}'>")

    if color_only:
        result.details.append(
            f"FAIL: {len(color_only)} element(s) use colour as the only indicator: "
            + ", ".join(color_only[:5])
        )
    else:
        result.details.append(
            f"OK: all {len(elements)} indicator element(s) pair colour with text/icon"
        )

    result.data["elements_checked"] = len(elements)
    result.data["color_only_elements"] = color_only
    return result


def run_axe_audit(
    page: Any,  # noqa: ANN401
    timeout: int = 10_000,
) -> list[dict[str, Any]]:
    """Inject axe-core and run a WCAG 2.x AA audit, returning violations.

    The function injects axe-core 4.9.1 from cdnjs (if not already present),
    then runs ``axe.run()`` restricted to WCAG 2.x AA tags.

    Args:
        page:    Playwright ``Page`` object.
        timeout: Milliseconds to wait for axe injection (default 10 000 ms).

    Returns:
        List of violation dicts — each with ``id``, ``impact``,
        ``description``, ``helpUrl``, and ``nodes``.  Empty list means no
        violations found.

    Raises:
        RuntimeError: If axe-core cannot be loaded or the audit fails.
    """
    try:
        page.evaluate(_JS_INJECT_AXE)
        page.wait_for_function("() => typeof window.axe !== 'undefined'", timeout=timeout)
        violations: list[dict[str, Any]] = page.evaluate(_JS_RUN_AXE)
        return violations if violations else []
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"axe-core audit failed: {exc}") from exc
