"""Interactive Element Test Utilities (Epic 58, Story 58.5).

Reusable helpers that exercise interactive UI elements via Playwright and assert
on the resulting DOM state changes, HTMX swaps, keyboard navigation order, focus
management, and form submission outcomes.

All helpers accept a Playwright ``Page`` object and selector strings.  They
return :class:`InteractionResult` objects that describe what happened and
whether the post-interaction state is correct.

Covers:

- ``assert_button_clickable`` — visible, enabled, accessible cursor
- ``click_and_assert_state_change`` — click, wait, diff attributes/text
- ``assert_htmx_swap`` — verify hx-* attributes and that a swap target changes
- ``assert_form_submit`` — fill fields, submit, assert outcome
- ``assert_keyboard_navigation`` — Tab through focusable elements in order
- ``assert_focus_trap`` — focus stays within a container (modals, drawers)
- ``assert_dropdown_toggle`` — open/close dropdown; verify expansion state
- ``assert_copy_button`` — click copy button, verify clipboard / UI feedback
- ``assert_link_navigation`` — verify anchor href and optional new-tab behaviour

Usage example::

    from tests.playwright.lib.interaction_helpers import (
        assert_button_clickable,
        click_and_assert_state_change,
        assert_htmx_swap,
        assert_form_submit,
        assert_keyboard_navigation,
        assert_focus_trap,
        assert_dropdown_toggle,
    )

    def test_submit_button(page):
        page.goto("/admin/ui/repos")
        result = assert_button_clickable(page, "button[type='submit']")
        assert result.passed, result.summary()

    def test_htmx_table_refresh(page):
        page.goto("/admin/ui/repos")
        result = assert_htmx_swap(page, "#refresh-btn", "#repo-table")
        assert result.passed, result.summary()

    def test_modal_focus_trap(page):
        page.goto("/admin/ui/repos")
        page.click("#open-modal-btn")
        result = assert_focus_trap(page, "[role='dialog']")
        assert result.passed, result.summary()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class InteractionResult:
    """Structured pass/fail result returned by every interaction helper.

    Attributes:
        action:   Short label identifying which interaction was tested.
        details:  List of check descriptions; failures are prefixed ``"FAIL:"``.
        data:     Optional dict with extra diagnostic information (e.g. captured
                  attribute values before/after).
    """

    action: str
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
            return f"[{status}] {self.action}: " + "; ".join(failures)
        return f"[{status}] {self.action}: all checks passed"


# ---------------------------------------------------------------------------
# Internal JS snippets
# ---------------------------------------------------------------------------

_JS_ELEMENT_INFO = """
(sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return {
        tagName: el.tagName.toLowerCase(),
        disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
        hidden: el.hidden || style.display === 'none' || style.visibility === 'hidden',
        cursor: style.cursor,
        role: el.getAttribute('role') || '',
        ariaLabel: el.getAttribute('aria-label') || el.textContent.trim().slice(0, 80),
        width: rect.width,
        height: rect.height,
        tabIndex: el.tabIndex,
    };
}
"""

_JS_INNER_TEXT = "(sel) => { const el = document.querySelector(sel); return el ? el.innerText : null; }"

_JS_ATTRIBUTE = "(args) => { const el = document.querySelector(args.sel); return el ? el.getAttribute(args.attr) : null; }"

_JS_ELEMENT_EXISTS = "(sel) => !!document.querySelector(sel)"

_JS_FOCUSABLE_SELECTORS = """
() => {
    const focusable = 'a[href], button:not([disabled]), input:not([disabled]), ' +
        'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"]), ' +
        '[contenteditable="true"]';
    return Array.from(document.querySelectorAll(focusable)).map(el => ({
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
        label: el.getAttribute('aria-label') || el.textContent.trim().slice(0, 40),
        tabIndex: el.tabIndex,
    }));
}
"""

_JS_FOCUSED_ELEMENT = """
() => {
    const el = document.activeElement;
    if (!el || el === document.body) return null;
    return {
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
        label: el.getAttribute('aria-label') || el.textContent.trim().slice(0, 40),
        tabIndex: el.tabIndex,
    };
}
"""

_JS_HTMX_ATTRS = """
(sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const attrs = {};
    for (const attr of el.attributes) {
        if (attr.name.startsWith('hx-') || attr.name.startsWith('data-hx-')) {
            attrs[attr.name] = attr.value;
        }
    }
    return attrs;
}
"""

_JS_ARIA_EXPANDED = "(sel) => { const el = document.querySelector(sel); return el ? el.getAttribute('aria-expanded') : null; }"

_JS_CONTAINS_SELECTOR = "(args) => { const parent = document.querySelector(args.parent); return parent ? !!parent.querySelector(args.child) : false; }"

_JS_CHILDREN_COUNT = "(args) => { const el = document.querySelector(args.sel); return el ? el.querySelectorAll(args.child).length : 0; }"


# ---------------------------------------------------------------------------
# assert_button_clickable
# ---------------------------------------------------------------------------


def assert_button_clickable(page: Any, selector: str) -> InteractionResult:
    """Assert that *selector* identifies a visible, enabled, interactive button.

    Checks:

    1. Element is found in DOM.
    2. Element is not disabled (``disabled`` attribute or ``aria-disabled``).
    3. Element is not visually hidden.
    4. Element has a touch target of at least 24×24 px (style guide §4.5).
    5. ``cursor`` is ``pointer`` or element is a native ``<button>``/``<a>``.
    6. Element has an accessible label (``aria-label`` or visible text).

    Args:
        page:     Playwright ``Page`` (or any object whose ``.evaluate()``
                  accepts JS expressions).
        selector: CSS selector identifying the interactive element.

    Returns:
        :class:`InteractionResult` with action ``"button_clickable"``.
    """
    result = InteractionResult(action="button_clickable", data={"selector": selector})
    info = page.evaluate(_JS_ELEMENT_INFO, selector)

    if info is None:
        result.details.append(f"FAIL: element not found: {selector!r}")
        return result

    result.data["element"] = info

    # 1. Not disabled
    if info["disabled"]:
        result.details.append(f"FAIL: element is disabled ({selector!r})")
    else:
        result.details.append("OK: element is not disabled")

    # 2. Not hidden
    if info["hidden"]:
        result.details.append(f"FAIL: element is visually hidden ({selector!r})")
    else:
        result.details.append("OK: element is visible")

    # 3. Touch target size
    w, h = info["width"], info["height"]
    if w < 24 or h < 24:
        result.details.append(
            f"FAIL: touch target {w:.0f}×{h:.0f}px is below 24×24px minimum"
        )
    else:
        result.details.append(f"OK: touch target {w:.0f}×{h:.0f}px ≥ 24×24px")

    # 4. Cursor / native element
    is_native = info["tagName"] in ("button", "a", "input", "select", "textarea")
    if not is_native and info["cursor"] != "pointer":
        result.details.append(
            f"FAIL: cursor is {info['cursor']!r} (expected 'pointer' for "
            f"non-native element)"
        )
    else:
        result.details.append(f"OK: cursor/tag indicates interactive ({info['tagName']})")

    # 5. Accessible label
    label = (info.get("ariaLabel") or "").strip()
    if not label:
        result.details.append("FAIL: element has no accessible label or visible text")
    else:
        result.details.append(f"OK: accessible label found: {label!r}")

    return result


# ---------------------------------------------------------------------------
# click_and_assert_state_change
# ---------------------------------------------------------------------------


def click_and_assert_state_change(
    page: Any,
    click_selector: str,
    state_selector: str,
    *,
    expected_text: str | None = None,
    expected_attr: tuple[str, str] | None = None,
    expected_class: str | None = None,
    timeout_ms: int = 3000,
) -> InteractionResult:
    """Click an element and assert that *state_selector* reflects the new state.

    After clicking *click_selector*, the helper waits up to *timeout_ms*
    milliseconds for one of three observable changes on *state_selector*:

    - ``expected_text``  — the element's ``innerText`` contains this value.
    - ``expected_attr``  — ``(attribute_name, expected_value)`` pair.
    - ``expected_class`` — the element's ``className`` contains this value.

    At least one of the three keyword arguments must be provided.

    Args:
        page:             Playwright ``Page``.
        click_selector:   CSS selector for the element to click.
        state_selector:   CSS selector for the element whose state is checked.
        expected_text:    Substring expected in the target's ``innerText``.
        expected_attr:    ``(attr, value)`` pair expected on the target.
        expected_class:   CSS class name expected on the target.
        timeout_ms:       How long to wait for state change (milliseconds).

    Returns:
        :class:`InteractionResult` with action ``"state_change"``.
    """
    result = InteractionResult(
        action="state_change",
        data={
            "click_selector": click_selector,
            "state_selector": state_selector,
        },
    )

    if expected_text is None and expected_attr is None and expected_class is None:
        result.details.append(
            "FAIL: at least one of expected_text / expected_attr / expected_class "
            "must be provided"
        )
        return result

    # Capture before state
    before_text = page.evaluate(_JS_INNER_TEXT, state_selector)

    # Perform click
    clickable = page.evaluate(_JS_ELEMENT_EXISTS, click_selector)
    if not clickable:
        result.details.append(f"FAIL: click target not found: {click_selector!r}")
        return result

    page.click(click_selector)

    # Wait for state change
    if expected_text is not None:
        try:
            page.wait_for_function(
                f"""() => {{
                    const el = document.querySelector({state_selector!r});
                    return el && el.innerText.includes({expected_text!r});
                }}""",
                timeout=timeout_ms,
            )
            after_text = page.evaluate(_JS_INNER_TEXT, state_selector)
            result.data["before_text"] = before_text
            result.data["after_text"] = after_text
            result.details.append(
                f"OK: text changed to include {expected_text!r}"
            )
        except Exception as exc:
            after_text = page.evaluate(_JS_INNER_TEXT, state_selector)
            result.data["after_text"] = after_text
            result.details.append(
                f"FAIL: text did not change to include {expected_text!r} "
                f"within {timeout_ms}ms — got: {after_text!r} ({exc})"
            )

    if expected_attr is not None:
        attr_name, attr_value = expected_attr
        try:
            page.wait_for_function(
                f"""() => {{
                    const el = document.querySelector({state_selector!r});
                    return el && el.getAttribute({attr_name!r}) === {attr_value!r};
                }}""",
                timeout=timeout_ms,
            )
            result.details.append(
                f"OK: attribute {attr_name!r} = {attr_value!r}"
            )
        except Exception as exc:
            actual = page.evaluate(_JS_ATTRIBUTE, {"sel": state_selector, "attr": attr_name})
            result.details.append(
                f"FAIL: attribute {attr_name!r} did not become {attr_value!r} "
                f"within {timeout_ms}ms — got: {actual!r} ({exc})"
            )

    if expected_class is not None:
        try:
            page.wait_for_function(
                f"""() => {{
                    const el = document.querySelector({state_selector!r});
                    return el && el.className.includes({expected_class!r});
                }}""",
                timeout=timeout_ms,
            )
            result.details.append(
                f"OK: class {expected_class!r} present after click"
            )
        except Exception as exc:
            result.details.append(
                f"FAIL: class {expected_class!r} not present within {timeout_ms}ms "
                f"({exc})"
            )

    return result


# ---------------------------------------------------------------------------
# assert_htmx_swap
# ---------------------------------------------------------------------------


def assert_htmx_swap(
    page: Any,
    trigger_selector: str,
    swap_target_selector: str,
    *,
    timeout_ms: int = 4000,
) -> InteractionResult:
    """Assert that clicking *trigger_selector* causes an HTMX swap on *swap_target_selector*.

    The helper first verifies that the trigger element carries at least one
    ``hx-*`` attribute (``hx-get``, ``hx-post``, ``hx-target``, etc.).  It then
    clicks the trigger and waits for the swap target's content to change.

    Args:
        page:                 Playwright ``Page``.
        trigger_selector:     CSS selector for the HTMX-enabled trigger.
        swap_target_selector: CSS selector for the element that will be replaced.
        timeout_ms:           How long to wait for the swap (milliseconds).

    Returns:
        :class:`InteractionResult` with action ``"htmx_swap"``.
    """
    result = InteractionResult(
        action="htmx_swap",
        data={
            "trigger": trigger_selector,
            "target": swap_target_selector,
        },
    )

    # 1. Verify trigger has hx-* attributes
    hx_attrs = page.evaluate(_JS_HTMX_ATTRS, trigger_selector)
    if hx_attrs is None:
        result.details.append(f"FAIL: trigger not found: {trigger_selector!r}")
        return result

    if not hx_attrs:
        result.details.append(
            f"FAIL: trigger {trigger_selector!r} has no hx-* attributes"
        )
    else:
        attrs_str = ", ".join(f"{k}={v!r}" for k, v in hx_attrs.items())
        result.details.append(f"OK: trigger has HTMX attributes: {attrs_str}")

    result.data["hx_attrs"] = hx_attrs

    # 2. Capture before-state of swap target
    before_text = page.evaluate(_JS_INNER_TEXT, swap_target_selector)
    if before_text is None:
        result.details.append(
            f"FAIL: swap target not found before click: {swap_target_selector!r}"
        )
        return result

    result.data["before_text"] = before_text[:200] if before_text else ""

    # 3. Click trigger
    page.click(trigger_selector)

    # 4. Wait for swap target to change
    try:
        page.wait_for_function(
            f"""() => {{
                const el = document.querySelector({swap_target_selector!r});
                if (!el) return false;
                const before = {result.data['before_text']!r};
                return el.innerText !== before;
            }}""",
            timeout=timeout_ms,
        )
        after_text = page.evaluate(_JS_INNER_TEXT, swap_target_selector)
        result.data["after_text"] = (after_text or "")[:200]
        result.details.append(
            "OK: swap target content changed after trigger click"
        )
    except Exception as exc:
        result.details.append(
            f"FAIL: swap target content did not change within {timeout_ms}ms ({exc})"
        )

    return result


# ---------------------------------------------------------------------------
# assert_form_submit
# ---------------------------------------------------------------------------


def assert_form_submit(
    page: Any,
    form_selector: str,
    field_values: dict[str, str],
    submit_selector: str,
    *,
    expected_success_selector: str | None = None,
    expected_success_text: str | None = None,
    expected_error_selector: str | None = None,
    timeout_ms: int = 5000,
) -> InteractionResult:
    """Fill *field_values* into form inputs and submit, then assert outcome.

    *field_values* maps CSS selectors to the values to enter.  After clicking
    *submit_selector* the helper waits for one of:

    - *expected_success_selector* to appear in the DOM.
    - *expected_success_text* to appear anywhere in the page's ``innerText``.
    - *expected_error_selector* to appear in the DOM (for error path tests).

    Args:
        page:                      Playwright ``Page``.
        form_selector:             CSS selector for the ``<form>`` element.
        field_values:              ``{selector: value}`` mapping of fields to fill.
        submit_selector:           CSS selector for the submit button/input.
        expected_success_selector: CSS selector expected in DOM after success.
        expected_success_text:     Text expected anywhere in page after success.
        expected_error_selector:   CSS selector expected in DOM after error.
        timeout_ms:                How long to wait for outcome (milliseconds).

    Returns:
        :class:`InteractionResult` with action ``"form_submit"``.
    """
    result = InteractionResult(
        action="form_submit",
        data={"form": form_selector, "fields": list(field_values.keys())},
    )

    # 1. Verify form exists
    form_exists = page.evaluate(_JS_ELEMENT_EXISTS, form_selector)
    if not form_exists:
        result.details.append(f"FAIL: form not found: {form_selector!r}")
        return result
    result.details.append(f"OK: form found: {form_selector!r}")

    # 2. Fill fields
    fill_errors: list[str] = []
    for sel, value in field_values.items():
        exists = page.evaluate(_JS_ELEMENT_EXISTS, sel)
        if not exists:
            fill_errors.append(f"field not found: {sel!r}")
            continue
        page.fill(sel, value)
        result.details.append(f"OK: filled {sel!r} with {value!r}")

    if fill_errors:
        for err in fill_errors:
            result.details.append(f"FAIL: {err}")

    # 3. Click submit
    submit_exists = page.evaluate(_JS_ELEMENT_EXISTS, submit_selector)
    if not submit_exists:
        result.details.append(f"FAIL: submit button not found: {submit_selector!r}")
        return result

    page.click(submit_selector)
    result.details.append(f"OK: clicked submit: {submit_selector!r}")

    # 4. Assert outcome
    if expected_success_selector is not None:
        try:
            page.wait_for_selector(expected_success_selector, timeout=timeout_ms)
            result.details.append(
                f"OK: success indicator appeared: {expected_success_selector!r}"
            )
        except Exception as exc:
            result.details.append(
                f"FAIL: success selector {expected_success_selector!r} did not "
                f"appear within {timeout_ms}ms ({exc})"
            )

    if expected_success_text is not None:
        try:
            page.wait_for_function(
                f"() => document.body.innerText.includes({expected_success_text!r})",
                timeout=timeout_ms,
            )
            result.details.append(
                f"OK: success text found: {expected_success_text!r}"
            )
        except Exception as exc:
            result.details.append(
                f"FAIL: success text {expected_success_text!r} did not appear "
                f"within {timeout_ms}ms ({exc})"
            )

    if expected_error_selector is not None:
        try:
            page.wait_for_selector(expected_error_selector, timeout=timeout_ms)
            result.details.append(
                f"OK: error indicator appeared as expected: {expected_error_selector!r}"
            )
        except Exception as exc:
            result.details.append(
                f"FAIL: error selector {expected_error_selector!r} did not "
                f"appear within {timeout_ms}ms ({exc})"
            )

    return result


# ---------------------------------------------------------------------------
# assert_keyboard_navigation
# ---------------------------------------------------------------------------


def assert_keyboard_navigation(
    page: Any,
    container_selector: str,
    *,
    expected_order: list[str] | None = None,
    min_focusable: int = 1,
) -> InteractionResult:
    """Tab through focusable elements in *container_selector* and verify order.

    The helper evaluates all focusable children, optionally compares their
    ``id`` or ``aria-label`` to *expected_order*, and verifies that at least
    *min_focusable* focusable elements are present.

    Args:
        page:               Playwright ``Page``.
        container_selector: CSS selector for the container to evaluate.
        expected_order:     Optional list of ``id`` or ``aria-label`` values in
                            expected Tab order.  Each entry is matched as a
                            substring.
        min_focusable:      Minimum number of focusable elements expected.

    Returns:
        :class:`InteractionResult` with action ``"keyboard_navigation"``.
    """
    result = InteractionResult(
        action="keyboard_navigation",
        data={"container": container_selector},
    )

    container_exists = page.evaluate(_JS_ELEMENT_EXISTS, container_selector)
    if not container_exists:
        result.details.append(
            f"FAIL: container not found: {container_selector!r}"
        )
        return result

    # Scope focusable query to container
    focusable_js = f"""
    () => {{
        const container = document.querySelector({container_selector!r});
        if (!container) return [];
        const focusable = 'a[href], button:not([disabled]), input:not([disabled]), ' +
            'select:not([disabled]), textarea:not([disabled]), ' +
            '[tabindex]:not([tabindex="-1"]), [contenteditable="true"]';
        return Array.from(container.querySelectorAll(focusable)).map(el => ({{
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
            label: el.getAttribute('aria-label') || el.textContent.trim().slice(0, 40),
            tabIndex: el.tabIndex,
        }}));
    }}
    """
    focusable_elements = page.evaluate(focusable_js)
    result.data["focusable"] = focusable_elements

    count = len(focusable_elements)
    if count < min_focusable:
        result.details.append(
            f"FAIL: only {count} focusable element(s) in container "
            f"(expected ≥ {min_focusable})"
        )
    else:
        result.details.append(
            f"OK: {count} focusable element(s) found (≥ {min_focusable})"
        )

    # Validate expected order if provided
    if expected_order is not None:
        labels = [
            (el.get("id") or el.get("label") or "").strip()
            for el in focusable_elements
        ]
        for i, expected_label in enumerate(expected_order):
            if i >= len(labels):
                result.details.append(
                    f"FAIL: expected item {i} ({expected_label!r}) but only "
                    f"{len(labels)} focusable elements found"
                )
                continue
            if expected_label.lower() not in labels[i].lower():
                result.details.append(
                    f"FAIL: Tab order item {i}: expected {expected_label!r}, "
                    f"got {labels[i]!r}"
                )
            else:
                result.details.append(
                    f"OK: Tab order item {i}: {labels[i]!r} ✓"
                )

    return result


# ---------------------------------------------------------------------------
# assert_focus_trap
# ---------------------------------------------------------------------------


def assert_focus_trap(
    page: Any,
    container_selector: str,
    *,
    min_focusable: int = 2,
) -> InteractionResult:
    """Verify that *container_selector* contains focusable elements for a focus trap.

    A proper focus trap (e.g. modal, drawer) must have at least *min_focusable*
    focusable children so that Tab and Shift+Tab can cycle within the container.
    The helper also checks that the container has ``role="dialog"`` or
    ``role="alertdialog"`` (or ``aria-modal="true"``).

    Note:
        This helper does **not** simulate Tab key presses — Playwright focus-trap
        simulation is environment-specific.  For live browser validation, use
        ``page.keyboard.press("Tab")`` in your test after calling this helper.

    Args:
        page:               Playwright ``Page``.
        container_selector: CSS selector for the modal/drawer container.
        min_focusable:      Minimum number of focusable elements required.

    Returns:
        :class:`InteractionResult` with action ``"focus_trap"``.
    """
    result = InteractionResult(
        action="focus_trap",
        data={"container": container_selector},
    )

    container_exists = page.evaluate(_JS_ELEMENT_EXISTS, container_selector)
    if not container_exists:
        result.details.append(
            f"FAIL: container not found: {container_selector!r}"
        )
        return result

    # Check ARIA role / aria-modal
    role_js = f"""
    () => {{
        const el = document.querySelector({container_selector!r});
        return {{
            role: el ? el.getAttribute('role') : null,
            ariaModal: el ? el.getAttribute('aria-modal') : null,
        }};
    }}
    """
    aria_info = page.evaluate(role_js)
    role = (aria_info or {}).get("role") or ""
    aria_modal = (aria_info or {}).get("ariaModal") or ""

    if role in ("dialog", "alertdialog") or aria_modal == "true":
        result.details.append(
            f"OK: container has role={role!r} / aria-modal={aria_modal!r}"
        )
    else:
        result.details.append(
            f"FAIL: container missing role='dialog' or aria-modal='true' "
            f"(got role={role!r}, aria-modal={aria_modal!r})"
        )

    # Count focusable elements inside container
    focusable_js = f"""
    () => {{
        const container = document.querySelector({container_selector!r});
        if (!container) return [];
        const focusable = 'a[href], button:not([disabled]), input:not([disabled]), ' +
            'select:not([disabled]), textarea:not([disabled]), ' +
            '[tabindex]:not([tabindex="-1"])';
        return Array.from(container.querySelectorAll(focusable)).map(el => ({{
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
        }}));
    }}
    """
    focusable = page.evaluate(focusable_js)
    count = len(focusable)
    result.data["focusable"] = focusable

    if count < min_focusable:
        result.details.append(
            f"FAIL: only {count} focusable element(s) in focus trap "
            f"(need ≥ {min_focusable} for Tab cycling)"
        )
    else:
        result.details.append(
            f"OK: {count} focusable element(s) in trap (≥ {min_focusable})"
        )

    return result


# ---------------------------------------------------------------------------
# assert_dropdown_toggle
# ---------------------------------------------------------------------------


def assert_dropdown_toggle(
    page: Any,
    trigger_selector: str,
    menu_selector: str,
    *,
    timeout_ms: int = 2000,
) -> InteractionResult:
    """Click *trigger_selector* and verify that *menu_selector* toggles open/closed.

    Checks:

    1. Trigger has ``aria-expanded`` attribute.
    2. Menu is initially hidden (``aria-expanded="false"`` or element hidden).
    3. After click, menu becomes visible (``aria-expanded="true"`` or display ≠ none).
    4. After second click, menu is hidden again.

    Args:
        page:             Playwright ``Page``.
        trigger_selector: CSS selector for the dropdown button/toggle.
        menu_selector:    CSS selector for the dropdown menu panel.
        timeout_ms:       How long to wait for each state change.

    Returns:
        :class:`InteractionResult` with action ``"dropdown_toggle"``.
    """
    result = InteractionResult(
        action="dropdown_toggle",
        data={"trigger": trigger_selector, "menu": menu_selector},
    )

    # 1. Trigger exists and has aria-expanded
    trigger_exists = page.evaluate(_JS_ELEMENT_EXISTS, trigger_selector)
    if not trigger_exists:
        result.details.append(f"FAIL: trigger not found: {trigger_selector!r}")
        return result

    aria_expanded_before = page.evaluate(_JS_ARIA_EXPANDED, trigger_selector)
    result.data["aria_expanded_before"] = aria_expanded_before

    if aria_expanded_before is None:
        result.details.append(
            f"FAIL: trigger {trigger_selector!r} has no aria-expanded attribute"
        )
    else:
        result.details.append(
            f"OK: trigger has aria-expanded={aria_expanded_before!r} initially"
        )

    # 2. Click to open
    page.click(trigger_selector)

    try:
        page.wait_for_function(
            f"""() => {{
                const el = document.querySelector({trigger_selector!r});
                if (!el) return false;
                const expanded = el.getAttribute('aria-expanded');
                if (expanded === 'true') return true;
                // Fallback: check menu visibility
                const menu = document.querySelector({menu_selector!r});
                if (!menu) return false;
                const style = window.getComputedStyle(menu);
                return style.display !== 'none' && style.visibility !== 'hidden';
            }}""",
            timeout=timeout_ms,
        )
        aria_expanded_open = page.evaluate(_JS_ARIA_EXPANDED, trigger_selector)
        result.data["aria_expanded_open"] = aria_expanded_open
        result.details.append(
            f"OK: dropdown opened (aria-expanded={aria_expanded_open!r})"
        )
    except Exception as exc:
        result.details.append(
            f"FAIL: dropdown did not open within {timeout_ms}ms ({exc})"
        )
        return result

    # 3. Click to close
    page.click(trigger_selector)

    try:
        page.wait_for_function(
            f"""() => {{
                const el = document.querySelector({trigger_selector!r});
                if (!el) return false;
                const expanded = el.getAttribute('aria-expanded');
                if (expanded === 'false') return true;
                // Fallback: check menu hidden
                const menu = document.querySelector({menu_selector!r});
                if (!menu) return true;  // removed from DOM = closed
                const style = window.getComputedStyle(menu);
                return style.display === 'none' || style.visibility === 'hidden';
            }}""",
            timeout=timeout_ms,
        )
        aria_expanded_closed = page.evaluate(_JS_ARIA_EXPANDED, trigger_selector)
        result.data["aria_expanded_closed"] = aria_expanded_closed
        result.details.append(
            f"OK: dropdown closed (aria-expanded={aria_expanded_closed!r})"
        )
    except Exception as exc:
        result.details.append(
            f"FAIL: dropdown did not close within {timeout_ms}ms ({exc})"
        )

    return result


# ---------------------------------------------------------------------------
# assert_copy_button
# ---------------------------------------------------------------------------


def assert_copy_button(
    page: Any,
    button_selector: str,
    *,
    feedback_selector: str | None = None,
    feedback_text: str | None = None,
    timeout_ms: int = 2000,
) -> InteractionResult:
    """Assert that *button_selector* is a functional copy-to-clipboard button.

    The helper checks that the button exists and is clickable, then optionally
    verifies that clicking it shows UI feedback (e.g. "Copied!" text or a
    checkmark icon) via *feedback_selector* or *feedback_text*.

    Note:
        Clipboard write access is blocked in headless Playwright unless
        ``browser_context.grant_permissions(["clipboard-write"])`` is called.
        This helper focuses on the **UI feedback** side of copy buttons.

    Args:
        page:              Playwright ``Page``.
        button_selector:   CSS selector for the copy button.
        feedback_selector: CSS selector for the element that shows copy feedback.
        feedback_text:     Text expected in the page after clicking copy.
        timeout_ms:        How long to wait for feedback (milliseconds).

    Returns:
        :class:`InteractionResult` with action ``"copy_button"``.
    """
    result = InteractionResult(
        action="copy_button",
        data={"button": button_selector},
    )

    # 1. Check button exists and is clickable
    clickable_result = assert_button_clickable(page, button_selector)
    result.data["clickable"] = clickable_result.passed
    if not clickable_result.passed:
        for detail in clickable_result.details:
            if detail.startswith("FAIL:"):
                result.details.append(detail)
        return result
    result.details.append("OK: copy button is visible and enabled")

    # 2. Click button
    page.click(button_selector)

    # 3. Check for UI feedback
    if feedback_selector is not None:
        try:
            page.wait_for_selector(feedback_selector, timeout=timeout_ms)
            result.details.append(
                f"OK: feedback element appeared: {feedback_selector!r}"
            )
        except Exception as exc:
            result.details.append(
                f"FAIL: feedback element {feedback_selector!r} did not appear "
                f"within {timeout_ms}ms ({exc})"
            )

    if feedback_text is not None:
        try:
            page.wait_for_function(
                f"() => document.body.innerText.includes({feedback_text!r})",
                timeout=timeout_ms,
            )
            result.details.append(
                f"OK: feedback text found: {feedback_text!r}"
            )
        except Exception as exc:
            result.details.append(
                f"FAIL: feedback text {feedback_text!r} did not appear "
                f"within {timeout_ms}ms ({exc})"
            )

    if feedback_selector is None and feedback_text is None:
        result.details.append(
            "OK: copy button clicked (no UI feedback assertion configured)"
        )

    return result


# ---------------------------------------------------------------------------
# assert_link_navigation
# ---------------------------------------------------------------------------


def assert_link_navigation(
    page: Any,
    link_selector: str,
    *,
    expected_href: str | None = None,
    expect_new_tab: bool = False,
) -> InteractionResult:
    """Assert properties of an anchor link without navigating away.

    Checks:

    1. Link element exists and is a native ``<a>`` tag.
    2. ``href`` attribute is non-empty.
    3. If *expected_href* is provided, ``href`` contains that string.
    4. If *expect_new_tab* is True, ``target="_blank"`` and
       ``rel`` contains ``"noopener"`` (security best practice).

    Args:
        page:            Playwright ``Page``.
        link_selector:   CSS selector for the link element.
        expected_href:   Substring expected within the ``href`` attribute.
        expect_new_tab:  Whether the link should open in a new tab.

    Returns:
        :class:`InteractionResult` with action ``"link_navigation"``.
    """
    result = InteractionResult(
        action="link_navigation",
        data={"selector": link_selector},
    )

    link_info_js = f"""
    () => {{
        const el = document.querySelector({link_selector!r});
        if (!el) return null;
        return {{
            tagName: el.tagName.toLowerCase(),
            href: el.getAttribute('href') || '',
            target: el.getAttribute('target') || '',
            rel: el.getAttribute('rel') || '',
            text: el.textContent.trim().slice(0, 80),
        }};
    }}
    """
    info = page.evaluate(link_info_js)

    if info is None:
        result.details.append(f"FAIL: link not found: {link_selector!r}")
        return result

    result.data["link"] = info

    # 1. Is an anchor
    if info["tagName"] != "a":
        result.details.append(
            f"FAIL: element is <{info['tagName']}>, expected <a>"
        )
    else:
        result.details.append("OK: element is <a>")

    # 2. Non-empty href
    href = info["href"]
    if not href:
        result.details.append("FAIL: href is empty")
    else:
        result.details.append(f"OK: href={href!r}")

    # 3. Expected href substring
    if expected_href is not None:
        if expected_href in href:
            result.details.append(f"OK: href contains {expected_href!r}")
        else:
            result.details.append(
                f"FAIL: href {href!r} does not contain {expected_href!r}"
            )

    # 4. New tab behaviour
    if expect_new_tab:
        if info["target"] == "_blank":
            result.details.append("OK: target='_blank'")
        else:
            result.details.append(
                f"FAIL: expected target='_blank', got {info['target']!r}"
            )
        if "noopener" in info["rel"]:
            result.details.append("OK: rel contains 'noopener'")
        else:
            result.details.append(
                f"FAIL: rel {info['rel']!r} should contain 'noopener' for "
                f"target='_blank' links (security)"
            )

    return result
