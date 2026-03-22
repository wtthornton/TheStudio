"""LLM provider adapters — mock and Anthropic implementations.

Story 8.5: Anthropic Claude LLM Adapter
Story 31.2: OAuth token auto-detection and dual-header support
Story 31.3: Token refresh on expiration
Story 31.4: Explicit auth mode override
Feature flag: THESTUDIO_LLM_PROVIDER ("mock" or "anthropic")

WARNING: OAuth tokens are for DEVELOPMENT/TESTING use only.
Using OAuth tokens in a standalone server may violate Anthropic TOS.
Production deployments MUST use standard API keys.
"""

from __future__ import annotations

import json as _json_module
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

import httpx

from src.admin.model_gateway import ProviderConfig
from src.settings import settings

_json_loads = _json_module.loads

logger = logging.getLogger(__name__)


class AuthMode(StrEnum):
    """Authentication mode for the Anthropic API."""

    AUTO = "auto"
    API_KEY = "api_key"
    OAUTH = "oauth"


@dataclass
class LLMRequest:
    """Request to an LLM provider.

    Story 32.5: ``enable_caching`` marks the system prompt as cacheable
    using Anthropic's ``cache_control`` blocks.  The system prompt is
    automatically converted to a content-block list with the last block
    tagged ``{"type": "ephemeral"}``.
    """

    messages: list[dict[str, str]]
    max_tokens: int = 4096
    temperature: float = 0.0
    system: str = ""
    enable_caching: bool = False


@dataclass
class LLMResponse:
    """Response from an LLM provider.

    Story 32.5: ``cache_creation_tokens`` and ``cache_read_tokens`` track
    Anthropic prompt caching usage for cost estimation.
    """

    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""
    stop_reason: str = ""
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """Result from a batch API submission.

    Story 32.15: Wraps the Anthropic Messages Batches API response.
    The batch is submitted, polled until complete, then results extracted.
    """

    batch_id: str = ""
    status: str = "pending"  # pending, in_progress, ended
    responses: list[LLMResponse] = field(default_factory=list)
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "status": self.status,
            "total_requests": self.total_requests,
            "completed_requests": self.completed_requests,
            "failed_requests": self.failed_requests,
            "error": self.error,
        }


class LLMAdapterProtocol(Protocol):
    """Interface for LLM provider adapters."""

    async def complete(
        self, provider: ProviderConfig, request: LLMRequest,
    ) -> LLMResponse: ...

    async def batch_submit(
        self, provider: ProviderConfig, requests: list[LLMRequest],
    ) -> BatchResult: ...

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

    async def batch_submit(
        self, provider: ProviderConfig, requests: list[LLMRequest],
    ) -> BatchResult:
        """Mock batch submission — immediately returns results."""
        responses = []
        for req in requests:
            resp = await self.complete(provider, req)
            responses.append(resp)
        return BatchResult(
            batch_id="mock-batch-001",
            status="ended",
            responses=responses,
            total_requests=len(requests),
            completed_requests=len(requests),
        )

    async def close(self) -> None:
        pass

    @property
    def call_count(self) -> int:
        return self._call_count


def _detect_auth_mode(api_key: str, explicit_mode: str = "auto") -> AuthMode:
    """Detect authentication mode from key prefix or explicit setting.

    Story 31.2: Auto-detection based on token prefix.
    Story 31.4: Explicit override via THESTUDIO_ANTHROPIC_AUTH_MODE.
    """
    mode = AuthMode(explicit_mode) if explicit_mode in AuthMode.__members__.values() else AuthMode.AUTO

    if mode != AuthMode.AUTO:
        return mode

    if api_key.startswith("sk-ant-oat01-"):
        logger.info(
            "OAuth token detected (prefix sk-ant-oat01-*), using Bearer auth. "
            "WARNING: OAuth is for development/testing only."
        )
        return AuthMode.OAUTH
    if api_key.startswith("sk-ant-api"):
        return AuthMode.API_KEY

    logger.warning(
        "Unrecognized API key prefix, falling back to x-api-key auth"
    )
    return AuthMode.API_KEY


class AnthropicAdapter:
    """Real Anthropic Claude adapter using httpx.

    Makes async API calls to the Anthropic Messages API.
    Uses httpx directly (not the anthropic SDK) to keep dependencies minimal
    and allow mock HTTP testing with respx.

    Story 31.2: Supports both API key and OAuth Bearer auth.
    Story 31.3: Automatic token refresh on 401 for OAuth tokens.

    WARNING: OAuth tokens are for DEVELOPMENT/TESTING use only.
    """

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"
    TOKEN_REFRESH_URL = "https://console.anthropic.com/api/oauth/token"  # noqa: S105

    def __init__(
        self,
        api_key: str | None = None,
        auth_mode: str | None = None,
        refresh_token: str | None = None,
        oauth_client_id: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.anthropic_api_key
        self._auth_mode = _detect_auth_mode(
            self._api_key,
            auth_mode or settings.anthropic_auth_mode,
        )
        self._refresh_token = refresh_token or settings.anthropic_refresh_token
        self._oauth_client_id = oauth_client_id or settings.anthropic_oauth_client_id
        self._client = httpx.AsyncClient(timeout=120.0)
        self._refresh_attempted = False

    def _build_headers(self) -> dict[str, str]:
        """Build auth headers based on detected mode."""
        headers: dict[str, str] = {
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }

        if self._auth_mode == AuthMode.OAUTH:
            headers["authorization"] = f"Bearer {self._api_key}"
            headers["anthropic-beta"] = "oauth-2025-04-20"
        else:
            headers["x-api-key"] = self._api_key

        return headers

    async def _refresh_oauth_token(self) -> bool:
        """Attempt to refresh an expired OAuth token.

        Story 31.3: Token refresh on 401 using refresh token rotation.
        Returns True if refresh succeeded.
        """
        if not self._refresh_token:
            logger.error("OAuth token expired but no refresh token configured")
            return False

        logger.info("Attempting OAuth token refresh...")
        try:
            resp = await self._client.post(
                self.TOKEN_REFRESH_URL,
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._oauth_client_id,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

            self._api_key = data["access_token"]
            if "refresh_token" in data:
                self._refresh_token = data["refresh_token"]

            logger.info(
                "OAuth token refreshed successfully, expires_in=%s",
                data.get("expires_in", "unknown"),
            )
            return True
        except Exception:
            logger.exception("OAuth token refresh failed")
            return False

    @staticmethod
    def _build_system_payload(
        system: str, enable_caching: bool,
    ) -> str | list[dict[str, Any]]:
        """Build system prompt payload, optionally with cache_control.

        Story 32.5: When caching is enabled, converts the system prompt to
        a content-block list with the last block tagged for caching.
        """
        if not enable_caching or not system:
            return system

        return [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    async def complete(
        self, provider: ProviderConfig, request: LLMRequest,
    ) -> LLMResponse:
        headers = self._build_headers()

        # Story 32.5: Add prompt-caching beta header when caching enabled
        if request.enable_caching and settings.cost_optimization_caching_enabled:
            existing_beta = headers.get("anthropic-beta", "")
            cache_beta = "prompt-caching-2024-07-31"
            if existing_beta:
                headers["anthropic-beta"] = f"{existing_beta},{cache_beta}"
            else:
                headers["anthropic-beta"] = cache_beta

        body: dict[str, Any] = {
            "model": provider.model_id,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": request.messages,
        }
        if request.system:
            body["system"] = self._build_system_payload(
                request.system,
                request.enable_caching and settings.cost_optimization_caching_enabled,
            )

        resp = await self._client.post(self.API_URL, headers=headers, json=body)

        # Story 31.3: On 401 with OAuth, attempt token refresh and retry once
        if resp.status_code == 401 and self._auth_mode == AuthMode.OAUTH and not self._refresh_attempted:
            self._refresh_attempted = True
            if await self._refresh_oauth_token():
                headers = self._build_headers()
                resp = await self._client.post(self.API_URL, headers=headers, json=body)
                self._refresh_attempted = False

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
            cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
            cache_read_tokens=usage.get("cache_read_input_tokens", 0),
            raw=data,
        )

    BATCH_API_URL = "https://api.anthropic.com/v1/messages/batches"

    async def batch_submit(
        self, provider: ProviderConfig, requests: list[LLMRequest],
    ) -> BatchResult:
        """Submit a batch of requests via the Messages Batches API.

        Story 32.15: Non-interactive batch submission with polling.
        Submits all requests, polls until the batch ends, then extracts results.
        """
        if not requests:
            return BatchResult(status="ended")

        headers = self._build_headers()

        # Build batch request items
        batch_requests = []
        for i, req in enumerate(requests):
            body: dict[str, Any] = {
                "model": provider.model_id,
                "max_tokens": req.max_tokens,
                "temperature": req.temperature,
                "messages": req.messages,
            }
            if req.system:
                body["system"] = self._build_system_payload(
                    req.system,
                    req.enable_caching and settings.cost_optimization_caching_enabled,
                )
            batch_requests.append({
                "custom_id": f"req-{i}",
                "params": body,
            })

        # Submit batch
        submit_resp = await self._client.post(
            self.BATCH_API_URL,
            headers=headers,
            json={"requests": batch_requests},
        )
        submit_resp.raise_for_status()
        batch_data = submit_resp.json()
        batch_id = batch_data.get("id", "")

        # Poll until batch completes
        import asyncio

        poll_url = f"{self.BATCH_API_URL}/{batch_id}"
        status = batch_data.get("processing_status", "in_progress")
        max_polls = 120  # 10 minutes at 5s intervals
        polls = 0

        while status not in ("ended",) and polls < max_polls:
            await asyncio.sleep(5.0)
            poll_resp = await self._client.get(poll_url, headers=headers)
            poll_resp.raise_for_status()
            batch_data = poll_resp.json()
            status = batch_data.get("processing_status", "unknown")
            polls += 1

        if status != "ended":
            return BatchResult(
                batch_id=batch_id,
                status=status,
                total_requests=len(requests),
                error=f"Batch did not complete after {max_polls} polls",
            )

        # Fetch results
        results_url = batch_data.get("results_url", f"{poll_url}/results")
        results_resp = await self._client.get(results_url, headers=headers)
        results_resp.raise_for_status()

        responses: list[LLMResponse] = []
        failed = 0
        for line in results_resp.text.strip().split("\n"):
            if not line.strip():
                continue
            try:
                item = _json_loads(line)
            except Exception:
                failed += 1
                continue

            result = item.get("result", {})
            if result.get("type") != "succeeded":
                failed += 1
                continue

            msg = result.get("message", {})
            content_blocks = msg.get("content", [])
            text = "".join(
                b["text"] for b in content_blocks if b.get("type") == "text"
            )
            usage = msg.get("usage", {})
            responses.append(LLMResponse(
                content=text,
                tokens_in=usage.get("input_tokens", 0),
                tokens_out=usage.get("output_tokens", 0),
                model=msg.get("model", provider.model_id),
                stop_reason=msg.get("stop_reason", ""),
                cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
                cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                raw=msg,
            ))

        counts = batch_data.get("request_counts", {})
        return BatchResult(
            batch_id=batch_id,
            status="ended",
            responses=responses,
            total_requests=len(requests),
            completed_requests=counts.get("succeeded", len(responses)),
            failed_requests=counts.get("errored", 0) + failed,
        )

    @property
    def auth_mode(self) -> AuthMode:
        """Current authentication mode."""
        return self._auth_mode

    async def close(self) -> None:
        await self._client.aclose()


def get_llm_adapter() -> LLMAdapterProtocol:
    """Return the configured LLM adapter based on feature flag."""
    if settings.llm_provider == "anthropic":
        return AnthropicAdapter(
            auth_mode=settings.anthropic_auth_mode,
            refresh_token=settings.anthropic_refresh_token,
            oauth_client_id=settings.anthropic_oauth_client_id,
        )
    return MockLLMAdapter()
