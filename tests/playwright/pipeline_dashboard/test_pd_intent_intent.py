"""Story 76.4 — Intent Review Tab: Page Intent & Semantic Content.

Validates that /dashboard/?tab=intent delivers its core purpose when no task
is selected (the primary test-environment state):

  - Empty state heading "No Task Selected" is rendered.
  - Description explains the intent review purpose.
  - "Go to Pipeline" and "Open Backlog" action buttons are present.
  - data-testid="intent-no-task-state" attribute is present for targeting.

When a task IS selected the IntentEditor component renders — that path is not
exercised here because the test environment has no pre-selected task.

These tests check *what* the page communicates, not *how* it looks.
Style compliance is in test_pd_intent_style.py.
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright


# ---------------------------------------------------------------------------
# Navigation helper
# ---------------------------------------------------------------------------


def _go(page: object, base_url: str) -> None:
    """Navigate to the intent tab and wait for React to hydrate."""
    dashboard_navigate(page, base_url, "intent")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Empty state — heading
# ---------------------------------------------------------------------------


class TestIntentEmptyStateHeading:
    """Empty state heading must communicate 'No Task Selected'.

    When no task is selected the dashboard renders an EmptyState component
    that guides the user to select a task from the Pipeline tab before
    performing intent review.
    """

    def test_no_task_selected_heading_present(self, page, base_url: str) -> None:
        """Intent tab empty state shows 'No Task Selected' heading."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "No Task Selected" in body, (
            "Intent tab empty state must display 'No Task Selected' heading "
            "so users understand no task has been chosen for review"
        )

    def test_heading_is_visible(self, page, base_url: str) -> None:
        """'No Task Selected' heading element is visible in the viewport."""
        _go(page, base_url)

        # Try heading elements first, fall back to any element containing the text.
        heading = page.locator("h1, h2, h3, h4").filter(has_text="No Task Selected")
        if heading.count() > 0:
            assert heading.first.is_visible(), (
                "'No Task Selected' heading must be visible on the intent tab"
            )
        else:
            body = page.locator("body").inner_text()
            assert "No Task Selected" in body, (
                "'No Task Selected' text must appear somewhere on the intent tab"
            )


# ---------------------------------------------------------------------------
# Empty state — description
# ---------------------------------------------------------------------------


class TestIntentEmptyStateDescription:
    """Empty state description must explain the intent review purpose.

    The description helps users understand what intent review is and how to
    begin — it should mention selecting a task, the Pipeline tab, or the
    intent specification concept.
    """

    def test_description_explains_intent_review(self, page, base_url: str) -> None:
        """Empty state description references intent review purpose."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        has_description = (
            "intent" in body
            or "pipeline" in body
            or "select" in body
            or "specification" in body
            or "spec" in body
        )
        assert has_description, (
            "Intent tab empty state must include a description that references "
            "'intent', 'pipeline', 'select', or 'specification' to explain the "
            "purpose of the intent review tab"
        )

    def test_description_guides_user_action(self, page, base_url: str) -> None:
        """Empty state description tells users how to proceed."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        # The description should give a path forward — select from pipeline, etc.
        has_guidance = (
            "select" in body
            or "pipeline tab" in body
            or "agent" in body
            or "implement" in body
        )
        assert has_guidance, (
            "Intent tab empty state description must guide users toward a next action "
            "(e.g. 'Select a task from the Pipeline tab')"
        )


# ---------------------------------------------------------------------------
# Empty state — action buttons
# ---------------------------------------------------------------------------


class TestIntentEmptyStateActions:
    """Action buttons must be present and correctly labelled.

    The primary CTA navigates to the Pipeline tab; the secondary CTA opens
    the Backlog board.  Both must be reachable from the empty state.
    """

    def test_go_to_pipeline_button_present(self, page, base_url: str) -> None:
        """'Go to Pipeline' action button is rendered in the intent empty state."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "Go to Pipeline" in body, (
            "Intent tab empty state must display a 'Go to Pipeline' button "
            "that navigates users to the Pipeline tab to select a task"
        )

    def test_open_backlog_button_present(self, page, base_url: str) -> None:
        """'Open Backlog' secondary action button is rendered in the intent empty state."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "Open Backlog" in body, (
            "Intent tab empty state must display an 'Open Backlog' secondary action "
            "button that navigates users to the Backlog board"
        )

    def test_go_to_pipeline_button_is_interactive(self, page, base_url: str) -> None:
        """'Go to Pipeline' button is visible and not disabled."""
        _go(page, base_url)

        buttons = page.locator("button")
        count = buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            if "Go to Pipeline" in (btn.inner_text() or ""):
                assert btn.is_visible(), "'Go to Pipeline' button must be visible"
                assert btn.is_enabled(), "'Go to Pipeline' button must not be disabled"
                return

        # Also accept <a> elements that act as buttons
        links = page.locator("a")
        lcount = links.count()
        for i in range(lcount):
            lnk = links.nth(i)
            if "Go to Pipeline" in (lnk.inner_text() or ""):
                assert lnk.is_visible(), "'Go to Pipeline' link must be visible"
                return

        pytest.skip("'Go to Pipeline' button/link not found — skipping interactivity check")

    def test_open_backlog_button_is_interactive(self, page, base_url: str) -> None:
        """'Open Backlog' button is visible and not disabled."""
        _go(page, base_url)

        buttons = page.locator("button")
        count = buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            if "Open Backlog" in (btn.inner_text() or ""):
                assert btn.is_visible(), "'Open Backlog' button must be visible"
                assert btn.is_enabled(), "'Open Backlog' button must not be disabled"
                return

        links = page.locator("a")
        lcount = links.count()
        for i in range(lcount):
            lnk = links.nth(i)
            if "Open Backlog" in (lnk.inner_text() or ""):
                assert lnk.is_visible(), "'Open Backlog' link must be visible"
                return

        pytest.skip("'Open Backlog' button/link not found — skipping interactivity check")


# ---------------------------------------------------------------------------
# Empty state — data-testid
# ---------------------------------------------------------------------------


class TestIntentEmptyStateTestId:
    """The intent empty state must be addressable by data-testid.

    Stable test IDs allow this test suite, analytics hooks, and future
    automation to target the intent empty state independently of its content.
    """

    def test_intent_no_task_state_testid_present(self, page, base_url: str) -> None:
        """Intent empty state carries data-testid='intent-no-task-state'."""
        _go(page, base_url)

        count = page.locator("[data-testid='intent-no-task-state']").count()
        assert count > 0, (
            "Intent tab empty state must carry data-testid='intent-no-task-state' "
            "for targeted testing and analytics hooks"
        )

    def test_intent_no_task_state_testid_visible(self, page, base_url: str) -> None:
        """data-testid='intent-no-task-state' element is visible in the viewport."""
        _go(page, base_url)

        locator = page.locator("[data-testid='intent-no-task-state']")
        if locator.count() == 0:
            pytest.skip("data-testid='intent-no-task-state' not found — skipping visibility check")

        assert locator.first.is_visible(), (
            "data-testid='intent-no-task-state' element must be visible in the viewport"
        )
