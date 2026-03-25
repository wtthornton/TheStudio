"""Shared Playwright test infrastructure for TheStudio (Epic 58).

All helpers are importable from this package:

    from tests.playwright.lib import (
        style_assertions,
        typography_assertions,
        component_validators,
    )

Or import helpers directly:

    from tests.playwright.lib.style_assertions import assert_status_colors
    from tests.playwright.lib.typography_assertions import assert_typography
    from tests.playwright.lib.component_validators import validate_card, validate_button
"""

from tests.playwright.lib import component_validators
from tests.playwright.lib import style_assertions
from tests.playwright.lib import typography_assertions

__all__ = ["component_validators", "style_assertions", "typography_assertions"]
