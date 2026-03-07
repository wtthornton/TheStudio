"""LLM provider adapters — mock and Anthropic implementations.

Story 8.5: Anthropic Claude LLM Adapter
Feature flag: THESTUDIO_LLM_PROVIDER ("mock" or "anthropic")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from src.admin.model_gateway import ModelCallAudit, ProviderConfig
from src.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMRequest:
    """Request to an LLM provider."""

    messages: list[dict[str, str]]
    max_tokens: int = 4096
    temperature: float = 0.0
    system: str = ""


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""
    stop_reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class LLMAdapterProtocol(Protocol):
    """Interface for LLM provider adapters."""

    async def complete(
        self, provider: ProviderConfig, request: LLMRequest,
    ) -> LLMResponse: ...

    async def close(self) -> None: ...


class MockLLMAdapter:
    """Mock LLM adapter that returns canned responses. Default for tests."""

    def __init__(self, default_response: str = "Mock LLM response.") -> None:
        self._default_response = default_response
        self._call_count = 0

    async def complete(
        self, provider: ProviderConfig, request: LLMRequest,
    ) -> LLMResponse:
        self._call_count += 1
        return LLMResponse(
            content=self._default_response,
            tokens_in=sum(len(m.get("content", "")) // 4 for m in request.messages),
            tokens_out=len(self._default_response) // 4,
            model=provider.model_id,
            stop_reason="end_turn",
        )

    async def close(self) -> None:
        pass

    @property
    def call_count(self) -> int:
        return self._call_count


class AnthropicAdapter:
    """Real Anthropic Claude adapter using httpx.

    Makes async API calls to the Anthropic Messages API.
    Uses httpx directly (not the anthropic SDK) to keep dependencies minimal
    and allow mock HTTP testing with respx.
    """

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.anthropic_api_key
        self._client = httpx.AsyncClient(timeout=120.0)

    async def complete(
        self, provider: ProviderConfig, request: LLMRequest,
    ) -> LLMResponse:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }

        body: dict[str, Any] = {
            "model": provider.model_id,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": request.messages,
        }
        if request.system:
            body["system"] = request.system

        resp = await self._client.post(self.API_URL, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

        content_blocks = data.get("content", [])
        text = "".join(
            block["text"] for block in content_blocks if block.get("type") == "text"
        )

        usage = data.get("usage", {})
        return LLMResponse(
            content=text,
            tokens_in=usage.get("input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
            model=data.get("model", provider.model_id),
            stop_reason=data.get("stop_reason", ""),
            raw=data,
        )

    async def close(self) -> None:
        await self._client.aclose()


def get_llm_adapter() -> LLMAdapterProtocol:
    """Return the configured LLM adapter based on feature flag."""
    if settings.llm_provider == "anthropic":
        return AnthropicAdapter()
    return MockLLMAdapter()
