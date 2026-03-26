"""Story 76.2 — Pipeline Dashboard: Page Intent & Semantic Content.

Validates that /dashboard/?tab=pipeline delivers its core purpose:
  - Pipeline rail renders stage nodes (Intake → Context → Intent → Router →
    Assembler → Implement → Verify → QA → Publish) OR shows the empty-pipeline
    state when no tasks exist.
  - Empty state communicates the correct heading, description, and CTA.
  - Event Log section ("RECENT EVENTS") is always present.
  - Gate Inspector section ("Gate Inspector") is always present.
  - Stage nodes carry visible stage name labels when tasks are active.

These tests check *what* the page communicates, not *how* it looks.
Style compliance is in test_pd_pipeline_style.py (Story 76.4).
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

# The nine canonical pipeline stage labels as rendered by the app.
PIPELINE_STAGE_LABELS = [
    "Intake",
    "Context",
    "Intent",
    "Router",
    "Assembler",
    "Implement",
    "Verify",
    "QA",
    "Publish",
]


# ---------------------------------------------------------------------------
# Navigation guard
# ---------------------------------------------------------------------------


def _go(page: object, base_url: str) -> None:
    """Navigate to the pipeline tab and wait for React to hydrate."""
    dashboard_navigate(page, base_url, "pipeline")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Pipeline rail — active state
# ---------------------------------------------------------------------------


class TestPipelineStageLabels:
    """Pipeline rail must show the nine canonical stage names when tasks exist.

    Operators need to identify which stage is active at a glance.  The stage
    labels are the primary navigation anchor for the pipeline section.
    """

    def test_pipeline_rail_or_empty_state_present(self, page, base_url: str) -> None:
        """Pipeline tab renders either the stage rail or an empty-pipeline state."""
        _go(page, base_url)

        has_rail = (
            page.locator("[data-testid='pipeline-rail']").count() > 0
            or page.locator("[data-testid='empty-pipeline-rail']").count() > 0
        )
        assert has_rail, (
            "Pipeline tab must render either the pipeline-rail or empty-pipeline-rail "
            "component — neither was found in the DOM"
        )

    def test_stage_nodes_present_when_tasks_active(self, page, base_url: str) -> None:
        """When tasks exist, each stage node is rendered in the pipeline rail."""
        _go(page, base_url)

        rail = page.locator("[data-testid='pipeline-rail']")
        if rail.count() == 0:
            pytest.skip("No pipeline-rail — empty state is present, no tasks active")

        body = page.locator("[data-testid='pipeline-rail']").inner_text()
        found = [label for label in PIPELINE_STAGE_LABELS if label in body]
        assert found, (
            "Pipeline rail must display at least one stage label "
            f"({', '.join(PIPELINE_STAGE_LABELS)!r} — none found in the rail)"
        )

    def test_all_nine_stages_shown_when_rail_active(self, page, base_url: str) -> None:
        """When the pipeline rail renders, all nine stage names are visible."""
        _go(page, base_url)

        rail = page.locator("[data-testid='pipeline-rail']")
        if rail.count() == 0:
            pytest.skip("Pipeline rail not rendered — empty state acceptable")

        body = rail.inner_text()
        missing = [label for label in PIPELINE_STAGE_LABELS if label not in body]
        assert not missing, (
            f"Pipeline rail is missing stage labels: {missing!r}"
        )


# ---------------------------------------------------------------------------
# Empty pipeline state
# ---------------------------------------------------------------------------


class TestEmptyPipelineState:
    """Empty pipeline state must surface the correct heading, description, and CTA.

    When no tasks are in the pipeline, the empty state guides the user to
    import a GitHub issue to kick off the AI delivery pipeline.
    """

    def test_empty_state_heading_when_no_tasks(self, page, base_url: str) -> None:
        """Empty pipeline state has the 'No tasks in the pipeline' heading."""
        _go(page, base_url)

        if page.locator("[data-testid='pipeline-rail']").count() > 0:
            pytest.skip("Pipeline rail active — not in empty state")

        body = page.locator("body").inner_text()
        assert "No tasks in the pipeline" in body, (
            "Empty pipeline state must display 'No tasks in the pipeline' heading"
        )

    def test_empty_state_description_present(self, page, base_url: str) -> None:
        """Empty state description explains how to kick off the pipeline."""
        _go(page, base_url)

        if page.locator("[data-testid='pipeline-rail']").count() > 0:
            pytest.skip("Pipeline rail active — not in empty state")

        body = page.locator("body").inner_text().lower()
        has_description = (
            "import" in body
            or "github" in body
            or "kick off" in body
            or "draft pr" in body
        )
        assert has_description, (
            "Empty pipeline state must include a description explaining how to "
            "import a GitHub issue to kick off the pipeline"
        )

    def test_import_an_issue_cta_present(self, page, base_url: str) -> None:
        """Empty pipeline state shows 'Import an Issue' call-to-action button."""
        _go(page, base_url)

        if page.locator("[data-testid='pipeline-rail']").count() > 0:
            pytest.skip("Pipeline rail active — not in empty state")

        body = page.locator("body").inner_text()
        assert "Import an Issue" in body, (
            "Empty pipeline state must display 'Import an Issue' CTA button "
            "to guide users into the pipeline"
        )

    def test_learn_about_pipeline_link_present(self, page, base_url: str) -> None:
        """Empty pipeline state includes a 'Learn about the pipeline' secondary link."""
        _go(page, base_url)

        if page.locator("[data-testid='pipeline-rail']").count() > 0:
            pytest.skip("Pipeline rail active — not in empty state")

        body = page.locator("body").inner_text()
        assert "Learn about the pipeline" in body, (
            "Empty pipeline state must include a 'Learn about the pipeline' "
            "secondary action link"
        )

    def test_empty_pipeline_rail_testid_present(self, page, base_url: str) -> None:
        """Empty pipeline state is addressable via data-testid='empty-pipeline-rail'."""
        _go(page, base_url)

        if page.locator("[data-testid='pipeline-rail']").count() > 0:
            pytest.skip("Pipeline rail active — not in empty state")

        assert page.locator("[data-testid='empty-pipeline-rail']").count() > 0, (
            "Empty pipeline state must carry data-testid='empty-pipeline-rail' "
            "for targeted testing and analytics"
        )


# ---------------------------------------------------------------------------
# Event Log section
# ---------------------------------------------------------------------------


class TestEventLogSection:
    """Event Log section must always be present on the pipeline tab.

    The Event Log shows real-time SSE events and is the primary diagnostic
    tool for operators monitoring pipeline activity.
    """

    def test_event_log_section_present(self, page, base_url: str) -> None:
        """Event log section is rendered on the pipeline tab."""
        _go(page, base_url)

        assert page.locator("[data-testid='event-log']").count() > 0, (
            "Pipeline tab must always render the event-log section "
            "(data-testid='event-log')"
        )

    def test_recent_events_heading_shown(self, page, base_url: str) -> None:
        """Event log has a 'Recent Events' section heading."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        assert "recent events" in body, (
            "Event log section must display a 'Recent Events' heading "
            "so operators can identify the log at a glance"
        )

    def test_event_log_empty_state_or_events(self, page, base_url: str) -> None:
        """Event log shows events or an appropriate empty state ('No events yet')."""
        _go(page, base_url)

        has_events = page.locator("[data-testid='event-list']").count() > 0
        has_empty = page.locator("[data-testid='event-log-empty']").count() > 0
        body_lower = page.locator("[data-testid='event-log']").inner_text().lower()
        has_no_events_text = "no events" in body_lower or "no events yet" in body_lower

        assert has_events or has_empty or has_no_events_text, (
            "Event log must show a list of events or an 'No events yet' empty state"
        )


# ---------------------------------------------------------------------------
# Gate Inspector section
# ---------------------------------------------------------------------------


class TestGateInspectorSection:
    """Gate Inspector section must always be present on the pipeline tab.

    The Gate Inspector gives operators chronological gate transition history
    with filtering by result (All / Pass / Fail) and pipeline stage.
    """

    def test_gate_inspector_section_present(self, page, base_url: str) -> None:
        """Gate Inspector section is rendered on the pipeline tab."""
        _go(page, base_url)

        assert page.locator("[data-testid='gate-inspector']").count() > 0, (
            "Pipeline tab must always render the gate-inspector section "
            "(data-testid='gate-inspector')"
        )

    def test_gate_inspector_heading_shown(self, page, base_url: str) -> None:
        """Gate Inspector section has a 'Gate Inspector' heading."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "Gate Inspector" in body, (
            "Gate Inspector section must display 'Gate Inspector' heading "
            "so operators can locate the diagnostic panel"
        )

    def test_gate_filter_bar_present(self, page, base_url: str) -> None:
        """Gate Inspector includes a filter bar for narrowing gate results."""
        _go(page, base_url)

        assert page.locator("[data-testid='gate-filter-bar']").count() > 0, (
            "Gate Inspector must include a filter bar (data-testid='gate-filter-bar') "
            "with All / Pass / Fail toggles"
        )

    def test_gate_all_pass_fail_filters_shown(self, page, base_url: str) -> None:
        """Gate Inspector filter bar shows All, Pass, and Fail filter options."""
        _go(page, base_url)

        filter_bar = page.locator("[data-testid='gate-filter-bar']")
        if filter_bar.count() == 0:
            pytest.skip("Gate filter bar not found — skipping filter label check")

        bar_text = filter_bar.inner_text()
        assert "All" in bar_text, "Gate filter bar must show 'All' filter option"
        assert "Pass" in bar_text, "Gate filter bar must show 'Pass' filter option"
        assert "Fail" in bar_text, "Gate filter bar must show 'Fail' filter option"
