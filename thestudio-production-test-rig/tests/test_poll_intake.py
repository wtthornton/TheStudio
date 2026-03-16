"""Poll intake tests — config and E2E poll cycle.

Requires deployment with THESTUDIO_INTAKE_POLL_ENABLED=true.
Poll E2E additionally requires THESTUDIO_POLL_TEST_REPO env var.
"""

import os

import httpx
import pytest


class TestPollConfig:
    """Poll intake config (Epic 17 — Admin API)."""

    def test_profile_update_accepts_poll_config(
        self,
        http_client: httpx.Client,
    ) -> None:
        """Register repo, PATCH profile with poll_enabled, GET to verify."""
        owner = "test-poll-org"
        repo_name = "test-poll-repo"
        payload = {
            "owner": owner,
            "repo": repo_name,
            "installation_id": 99999,
            "default_branch": "main",
        }
        r = http_client.post("/admin/repos", json=payload)
        assert r.status_code in (201, 409), f"Register failed: {r.status_code} {r.text}"
        data = r.json()
        if r.status_code == 201:
            repo_id = data["id"]
        else:
            list_r = http_client.get("/admin/repos")
            assert list_r.status_code == 200, f"List repos failed: {list_r.status_code}"
            repos = [
                p
                for p in list_r.json()["repos"]
                if p["owner"] == owner and p["repo"] == repo_name
            ]
            assert repos, f"Repo {owner}/{repo_name} not found after 409"
            repo_id = repos[0]["id"]

        r2 = http_client.patch(
            f"/admin/repos/{repo_id}/profile",
            json={"poll_enabled": True, "poll_interval_minutes": 15},
        )
        assert r2.status_code == 200, f"Profile update failed: {r2.status_code} {r2.text}"
        upd = r2.json()
        assert "poll_enabled" in upd.get("updated_fields", [])
        assert "poll_interval_minutes" in upd.get("updated_fields", [])

        r3 = http_client.get(f"/admin/repos/{repo_id}")
        assert r3.status_code == 200, f"Get repo failed: {r3.status_code} {r3.text}"
        detail = r3.json()
        assert detail.get("poll_enabled") is True
        assert detail.get("poll_interval_minutes") == 15

        # Cleanup
        http_client.patch(
            f"/admin/repos/{repo_id}/profile",
            json={"poll_enabled": False},
        )


class TestPollE2E:
    """Poll intake E2E — real GitHub API, no webhook."""

    @pytest.fixture
    def poll_test_repo(self) -> str:
        """owner/repo for poll E2E — set THESTUDIO_POLL_TEST_REPO or use default."""
        return os.environ.get(
            "THESTUDIO_POLL_TEST_REPO",
            "wtthornton/TheStudio",
        )

    def test_poll_run_fetches_issues(
        self,
        http_client: httpx.Client,
        poll_test_repo: str,
    ) -> None:
        """Register real repo, enable poll, trigger poll/run, verify GitHub fetch."""
        parts = poll_test_repo.split("/", 1)
        assert len(parts) == 2, f"THESTUDIO_POLL_TEST_REPO must be owner/repo, got {poll_test_repo}"
        owner, repo_name = parts

        payload = {
            "owner": owner,
            "repo": repo_name,
            "installation_id": 99999,
            "default_branch": "main",
        }
        r = http_client.post("/admin/repos", json=payload)
        assert r.status_code in (201, 409), f"Register failed: {r.status_code} {r.text}"
        data = r.json()
        if r.status_code == 201:
            repo_id = data["id"]
        else:
            list_r = http_client.get("/admin/repos")
            assert list_r.status_code == 200
            repos = [
                p
                for p in list_r.json()["repos"]
                if p["owner"] == owner and p["repo"] == repo_name
            ]
            assert repos, f"Repo {owner}/{repo_name} not found"
            repo_id = repos[0]["id"]

        http_client.patch(
            f"/admin/repos/{repo_id}/profile",
            json={"poll_enabled": True, "poll_interval_minutes": 15},
        )

        r_run = http_client.post("/admin/poll/run")
        assert r_run.status_code == 200, f"Poll run failed: {r_run.status_code} {r_run.text}"
        result = r_run.json()
        assert "repos_polled" in result
        assert "issues_created" in result
        assert "rate_limit_hit" in result
        assert result["repos_polled"] >= 0
        assert result["rate_limit_hit"] is False, "GitHub rate limit hit during poll"

        # Cleanup
        http_client.patch(
            f"/admin/repos/{repo_id}/profile",
            json={"poll_enabled": False},
        )
