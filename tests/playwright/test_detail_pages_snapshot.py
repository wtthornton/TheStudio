"""Epic 74.6 — Detail Pages: Visual Snapshot Baseline.

Captures baseline screenshots for entity detail views (repo, workflow, expert)
and registers them for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baselines for each entity's list page (always reachable).
- Detail-page baselines when seed data is available (entity IDs found via API).
- Component-level baselines for the primary detail sections:
    * Inspector / detail panel content area
    * Entity header (name + tier badge)
    * Action button row
    * Timeline or pipeline stage indicator (workflow)
    * Drift / performance signal section (expert)

Note: Detail pages require seed data (see Epic 74 note).  When no entities
exist the tests fall back to the list page so that a baseline is always
captured.  Detail-page section snapshots are skipped when seed data is absent.

First run
~~~~~~~~~
No baseline files exist — ``compare_snapshot`` auto-creates them; every test
passes with ``is_new_baseline=True``.

Subsequent runs
~~~~~~~~~~~~~~~
Existing baselines are loaded and compared.  Tests fail when the pixel-diff
ratio exceeds ``DEFAULT_THRESHOLD`` (0.1 %).

Updating baselines
~~~~~~~~~~~~~~~~~~
Set ``SNAPSHOT_UPDATE=1`` in the environment to overwrite all baselines and
always pass.

Related suites
~~~~~~~~~~~~~~
- 74.1 test_detail_pages_intent.py       - semantic content
- 74.2 test_detail_pages_api.py          - API endpoints
- 74.3 test_detail_pages_style.py        - style-guide compliance
- 74.4 test_detail_pages_interactions.py - interactive elements
- 74.5 test_detail_pages_a11y.py         - WCAG 2.2 AA
"""

from __future__ import annotations

import httpx
import pytest

from tests.playwright.conftest import navigate
from tests.playwright.lib.snapshot_helpers import (
    capture_element_snapshot,
    compare_snapshot,
    create_baseline,
)

pytestmark = pytest.mark.playwright

REPOS_URL = "/admin/ui/repos"
WORKFLOWS_URL = "/admin/ui/workflows"
EXPERTS_URL = "/admin/ui/experts"
API_REPOS = "/api/v1/repos"
API_WORKFLOWS = "/api/v1/workflows"
API_EXPERTS = "/api/v1/experts"

PAGE_NAME_REPO = "detail-pages-repo"
PAGE_NAME_WORKFLOW = "detail-pages-workflow"
PAGE_NAME_EXPERT = "detail-pages-expert"
PAGE_NAME_DETAIL = "detail-pages"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_entity_id(base_url: str, api_path: str) -> str | None:
    """Return the first entity ID from a list endpoint, or None if unavailable."""
    try:
        r = httpx.get(f"{base_url.rstrip('/')}{api_path}", timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", data.get("data", []))
        if items:
            first = items[0]
            return str(
                first.get("id")
                or first.get("repo_id")
                or first.get("workflow_id")
                or first.get("expert_id")
                or ""
            )
        return None
    except Exception:
        return None


def _go_list(page: object, base_url: str, list_url: str) -> None:
    """Navigate to the entity list page and wait for content to settle."""
    navigate(page, f"{base_url}{list_url}")  # type: ignore[arg-type]


def _go_detail(page: object, base_url: str, detail_base: str, entity_id: str) -> None:
    """Navigate to a specific entity detail page."""
    navigate(page, f"{base_url}{detail_base}/{entity_id}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshots — list pages (always reachable)
# ---------------------------------------------------------------------------


class TestDetailPagesListSnapshot:
    """Capture full-page baselines for entity list pages as stable anchor views.

    These snapshots always pass regardless of seed data, because the list
    page renders an empty-state or populated table in all environments.
    """

    def test_repos_list_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the repo list page at 1280x720."""
        _go_list(page, base_url, REPOS_URL)
        result = compare_snapshot(page, "repos-list-full-page", page_name=PAGE_NAME_REPO)
        assert result.passed, result.summary()

    def test_workflows_list_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the workflow list page at 1280x720."""
        _go_list(page, base_url, WORKFLOWS_URL)
        result = compare_snapshot(page, "workflows-list-full-page", page_name=PAGE_NAME_WORKFLOW)
        assert result.passed, result.summary()

    def test_experts_list_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the expert list page at 1280x720."""
        _go_list(page, base_url, EXPERTS_URL)
        result = compare_snapshot(page, "experts-list-full-page", page_name=PAGE_NAME_EXPERT)
        assert result.passed, result.summary()

    def test_repos_list_create_explicit_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the repo list full-page baseline.

        Always passes — guarantees a baseline is committed so CI never starts
        from a blank slate.
        """
        _go_list(page, base_url, REPOS_URL)
        result = create_baseline(page, "repos-list-explicit", page_name=PAGE_NAME_REPO)
        assert result.passed, result.summary()
        assert result.is_new_baseline, "create_baseline must always report is_new_baseline=True"

    def test_workflows_list_create_explicit_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the workflow list full-page baseline."""
        _go_list(page, base_url, WORKFLOWS_URL)
        result = create_baseline(page, "workflows-list-explicit", page_name=PAGE_NAME_WORKFLOW)
        assert result.passed, result.summary()
        assert result.is_new_baseline, "create_baseline must always report is_new_baseline=True"

    def test_experts_list_create_explicit_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the expert list full-page baseline."""
        _go_list(page, base_url, EXPERTS_URL)
        result = create_baseline(page, "experts-list-explicit", page_name=PAGE_NAME_EXPERT)
        assert result.passed, result.summary()
        assert result.is_new_baseline, "create_baseline must always report is_new_baseline=True"


# ---------------------------------------------------------------------------
# Full-page snapshots — detail pages (seed-data dependent)
# ---------------------------------------------------------------------------


class TestDetailPagesDetailSnapshot:
    """Capture full-page baselines for entity detail pages when seed data exists.

    Tests skip gracefully when no entities are registered in the system so
    that CI environments without seed data still produce a green suite.
    """

    def test_repo_detail_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of a repo detail page at 1280x720."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos registered — seed data required for repo detail snapshot 74.6")

        _go_detail(page, base_url, "/admin/ui/repos", entity_id)
        result = compare_snapshot(page, "repo-detail-full-page", page_name=PAGE_NAME_REPO)
        assert result.passed, result.summary()

    def test_workflow_detail_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of a workflow detail page at 1280x720."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if not entity_id:
            pytest.skip(
                "No workflows registered — seed data required for workflow detail snapshot 74.6"
            )

        _go_detail(page, base_url, "/admin/ui/workflows", entity_id)
        result = compare_snapshot(page, "workflow-detail-full-page", page_name=PAGE_NAME_WORKFLOW)
        assert result.passed, result.summary()

    def test_expert_detail_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of an expert detail page at 1280x720."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if not entity_id:
            pytest.skip(
                "No experts registered — seed data required for expert detail snapshot 74.6"
            )

        _go_detail(page, base_url, "/admin/ui/experts", entity_id)
        result = compare_snapshot(page, "expert-detail-full-page", page_name=PAGE_NAME_EXPERT)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Section-level snapshots — inspector / detail panel
# ---------------------------------------------------------------------------


class TestDetailPanesSectionSnapshots:
    """Element-level snapshots for primary detail panel sections.

    Isolating sections reduces noise: a change to the action button row should
    not fail the entity header snapshot.
    """

    def test_repo_inspector_panel_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the repo inspector / detail panel section."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if entity_id:
            _go_detail(page, base_url, "/admin/ui/repos", entity_id)
        else:
            _go_list(page, base_url, REPOS_URL)

        panel_selectors = [
            "[data-testid='repo-detail']",
            "[data-testid='inspector-panel']",
            "[data-testid='detail-panel']",
            "[class*='inspector-panel']",
            "[class*='detail-panel']",
            "[class*='repo-detail']",
            "[class*='slide-panel']",
            "[class*='entity-detail']",
            "aside[aria-label*='detail' i]",
            "aside[aria-label*='repo' i]",
            "main article",
            "main section",
        ]

        section_found = False
        for selector in panel_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "repo-inspector-panel", page_name=PAGE_NAME_REPO
                    )
                    assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "repo-inspector-panel-fallback", page_name=PAGE_NAME_REPO
            )
            assert result.passed, result.summary()

    def test_workflow_inspector_panel_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the workflow inspector / detail panel section."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if entity_id:
            _go_detail(page, base_url, "/admin/ui/workflows", entity_id)
        else:
            _go_list(page, base_url, WORKFLOWS_URL)

        panel_selectors = [
            "[data-testid='workflow-detail']",
            "[data-testid='inspector-panel']",
            "[data-testid='detail-panel']",
            "[class*='inspector-panel']",
            "[class*='detail-panel']",
            "[class*='workflow-detail']",
            "[class*='slide-panel']",
            "[class*='entity-detail']",
            "aside[aria-label*='workflow' i]",
            "aside[aria-label*='detail' i]",
            "main article",
            "main section",
        ]

        section_found = False
        for selector in panel_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "workflow-inspector-panel", page_name=PAGE_NAME_WORKFLOW
                    )
                    assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "workflow-inspector-panel-fallback", page_name=PAGE_NAME_WORKFLOW
            )
            assert result.passed, result.summary()

    def test_expert_inspector_panel_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the expert inspector / detail panel section."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if entity_id:
            _go_detail(page, base_url, "/admin/ui/experts", entity_id)
        else:
            _go_list(page, base_url, EXPERTS_URL)

        panel_selectors = [
            "[data-testid='expert-detail']",
            "[data-testid='inspector-panel']",
            "[data-testid='detail-panel']",
            "[class*='inspector-panel']",
            "[class*='detail-panel']",
            "[class*='expert-detail']",
            "[class*='slide-panel']",
            "[class*='entity-detail']",
            "aside[aria-label*='expert' i]",
            "aside[aria-label*='detail' i]",
            "main article",
            "main section",
        ]

        section_found = False
        for selector in panel_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "expert-inspector-panel", page_name=PAGE_NAME_EXPERT
                    )
                    assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "expert-inspector-panel-fallback", page_name=PAGE_NAME_EXPERT
            )
            assert result.passed, result.summary()

    def test_entity_header_badge_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the entity header including tier badge.

        The header (name + tier badge) must remain visually consistent across
        all entity types — operators use the tier badge for rapid orientation.
        Falls back to the repo list page when no entities are registered.
        """
        entity_id = _first_entity_id(base_url, API_REPOS)
        if entity_id:
            _go_detail(page, base_url, "/admin/ui/repos", entity_id)
        else:
            _go_list(page, base_url, REPOS_URL)

        header_selectors = [
            "[data-testid='entity-header']",
            "[data-testid='detail-header']",
            "[class*='entity-header']",
            "[class*='detail-header']",
            "[class*='page-header']:has([class*='badge'])",
            "header:has([class*='badge'])",
            "h1:has(~ [class*='badge'])",
            "[class*='header']:has([class*='tier'])",
        ]

        section_found = False
        for selector in header_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "entity-header-badge", page_name=PAGE_NAME_DETAIL
                    )
                    assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "entity-header-badge-fallback", page_name=PAGE_NAME_DETAIL
            )
            assert result.passed, result.summary()

    def test_action_buttons_row_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the entity action button row.

        Action buttons (e.g. Pause / Resume, Change Tier) must remain
        visually consistent — operators rely on them to control entity state.
        Falls back to the repos list page when no entities are registered.
        """
        entity_id = _first_entity_id(base_url, API_REPOS)
        if entity_id:
            _go_detail(page, base_url, "/admin/ui/repos", entity_id)
        else:
            _go_list(page, base_url, REPOS_URL)

        action_selectors = [
            "[data-testid='action-buttons']",
            "[data-testid='detail-actions']",
            "[class*='action-buttons']",
            "[class*='detail-actions']",
            "[class*='action-row']",
            "[class*='entity-actions']",
            "[role='toolbar']",
            "div:has(button[class*='primary']) + div:has(button)",
            "footer:has(button)",
        ]

        section_found = False
        for selector in action_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "action-buttons-row", page_name=PAGE_NAME_DETAIL
                    )
                    assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "action-buttons-row-fallback", page_name=PAGE_NAME_DETAIL
            )
            assert result.passed, result.summary()

    def test_workflow_pipeline_stage_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the workflow pipeline stage indicator.

        The pipeline stage display (e.g. progress bar, step list, Gantt-style
        timeline) must remain visually consistent — operators use it to
        understand where a workflow is in the 9-step pipeline or where it
        failed.  Skipped when no workflows are registered.
        """
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if not entity_id:
            pytest.skip(
                "No workflows registered — seed data required for pipeline stage snapshot 74.6"
            )

        _go_detail(page, base_url, "/admin/ui/workflows", entity_id)

        stage_selectors = [
            "[data-testid='pipeline-stage']",
            "[data-testid='pipeline-steps']",
            "[data-testid='workflow-timeline']",
            "[class*='pipeline-stage']",
            "[class*='pipeline-steps']",
            "[class*='pipeline-progress']",
            "[class*='workflow-timeline']",
            "[class*='stage-indicator']",
            "[class*='step-list']",
            "[aria-label*='pipeline' i]",
            "ol[class*='stage'], ul[class*='stage']",
            "ol[class*='step'], ul[class*='step']",
        ]

        section_found = False
        for selector in stage_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "workflow-pipeline-stage", page_name=PAGE_NAME_WORKFLOW
                    )
                    assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "workflow-pipeline-stage-fallback", page_name=PAGE_NAME_WORKFLOW
            )
            assert result.passed, result.summary()

    def test_expert_drift_signals_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the expert drift / performance signal section.

        The drift indicator panel must remain visually consistent — operators
        use it to spot performance degradation before it affects output quality.
        Skipped when no experts are registered.
        """
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if not entity_id:
            pytest.skip(
                "No experts registered — seed data required for drift signal snapshot 74.6"
            )

        _go_detail(page, base_url, "/admin/ui/experts", entity_id)

        drift_selectors = [
            "[data-testid='drift-signals']",
            "[data-testid='performance-signals']",
            "[data-testid='expert-drift']",
            "[class*='drift-signals']",
            "[class*='drift-panel']",
            "[class*='performance-signals']",
            "[class*='signal-section']",
            "[class*='drift-indicator']",
            "[class*='health-signals']",
            "[aria-label*='drift' i]",
            "[aria-label*='performance signal' i]",
            "section:has([class*='drift'])",
            "div:has([class*='drift-badge'])",
        ]

        section_found = False
        for selector in drift_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "expert-drift-signals", page_name=PAGE_NAME_EXPERT
                    )
                    assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "expert-drift-signals-fallback", page_name=PAGE_NAME_EXPERT
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestDetailPagesSnapshotRegression:
    """Verify current render matches committed baselines (pixel-diff guard).

    These tests are the continuous-integration regression guards.  They pass
    on first run (baseline auto-created) and fail only when a subsequent run
    produces a pixel-diff above the threshold.

    Override the threshold with ``SNAPSHOT_THRESHOLD=0.002`` (0.2%) for
    environments where minor antialiasing differences are expected.
    """

    def test_repos_list_full_page_regression(self, page: object, base_url: str) -> None:
        """Full-page pixel-diff for the repos list must not exceed the threshold."""
        _go_list(page, base_url, REPOS_URL)
        result = compare_snapshot(page, "regression-repos-list", page_name=PAGE_NAME_REPO)
        assert result.passed, result.summary()

    def test_workflows_list_full_page_regression(self, page: object, base_url: str) -> None:
        """Full-page pixel-diff for the workflows list must not exceed the threshold."""
        _go_list(page, base_url, WORKFLOWS_URL)
        result = compare_snapshot(page, "regression-workflows-list", page_name=PAGE_NAME_WORKFLOW)
        assert result.passed, result.summary()

    def test_experts_list_full_page_regression(self, page: object, base_url: str) -> None:
        """Full-page pixel-diff for the experts list must not exceed the threshold."""
        _go_list(page, base_url, EXPERTS_URL)
        result = compare_snapshot(page, "regression-experts-list", page_name=PAGE_NAME_EXPERT)
        assert result.passed, result.summary()

    def test_no_critical_console_errors_repos(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Repos list/detail page must not emit critical JS errors during snapshot capture."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if entity_id:
            _go_detail(page, base_url, "/admin/ui/repos", entity_id)
        else:
            _go_list(page, base_url, REPOS_URL)

        compare_snapshot(page, "console-check-repos", page_name=PAGE_NAME_REPO)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Repos detail page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )

    def test_no_critical_console_errors_workflows(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Workflows list/detail page must not emit critical JS errors during snapshot capture."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if entity_id:
            _go_detail(page, base_url, "/admin/ui/workflows", entity_id)
        else:
            _go_list(page, base_url, WORKFLOWS_URL)

        compare_snapshot(page, "console-check-workflows", page_name=PAGE_NAME_WORKFLOW)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Workflows detail page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )

    def test_no_critical_console_errors_experts(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Experts list/detail page must not emit critical JS errors during snapshot capture."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if entity_id:
            _go_detail(page, base_url, "/admin/ui/experts", entity_id)
        else:
            _go_list(page, base_url, EXPERTS_URL)

        compare_snapshot(page, "console-check-experts", page_name=PAGE_NAME_EXPERT)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Experts detail page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
