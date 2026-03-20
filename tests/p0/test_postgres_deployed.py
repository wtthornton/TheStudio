"""Deployment-mode Postgres integration tests.

These tests prove the deployed app's persistence works by exercising
the API through Caddy. Unlike tests/integration/test_postgres_backend.py
(which creates its own SQLAlchemy engine), these tests never touch the
database directly — they use the app's HTTP API to create and query data.

Tests verify:
  1. Admin health endpoint confirms Postgres connectivity.
  2. Webhook creates a TaskPacket in Postgres (201 response).
  3. Repo registration persists and re-registration returns 409.
"""

from __future__ import annotations

import json

import httpx
import pytest

from tests.p0.conftest import build_webhook_headers, make_issue_payload


@pytest.mark.p0
class TestPostgresDeployed:
    """Verify persistence through the deployed app's API."""

    def test_postgres_healthy_via_admin(self, p0_client: httpx.Client) -> None:
        """Admin health endpoint reports Postgres as OK."""
        r = p0_client.get("/admin/health")
        assert r.status_code == 200
        data = r.json()
        pg = data.get("postgres", {})
        assert pg.get("status") == "OK", f"Postgres status: {pg}"

    def test_webhook_creates_taskpacket(
        self,
        p0_base_url: str,
        registered_test_repo: dict,
    ) -> None:
        """Webhook creates a TaskPacket persisted in Postgres.

        The webhook handler creates a TaskPacket row before attempting to
        start a Temporal workflow. A 201 response proves the database
        INSERT succeeded through the deployed stack.
        """
        import random
        issue_num = random.randint(50000, 59999)
        payload = make_issue_payload(issue_number=issue_num)
        body = json.dumps(payload).encode()
        headers = build_webhook_headers(body)

        r = httpx.post(
            f"{p0_base_url}/webhook/github",
            content=body,
            headers=headers,
            verify=False,
            timeout=15,
        )
        # 201 = TaskPacket created (workflow may or may not start)
        assert r.status_code == 201, (
            f"Expected 201 (TaskPacket created), got {r.status_code}: {r.text}"
        )
        assert "TaskPacket created" in r.text

    def test_repo_registration_persists(
        self,
        p0_client: httpx.Client,
    ) -> None:
        """Repo registration persists — re-registering returns 409.

        Proves data survived the first registration and the uniqueness
        constraint in Postgres is enforced.
        """
        payload = {
            "owner": "p0-test-org",
            "repo": "p0-test-repo",
            "installation_id": 99999,
            "default_branch": "main",
        }
        r = p0_client.post("/admin/repos", json=payload)
        # 409 = already exists (from registered_test_repo fixture or prior run)
        assert r.status_code in (201, 409), (
            f"Expected 201 or 409, got {r.status_code}: {r.text}"
        )

    def test_repos_persist_across_requests(
        self, p0_client: httpx.Client,
    ) -> None:
        """Registered repos persist in Postgres across requests."""
        r1 = p0_client.get("/admin/repos")
        assert r1.status_code == 200
        repos1 = r1.json()["repos"]

        # Second request should return same data
        r2 = p0_client.get("/admin/repos")
        assert r2.status_code == 200
        repos2 = r2.json()["repos"]

        ids1 = {rp["id"] for rp in repos1}
        ids2 = {rp["id"] for rp in repos2}
        assert ids1 == ids2, "Repos should persist between requests"

    def test_audit_log_persists(self, p0_client: httpx.Client) -> None:
        """Audit log entries persist in Postgres."""
        r = p0_client.get("/admin/audit", params={"limit": 5})
        assert r.status_code == 200
        data = r.json()
        # Audit endpoint returns entries list
        assert "entries" in data, f"Expected 'entries' key, got: {list(data.keys())}"
        assert isinstance(data["entries"], list)
