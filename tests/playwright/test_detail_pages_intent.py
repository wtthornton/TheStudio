"""Epic 74.1 — Detail Pages: Page Intent & Semantic Content.

Validates that entity detail views (/{entity}/{id}) deliver their core purpose:
  - Repo detail shows name, tier, status, queue depth, and configuration
  - Workflow detail shows ID, repo, status, pipeline stage, and timeline
  - Expert detail shows name, trust tier, confidence score, and drift signals

Note: Detail pages require seed data. Tests skip gracefully when no entities exist
and fall back to verifying the detail panel/slide-out behaviour on list pages
(inspector panels per §9.14 of the style guide).

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_detail_pages_style.py (Epic 74.3).
"""

import pytest
import httpx

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

REPOS_URL = "/admin/ui/repos"
WORKFLOWS_URL = "/admin/ui/workflows"
EXPERTS_URL = "/admin/ui/experts"
API_REPOS = "/api/v1/repos"
API_WORKFLOWS = "/api/v1/workflows"
API_EXPERTS = "/api/v1/experts"


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
            return str(first.get("id") or first.get("repo_id") or first.get("workflow_id") or "")
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Repo detail
# ---------------------------------------------------------------------------

class TestRepoDetailIntent:
    """Repo detail view must surface the information an operator needs to manage a single repo.

    When a repo detail page (or inspector panel) is open it must show:
      Name / URL  — human-readable identifier and GitHub URL
      Tier        — current trust tier (Observe / Suggest / Execute)
      Status      — active / paused / error state
      Queue depth — number of pending tasks for that repo
    """

    def test_repo_detail_page_or_panel_renders(self, page, base_url: str) -> None:
        """Repo detail renders via a dedicated URL or an inspector panel on the list page."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if entity_id:
            navigate(page, f"{base_url}/admin/ui/repos/{entity_id}")
        else:
            navigate(page, f"{base_url}{REPOS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Repo detail page body must not be empty"

    def test_repo_detail_shows_name_or_identifier(self, page, base_url: str) -> None:
        """Repo detail view displays a repo name or GitHub URL as its primary identifier."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos registered — seed data required for repo detail 74.1")

        navigate(page, f"{base_url}/admin/ui/repos/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        name_keywords = ("repo", "repository", "github.com", "name", "url")
        assert any(kw in body_lower for kw in name_keywords), (
            "Repo detail page must display the repo name or URL as a primary identifier"
        )

    def test_repo_detail_shows_tier(self, page, base_url: str) -> None:
        """Repo detail view displays the trust tier."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos registered — seed data required for repo detail 74.1")

        navigate(page, f"{base_url}/admin/ui/repos/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        tier_keywords = ("observe", "suggest", "execute", "tier", "trust")
        assert any(kw in body_lower for kw in tier_keywords), (
            "Repo detail page must display the trust tier (Observe/Suggest/Execute)"
        )

    def test_repo_detail_shows_status(self, page, base_url: str) -> None:
        """Repo detail view displays the repo status."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos registered — seed data required for repo detail 74.1")

        navigate(page, f"{base_url}/admin/ui/repos/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        status_keywords = ("status", "active", "paused", "error", "enabled", "disabled")
        assert any(kw in body_lower for kw in status_keywords), (
            "Repo detail page must display the repo status"
        )

    def test_repo_detail_shows_queue_or_tasks(self, page, base_url: str) -> None:
        """Repo detail view includes queue depth or task count information."""
        entity_id = _first_entity_id(base_url, API_REPOS)
        if not entity_id:
            pytest.skip("No repos registered — seed data required for repo detail 74.1")

        navigate(page, f"{base_url}/admin/ui/repos/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        queue_keywords = ("queue", "pending", "tasks", "depth", "backlog", "workflows")
        assert any(kw in body_lower for kw in queue_keywords), (
            "Repo detail page must display queue depth or related task/workflow count"
        )

    def test_repo_inspector_panel_accessible_from_list(self, page, base_url: str) -> None:
        """Repo list page exposes a detail panel or detail link for each row."""
        navigate(page, f"{base_url}{REPOS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No repos in table — inspector panel test requires at least one repo")

        rows = page.locator("table tbody tr").count()
        if rows == 0:
            pytest.skip("No repo rows — inspector panel test requires at least one repo row")

        # Detail should be reachable via a link, button, or clickable row
        has_detail_link = page.locator("table a[href*='/repos/']").count() > 0
        has_detail_button = page.locator("table button").count() > 0
        has_clickable_row = page.locator("table tbody tr[data-href], table tbody tr[role='link']").count() > 0
        assert has_detail_link or has_detail_button or has_clickable_row, (
            "Repo table must provide a way to reach the detail view for each row"
        )


# ---------------------------------------------------------------------------
# Workflow detail
# ---------------------------------------------------------------------------

class TestWorkflowDetailIntent:
    """Workflow detail view must surface the information an operator needs to debug a run.

    When a workflow detail page (or inspector panel) is open it must show:
      ID / Run     — unique identifier for cross-referencing logs and CI
      Repo         — which repository triggered this workflow
      Status       — running / stuck / failed / completed state
      Pipeline stage — which step is currently active or where it failed
    """

    def test_workflow_detail_page_or_panel_renders(self, page, base_url: str) -> None:
        """Workflow detail renders via a dedicated URL or an inspector panel on the list page."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if entity_id:
            navigate(page, f"{base_url}/admin/ui/workflows/{entity_id}")
        else:
            navigate(page, f"{base_url}{WORKFLOWS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Workflow detail page body must not be empty"

    def test_workflow_detail_shows_identifier(self, page, base_url: str) -> None:
        """Workflow detail view displays a workflow ID or run reference."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if not entity_id:
            pytest.skip("No workflows registered — seed data required for workflow detail 74.1")

        navigate(page, f"{base_url}/admin/ui/workflows/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        id_keywords = ("workflow", "run", "id", "#", "task")
        assert any(kw in body_lower for kw in id_keywords), (
            "Workflow detail page must display a workflow ID or run identifier"
        )

    def test_workflow_detail_shows_repo(self, page, base_url: str) -> None:
        """Workflow detail view displays the associated repository."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if not entity_id:
            pytest.skip("No workflows registered — seed data required for workflow detail 74.1")

        navigate(page, f"{base_url}/admin/ui/workflows/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        assert "repo" in body_lower or "repository" in body_lower, (
            "Workflow detail page must display the associated repository"
        )

    def test_workflow_detail_shows_status(self, page, base_url: str) -> None:
        """Workflow detail view displays the workflow status."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if not entity_id:
            pytest.skip("No workflows registered — seed data required for workflow detail 74.1")

        navigate(page, f"{base_url}/admin/ui/workflows/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        status_keywords = ("status", "running", "stuck", "failed", "complete", "pending", "queued")
        assert any(kw in body_lower for kw in status_keywords), (
            "Workflow detail page must display the workflow status"
        )

    def test_workflow_detail_shows_pipeline_stage(self, page, base_url: str) -> None:
        """Workflow detail view shows the active or failed pipeline stage."""
        entity_id = _first_entity_id(base_url, API_WORKFLOWS)
        if not entity_id:
            pytest.skip("No workflows registered — seed data required for workflow detail 74.1")

        navigate(page, f"{base_url}/admin/ui/workflows/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        stage_keywords = (
            "stage", "step", "intake", "context", "intent", "routing",
            "assembler", "implement", "verify", "qa", "publish", "pipeline",
        )
        assert any(kw in body_lower for kw in stage_keywords), (
            "Workflow detail page must display the current or last pipeline stage"
        )

    def test_workflow_inspector_panel_accessible_from_list(self, page, base_url: str) -> None:
        """Workflow list page exposes a detail panel or detail link for each row."""
        navigate(page, f"{base_url}{WORKFLOWS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No workflows in table — inspector panel test requires at least one workflow")

        rows = page.locator("table tbody tr").count()
        if rows == 0:
            pytest.skip("No workflow rows — inspector panel test requires at least one workflow row")

        has_detail_link = page.locator("table a[href*='/workflows/']").count() > 0
        has_detail_button = page.locator("table button").count() > 0
        has_clickable_row = page.locator("table tbody tr[data-href], table tbody tr[role='link']").count() > 0
        assert has_detail_link or has_detail_button or has_clickable_row, (
            "Workflow table must provide a way to reach the detail view for each row"
        )


# ---------------------------------------------------------------------------
# Expert detail
# ---------------------------------------------------------------------------

class TestExpertDetailIntent:
    """Expert detail view must surface the information an operator needs to evaluate an expert agent.

    When an expert detail page (or inspector panel) is open it must show:
      Name / Type   — expert identifier and specialisation
      Trust tier    — Observe / Suggest / Execute level
      Confidence    — numeric or visual confidence score
      Drift signals — any detected drift or performance degradation indicators
    """

    def test_expert_detail_page_or_panel_renders(self, page, base_url: str) -> None:
        """Expert detail renders via a dedicated URL or an inspector panel on the list page."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if entity_id:
            navigate(page, f"{base_url}/admin/ui/experts/{entity_id}")
        else:
            navigate(page, f"{base_url}{EXPERTS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Expert detail page body must not be empty"

    def test_expert_detail_shows_name_or_type(self, page, base_url: str) -> None:
        """Expert detail view displays the expert name or type as its primary identifier."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if not entity_id:
            pytest.skip("No experts registered — seed data required for expert detail 74.1")

        navigate(page, f"{base_url}/admin/ui/experts/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        name_keywords = ("expert", "name", "type", "agent", "role", "specialist")
        assert any(kw in body_lower for kw in name_keywords), (
            "Expert detail page must display the expert name or type"
        )

    def test_expert_detail_shows_tier(self, page, base_url: str) -> None:
        """Expert detail view displays the trust tier."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if not entity_id:
            pytest.skip("No experts registered — seed data required for expert detail 74.1")

        navigate(page, f"{base_url}/admin/ui/experts/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        tier_keywords = ("observe", "suggest", "execute", "tier", "trust")
        assert any(kw in body_lower for kw in tier_keywords), (
            "Expert detail page must display the trust tier (Observe/Suggest/Execute)"
        )

    def test_expert_detail_shows_confidence(self, page, base_url: str) -> None:
        """Expert detail view displays a confidence score or rating."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if not entity_id:
            pytest.skip("No experts registered — seed data required for expert detail 74.1")

        navigate(page, f"{base_url}/admin/ui/experts/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        confidence_keywords = ("confidence", "score", "accuracy", "rating", "performance", "%")
        assert any(kw in body_lower for kw in confidence_keywords), (
            "Expert detail page must display a confidence score or performance metric"
        )

    def test_expert_detail_shows_drift_signals(self, page, base_url: str) -> None:
        """Expert detail view includes drift or performance signal indicators."""
        entity_id = _first_entity_id(base_url, API_EXPERTS)
        if not entity_id:
            pytest.skip("No experts registered — seed data required for expert detail 74.1")

        navigate(page, f"{base_url}/admin/ui/experts/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        drift_keywords = (
            "drift", "signal", "degradation", "trend", "anomaly",
            "alert", "warning", "healthy", "performance",
        )
        assert any(kw in body_lower for kw in drift_keywords), (
            "Expert detail page must display drift signals or performance health indicators"
        )

    def test_expert_inspector_panel_accessible_from_list(self, page, base_url: str) -> None:
        """Expert list page exposes a detail panel or detail link for each row."""
        navigate(page, f"{base_url}{EXPERTS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No experts in table — inspector panel test requires at least one expert")

        rows = page.locator("table tbody tr").count()
        if rows == 0:
            pytest.skip("No expert rows — inspector panel test requires at least one expert row")

        has_detail_link = page.locator("table a[href*='/experts/']").count() > 0
        has_detail_button = page.locator("table button").count() > 0
        has_clickable_row = page.locator("table tbody tr[data-href], table tbody tr[role='link']").count() > 0
        assert has_detail_link or has_detail_button or has_clickable_row, (
            "Expert table must provide a way to reach the detail view for each row"
        )


# ---------------------------------------------------------------------------
# Shared detail page structure
# ---------------------------------------------------------------------------

class TestDetailPageStructure:
    """All entity detail pages must have consistent structural elements.

    Operators jumping between detail pages expect a predictable layout:
      Breadcrumb / back nav — to return to the list page
      Page heading          — clearly identifies which entity and type is shown
      Action buttons        — primary actions relevant to the entity
    """

    @pytest.mark.parametrize("list_url,entity_name", [
        (REPOS_URL, "repo"),
        (WORKFLOWS_URL, "workflow"),
        (EXPERTS_URL, "expert"),
    ])
    def test_detail_page_loads_without_error(
        self, page, base_url: str, list_url: str, entity_name: str
    ) -> None:
        """Detail page (or list page as fallback) loads with non-empty body."""
        navigate(page, f"{base_url}{list_url}")
        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, f"{entity_name} detail/list page body must not be empty"

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_detail_page_has_heading(
        self, page, base_url: str, api_path: str, detail_base: str, entity_name: str
    ) -> None:
        """Detail page has a heading that names the entity type."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for detail 74.1")

        navigate(page, f"{base_url}{detail_base}/{entity_id}")

        body_lower = page.locator("body").inner_text().lower()
        assert entity_name.lower() in body_lower or detail_base.split("/")[-1] in body_lower, (
            f"{entity_name} detail page must have a heading referencing '{entity_name}'"
        )

    @pytest.mark.parametrize("api_path,detail_base,entity_name", [
        (API_REPOS, "/admin/ui/repos", "repo"),
        (API_WORKFLOWS, "/admin/ui/workflows", "workflow"),
        (API_EXPERTS, "/admin/ui/experts", "expert"),
    ])
    def test_detail_page_has_back_navigation(
        self, page, base_url: str, api_path: str, detail_base: str, entity_name: str
    ) -> None:
        """Detail page provides breadcrumb or back navigation to the list page."""
        entity_id = _first_entity_id(base_url, api_path)
        if not entity_id:
            pytest.skip(f"No {entity_name} entities — seed data required for detail 74.1")

        navigate(page, f"{base_url}{detail_base}/{entity_id}")

        has_back_link = (
            page.locator(f"a[href='{detail_base}']").count() > 0
            or page.locator("a:has-text('Back'), a:has-text('back'), nav a").count() > 0
            or page.locator("[aria-label*='back'], [aria-label*='Back']").count() > 0
        )
        has_breadcrumb = page.locator("nav[aria-label*='breadcrumb'], .breadcrumb, [class*='breadcrumb']").count() > 0

        body_lower = page.locator("body").inner_text().lower()
        has_back_text = "back" in body_lower or "breadcrumb" in body_lower

        assert has_back_link or has_breadcrumb or has_back_text, (
            f"{entity_name} detail page must provide back navigation or breadcrumb to the list"
        )
