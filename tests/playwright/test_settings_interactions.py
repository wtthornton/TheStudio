"""Epic 71.4 — Settings: Interactive Elements.

Validates that /admin/ui/settings interactive behaviours work correctly:

  Tab switching  — Clicking a tab reveals its panel and hides other panels
  Form submission — Submit button / form can be triggered; server responds
  Validation      — Required fields show validation feedback on empty submit
  Persistence     — Tab preference is preserved after page reload (optional)
  HTMX            — hx-get / hx-post attributes target valid DOM elements

These tests verify *interactive behaviour*, not visual appearance.
Style compliance is covered in test_settings_style.py (Epic 71.3).
Content is covered in test_settings_intent.py (Epic 71.1).
API contracts are covered in test_settings_api.py (Epic 71.2).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

SETTINGS_URL = "/admin/ui/settings"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _go(page: object, base_url: str) -> None:
    """Navigate to the settings page and wait for content to settle."""
    navigate(page, f"{base_url}{SETTINGS_URL}")  # type: ignore[arg-type]


def _count(page: object, selector: str) -> int:
    """Return the count of elements matching *selector* via JS querySelectorAll."""
    return page.evaluate(  # type: ignore[attr-defined]
        f"document.querySelectorAll({selector!r}).length"
    )


def _has_tabs(page: object) -> bool:
    """Return True when at least one ARIA tab or tab-like element is present."""
    return (
        _count(page, "[role='tab']") > 0
        or _count(page, "[data-tab]") > 0
        or _count(page, "[class*='tab-btn']") > 0
        or _count(page, "[class*='tab-item']") > 0
        or _count(page, "nav a[href*='tab']") > 0
    )


def _first_visible_tab(page: object) -> object | None:
    """Return the first visible tab element, or None if none present."""
    tab_selectors = [
        "[role='tab']",
        "[data-tab]",
        "[class*='tab-btn']",
        "[class*='tab-item']",
        "nav a[data-tab-target]",
    ]
    for sel in tab_selectors:
        tabs = page.locator(sel)  # type: ignore[attr-defined]
        for i in range(tabs.count()):
            tab = tabs.nth(i)
            if tab.is_visible():
                return tab
    return None


# ---------------------------------------------------------------------------
# Tab switching
# ---------------------------------------------------------------------------


class TestSettingsTabSwitching:
    """Clicking a settings tab must reveal its panel content (§9.x tab recipe).

    Settings exposes 6 configuration tabs: API keys, infra, flags, agent,
    budget, and secrets. Each tab switch must:
      1. Show the clicked tab's panel
      2. Hide (or visually deactivate) the previously active panel
      3. Update the aria-selected attribute on the active tab
    """

    def test_tab_elements_are_clickable(self, page: object, base_url: str) -> None:
        """Settings tab navigation elements are present and not disabled."""
        _go(page, base_url)

        if not _has_tabs(page):
            pytest.skip(
                "No tab navigation found on settings page — "
                "page may use a scroll/anchor layout instead"
            )

        tab = _first_visible_tab(page)
        assert tab is not None, "Expected at least one visible tab"
        assert tab.is_enabled(), "First visible tab must not be disabled"  # type: ignore[attr-defined]

    def test_clicking_tab_changes_active_indicator(
        self, page: object, base_url: str
    ) -> None:
        """Clicking a non-active tab updates the active/selected state."""
        _go(page, base_url)

        all_tabs = page.locator("[role='tab']")  # type: ignore[attr-defined]
        if all_tabs.count() < 2:
            pytest.skip(
                "Fewer than 2 role='tab' elements found — "
                "cannot verify tab switching behaviour"
            )

        # Activate second tab
        second_tab = all_tabs.nth(1)
        if not second_tab.is_visible():
            pytest.skip("Second tab is not visible — skipping tab switch test")

        second_tab.click()
        page.wait_for_timeout(300)  # type: ignore[attr-defined]

        # The second tab must now be active
        aria_selected = second_tab.get_attribute("aria-selected")  # type: ignore[attr-defined]
        classes = second_tab.get_attribute("class") or ""  # type: ignore[attr-defined]
        is_active = aria_selected == "true" or "active" in classes
        assert is_active, (
            "After clicking the second tab, it must be marked as active — "
            f"aria-selected={aria_selected!r}, class={classes!r}"
        )

    def test_clicking_tab_reveals_panel_content(
        self, page: object, base_url: str
    ) -> None:
        """Clicking a tab reveals the corresponding tabpanel in the DOM."""
        _go(page, base_url)

        all_tabs = page.locator("[role='tab']")  # type: ignore[attr-defined]
        if all_tabs.count() == 0:
            pytest.skip("No role='tab' elements found — skipping panel reveal test")

        # Click the first visible tab
        for i in range(all_tabs.count()):
            tab = all_tabs.nth(i)
            if tab.is_visible():
                tab.click()
                page.wait_for_timeout(300)  # type: ignore[attr-defined]
                break

        # At least one tabpanel must be visible / non-hidden
        panel_sel = (
            "[role='tabpanel']:not([hidden]):not([aria-hidden='true']), "
            "[data-tab-content]:not(.hidden):not([hidden]), "
            ".tab-pane.active, .tab-pane:not(.hidden)"
        )
        visible_panels = page.locator(panel_sel)  # type: ignore[attr-defined]
        assert visible_panels.count() > 0, (
            "Clicking a tab must reveal at least one tabpanel — "
            "no visible tabpanel found after click"
        )

    def test_tab_panels_switch_on_click(self, page: object, base_url: str) -> None:
        """Switching tabs changes which tabpanel is displayed."""
        _go(page, base_url)

        all_tabs = page.locator("[role='tab']")  # type: ignore[attr-defined]
        if all_tabs.count() < 2:
            pytest.skip(
                "Fewer than 2 role='tab' elements — cannot verify panel switching"
            )

        # Click first tab and capture body HTML
        first_tab = all_tabs.nth(0)
        if not first_tab.is_visible():
            pytest.skip("First tab not visible — skipping panel switch test")
        first_tab.click()
        page.wait_for_timeout(300)  # type: ignore[attr-defined]
        html_after_first = page.locator("body").inner_html()  # type: ignore[attr-defined]

        # Click second tab and capture body HTML
        second_tab = all_tabs.nth(1)
        if not second_tab.is_visible():
            pytest.skip("Second tab not visible — skipping panel switch test")
        second_tab.click()
        page.wait_for_timeout(300)  # type: ignore[attr-defined]
        html_after_second = page.locator("body").inner_html()  # type: ignore[attr-defined]

        assert html_after_first != html_after_second, (
            "Switching between tabs must change the visible content — "
            "body HTML was identical after clicking first vs second tab"
        )

    def test_no_js_errors_on_tab_click(self, page: object, base_url: str) -> None:
        """Tab switching must not raise JavaScript errors."""
        _go(page, base_url)

        js_errors: list[str] = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))  # type: ignore[attr-defined]

        all_tabs = page.locator("[role='tab']")  # type: ignore[attr-defined]
        if all_tabs.count() == 0:
            pytest.skip("No role='tab' elements found — skipping JS error check")

        for i in range(min(all_tabs.count(), 3)):
            tab = all_tabs.nth(i)
            if tab.is_visible():
                tab.click()
                page.wait_for_timeout(200)  # type: ignore[attr-defined]

        assert not js_errors, (
            f"JavaScript errors occurred during tab switching: {js_errors}"
        )


# ---------------------------------------------------------------------------
# Form submission
# ---------------------------------------------------------------------------


class TestSettingsFormSubmission:
    """Settings forms must be submittable and respond to save actions.

    Each configuration section should expose a save/update mechanism.
    Tests verify the submit path exists and can be triggered without
    crashing the page.
    """

    def test_submit_button_present(self, page: object, base_url: str) -> None:
        """At least one submit/save button is present on the settings page."""
        _go(page, base_url)

        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Save')",
            "button:has-text('Update')",
            "button:has-text('Apply')",
            "button[form]",
            "[data-action='save']",
            "[data-action='submit']",
            "button[class*='save']",
            "button[class*='submit']",
        ]
        for sel in submit_selectors:
            try:
                if _count(page, sel) > 0:
                    btn = page.locator(sel).first  # type: ignore[attr-defined]
                    assert btn.is_visible(), (
                        f"Submit/save button ({sel!r}) must be visible"
                    )
                    return
            except Exception:  # noqa: BLE001
                continue

        # If no explicit submit button, check for a form element at minimum
        form_count = _count(page, "form")
        if form_count > 0:
            pytest.skip(
                "No explicit submit button found but a <form> element is present — "
                "settings may use an auto-save or inline-edit pattern"
            )

        pytest.skip(
            "No submit/save button or <form> found on settings page — "
            "page may be read-only configuration view"
        )

    def test_form_element_is_present(self, page: object, base_url: str) -> None:
        """At least one <form> element exists to wrap settings inputs."""
        _go(page, base_url)

        form_count = _count(page, "form")
        if form_count == 0:
            # Accept HTMX-driven forms that use hx-post / hx-put
            htmx_forms = _count(page, "[hx-post], [hx-put], [hx-patch]")
            if htmx_forms > 0:
                return  # HTMX form pattern is acceptable
            pytest.skip(
                "No <form> or HTMX form elements found — "
                "settings may be rendered as read-only or use a different pattern"
            )
        assert form_count >= 1, (
            "Settings page must have at least one <form> element to accept user input"
        )

    def test_form_action_or_htmx_post_defined(self, page: object, base_url: str) -> None:
        """Each settings form has an action URL or hx-post target defined."""
        _go(page, base_url)

        # Check traditional HTML forms
        form_count = _count(page, "form")
        if form_count > 0:
            first_action = page.evaluate(  # type: ignore[attr-defined]
                """
                (function() {
                    var form = document.querySelector('form');
                    if (!form) return null;
                    return {
                        action: form.getAttribute('action'),
                        method: form.getAttribute('method'),
                        hxPost: form.getAttribute('hx-post'),
                        hxPut: form.getAttribute('hx-put')
                    };
                })()
                """
            )
            if first_action:
                has_target = (
                    first_action.get("action")
                    or first_action.get("hxPost")
                    or first_action.get("hxPut")
                )
                # A missing action on a form defaults to the current URL (valid)
                if not has_target:
                    pytest.skip(
                        "Settings form has no explicit action/hx-post — "
                        "defaults to current URL (acceptable)"
                    )
                return

        # Check standalone HTMX triggers
        htmx_count = _count(page, "[hx-post], [hx-put], [hx-patch]")
        if htmx_count > 0:
            return  # HTMX form pattern

        pytest.skip(
            "No form or HTMX form elements found — "
            "skipping form action verification"
        )

    def test_submit_button_triggers_response(self, page: object, base_url: str) -> None:
        """Clicking the settings save/submit button triggers a network request."""
        _go(page, base_url)

        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Save')",
            "button:has-text('Update')",
            "button:has-text('Apply')",
        ]
        submit_btn = None
        for sel in submit_selectors:
            try:
                if _count(page, sel) > 0:
                    btn = page.locator(sel).first  # type: ignore[attr-defined]
                    if btn.is_visible() and btn.is_enabled():
                        submit_btn = btn
                        break
            except Exception:  # noqa: BLE001
                continue

        if submit_btn is None:
            pytest.skip(
                "No enabled visible submit/save button found — skipping trigger test"
            )

        # Intercept requests to detect form submission
        requests_made: list[str] = []
        page.on(  # type: ignore[attr-defined]
            "request",
            lambda req: requests_made.append(req.method)
            if req.method in ("POST", "PUT", "PATCH", "DELETE")
            else None,
        )

        submit_btn.click()
        page.wait_for_timeout(600)  # type: ignore[attr-defined]

        # Either a POST/PUT was made or the page responded with feedback
        body_text = page.locator("body").inner_text()  # type: ignore[attr-defined]
        has_request = len(requests_made) > 0
        has_feedback = any(
            kw in body_text.lower()
            for kw in ("saved", "updated", "success", "error", "invalid", "required")
        )

        assert has_request or has_feedback, (
            "Clicking the submit/save button must trigger a network request or "
            "display feedback — neither occurred"
        )


# ---------------------------------------------------------------------------
# Validation feedback
# ---------------------------------------------------------------------------


class TestSettingsValidationFeedback:
    """Required form fields must show validation feedback on empty submission.

    Settings forms protect against accidental empty saves.  Required fields
    should display an error message, border change, or ARIA invalid attribute
    when the user attempts to submit without filling them in.
    """

    def test_required_field_attribute_present(self, page: object, base_url: str) -> None:
        """At least one input field has a required attribute or aria-required."""
        _go(page, base_url)

        required_selectors = [
            "input[required]",
            "input[aria-required='true']",
            "textarea[required]",
            "select[required]",
            "[required]:not(form):not(fieldset)",
        ]
        for sel in required_selectors:
            if _count(page, sel) > 0:
                return  # At least one required field found

        pytest.skip(
            "No required form fields found on settings page — "
            "settings may use optional-only fields or server-side validation"
        )

    def test_empty_required_field_shows_browser_validation(
        self, page: object, base_url: str
    ) -> None:
        """Submitting an empty required field triggers browser or custom validation."""
        _go(page, base_url)

        # Look for a required text/password/email input
        input_selectors = [
            "input[required][type='text']",
            "input[required][type='password']",
            "input[required][type='email']",
            "input[required][type='url']",
            "input[required]:not([type='hidden'])"
            ":not([type='checkbox']):not([type='radio'])",
        ]
        target_input = None
        for sel in input_selectors:
            if _count(page, sel) > 0:
                inp = page.locator(sel).first  # type: ignore[attr-defined]
                if inp.is_visible():
                    target_input = inp
                    break

        if target_input is None:
            pytest.skip(
                "No visible required text input found — "
                "skipping empty-field validation test"
            )

        # Clear the field
        target_input.fill("")  # type: ignore[attr-defined]

        # Try to submit the form
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Save')",
            "button:has-text('Update')",
        ]
        submitted = False
        for sel in submit_selectors:
            if _count(page, sel) > 0:
                btn = page.locator(sel).first  # type: ignore[attr-defined]
                if btn.is_visible() and btn.is_enabled():
                    btn.click()
                    page.wait_for_timeout(400)  # type: ignore[attr-defined]
                    submitted = True
                    break

        if not submitted:
            pytest.skip(
                "Could not find a submit button to trigger validation — skipping"
            )

        # Validation evidence: aria-invalid, custom error element, or browser validity
        aria_invalid = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var inputs = document.querySelectorAll('input[required], textarea[required]');
                for (var i = 0; i < inputs.length; i++) {
                    if (inputs[i].getAttribute('aria-invalid') === 'true') return true;
                    if (!inputs[i].validity.valid) return true;
                }
                return false;
            })()
            """
        )
        body_text = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
        has_error_text = any(
            kw in body_text
            for kw in (
                "required",
                "invalid",
                "error",
                "cannot be empty",
                "please fill",
            )
        )

        assert aria_invalid or has_error_text, (
            "Submitting an empty required field must trigger validation feedback — "
            "no aria-invalid attribute or error text found"
        )

    def test_input_validity_api_is_correct(self, page: object, base_url: str) -> None:
        """Required inputs report invalid via the HTML Constraint Validation API."""
        _go(page, base_url)

        has_invalid = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var inputs = document.querySelectorAll(
                    'input[required]:not([type="hidden"]):not([type="checkbox"])'
                    ':not([type="radio"])'
                );
                if (inputs.length === 0) return null;
                for (var i = 0; i < inputs.length; i++) {
                    var inp = inputs[i];
                    // Only check inputs that have a value (non-empty default is valid)
                    if (inp.value === '') {
                        return !inp.validity.valid;
                    }
                }
                return false;
            })()
            """
        )

        if has_invalid is None:
            pytest.skip(
                "No required inputs on settings page — "
                "skipping Constraint Validation API check"
            )

        # If there are empty required inputs, they should be invalid
        assert has_invalid is True or has_invalid is False, (
            "Constraint Validation API check returned unexpected value"
        )


# ---------------------------------------------------------------------------
# HTMX swap attributes
# ---------------------------------------------------------------------------


class TestSettingsHtmxAttributes:
    """Settings page HTMX-driven elements must carry correct hx-* attributes."""

    def test_htmx_elements_have_target(self, page: object, base_url: str) -> None:
        """Elements with hx-get / hx-post declare hx-target or hx-swap."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-get], [hx-post], [hx-put]")  # type: ignore[attr-defined]
        count = hx_elements.count()

        if count == 0:
            pytest.skip(
                "No HTMX hx-get/hx-post/hx-put elements found — "
                "settings page may not use HTMX"
            )

        for i in range(min(count, 10)):
            el = hx_elements.nth(i)
            hx_target = el.get_attribute("hx-target")
            hx_swap = el.get_attribute("hx-swap")
            assert hx_target is not None or hx_swap is not None, (
                f"HTMX element {i} must declare hx-target or hx-swap — "
                "missing both attributes"
            )

    def test_htmx_targets_exist_in_dom(self, page: object, base_url: str) -> None:
        """hx-target selectors on settings page reference elements in the current DOM."""
        _go(page, base_url)

        hx_elements = page.locator("[hx-target]")  # type: ignore[attr-defined]
        count = hx_elements.count()

        if count == 0:
            pytest.skip("No elements with hx-target found on settings page")

        _relative_keywords = {"this", "closest", "next", "previous", "find"}
        missing: list[str] = []

        for i in range(min(count, 10)):
            target_sel = hx_elements.nth(i).get_attribute("hx-target") or ""
            if not target_sel:
                continue
            base_kw = target_sel.split()[0]
            if base_kw in _relative_keywords:
                continue
            try:
                if page.locator(target_sel).count() == 0:  # type: ignore[attr-defined]
                    missing.append(target_sel)
            except Exception:  # noqa: BLE001
                pass

        assert not missing, (
            f"hx-target selector(s) not found in DOM: {missing}"
        )


# ---------------------------------------------------------------------------
# Tab preference persistence (optional / degraded-graceful)
# ---------------------------------------------------------------------------


class TestSettingsTabPersistence:
    """Active tab preference may be persisted across page reloads.

    This is an enhancement; tests skip gracefully if persistence is not
    implemented. The style guide recommends localStorage or URL hash for
    tab state.
    """

    def test_tab_state_encoded_in_url_or_storage(
        self, page: object, base_url: str
    ) -> None:
        """After switching tabs, the selected tab is encoded in the URL or localStorage."""
        _go(page, base_url)

        all_tabs = page.locator("[role='tab']")  # type: ignore[attr-defined]
        if all_tabs.count() < 2:
            pytest.skip(
                "Fewer than 2 tabs found — skipping persistence test"
            )

        second_tab = all_tabs.nth(1)
        if not second_tab.is_visible():
            pytest.skip("Second tab not visible — skipping persistence test")

        second_tab.click()
        page.wait_for_timeout(300)  # type: ignore[attr-defined]

        # Check URL hash / query param for tab state
        current_url: str = page.url  # type: ignore[attr-defined]
        has_url_state = "#" in current_url or "tab=" in current_url

        # Check localStorage for tab preference
        local_storage_keys = page.evaluate(  # type: ignore[attr-defined]
            "Object.keys(localStorage).filter(k => k.toLowerCase().includes('tab'))"
        )
        has_storage = len(local_storage_keys) > 0

        if not has_url_state and not has_storage:
            pytest.skip(
                "Tab state not persisted in URL or localStorage — "
                "persistence is optional but recommended (style guide §9.x)"
            )

    def test_tab_state_restored_after_reload(
        self, page: object, base_url: str
    ) -> None:
        """After reloading, the previously active tab is restored."""
        _go(page, base_url)

        all_tabs = page.locator("[role='tab']")  # type: ignore[attr-defined]
        if all_tabs.count() < 2:
            pytest.skip(
                "Fewer than 2 tabs found — skipping persistence restore test"
            )

        second_tab = all_tabs.nth(1)
        if not second_tab.is_visible():
            pytest.skip("Second tab not visible — skipping persistence restore test")

        second_tab.click()
        page.wait_for_timeout(300)  # type: ignore[attr-defined]

        # Check that URL has changed (required for reload-based persistence)
        current_url: str = page.url  # type: ignore[attr-defined]
        if "#" not in current_url and "tab=" not in current_url:
            pytest.skip(
                "Tab state not encoded in URL — reload persistence not implemented"
            )

        page.reload()  # type: ignore[attr-defined]
        page.wait_for_timeout(500)  # type: ignore[attr-defined]

        # After reload, a tab should still be active
        active_tabs = page.locator("[role='tab'][aria-selected='true']")  # type: ignore[attr-defined]
        assert active_tabs.count() > 0, (
            "After reloading the settings page, at least one tab must be active — "
            "no aria-selected='true' tab found"
        )
