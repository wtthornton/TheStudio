"""Tests for LLM provider adapters (Story 8.5, Epic 31).

Story 8.5: Basic adapter tests
Story 31.2: OAuth token auto-detection and Bearer header tests
Story 31.3: Token refresh on 401 tests
Story 31.4: Explicit auth mode override tests
"""

import json

import httpx
import pytest

from src.adapters.llm import (
    AnthropicAdapter,
    AuthMode,
    LLMRequest,
    LLMResponse,
    MockLLMAdapter,
    _detect_auth_mode,
    get_llm_adapter,
)
from src.admin.model_gateway import ModelClass, ProviderConfig


def _success_response(model: str = "claude-sonnet-4-6") -> dict:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": "Hello!"}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


@pytest.fixture
def provider() -> ProviderConfig:
    return ProviderConfig(
        provider_id="test-provider",
        provider="anthropic",
        model_id="claude-sonnet-4-6",
        model_class=ModelClass.BALANCED,
        cost_per_1k_tokens=0.003,
    )


@pytest.fixture
def request_msg() -> LLMRequest:
    return LLMRequest(
        messages=[{"role": "user", "content": "Hello, Claude!"}],
        max_tokens=1024,
        temperature=0.0,
    )


class TestMockLLMAdapter:
    async def test_returns_canned_response(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        adapter = MockLLMAdapter(default_response="Test response")
        result = await adapter.complete(provider, request_msg)
        assert result.content == "Test response"
        assert result.model == "claude-sonnet-4-6"
        assert result.stop_reason == "end_turn"

    async def test_tracks_call_count(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        adapter = MockLLMAdapter()
        assert adapter.call_count == 0
        await adapter.complete(provider, request_msg)
        await adapter.complete(provider, request_msg)
        assert adapter.call_count == 2

    async def test_estimates_tokens(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        adapter = MockLLMAdapter()
        result = await adapter.complete(provider, request_msg)
        assert result.tokens_in > 0
        assert result.tokens_out > 0

    async def test_close_is_noop(self) -> None:
        adapter = MockLLMAdapter()
        await adapter.close()  # Should not raise


class TestAnthropicAdapter:
    async def test_sends_correct_request_shape(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        """Test that the adapter sends the correct request to Anthropic API."""
        captured_request: httpx.Request | None = None

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_request
            captured_request = request
            return httpx.Response(200, json=_success_response())

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(api_key="test-key", auth_mode="api_key")
        adapter._client = httpx.AsyncClient(transport=transport)

        result = await adapter.complete(provider, request_msg)

        assert captured_request is not None
        assert captured_request.url == AnthropicAdapter.API_URL
        assert captured_request.headers["x-api-key"] == "test-key"
        assert captured_request.headers["anthropic-version"] == "2023-06-01"

        body = json.loads(captured_request.content)
        assert body["model"] == "claude-sonnet-4-6"
        assert body["max_tokens"] == 1024
        assert body["messages"] == [{"role": "user", "content": "Hello, Claude!"}]

    async def test_parses_response(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-sonnet-4-6",
                    "content": [{"type": "text", "text": "Response text"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 15, "output_tokens": 8},
                },
            )

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(api_key="test-key", auth_mode="api_key")
        adapter._client = httpx.AsyncClient(transport=transport)

        result = await adapter.complete(provider, request_msg)
        assert result.content == "Response text"
        assert result.tokens_in == 15
        assert result.tokens_out == 8
        assert result.model == "claude-sonnet-4-6"
        assert result.stop_reason == "end_turn"

    async def test_includes_system_prompt(
        self, provider: ProviderConfig,
    ) -> None:
        request_with_system = LLMRequest(
            messages=[{"role": "user", "content": "Hi"}],
            system="You are helpful.",
        )
        captured_body: dict | None = None

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            captured_body = json.loads(request.content)
            return httpx.Response(200, json=_success_response())

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(api_key="test-key", auth_mode="api_key")
        adapter._client = httpx.AsyncClient(transport=transport)

        await adapter.complete(provider, request_with_system)
        assert captured_body is not None
        assert captured_body["system"] == "You are helpful."

    async def test_raises_on_api_error(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": {"message": "Invalid API key"}})

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(api_key="bad-key", auth_mode="api_key")
        adapter._client = httpx.AsyncClient(transport=transport)

        with pytest.raises(httpx.HTTPStatusError):
            await adapter.complete(provider, request_msg)

    async def test_handles_multi_block_response(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-sonnet-4-6",
                    "content": [
                        {"type": "text", "text": "Part 1. "},
                        {"type": "text", "text": "Part 2."},
                    ],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 8},
                },
            )

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(api_key="test-key", auth_mode="api_key")
        adapter._client = httpx.AsyncClient(transport=transport)

        result = await adapter.complete(provider, request_msg)
        assert result.content == "Part 1. Part 2."


# --------------------------------------------------------------------------
# Story 31.2: OAuth auto-detection tests
# --------------------------------------------------------------------------


class TestAuthModeDetection:
    def test_oauth_prefix_detected(self) -> None:
        assert _detect_auth_mode("sk-ant-oat01-abc123", "auto") == AuthMode.OAUTH

    def test_api_key_prefix_detected(self) -> None:
        assert _detect_auth_mode("sk-ant-api03-xyz789", "auto") == AuthMode.API_KEY

    def test_unrecognized_prefix_falls_back_to_api_key(self) -> None:
        assert _detect_auth_mode("some-random-key", "auto") == AuthMode.API_KEY

    def test_explicit_override_api_key(self) -> None:
        assert _detect_auth_mode("sk-ant-oat01-abc123", "api_key") == AuthMode.API_KEY

    def test_explicit_override_oauth(self) -> None:
        assert _detect_auth_mode("sk-ant-api03-xyz789", "oauth") == AuthMode.OAUTH

    def test_explicit_override_auto(self) -> None:
        assert _detect_auth_mode("sk-ant-oat01-abc123", "auto") == AuthMode.OAUTH


class TestOAuthHeaders:
    async def test_oauth_token_uses_bearer_header(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        """Story 31.2: OAuth token produces Bearer + beta headers."""
        captured_request: httpx.Request | None = None

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_request
            captured_request = request
            return httpx.Response(200, json=_success_response())

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(
            api_key="sk-ant-oat01-test-token",
            auth_mode="auto",
        )
        adapter._client = httpx.AsyncClient(transport=transport)

        await adapter.complete(provider, request_msg)

        assert captured_request is not None
        assert captured_request.headers["authorization"] == "Bearer sk-ant-oat01-test-token"
        assert captured_request.headers["anthropic-beta"] == "oauth-2025-04-20"
        assert "x-api-key" not in captured_request.headers

    async def test_api_key_uses_xapikey_header(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        """Story 31.2: API key produces x-api-key header."""
        captured_request: httpx.Request | None = None

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_request
            captured_request = request
            return httpx.Response(200, json=_success_response())

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(
            api_key="sk-ant-api03-test-key",
            auth_mode="auto",
        )
        adapter._client = httpx.AsyncClient(transport=transport)

        await adapter.complete(provider, request_msg)

        assert captured_request is not None
        assert captured_request.headers["x-api-key"] == "sk-ant-api03-test-key"
        assert "authorization" not in captured_request.headers

    async def test_auth_mode_property(self) -> None:
        adapter = AnthropicAdapter(api_key="sk-ant-oat01-test", auth_mode="auto")
        assert adapter.auth_mode == AuthMode.OAUTH

        adapter2 = AnthropicAdapter(api_key="sk-ant-api03-test", auth_mode="auto")
        assert adapter2.auth_mode == AuthMode.API_KEY


# --------------------------------------------------------------------------
# Story 31.3: Token refresh tests
# --------------------------------------------------------------------------


class TestOAuthTokenRefresh:
    async def test_refresh_on_401_with_oauth(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        """Story 31.3: On 401 with OAuth, adapter refreshes and retries."""
        call_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1

            # Token refresh endpoint
            if "console.anthropic.com" in str(request.url):
                return httpx.Response(200, json={
                    "access_token": "sk-ant-oat01-refreshed-token",
                    "refresh_token": "sk-ant-ort01-new-refresh",
                    "expires_in": 28800,
                })

            # First API call returns 401, second succeeds
            if call_count == 1:
                return httpx.Response(401, json={"error": {"message": "Token expired"}})
            return httpx.Response(200, json=_success_response())

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(
            api_key="sk-ant-oat01-expired-token",
            auth_mode="auto",
            refresh_token="sk-ant-ort01-test-refresh",
        )
        adapter._client = httpx.AsyncClient(transport=transport)

        result = await adapter.complete(provider, request_msg)
        assert result.content == "Hello!"
        assert call_count == 3  # 1st fail + refresh + retry

    async def test_no_refresh_for_api_key_401(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        """Story 31.3: API key auth does NOT attempt refresh on 401."""
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": {"message": "Invalid key"}})

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(api_key="sk-ant-api03-bad", auth_mode="api_key")
        adapter._client = httpx.AsyncClient(transport=transport)

        with pytest.raises(httpx.HTTPStatusError):
            await adapter.complete(provider, request_msg)

    async def test_refresh_failure_raises(
        self, provider: ProviderConfig, request_msg: LLMRequest,
    ) -> None:
        """Story 31.3: If refresh fails, raise the original 401."""
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            if "console.anthropic.com" in str(request.url):
                return httpx.Response(400, json={"error": "bad refresh"})
            return httpx.Response(401, json={"error": {"message": "Expired"}})

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(
            api_key="sk-ant-oat01-expired",
            auth_mode="auto",
            refresh_token="sk-ant-ort01-bad-refresh",
        )
        adapter._client = httpx.AsyncClient(transport=transport)

        with pytest.raises(httpx.HTTPStatusError):
            await adapter.complete(provider, request_msg)


class TestGetLLMAdapter:
    def test_default_returns_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.adapters.llm.settings.llm_provider", "mock")
        adapter = get_llm_adapter()
        assert isinstance(adapter, MockLLMAdapter)

    def test_anthropic_flag_returns_anthropic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.adapters.llm.settings.llm_provider", "anthropic")
        adapter = get_llm_adapter()
        assert isinstance(adapter, AnthropicAdapter)
