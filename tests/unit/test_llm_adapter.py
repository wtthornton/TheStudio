"""Tests for LLM provider adapters (Story 8.5)."""

import httpx
import pytest

from src.adapters.llm import (
    AnthropicAdapter,
    LLMRequest,
    LLMResponse,
    MockLLMAdapter,
    get_llm_adapter,
)
from src.admin.model_gateway import ModelClass, ProviderConfig


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
            return httpx.Response(
                200,
                json={
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-sonnet-4-6",
                    "content": [{"type": "text", "text": "Hello!"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            )

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = httpx.AsyncClient(transport=transport)

        result = await adapter.complete(provider, request_msg)

        assert captured_request is not None
        assert captured_request.url == AnthropicAdapter.API_URL
        assert captured_request.headers["x-api-key"] == "test-key"
        assert captured_request.headers["anthropic-version"] == "2023-06-01"

        import json
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
        adapter = AnthropicAdapter(api_key="test-key")
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
            import json
            captured_body = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-sonnet-4-6",
                    "content": [{"type": "text", "text": "Hi!"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 3},
                },
            )

        transport = httpx.MockTransport(mock_handler)
        adapter = AnthropicAdapter(api_key="test-key")
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
        adapter = AnthropicAdapter(api_key="bad-key")
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
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = httpx.AsyncClient(transport=transport)

        result = await adapter.complete(provider, request_msg)
        assert result.content == "Part 1. Part 2."


class TestGetLLMAdapter:
    def test_default_returns_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.adapters.llm.settings.llm_provider", "mock")
        adapter = get_llm_adapter()
        assert isinstance(adapter, MockLLMAdapter)

    def test_anthropic_flag_returns_anthropic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.adapters.llm.settings.llm_provider", "anthropic")
        adapter = get_llm_adapter()
        assert isinstance(adapter, AnthropicAdapter)
