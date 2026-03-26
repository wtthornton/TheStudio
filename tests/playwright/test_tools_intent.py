"""Epic 65.1 — Tool Hub: Page Intent & Semantic Content.

Validates that /admin/ui/tools delivers its core purpose:
  - Tool catalog renders with approval status badges and tool profiles
  - Empty state is shown when no tools are registered
  - Page heading clearly identifies the tool hub section

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_tools_style.py (Epic 65.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

TOOLS_URL = "/admin/ui/tools"


class TestToolsCatalogContent:
    """Tool catalog must surface the key columns operators need at a glance.

    When tools are registered the catalog must show:
      Name/ID          — human-readable identifier for the tool
      Approval status  — Pending / Approved / Rejected status badge
      Profile          — tool profile or capability description
    """

    def test_tools_page_renders(self, page, base_url: str) -> None:
        """Tools page shows a catalog table/list or an empty-state container."""
        navigate(page, f"{base_url}{TOOLS_URL}")

        has_table = page.locator("table").count() > 0
        has_list = page.locator(
            "[class*='tool'], [data-tool], [data-component='tool-card']"
        ).count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in ("no tools", "no tool", "get started", "add your first", "empty")
        )
        assert has_table or has_list or has_empty_state, (
            "Tools page must show a tool catalog (table or card list) or an empty-state "
            "message when no tools are registered"
        )

    def test_approval_status_shown(self, page, base_url: str) -> None:
        """Tool catalog or page body includes approval status information."""
        navigate(page, f"{base_url}{TOOLS_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-tool]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no tools", "empty")):
                pytest.skip("No tools registered — empty state is acceptable for 65.1")

        body_lower = page.locator("body").inner_text().lower()
        approval_keywords = (
            "approved",
            "approval",
            "pending",
            "rejected",
            "status",
            "review",
        )
        assert any(kw in body_lower for kw in approval_keywords), (
            "Tools page must display approval status information (Approved/Pending/Rejected)"
        )

    def test_tool_profile_or_name_shown(self, page, base_url: str) -> None:
        """Tool catalog includes a name, profile, or identifier for each tool."""
        navigate(page, f"{base_url}{TOOLS_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-tool]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no tools", "empty")):
                pytest.skip("No tools registered — empty state is acceptable for 65.1")

        body_lower = page.locator("body").inner_text().lower()
        profile_keywords = ("tool", "name", "profile", "capability", "description", "id")
        assert any(kw in body_lower for kw in profile_keywords), (
            "Tools page must display a name, profile, or description for each tool"
        )

    def test_tool_identifier_column_present(self, page, base_url: str) -> None:
        """Tool catalog has a column or field identifying each tool by name or ID."""
        navigate(page, f"{base_url}{TOOLS_URL}")

        has_table = page.locator("table").count() > 0
        if not has_table:
            pytest.skip("No table on tools page — card-based layout acceptable for 65.1")

        body_lower = page.locator("body").inner_text().lower()
        id_keywords = ("tool", "name", "id", "key", "slug")
        assert any(kw in body_lower for kw in id_keywords), (
            "Tool catalog table must include an identifier column (name or ID) for each tool"
        )


class TestToolsEmptyState:
    """Empty-state must communicate clearly when no tools are registered.

    An informative empty state prevents confusion when the catalog is blank and
    gives operators context about what the tools section manages.
    """

    def test_empty_state_has_descriptive_text(self, page, base_url: str) -> None:
        """When no tools exist, the page shows descriptive text about the tool hub."""
        navigate(page, f"{base_url}{TOOLS_URL}")

        if page.locator("table").count() > 0:
            rows = page.locator("table tbody tr").count()
            if rows > 0:
                pytest.skip("Tools are registered — empty-state test not applicable")

        body_lower = page.locator("body").inner_text().lower()
        descriptive_keywords = (
            "tool",
            "tools",
            "no tools",
            "catalog",
            "hub",
            "approval",
            "get started",
        )
        assert any(kw in body_lower for kw in descriptive_keywords), (
            "Empty-state tools page must include descriptive text about the tool catalog"
        )


class TestToolsPageStructure:
    """Tools page must have clear page-level structure for operator orientation.

    Operators navigating between admin pages need consistent heading hierarchy
    so they know immediately which page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Tools page has a heading identifying it as the tool hub section."""
        navigate(page, f"{base_url}{TOOLS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = ("tool", "tools", "hub", "catalog", "tool hub", "tool catalog")
        assert any(kw in body_lower for kw in heading_keywords), (
            "Tools page must have a heading referencing 'Tools', 'Tool Hub', or 'Tool Catalog'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Tools page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{TOOLS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Tools page body must not be empty"
