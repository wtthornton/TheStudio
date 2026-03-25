"""Shared Playwright test infrastructure for TheStudio (Epic 58).

All helpers are importable from this package:

    from tests.playwright.lib import (
        style_assertions,
        typography_assertions,
        component_validators,
        api_helpers,
        interaction_helpers,
    )

Or import helpers directly:

    from tests.playwright.lib.style_assertions import assert_status_colors
    from tests.playwright.lib.typography_assertions import assert_typography
    from tests.playwright.lib.component_validators import validate_card, validate_button
    from tests.playwright.lib.api_helpers import assert_api_endpoint, assert_api_no_error
    from tests.playwright.lib.interaction_helpers import (
        assert_button_clickable,
        click_and_assert_state_change,
        assert_htmx_swap,
        assert_form_submit,
        assert_keyboard_navigation,
        assert_focus_trap,
        assert_dropdown_toggle,
        assert_copy_button,
        assert_link_navigation,
    )
"""

from tests.playwright.lib import api_helpers
from tests.playwright.lib import component_validators
from tests.playwright.lib import interaction_helpers
from tests.playwright.lib import style_assertions
from tests.playwright.lib import typography_assertions

__all__ = [
    "api_helpers",
    "component_validators",
    "interaction_helpers",
    "style_assertions",
    "typography_assertions",
]
