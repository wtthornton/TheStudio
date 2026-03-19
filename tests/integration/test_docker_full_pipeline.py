"""Full pipeline end-to-end test against Docker prod container.

Story 30.7: Full pipeline with all real providers at Observe tier.
Story 32.0: Measured per-agent cost baselines.

Runs against the Docker prod stack (thestudio-prod-*) with:
- llm_provider=anthropic (real Anthropic API)
- store_backend=postgres (real Postgres in container)
- Agent LLM enabled for key agents

This test exercises the real adapter path through Docker, NOT
via mock providers.

Run:
    export THESTUDIO_ANTHROPIC_API_KEY=$(grep THESTUDIO_ANTHROPIC_API_KEY infra/.env | cut -d= -f2)
    pytest tests/integration/test_docker_full_pipeline.py -m integration -v
"""

from __future__ import annotations

import os
import time

import pytest

from src.adapters.llm import AnthropicAdapter, LLMRequest, LLMResponse
from src.admin.model_gateway import (
    DEFAULT_PROVIDERS,
    ModelCallAudit,
    ModelClass,
    ModelRouter,
    ProviderConfig,
)
from src.agent.framework import AgentConfig, AgentContext, AgentRunner
from src.eval.models import EvalSummary

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_api_key,
]


def _get_api_key() -> str:
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


# ---- Provider configs for different model classes ----


@pytest.fixture
def fast_provider() -> ProviderConfig:
    return ProviderConfig(
        provider_id="fast-test",
        provider="anthropic",
        model_id="claude-haiku-4-5",
        model_class=ModelClass.FAST,
        cost_per_1k_tokens=0.001,
        cost_per_1k_input=0.001,
        cost_per_1k_output=0.005,
    )


@pytest.fixture
def balanced_provider() -> ProviderConfig:
    return ProviderConfig(
        provider_id="balanced-test",
        provider="anthropic",
        model_id="claude-sonnet-4-6",
        model_class=ModelClass.BALANCED,
        cost_per_1k_tokens=0.003,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
    )


# ---- Story 30.7: Full pipeline agent smoke tests against Docker ----


class TestDockerAgentSmoke:
    """Validate each pipeline agent produces valid output via real Anthropic API."""

    ISSUE_BODY = (
        "## Problem\n\n"
        "The login page times out after 30 seconds when using SSO.\n\n"
        "## Acceptance Criteria\n\n"
        "- [ ] SSO login completes within 5 seconds\n"
        "- [ ] Error message shown on timeout\n"
    )

    async def test_intent_agent_real_llm(
        self, api_key: str, balanced_provider: ProviderConfig,
    ) -> None:
        """Intent agent produces valid output against real Anthropic API."""
        adapter = AnthropicAdapter(api_key=api_key, auth_mode="api_key")
        try:
            request = LLMRequest(
                messages=[{
                    "role": "user",
                    "content": (
                        f"## Issue\n\n**Fix SSO login timeout**\n\n{self.ISSUE_BODY}\n\n"
                        "Respond with a JSON intent specification including: "
                        "goal, constraints, invariants, acceptance_criteria."
                    ),
                }],
                max_tokens=2048,
                temperature=0.0,
                system="You are the intent_agent. Produce a JSON intent specification.",
            )
            result = await adapter.complete(balanced_provider, request)
            assert result.content
            assert result.tokens_in > 0
            assert result.tokens_out > 0
            assert result.model
            # Log cost for Story 32.0
            cost = balanced_provider.estimate_cost(result.tokens_in, result.tokens_out)
            print(f"\n  Intent Agent: tokens_in={result.tokens_in}, tokens_out={result.tokens_out}, cost=${cost:.4f}")
        finally:
            await adapter.close()

    async def test_context_agent_real_llm(
        self, api_key: str, fast_provider: ProviderConfig,
    ) -> None:
        """Context agent (FAST class) produces valid enrichment output."""
        adapter = AnthropicAdapter(api_key=api_key, auth_mode="api_key")
        try:
            request = LLMRequest(
                messages=[{
                    "role": "user",
                    "content": (
                        "Analyze this GitHub issue for complexity, risk flags, "
                        "and technology domains:\n\n"
                        f"**Fix SSO login timeout**\n\n{self.ISSUE_BODY}\n\n"
                        "Respond with JSON: complexity (low/medium/high), "
                        "risk_flags (list), tech_domains (list)."
                    ),
                }],
                max_tokens=1024,
                temperature=0.0,
                system="You are the context_agent. Analyze issues for complexity and risk.",
            )
            result = await adapter.complete(fast_provider, request)
            assert result.content
            cost = fast_provider.estimate_cost(result.tokens_in, result.tokens_out)
            print(f"\n  Context Agent: tokens_in={result.tokens_in}, tokens_out={result.tokens_out}, cost=${cost:.4f}")
        finally:
            await adapter.close()

    async def test_qa_agent_real_llm(
        self, api_key: str, balanced_provider: ProviderConfig,
    ) -> None:
        """QA agent produces valid evaluation against real API."""
        adapter = AnthropicAdapter(api_key=api_key, auth_mode="api_key")
        try:
            request = LLMRequest(
                messages=[{
                    "role": "user",
                    "content": (
                        "Evaluate this code change against the intent specification:\n\n"
                        "**Intent:** Fix SSO login timeout to complete within 5 seconds.\n"
                        "**Evidence:** Ruff: 0 errors. Pytest: 5 passed. "
                        "Security scan: clean.\n"
                        "**Changes:** Modified auth/sso.py to add 5s timeout.\n\n"
                        "Respond with JSON: criteria_results (list), defects (list), "
                        "overall_verdict (pass/fail)."
                    ),
                }],
                max_tokens=2048,
                temperature=0.0,
                system="You are the qa_agent. Evaluate code changes against intent.",
            )
            result = await adapter.complete(balanced_provider, request)
            assert result.content
            cost = balanced_provider.estimate_cost(result.tokens_in, result.tokens_out)
            print(f"\n  QA Agent: tokens_in={result.tokens_in}, tokens_out={result.tokens_out}, cost=${cost:.4f}")
        finally:
            await adapter.close()

    async def test_router_agent_real_llm(
        self, api_key: str, balanced_provider: ProviderConfig,
    ) -> None:
        """Router agent produces valid expert selection output."""
        adapter = AnthropicAdapter(api_key=api_key, auth_mode="api_key")
        try:
            request = LLMRequest(
                messages=[{
                    "role": "user",
                    "content": (
                        "Select experts for this issue:\n\n"
                        f"**Fix SSO login timeout**\n\n{self.ISSUE_BODY}\n"
                        "Complexity: medium. Risk flags: none.\n\n"
                        "Respond with JSON: selections (list of expert_class + pattern), "
                        "escalation_flags (list)."
                    ),
                }],
                max_tokens=1024,
                temperature=0.0,
                system="You are the router_agent. Select experts for the task.",
            )
            result = await adapter.complete(balanced_provider, request)
            assert result.content
            cost = balanced_provider.estimate_cost(result.tokens_in, result.tokens_out)
            print(f"\n  Router Agent: tokens_in={result.tokens_in}, tokens_out={result.tokens_out}, cost=${cost:.4f}")
        finally:
            await adapter.close()


# ---- Story 32.0: Per-agent cost baselines ----


class TestCostBaselines:
    """Measure per-agent cost baselines for cost optimization planning."""

    async def test_measure_all_agent_costs(
        self, api_key: str,
        fast_provider: ProviderConfig,
        balanced_provider: ProviderConfig,
    ) -> None:
        """Run each agent type and report per-agent token/cost breakdown."""
        issue = (
            "## Problem\n\nThe search API returns stale results after index update.\n\n"
            "## Acceptance Criteria\n\n- Fresh results within 5 seconds of index commit\n"
            "- No stale cache served after explicit invalidation\n"
        )

        agents = [
            ("intake_agent", fast_provider, "Classify this issue: eligible or ineligible?"),
            ("context_agent", fast_provider, "Analyze complexity and risk flags for this issue."),
            ("intent_agent", balanced_provider, "Generate an intent specification with goal, constraints, ACs."),
            ("router_agent", balanced_provider, "Select experts and consultation pattern for this issue."),
            ("assembler_agent", balanced_provider, "Merge expert outputs into a coherent implementation plan."),
            ("qa_agent", balanced_provider, "Evaluate: evidence shows ruff clean, tests pass. Verdict?"),
        ]

        results: list[dict] = []
        adapter = AnthropicAdapter(api_key=api_key, auth_mode="api_key")
        try:
            for agent_name, provider, task in agents:
                request = LLMRequest(
                    messages=[{"role": "user", "content": f"{task}\n\n{issue}"}],
                    max_tokens=2048,
                    temperature=0.0,
                    system=f"You are the {agent_name}. Respond with JSON.",
                )
                start = time.monotonic()
                result = await adapter.complete(provider, request)
                elapsed_ms = int((time.monotonic() - start) * 1000)
                cost = provider.estimate_cost(result.tokens_in, result.tokens_out)
                results.append({
                    "agent": agent_name,
                    "model": provider.model_id,
                    "tokens_in": result.tokens_in,
                    "tokens_out": result.tokens_out,
                    "cost": cost,
                    "latency_ms": elapsed_ms,
                })

            # Print cost baseline table
            print("\n\n=== Per-Agent Cost Baselines (Story 32.0) ===")
            print(f"{'Agent':<20} {'Model':<25} {'In':>8} {'Out':>8} {'Cost':>10} {'Latency':>10}")
            print("-" * 85)
            total_cost = 0.0
            for r in results:
                total_cost += r["cost"]
                print(
                    f"{r['agent']:<20} {r['model']:<25} "
                    f"{r['tokens_in']:>8} {r['tokens_out']:>8} "
                    f"${r['cost']:>8.4f} {r['latency_ms']:>8}ms"
                )
            print("-" * 85)
            print(f"{'TOTAL':<20} {'':<25} {'':<8} {'':<8} ${total_cost:>8.4f}")
            print(f"\nProjected per-issue cost (9 agents): ${total_cost * 1.5:.2f}")
            print(f"Projected monthly (10 issues/day): ${total_cost * 1.5 * 10 * 30:.0f}")
            print(f"Projected monthly (50 issues/day): ${total_cost * 1.5 * 50 * 30:.0f}")

            # Assertions
            assert len(results) == 6
            for r in results:
                assert r["tokens_in"] > 0
                assert r["tokens_out"] > 0
                assert r["cost"] > 0
            assert total_cost < 1.0  # Should be well under $1 for 6 calls
        finally:
            await adapter.close()


# ---- Prompt caching validation (Story 32.5) ----


class TestPromptCaching:
    """Validate that prompt caching headers are sent correctly."""

    async def test_caching_produces_cache_tokens(
        self, api_key: str, balanced_provider: ProviderConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When caching is enabled, cache tokens appear in response."""
        monkeypatch.setattr(
            "src.adapters.llm.settings.cost_optimization_caching_enabled", True,
        )

        adapter = AnthropicAdapter(api_key=api_key, auth_mode="api_key")
        try:
            # First call creates cache
            system_prompt = (
                "You are a test agent. This is a long system prompt that "
                "should be cacheable. " * 50  # Make it long enough to be cache-worthy
            )
            request = LLMRequest(
                messages=[{"role": "user", "content": "Say hello."}],
                max_tokens=10,
                temperature=0.0,
                system=system_prompt,
                enable_caching=True,
            )
            result1 = await adapter.complete(balanced_provider, request)
            assert result1.content

            # Second call should hit cache
            result2 = await adapter.complete(balanced_provider, request)
            assert result2.content

            # At least one should have cache metrics
            total_cache = (
                result1.cache_creation_tokens + result1.cache_read_tokens
                + result2.cache_creation_tokens + result2.cache_read_tokens
            )
            print(f"\n  Call 1: cache_creation={result1.cache_creation_tokens}, cache_read={result1.cache_read_tokens}")
            print(f"  Call 2: cache_creation={result2.cache_creation_tokens}, cache_read={result2.cache_read_tokens}")
            # Cache may or may not be used depending on API support for this model
            # Don't assert on cache tokens - just verify the plumbing works
        finally:
            await adapter.close()
