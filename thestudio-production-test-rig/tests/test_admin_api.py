"""Admin API tests — fleet health, repo registration, profile updates.

Contract: /admin/health, /admin/repos (POST/GET), /admin/repos/{id} (GET),
/admin/repos/{id}/profile (PATCH), /docs.
"""

import httpx


class TestAdminHealth:
    """Fleet health (admin API)."""

    def test_admin_health_returns_200(self, http_client: httpx.Client) -> None:
        r = http_client.get("/admin/health")
        assert r.status_code == 200
        data = r.json()
        assert "overall_status" in data


class TestOpenAPI:
    """Docs endpoint."""

    def test_docs_returns_200(self, http_client: httpx.Client) -> None:
        r = http_client.get("/docs")
        assert r.status_code == 200


class TestRepoRegistration:
    """Repo CRUD via admin API (standalone, not poll-specific)."""

    TEST_OWNER = "test-admin-org"
    TEST_REPO = "test-admin-repo"

    def _register_or_find(self, http_client: httpx.Client) -> str:
        """Register a test repo and return its ID (idempotent)."""
        payload = {
            "owner": self.TEST_OWNER,
            "repo": self.TEST_REPO,
            "installation_id": 88888,
            "default_branch": "main",
        }
        r = http_client.post("/admin/repos", json=payload)
        assert r.status_code in (201, 409), f"Register failed: {r.status_code} {r.text}"
        if r.status_code == 201:
            return r.json()["id"]
        # 409 — already exists, find it
        list_r = http_client.get("/admin/repos")
        assert list_r.status_code == 200
        repos = [
            p for p in list_r.json()["repos"]
            if p["owner"] == self.TEST_OWNER and p["repo"] == self.TEST_REPO
        ]
        assert repos, f"Repo {self.TEST_OWNER}/{self.TEST_REPO} not found after 409"
        return repos[0]["id"]

    def test_repo_registration_returns_201_or_409(
        self, http_client: httpx.Client
    ) -> None:
        """POST /admin/repos creates or reports conflict."""
        payload = {
            "owner": self.TEST_OWNER,
            "repo": self.TEST_REPO,
            "installation_id": 88888,
            "default_branch": "main",
        }
        r = http_client.post("/admin/repos", json=payload)
        assert r.status_code in (201, 409)

    def test_repo_list_returns_repos(self, http_client: httpx.Client) -> None:
        """GET /admin/repos returns list with repos key."""
        self._register_or_find(http_client)
        r = http_client.get("/admin/repos")
        assert r.status_code == 200
        data = r.json()
        assert "repos" in data
        assert isinstance(data["repos"], list)

    def test_repo_detail_returns_profile(self, http_client: httpx.Client) -> None:
        """GET /admin/repos/{id} returns repo detail."""
        repo_id = self._register_or_find(http_client)
        r = http_client.get(f"/admin/repos/{repo_id}")
        assert r.status_code == 200
        detail = r.json()
        assert detail.get("owner") == self.TEST_OWNER
        assert detail.get("repo") == self.TEST_REPO

    def test_repo_profile_patch(self, http_client: httpx.Client) -> None:
        """PATCH /admin/repos/{id}/profile updates fields and verifies."""
        repo_id = self._register_or_find(http_client)

        r = http_client.patch(
            f"/admin/repos/{repo_id}/profile",
            json={"poll_enabled": False},
        )
        assert r.status_code == 200
        upd = r.json()
        assert "poll_enabled" in upd.get("updated_fields", [])

        r2 = http_client.get(f"/admin/repos/{repo_id}")
        assert r2.status_code == 200
        assert r2.json().get("poll_enabled") is False
