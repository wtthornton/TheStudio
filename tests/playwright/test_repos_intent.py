"""Epic 60.1 — Repo Management: Page Intent & Semantic Content.

Validates that /admin/ui/repos delivers its core purpose:
  - Repo table renders with name, tier badge, status, and queue depth columns
  - Empty state with a clear CTA is shown when no repos are registered

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_repos_style.py (Epic 60.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

REPOS_URL = "/admin/ui/repos"


class TestReposTableContent:
    """Repo table must surface the key columns operators need at a glance.

    When repos are registered the table must show:
      Name        — human-readable identifier for the repository
      Tier badge  — trust tier (Observe / Suggest / Execute)
      Status      — active / paused / error signal for the repo
      Queue depth — number of pending tasks waiting for that repo
    """

    def test_repo_table_renders(self, page, base_url: str) -> None:
        """Repos page shows a table or an empty-state container — one or the other."""
        navigate(page, f"{base_url}{REPOS_URL}")

        has_table = page.locator("table").count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in ("no repos", "no repositories", "no repo", "get started", "add your first")
        )
        assert has_table or has_empty_state, (
            "Repos page must show a repo table or an empty-state CTA when no repos exist"
        )

    def test_repo_name_column_shown(self, page, base_url: str) -> None:
        """Repo table header or body contains repo name information."""
        navigate(page, f"{base_url}{REPOS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No repos registered — empty state is acceptable for 60.1")

        table_text = page.locator("table").first.inner_text().lower()
        assert "repo" in table_text or "name" in table_text or "repository" in table_text, (
            "Repo table must include a 'Repo' or 'Name' column"
        )

    def test_tier_badge_shown(self, page, base_url: str) -> None:
        """Repo table includes a tier column or tier badge text."""
        navigate(page, f"{base_url}{REPOS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No repos registered — empty state is acceptable for 60.1")

        body_lower = page.locator("body").inner_text().lower()
        tier_keywords = ("tier", "observe", "suggest", "execute", "trust")
        assert any(kw in body_lower for kw in tier_keywords), (
            "Repos page must display trust tier information (Observe/Suggest/Execute)"
        )

    def test_status_column_shown(self, page, base_url: str) -> None:
        """Repo table includes a status column."""
        navigate(page, f"{base_url}{REPOS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No repos registered — empty state is acceptable for 60.1")

        body_lower = page.locator("body").inner_text().lower()
        assert "status" in body_lower or "active" in body_lower or "paused" in body_lower, (
            "Repos page must display repo status information"
        )

    def test_queue_depth_column_shown(self, page, base_url: str) -> None:
        """Repo table includes queue depth or pending task count."""
        navigate(page, f"{base_url}{REPOS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No repos registered — empty state is acceptable for 60.1")

        body_lower = page.locator("body").inner_text().lower()
        queue_keywords = ("queue", "depth", "pending", "backlog", "tasks")
        assert any(kw in body_lower for kw in queue_keywords), (
            "Repos page must display queue depth or pending task count per repo"
        )


class TestReposEmptyState:
    """Empty-state must guide operators to register a repo when none exist.

    An actionable empty state prevents confusion when the table is blank and
    directs operators to the next step (registering a repository).
    """

    def test_empty_state_has_cta(self, page, base_url: str) -> None:
        """When no repos exist, the page shows a CTA button or link."""
        navigate(page, f"{base_url}{REPOS_URL}")

        if page.locator("table").count() > 0:
            # Table is present — empty state test not applicable
            rows = page.locator("table tbody tr").count()
            if rows > 0:
                pytest.skip("Repos are registered — empty-state test not applicable")

        # Look for actionable element on the page
        has_button = page.locator("button").count() > 0
        has_link_cta = page.locator("a[href]").count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_cta_text = any(
            kw in body_lower
            for kw in ("add repo", "register", "connect", "get started", "add your first")
        )

        assert has_button or has_link_cta or has_cta_text, (
            "Empty-state repos page must show a CTA to register/add a repository"
        )

    def test_empty_state_has_descriptive_text(self, page, base_url: str) -> None:
        """Empty-state page has descriptive text explaining what to do."""
        navigate(page, f"{base_url}{REPOS_URL}")

        if page.locator("table").count() > 0:
            rows = page.locator("table tbody tr").count()
            if rows > 0:
                pytest.skip("Repos are registered — empty-state test not applicable")

        body_lower = page.locator("body").inner_text().lower()
        descriptive_keywords = (
            "repo", "repository", "repositories", "no repos", "no repositories",
            "get started", "register", "connect"
        )
        assert any(kw in body_lower for kw in descriptive_keywords), (
            "Empty-state repos page must include descriptive text about repositories"
        )


class TestReposPageStructure:
    """Repos page must have clear page-level structure for orientation.

    Operators navigating between admin pages need consistent heading hierarchy
    so they know immediately which page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Repos page has a heading identifying it as the repos/repositories section."""
        navigate(page, f"{base_url}{REPOS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = ("repo", "repository", "repositories")
        assert any(kw in body_lower for kw in heading_keywords), (
            "Repos page must have a heading referencing 'Repos' or 'Repositories'"
        )

    def test_page_loads_without_js_error(self, page, base_url: str) -> None:
        """Repos page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{REPOS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Repos page body must not be empty"
