"""Tests for GitHub REST API adapter with retry logic (Story 8.6)."""

import pytest
import httpx

from src.adapters.github import (
    ResilientGitHubClient,
    GitHubAPIError,
    _classify_error,
    get_github_client,
)


class TestClassifyError:
    def test_auth_errors(self) -> None:
        assert _classify_error(401) == "auth"
        assert _classify_error(403) == "auth"

    def test_not_found(self) -> None:
        assert _classify_error(404) == "not_found"

    def test_validation(self) -> None:
        assert _classify_error(422) == "validation"

    def test_rate_limit(self) -> None:
        assert _classify_error(429) == "rate_limit"

    def test_server_errors(self) -> None:
        assert _classify_error(500) == "server"
        assert _classify_error(502) == "server"
        assert _classify_error(503) == "server"

    def test_unknown(self) -> None:
        assert _classify_error(400) == "unknown"


class TestResilientGitHubClient:
    @pytest.fixture
    def mock_github(self) -> tuple[ResilientGitHubClient, list[httpx.Request]]:
        """Create a client with a recording mock transport."""
        requests: list[httpx.Request] = []

        def make_client(
            responses: list[httpx.Response],
        ) -> ResilientGitHubClient:
            call_idx = 0

            async def handler(request: httpx.Request) -> httpx.Response:
                nonlocal call_idx
                requests.append(request)
                resp = responses[min(call_idx, len(responses) - 1)]
                call_idx += 1
                return resp

            client = ResilientGitHubClient("test-token")
            client._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler),
                base_url="https://api.github.com",
                headers=dict(client._client.headers),
            )
            return client

        # Return factory and requests list
        return make_client, requests  # type: ignore[return-value]

    async def test_create_pull_request(self, mock_github: tuple) -> None:
        make_client, requests = mock_github
        pr_response = {"number": 42, "html_url": "https://github.com/o/r/pull/42"}
        client = make_client([httpx.Response(201, json=pr_response)])

        result = await client.create_pull_request(
            "owner", "repo", "Title", "Body", "feature", "main",
        )
        assert result["number"] == 42
        assert len(requests) == 1
        assert b'"title":"Title"' in requests[0].content

    async def test_add_comment(self, mock_github: tuple) -> None:
        make_client, requests = mock_github
        client = make_client([httpx.Response(201, json={"id": 1, "body": "test"})])

        result = await client.add_comment("owner", "repo", 42, "Test comment")
        assert result["body"] == "test"

    async def test_add_labels(self, mock_github: tuple) -> None:
        make_client, requests = mock_github
        client = make_client([
            httpx.Response(200, json=[{"name": "bug"}, {"name": "urgent"}]),
        ])

        result = await client.add_labels("owner", "repo", 42, ["bug", "urgent"])
        assert len(result) == 2

    async def test_auth_error_fails_immediately(self, mock_github: tuple) -> None:
        make_client, requests = mock_github
        client = make_client([
            httpx.Response(401, json={"message": "Bad credentials"}),
        ])

        with pytest.raises(GitHubAPIError) as exc_info:
            await client.create_pull_request(
                "owner", "repo", "Title", "Body", "feature", "main",
            )
        assert exc_info.value.error_class == "auth"
        assert len(requests) == 1  # No retries for auth errors

    async def test_not_found_fails_immediately(self, mock_github: tuple) -> None:
        make_client, requests = mock_github
        client = make_client([
            httpx.Response(404, json={"message": "Not Found"}),
        ])

        with pytest.raises(GitHubAPIError) as exc_info:
            await client.get_default_branch("owner", "nonexistent")
        assert exc_info.value.error_class == "not_found"
        assert len(requests) == 1

    async def test_rate_limit_retries(self, mock_github: tuple) -> None:
        make_client, requests = mock_github
        # Override delay for fast tests
        client = make_client([
            httpx.Response(429, json={"message": "Rate limited"}),
            httpx.Response(200, json={"default_branch": "main"}),
        ])
        client.BASE_DELAY = 0.01  # Fast retries for tests

        result = await client.get_default_branch("owner", "repo")
        assert result == "main"
        assert len(requests) == 2  # Retried once

    async def test_server_error_retries(self, mock_github: tuple) -> None:
        make_client, requests = mock_github
        client = make_client([
            httpx.Response(502, json={"message": "Bad Gateway"}),
            httpx.Response(502, json={"message": "Bad Gateway"}),
            httpx.Response(200, json={"object": {"sha": "abc123"}}),
        ])
        client.BASE_DELAY = 0.01

        result = await client.get_branch_sha("owner", "repo", "main")
        assert result == "abc123"
        assert len(requests) == 3

    async def test_max_retries_exceeded(self, mock_github: tuple) -> None:
        make_client, requests = mock_github
        client = make_client([
            httpx.Response(500, json={"message": "Internal Server Error"}),
            httpx.Response(500, json={"message": "Internal Server Error"}),
            httpx.Response(500, json={"message": "Internal Server Error"}),
            httpx.Response(500, json={"message": "Internal Server Error"}),
        ])
        client.BASE_DELAY = 0.01

        with pytest.raises(GitHubAPIError) as exc_info:
            await client.get_default_branch("owner", "repo")
        assert exc_info.value.error_class == "server"
        assert len(requests) == 4  # 1 initial + 3 retries

    async def test_auth_headers_sent(self, mock_github: tuple) -> None:
        make_client, requests = mock_github
        client = make_client([httpx.Response(200, json={"default_branch": "main"})])

        await client.get_default_branch("owner", "repo")
        assert requests[0].headers["authorization"] == "Bearer test-token"
        assert requests[0].headers["x-github-api-version"] == "2022-11-28"


class TestGetGitHubClient:
    def test_default_returns_original_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.adapters.github.settings.github_provider", "mock")
        from src.publisher.github_client import GitHubClient
        client = get_github_client("test-token")
        assert isinstance(client, GitHubClient)

    def test_real_flag_returns_resilient(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.adapters.github.settings.github_provider", "real")
        client = get_github_client("test-token")
        assert isinstance(client, ResilientGitHubClient)
