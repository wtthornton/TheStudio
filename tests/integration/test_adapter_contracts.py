"""Adapter contract tests for GitHub and LLM adapters.

Story 9.5 (Epic 9): Verify adapter behavior, retry logic, error classification,
and feature flag switching. Uses respx for HTTP mocking.
"""

import pytest
import respx
from httpx import Response

from src.adapters.github import (
    GitHubAPIError,
    ResilientGitHubClient,
    _classify_error,
)
from src.adapters.llm import (
    AnthropicAdapter,
    LLMRequest,
    MockLLMAdapter,
    get_llm_adapter,
)
from src.admin.model_gateway import ModelClass, ProviderConfig


# --- GitHub Adapter Contract Tests ---


class TestGitHubErrorClassification:
    """Error classification maps HTTP status codes correctly."""

    def test_auth_errors(self):
        assert _classify_error(401) == "auth"
        assert _classify_error(403) == "auth"

    def test_not_found(self):
        assert _classify_error(404) == "not_found"

    def test_validation(self):
        assert _classify_error(422) == "validation"

    def test_rate_limit(self):
        assert _classify_error(429) == "rate_limit"

    def test_server_errors(self):
        assert _classify_error(500) == "server"
        assert _classify_error(502) == "server"
        assert _classify_error(503) == "server"

    def test_unknown(self):
        assert _classify_error(418) == "unknown"


class TestGitHubClientRetry:
    """ResilientGitHubClient retries on 429/500 and fails fast on 401/404."""

    @respx.mock
    async def test_retries_on_rate_limit_then_succeeds(self):
        """Client retries 429 and succeeds on next attempt."""
        route = respx.get("https://api.github.com/repos/acme/repo").mock(
            side_effect=[
                Response(429, json={"message": "rate limited"}),
                Response(200, json={"default_branch": "main"}),
            ]
        )

        async with ResilientGitHubClient("test-token") as client:
            client.BASE_DELAY = 0.01  # Speed up tests
            branch = await client.get_default_branch("acme", "repo")

        assert branch == "main"
        assert route.call_count == 2

    @respx.mock
    async def test_retries_on_server_error_then_succeeds(self):
        """Client retries 500 and succeeds on next attempt."""
        route = respx.get("https://api.github.com/repos/acme/repo").mock(
            side_effect=[
                Response(500, json={"message": "internal error"}),
                Response(200, json={"default_branch": "main"}),
            ]
        )

        async with ResilientGitHubClient("test-token") as client:
            client.BASE_DELAY = 0.01
            branch = await client.get_default_branch("acme", "repo")

        assert branch == "main"
        assert route.call_count == 2

    @respx.mock
    async def test_fails_fast_on_auth_error(self):
        """Client does not retry 401 — fails immediately."""
        respx.get("https://api.github.com/repos/acme/repo").mock(
            return_value=Response(401, json={"message": "bad credentials"})
        )

        async with ResilientGitHubClient("bad-token") as client:
            client.BASE_DELAY = 0.01
            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get_default_branch("acme", "repo")

        assert exc_info.value.error_class == "auth"
        assert exc_info.value.status_code == 401

    @respx.mock
    async def test_fails_fast_on_not_found(self):
        """Client does not retry 404 — fails immediately."""
        respx.get("https://api.github.com/repos/acme/repo").mock(
            return_value=Response(404, json={"message": "not found"})
        )

        async with ResilientGitHubClient("test-token") as client:
            client.BASE_DELAY = 0.01
            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get_default_branch("acme", "repo")

        assert exc_info.value.error_class == "not_found"

    @respx.mock
    async def test_create_pull_request(self):
        """Client can create a pull request."""
        respx.post("https://api.github.com/repos/acme/repo/pulls").mock(
            return_value=Response(
                201,
                json={
                    "number": 42,
                    "html_url": "https://github.com/acme/repo/pull/42",
                    "draft": True,
                },
            )
        )

        async with ResilientGitHubClient("test-token") as client:
            result = await client.create_pull_request(
                "acme", "repo", "Add health check", "Body", "feature/health", "main"
            )

        assert result["number"] == 42
        assert result["draft"] is True

    @respx.mock
    async def test_add_comment(self):
        """Client can add a comment to a PR."""
        respx.post("https://api.github.com/repos/acme/repo/issues/42/comments").mock(
            return_value=Response(201, json={"id": 100, "body": "Evidence"})
        )

        async with ResilientGitHubClient("test-token") as client:
            result = await client.add_comment("acme", "repo", 42, "Evidence")

        assert result["id"] == 100

    @respx.mock
    async def test_exhausts_retries_on_persistent_server_error(self):
        """Client raises after exhausting retries on persistent 500s."""
        respx.get("https://api.github.com/repos/acme/repo").mock(
            return_value=Response(500, json={"message": "broken"})
        )

        async with ResilientGitHubClient("test-token") as client:
            client.BASE_DELAY = 0.01
            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get_default_branch("acme", "repo")

        assert exc_info.value.error_class == "server"


# --- LLM Adapter Contract Tests ---


class TestMockLLMAdapter:
    """MockLLMAdapter returns canned responses."""

    async def test_returns_default_response(self):
        adapter = MockLLMAdapter("test response")
        provider = ProviderConfig(
            "mock-id", "mock", "mock-model", ModelClass.FAST, 0.001
        )
        request = LLMRequest(
            messages=[{"role": "user", "content": "hello"}]
        )

        response = await adapter.complete(provider, request)

        assert response.content == "test response"
        assert response.model == "mock-model"
        assert response.stop_reason == "end_turn"
        assert adapter.call_count == 1

    async def test_tracks_call_count(self):
        adapter = MockLLMAdapter()
        provider = ProviderConfig(
            "mock-id", "mock", "mock-model", ModelClass.FAST, 0.001
        )
        request = LLMRequest(messages=[{"role": "user", "content": "hi"}])

        await adapter.complete(provider, request)
        await adapter.complete(provider, request)

        assert adapter.call_count == 2


class TestAnthropicAdapter:
    """AnthropicAdapter sends correct headers and parses response."""

    @respx.mock
    async def test_sends_correct_headers_and_parses_response(self):
        """Adapter sends API key, version header, and parses content blocks."""
        route = respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(
                200,
                json={
                    "content": [{"type": "text", "text": "Hello from Claude"}],
                    "model": "claude-sonnet-4-5",
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            )
        )

        adapter = AnthropicAdapter(api_key="test-key-123")
        provider = ProviderConfig(
            "anthropic-id", "anthropic", "claude-sonnet-4-5", ModelClass.STRONG, 0.015,
        )
        request = LLMRequest(
            messages=[{"role": "user", "content": "hello"}],
            system="You are helpful.",
        )

        response = await adapter.complete(provider, request)
        await adapter.close()

        assert response.content == "Hello from Claude"
        assert response.model == "claude-sonnet-4-5"
        assert response.tokens_in == 10
        assert response.tokens_out == 5
        assert response.stop_reason == "end_turn"

        # Verify headers
        sent_request = route.calls[0].request
        assert sent_request.headers["x-api-key"] == "test-key-123"
        assert sent_request.headers["anthropic-version"] == "2023-06-01"

    @respx.mock
    async def test_includes_system_prompt_in_body(self):
        """When system prompt is provided, it's included in the request body."""
        route = respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(
                200,
                json={
                    "content": [{"type": "text", "text": "OK"}],
                    "model": "claude-sonnet-4-5",
                    "stop_reason": "end_turn",
                    "usage": {},
                },
            )
        )

        adapter = AnthropicAdapter(api_key="test-key")
        provider = ProviderConfig(
            "anthropic-id", "anthropic", "claude-sonnet-4-5", ModelClass.STRONG, 0.015,
        )
        request = LLMRequest(
            messages=[{"role": "user", "content": "hi"}],
            system="Be concise.",
        )

        await adapter.complete(provider, request)
        await adapter.close()

        import json

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["system"] == "Be concise."
        assert sent_body["model"] == "claude-sonnet-4-5"


class TestAdapterFactoryFlags:
    """Feature flags return correct adapter implementations."""

    def test_get_llm_adapter_mock(self, monkeypatch):
        """Default 'mock' flag returns MockLLMAdapter."""
        monkeypatch.setenv("THESTUDIO_LLM_PROVIDER", "mock")
        # Force settings reload
        from src.settings import Settings

        monkeypatch.setattr("src.adapters.llm.settings", Settings())
        adapter = get_llm_adapter()
        assert isinstance(adapter, MockLLMAdapter)

    def test_get_llm_adapter_anthropic(self, monkeypatch):
        """'anthropic' flag returns AnthropicAdapter."""
        monkeypatch.setenv("THESTUDIO_LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("THESTUDIO_ANTHROPIC_API_KEY", "test-key")
        from src.settings import Settings

        monkeypatch.setattr("src.adapters.llm.settings", Settings())
        adapter = get_llm_adapter()
        assert isinstance(adapter, AnthropicAdapter)

    def test_get_github_client_mock(self, monkeypatch):
        """Default 'mock' flag returns the basic GitHubClient."""
        monkeypatch.setenv("THESTUDIO_GITHUB_PROVIDER", "mock")
        from src.adapters.github import get_github_client
        from src.publisher.github_client import GitHubClient
        from src.settings import Settings

        monkeypatch.setattr("src.adapters.github.settings", Settings())
        client = get_github_client("test-token")
        assert isinstance(client, GitHubClient)

    def test_get_github_client_real(self, monkeypatch):
        """'real' flag returns ResilientGitHubClient."""
        monkeypatch.setenv("THESTUDIO_GITHUB_PROVIDER", "real")
        from src.adapters.github import get_github_client
        from src.settings import Settings

        monkeypatch.setattr("src.adapters.github.settings", Settings())
        client = get_github_client("test-token")
        assert isinstance(client, ResilientGitHubClient)
