"""Story 76.5 — Routing Review Tab: Page Intent & Semantic Content.

Validates that /dashboard/?tab=routing delivers its core purpose:
  - When NO task is selected: shows an empty state with heading "No Task Selected",
    a description about expert routing, and two action buttons ("Go to Pipeline",
    "Open Backlog"), all addressable via data-testid="routing-no-task-state".
  - When a task IS selected: shows RoutingPreview with expert selection details
    (covered separately in integration tests that inject a task ID).

These tests check *what* the page communicates, not *how* it looks.
Style compliance is in test_pd_routing_style.py (Story 76.5).
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


def _go(page: object, base_url: str) -> None:
    """Navigate to the routing tab and wait for React to hydrate."""
    dashboard_navigate(page, base_url, "routing")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Empty state — no task selected (default state)
# ---------------------------------------------------------------------------


class TestRoutingNoTaskEmptyState:
    """When no task is selected the routing tab must show the 'No Task Selected' state.

    Operators land on the routing tab without a task pre-selected in the majority
    of sessions.  The empty state must communicate what the tab is for and give
    clear CTAs to reach tasks.
    """

    def test_routing_no_task_testid_present(self, page, base_url: str) -> None:
        """Empty routing state is addressable via data-testid='routing-no-task-state'."""
        _go(page, base_url)

        assert page.locator("[data-testid='routing-no-task-state']").count() > 0, (  # type: ignore[attr-defined]
            "Routing tab empty state must carry data-testid='routing-no-task-state' "
            "for targeted testing and analytics"
        )

    def test_no_task_selected_heading_present(self, page, base_url: str) -> None:
        """Empty routing state has a 'No Task Selected' heading."""
        _go(page, base_url)

        if page.locator("[data-testid='routing-no-task-state']").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("routing-no-task-state not found — task may be pre-selected")

        body = page.locator("body").inner_text()  # type: ignore[attr-defined]
        assert "No Task Selected" in body, (
            "Routing tab empty state must display 'No Task Selected' heading "
            "so operators understand why no routing details appear"
        )

    def test_routing_description_mentions_expert_routing(self, page, base_url: str) -> None:
        """Empty routing state description references expert routing."""
        _go(page, base_url)

        if page.locator("[data-testid='routing-no-task-state']").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("routing-no-task-state not found — task may be pre-selected")

        body = page.locator("body").inner_text().lower()  # type: ignore[attr-defined]
        has_routing_mention = (
            "routing" in body
            or "expert" in body
            or "specialist" in body
        )
        assert has_routing_mention, (
            "Routing tab empty state description must explain what expert routing is "
            "so operators understand the purpose of the Routing Review tab"
        )

    def test_go_to_pipeline_button_present(self, page, base_url: str) -> None:
        """Empty routing state shows a 'Go to Pipeline' primary action button."""
        _go(page, base_url)

        if page.locator("[data-testid='routing-no-task-state']").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("routing-no-task-state not found — task may be pre-selected")

        body = page.locator("body").inner_text()  # type: ignore[attr-defined]
        assert "Go to Pipeline" in body, (
            "Routing tab empty state must display 'Go to Pipeline' CTA button "
            "to guide operators toward selecting a task"
        )

    def test_open_backlog_button_present(self, page, base_url: str) -> None:
        """Empty routing state shows an 'Open Backlog' secondary action button."""
        _go(page, base_url)

        if page.locator("[data-testid='routing-no-task-state']").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("routing-no-task-state not found — task may be pre-selected")

        body = page.locator("body").inner_text()  # type: ignore[attr-defined]
        assert "Open Backlog" in body, (
            "Routing tab empty state must display 'Open Backlog' secondary action "
            "to guide operators to the task backlog"
        )

    def test_routing_tab_renders_without_error(self, page, base_url: str) -> None:
        """Routing tab renders a recognisable UI element without a JS crash."""
        _go(page, base_url)

        # Either the empty state or a RoutingPreview is acceptable.
        has_empty = page.locator("[data-testid='routing-no-task-state']").count() > 0  # type: ignore[attr-defined]
        has_preview = page.locator("[data-tour='routing-preview']").count() > 0  # type: ignore[attr-defined]
        has_any_heading = page.locator("h1, h2, h3").count() > 0  # type: ignore[attr-defined]

        assert has_empty or has_preview or has_any_heading, (
            "Routing tab must render at least one recognisable element — "
            "empty state, routing preview, or a heading"
        )
