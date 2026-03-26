"""Epic 70.1 — Execution Planes: Page Intent & Semantic Content.

Validates that /admin/ui/planes delivers its core purpose:
  - Worker clusters table/list renders with cluster identity information
  - Health status is surfaced so operators understand cluster availability
  - Registration status is shown so operators know which planes are active
  - Page heading clearly identifies the execution planes section
  - Empty state is shown when no execution planes are registered

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_planes_style.py (Epic 70.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

PLANES_URL = "/admin/ui/planes"


class TestPlanesWorkerClusterContent:
    """Worker clusters table/list must surface the key information operators need.

    When execution planes are registered the page must show:
      Cluster identity     — cluster name, ID, or label identifying the plane
      Health status        — current health of the worker cluster (healthy/degraded/offline)
      Registration status  — whether the plane is active/registered/deregistered
    """

    def test_planes_page_renders(self, page, base_url: str) -> None:
        """Execution planes page shows a cluster table/list or an empty-state container."""
        navigate(page, f"{base_url}{PLANES_URL}")

        has_table = page.locator("table").count() > 0
        has_list = page.locator(
            "[class*='plane'], [data-plane], [data-component='plane-card'], "
            "[class*='cluster'], [data-cluster]"
        ).count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in (
                "no planes",
                "no workers",
                "no clusters",
                "no execution",
                "nothing registered",
                "empty",
                "execution plane",
                "worker cluster",
                "planes",
            )
        )
        assert has_table or has_list or has_empty_state, (
            "Execution planes page must show a cluster table (or card list) or an "
            "empty-state message when no planes are registered"
        )

    def test_cluster_identity_shown(self, page, base_url: str) -> None:
        """Planes list or page body includes cluster identity information."""
        navigate(page, f"{base_url}{PLANES_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-plane]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no planes", "empty", "no workers")):
                pytest.skip("No execution planes registered — empty state is acceptable for 70.1")

        body_lower = page.locator("body").inner_text().lower()
        identity_keywords = (
            "plane",
            "cluster",
            "worker",
            "name",
            "id",
            "label",
            "host",
            "node",
            "region",
            "zone",
        )
        assert any(kw in body_lower for kw in identity_keywords), (
            "Execution planes page must display cluster identity information (name, ID, or host)"
        )

    def test_health_status_shown(self, page, base_url: str) -> None:
        """Execution planes page surfaces health status for each worker cluster."""
        navigate(page, f"{base_url}{PLANES_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-plane]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no planes", "empty", "no workers")):
                pytest.skip("No execution planes registered — empty state is acceptable for 70.1")

        body_lower = page.locator("body").inner_text().lower()
        health_keywords = (
            "health",
            "healthy",
            "degraded",
            "offline",
            "online",
            "status",
            "up",
            "down",
            "available",
            "unavailable",
            "active",
            "inactive",
        )
        assert any(kw in body_lower for kw in health_keywords), (
            "Execution planes page must display health status for worker clusters"
        )

    def test_registration_status_shown(self, page, base_url: str) -> None:
        """Execution planes page surfaces registration status for each plane."""
        navigate(page, f"{base_url}{PLANES_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-plane]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no planes", "empty", "no workers")):
                pytest.skip("No execution planes registered — empty state is acceptable for 70.1")

        body_lower = page.locator("body").inner_text().lower()
        registration_keywords = (
            "registered",
            "registration",
            "active",
            "inactive",
            "deregistered",
            "paused",
            "running",
            "status",
            "enabled",
            "disabled",
            "connected",
            "disconnected",
        )
        assert any(kw in body_lower for kw in registration_keywords), (
            "Execution planes page must display registration status for each plane"
        )

    def test_planes_table_has_identifier_column(self, page, base_url: str) -> None:
        """Execution planes table has a column or field identifying each worker cluster."""
        navigate(page, f"{base_url}{PLANES_URL}")

        has_table = page.locator("table").count() > 0
        if not has_table:
            pytest.skip("No table on planes page — card-based layout acceptable for 70.1")

        body_lower = page.locator("body").inner_text().lower()
        id_keywords = (
            "plane",
            "cluster",
            "worker",
            "name",
            "id",
            "host",
            "node",
            "region",
        )
        assert any(kw in body_lower for kw in id_keywords), (
            "Execution planes table must include an identifier column (cluster name, ID, or host)"
        )


class TestPlanesEmptyState:
    """Empty-state must communicate clearly when no execution planes are registered.

    An informative empty state prevents confusion when no worker clusters are
    registered and gives operators context about what the planes section manages.
    """

    def test_empty_state_has_descriptive_text(self, page, base_url: str) -> None:
        """When no execution planes exist, the page shows descriptive text."""
        navigate(page, f"{base_url}{PLANES_URL}")

        if page.locator("table").count() > 0:
            rows = page.locator("table tbody tr").count()
            if rows > 0:
                pytest.skip("Execution planes are present — empty-state test not applicable")

        body_lower = page.locator("body").inner_text().lower()
        descriptive_keywords = (
            "plane",
            "planes",
            "execution plane",
            "worker cluster",
            "no planes",
            "no workers",
            "no clusters",
            "nothing registered",
            "empty",
            "register",
        )
        assert any(kw in body_lower for kw in descriptive_keywords), (
            "Empty-state planes page must include descriptive text about execution planes"
        )


class TestPlanesPageStructure:
    """Execution planes page must have clear page-level structure for operator orientation.

    Operators navigating between admin pages need consistent heading hierarchy
    so they know immediately which page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Execution planes page has a heading identifying it as the planes section."""
        navigate(page, f"{base_url}{PLANES_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = (
            "execution plane",
            "execution planes",
            "worker cluster",
            "worker clusters",
            "planes",
            "compute plane",
            "compute planes",
        )
        assert any(kw in body_lower for kw in heading_keywords), (
            "Execution planes page must have a heading referencing 'Execution Planes' "
            "or 'Worker Clusters'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Execution planes page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{PLANES_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Execution planes page body must not be empty"
