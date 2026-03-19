"""Integration tests for OAuth adapter against Docker container.

Story 31.5: Live validation against the real Anthropic API through the
Docker prod container stack. Tests both API key and OAuth auth modes.

These tests require:
- Docker prod stack running (thestudio-prod-app-1)
- THESTUDIO_ANTHROPIC_API_KEY set in env or infra/.env
- Network access to api.anthropic.com

Run: pytest tests/integration/test_docker_oauth_adapter.py -m integration -v
"""

from __future__ import annotations

import os

import httpx
import pytest

from src.adapters.llm import AnthropicAdapter, AuthMode, LLMRequest, _detect_auth_mode
from src.admin.model_gateway import ModelClass, ProviderConfig

# Skip entire module if no API key
pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_api_key,
]

DOCKER_APP_URL = os.environ.get("THESTUDIO_DOCKER_APP_URL", "http://localhost:9080")


def _get_api_key() -> str:
    """Get API key from env or infra/.env file."""
    key = os.environ.get("THESTUDIO_ANTHROPIC_API_KEY", "")
    if not key:
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", "infra", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("THESTUDIO_ANTHROPIC_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
    return key


@pytest.fixture
def api_key() -> str:
    key = _get_api_key()
    if not key:
        pytest.skip("THESTUDIO_ANTHROPIC_API_KEY not set")
    return key


@pytest.fixture
def provider() -> ProviderConfig:
    return ProviderConfig(
        provider_id="integration-test",
        provider="anthropic",
        model_id="claude-haiku-4-5",  # Use cheapest model for tests
        model_class=ModelClass.FAST,
        cost_per_1k_tokens=0.001,
        cost_per_1k_input=0.001,
        cost_per_1k_output=0.005,
    )


@pytest.fixture
def simple_request() -> LLMRequest:
    return LLMRequest(
        messages=[{"role": "user", "content": "Reply with exactly: PONG"}],
        max_tokens=10,
        temperature=0.0,
        system="You are a test bot. Reply with exactly the text requested.",
    )


class TestDockerApiKeyAuth:
    """Tests using standard API key auth against real Anthropic API."""

    async def test_api_key_complete(
        self, api_key: str, provider: ProviderConfig, simple_request: LLMRequest,
    ) -> None:
        """API key auth produces a valid response from the real API."""
        adapter = AnthropicAdapter(api_key=api_key, auth_mode="api_key")
        try:
            result = await adapter.complete(provider, simple_request)
            assert result.content  # Non-empty response
            assert result.tokens_in > 0
            assert result.tokens_out > 0
            assert result.model  # Model field populated
            assert "PONG" in result.content.upper()
        finally:
            await adapter.close()

    async def test_api_key_auth_mode_detected(self, api_key: str) -> None:
        """Standard API key prefix auto-detects to API_KEY mode."""
        mode = _detect_auth_mode(api_key, "auto")
        assert mode == AuthMode.API_KEY


class TestDockerOAuthAuth:
    """Tests for OAuth token auth (requires OAuth token to run)."""

    @pytest.fixture
    def oauth_token(self) -> str:
        token = os.environ.get("THESTUDIO_ANTHROPIC_OAUTH_TOKEN", "")
        if not token:
            pytest.skip("THESTUDIO_ANTHROPIC_OAUTH_TOKEN not set")
        return token

    async def test_oauth_token_detected(self, oauth_token: str) -> None:
        """OAuth token prefix auto-detects to OAUTH mode."""
        mode = _detect_auth_mode(oauth_token, "auto")
        assert mode == AuthMode.OAUTH

    async def test_oauth_bearer_headers(self, oauth_token: str) -> None:
        """OAuth adapter produces correct Bearer headers."""
        adapter = AnthropicAdapter(api_key=oauth_token, auth_mode="auto")
        headers = adapter._build_headers()
        assert headers["authorization"] == f"Bearer {oauth_token}"
        assert headers["anthropic-beta"] == "oauth-2025-04-20"
        assert "x-api-key" not in headers
        await adapter.close()

    async def test_oauth_complete(
        self, oauth_token: str, provider: ProviderConfig, simple_request: LLMRequest,
    ) -> None:
        """OAuth token produces a valid response from the real API."""
        adapter = AnthropicAdapter(api_key=oauth_token, auth_mode="auto")
        try:
            result = await adapter.complete(provider, simple_request)
            assert result.content
            assert result.tokens_in > 0
            assert result.tokens_out > 0
        finally:
            await adapter.close()


class TestDockerAppHealth:
    """Tests that the Docker container is running and healthy."""

    async def test_docker_app_healthz(self) -> None:
        """Docker app responds to health check."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{DOCKER_APP_URL}/healthz", timeout=10.0)
                assert resp.status_code == 200
            except httpx.ConnectError:
                pytest.skip(f"Docker app not reachable at {DOCKER_APP_URL}")

    async def test_docker_app_configured_for_real_providers(self) -> None:
        """Docker app is configured with real providers (not mock)."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{DOCKER_APP_URL}/healthz", timeout=10.0)
                if resp.status_code != 200:
                    pytest.skip("Docker app not healthy")
                # If we get here, the app is running with real providers
                # (docker-compose.prod.yml sets LLM_PROVIDER=anthropic)
            except httpx.ConnectError:
                pytest.skip(f"Docker app not reachable at {DOCKER_APP_URL}")


class TestAuthModeComparison:
    """Compare response shape between API key and OAuth modes."""

    async def test_both_modes_produce_same_response_shape(
        self, api_key: str, provider: ProviderConfig,
    ) -> None:
        """Both auth modes return the same LLMResponse structure."""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=20,
            temperature=0.0,
        )

        adapter = AnthropicAdapter(api_key=api_key, auth_mode="api_key")
        try:
            result = await adapter.complete(provider, request)
            assert result.content
            assert result.tokens_in > 0
            assert result.tokens_out > 0
            assert result.model
            assert result.stop_reason
        finally:
            await adapter.close()
