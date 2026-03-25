"""Shared Playwright test infrastructure for TheStudio (Epic 58).

All helpers are importable from this package:

    from tests.playwright.lib import (
        style_assertions,
    )

Or import helpers directly:

    from tests.playwright.lib.style_assertions import assert_status_colors
"""

from tests.playwright.lib import style_assertions

__all__ = ["style_assertions"]
