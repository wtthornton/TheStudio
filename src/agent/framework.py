"""Unified Agent Framework — shared infrastructure for all pipeline agents.

Epic 23: Provides AgentConfig, AgentContext, AgentResult dataclasses and
the AgentRunner class that handles provider resolution, budget enforcement,
audit recording, structured output parsing, observability, and fallback.

Architecture reference: thestudioarc/08-agent-roles.md
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError

from src.adapters.llm import LLMRequest, LLMResponse, get_llm_adapter
from src.admin.model_gateway import (
    BudgetExceededError,
    ModelCallAudit,
    NoProviderAvailableError,
    ProviderConfig,
    get_budget_enforcer,
    get_model_audit_store,
    get_model_router,
)
from src.dashboard.events_publisher import emit_cost_update
from src.observability.tracing import get_tracer
from src.settings import settings

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.agent.framework")


# ---------------------------------------------------------------------------
# Story 1.12: Pipeline-wide budget (Appendix D defaults by trust tier)
# ---------------------------------------------------------------------------

PIPELINE_BUDGET_DEFAULTS: dict[str, float] = {
    "observe": 5.00,
    "suggest": 8.50,
    "execute": 10.00,
}


def get_budget_for_tier(tier: str) -> float:
    """Return the budget cap (USD) for a trust tier.

    When cost_optimization_routing_enabled is True, uses the tighter caps
    from settings.cost_optimization_budget_tiers.  Otherwise falls back
    to PIPELINE_BUDGET_DEFAULTS.
    """
    if settings.cost_optimization_routing_enabled:
        return settings.cost_optimization_budget_tiers.get(
            tier, PIPELINE_BUDGET_DEFAULTS.get(tier, 5.00)
        )
    return PIPELINE_BUDGET_DEFAULTS.get(tier, 5.00)


class PipelineBudget:
    """Thread-safe shared cost counter across all agents for a single TaskPacket.

    Created per workflow execution.  Every agent in the pipeline calls
    ``consume()`` before invoking an LLM; if the budget is exhausted the
    call returns *False* and the agent should use its fallback path.
    """

    def __init__(self, max_total_usd: float) -> None:
        self._max_total_usd = max_total_usd
        self._used: float = 0.0
        self._lock = threading.Lock()

    # -- public API ---------------------------------------------------------

    def consume(self, cost: float) -> bool:
        """Try to consume *cost* USD from the budget.

        Returns ``True`` if the budget had enough room (and *cost* was
        deducted), ``False`` if the budget is exhausted.  Thread-safe.
        """
        with self._lock:
            if self._used + cost > self._max_total_usd:
                return False
            self._used += cost
            return True

    @property
    def remaining(self) -> float:
        """How much budget is left (USD)."""
        with self._lock:
            return max(self._max_total_usd - self._used, 0.0)

    @property
    def used(self) -> float:
        """How much has been spent so far (USD)."""
        with self._lock:
            return self._used

    @property
    def max_total_usd(self) -> float:
        return self._max_total_usd


# ---------------------------------------------------------------------------
# Story 1.1: Core dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for a pipeline agent.

    Each agent type defines one of these as a module-level constant.
    Frozen to prevent mutation after construction.
    """

    agent_name: str
    pipeline_step: str
    model_class: str = "balanced"  # "fast", "balanced", "strong"
    system_prompt_template: str = ""
    tool_allowlist: list[str] = field(default_factory=list)
    max_turns: int = 1
    max_budget_usd: float = 0.50
    permission_mode: str = "acceptEdits"
    output_schema: type[BaseModel] | None = None
    fallback_fn: Callable[[AgentContext], Awaitable[str] | str] | None = None
    block_on_threat: bool = False
    compress_threshold: float = 0.5
    compress_model_class: str = "fast"
    batch_eligible: bool = False


@dataclass
class AgentContext:
    """All inputs an agent might need. Passed to AgentRunner.run()."""

    taskpacket_id: UUID | None = None
    correlation_id: UUID | None = None
    repo: str = ""
    issue_title: str = ""
    issue_body: str = ""
    labels: list[str] = field(default_factory=list)
    risk_flags: dict[str, Any] = field(default_factory=dict)
    complexity: str = ""
    overlays: list[str] = field(default_factory=list)
    repo_tier: str = ""
    intent: Any = None  # IntentSpecRead | None
    expert_outputs: list[Any] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
    per_repo_notes: list[str] = field(default_factory=list)
    pipeline_budget: PipelineBudget | None = None


@dataclass
class AgentResult:
    """Output from an agent run."""

    agent_name: str
    raw_output: str = ""
    parsed_output: BaseModel | None = None
    model_used: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_estimated: float = 0.0
    duration_ms: int = 0
    used_fallback: bool = False
    threat_flags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Story 1.2 + 1.4 + 1.5 + 1.6: AgentRunner
# ---------------------------------------------------------------------------


# Regex for extracting JSON from fenced code blocks
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _extract_json_block(raw: str) -> str:
    """Extract JSON from LLM output that may include fences or preamble.

    Handles three patterns:
    1. Raw JSON (starts with { or [)
    2. Fenced JSON (```json ... ```)
    3. JSON preceded by explanation text
    """
    stripped = raw.strip()

    # Pattern 1: raw JSON
    if stripped.startswith("{") or stripped.startswith("["):
        return stripped

    # Pattern 2: fenced JSON
    match = _JSON_FENCE_RE.search(stripped)
    if match:
        return match.group(1).strip()

    # Pattern 3: find first { ... last }
    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = stripped[first_brace : last_brace + 1]
        # Validate it's parseable JSON
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # Return as-is if no JSON found
    return stripped


class AgentRunner:
    """Runs a pipeline agent through the standard lifecycle.

    Lifecycle: span → provider → budget check → prompt build → LLM call → audit → parse → result

    For agentic mode (Primary Agent): uses Claude Agent SDK via _call_llm_agentic().
    For completion mode (all other agents): uses AnthropicAdapter via _call_llm_completion().
    Mode is determined by whether tool_allowlist is non-empty.
    """

    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the agent lifecycle."""
        start_time = time.monotonic()
        span_name = f"agent.{self.config.agent_name}"

        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("thestudio.agent_name", self.config.agent_name)
            span.set_attribute("thestudio.pipeline_step", self.config.pipeline_step)
            if context.taskpacket_id:
                span.set_attribute("thestudio.taskpacket_id", str(context.taskpacket_id))
            if context.correlation_id:
                span.set_attribute("thestudio.correlation_id", str(context.correlation_id))

            # Check feature flag
            agent_flags = getattr(settings, "agent_llm_enabled", {})
            if not agent_flags.get(self.config.agent_name, False):
                logger.info(
                    "Agent %s LLM disabled by feature flag, using fallback",
                    self.config.agent_name,
                )
                return await self._run_fallback(context, span, start_time)

            # Resolve provider
            try:
                provider = self._resolve_provider(context)
            except NoProviderAvailableError:
                logger.warning(
                    "No provider available for agent %s, using fallback",
                    self.config.agent_name,
                )
                return await self._run_fallback(context, span, start_time)

            # Budget check (per-agent)
            if context.taskpacket_id:
                try:
                    self._check_budget(str(context.taskpacket_id), context.repo_tier)
                except BudgetExceededError:
                    logger.warning(
                        "Budget exceeded for agent %s task %s, using fallback",
                        self.config.agent_name,
                        context.taskpacket_id,
                    )
                    return await self._run_fallback(context, span, start_time)

            # Pipeline-wide budget check (Story 1.12 / Story 32.8)
            if context.pipeline_budget is not None:
                if not context.pipeline_budget.consume(self.config.max_budget_usd):
                    span.set_attribute("thestudio.agent.pipeline_budget_exhausted", True)
                    raise BudgetExceededError(
                        task_id=str(context.taskpacket_id or "unknown"),
                        current_spend=context.pipeline_budget.used,
                        limit=context.pipeline_budget.max_total_usd,
                        step=self.config.pipeline_step,
                    )

            # Build prompts
            system_prompt = self.build_system_prompt(context)
            user_prompt = self.build_user_prompt(context)

            span.set_attribute("thestudio.agent_model", provider.model_id)

            # Call LLM
            try:
                if self.config.tool_allowlist:
                    response = await self._call_llm_agentic(
                        system_prompt,
                        user_prompt,
                        context,
                        provider,
                    )
                else:
                    response = await self._call_llm_completion(
                        system_prompt,
                        user_prompt,
                        provider,
                    )
            except Exception:
                logger.exception(
                    "LLM call failed for agent %s, using fallback",
                    self.config.agent_name,
                )
                return await self._run_fallback(context, span, start_time)

            # Record audit
            cost_delta = provider.estimate_cost(response.tokens_in, response.tokens_out)
            self._record_audit(
                context=context,
                provider=provider,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cost=cost_delta,
                cache_creation_tokens=response.cache_creation_tokens,
                cache_read_tokens=response.cache_read_tokens,
            )

            # Emit cost update event (fire-and-forget, S1.B5)
            if context.pipeline_budget is not None:
                try:
                    await emit_cost_update(
                        task_id=str(context.taskpacket_id or "unknown"),
                        cost_delta=cost_delta,
                        total_cost=context.pipeline_budget.used,
                        model=provider.model_id,
                        stage=self.config.pipeline_step,
                        correlation_id=str(context.correlation_id or ""),
                    )
                except Exception:
                    logger.debug("cost_update emit failed", exc_info=True)

            # Parse output
            parsed = self._parse_output(response.content, span)

            # If schema expected but parse failed, fall back
            if self.config.output_schema is not None and parsed is None:
                logger.warning(
                    "Output parse failed for agent %s, using fallback",
                    self.config.agent_name,
                )
                return await self._run_fallback(context, span, start_time)

            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return AgentResult(
                agent_name=self.config.agent_name,
                raw_output=response.content,
                parsed_output=parsed,
                model_used=response.model or provider.model_id,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cost_estimated=cost_delta,
                duration_ms=elapsed_ms,
                used_fallback=False,
            )

    def build_system_prompt(self, context: AgentContext) -> str:
        """Render the system prompt template with context variables."""
        template = self.config.system_prompt_template
        if not template:
            return f"You are the {self.config.agent_name} agent."

        # Build a format dict from context fields
        fmt: dict[str, Any] = {
            "agent_name": self.config.agent_name,
            "repo": context.repo,
            "issue_title": context.issue_title,
            "issue_body": context.issue_body,
            "complexity": context.complexity,
            "risk_flags": context.risk_flags,
            "labels": context.labels,
            "overlays": context.overlays,
        }
        fmt.update(context.extra)

        try:
            return template.format(**fmt)
        except KeyError:
            # If template has keys not in fmt, return template with partial formatting
            logger.warning(
                "System prompt template for %s has unresolved keys, using raw template",
                self.config.agent_name,
            )
            return template

    def build_user_prompt(self, context: AgentContext) -> str:
        """Build the user prompt from context. Subclasses may override."""
        parts: list[str] = []
        if context.issue_title:
            parts.append(f"## Issue\n\n**{context.issue_title}**")
        if context.issue_body:
            parts.append(context.issue_body)
        if context.per_repo_notes:
            notes = "\n".join(f"- {n}" for n in context.per_repo_notes)
            parts.append(f"## Operational Notes\n\n{notes}")
        return "\n\n".join(parts) if parts else "Process the input."

    def _resolve_provider(self, context: AgentContext) -> ProviderConfig:
        """Select a provider via the Model Gateway."""
        router = get_model_router()
        try:
            return router.select_model(
                step=self.config.pipeline_step,
                role=self.config.agent_name,
                overlays=context.overlays or None,
                repo_tier=context.repo_tier,
                complexity=context.complexity,
            )
        except NoProviderAvailableError:
            logger.warning(
                "Primary provider unavailable for %s, attempting fallback chain",
                self.config.agent_name,
            )
            provider, chain = router.select_with_fallback(
                step=self.config.pipeline_step,
                role=self.config.agent_name,
                overlays=context.overlays or None,
                repo_tier=context.repo_tier,
                complexity=context.complexity,
            )
            logger.info("Fallback resolved to %s (chain: %s)", provider.model_id, chain)
            return provider

    def _check_budget(self, task_id: str, repo_tier: str = "") -> None:
        """Check per-agent budget. Raises BudgetExceededError if over limit."""
        enforcer = get_budget_enforcer()
        if not enforcer.check_budget(task_id, repo_tier):
            current = enforcer.get_task_spend(task_id)
            raise BudgetExceededError(task_id, current, self.config.max_budget_usd)

    def _record_audit(
        self,
        *,
        context: AgentContext,
        provider: ProviderConfig,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        batch: bool = False,
    ) -> None:
        """Create an audit record and record spend.

        Story 32.17: When *batch* is True and cost_optimization_batch_enabled
        is on, apply 50% discount to cost estimation.
        """
        if batch and settings.cost_optimization_batch_enabled:
            cost = cost * 0.5

        audit = ModelCallAudit(
            correlation_id=context.correlation_id,
            task_id=context.taskpacket_id,
            step=self.config.pipeline_step,
            role=self.config.agent_name,
            overlays=list(context.overlays) if context.overlays else [],
            provider=provider.provider,
            model=provider.model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            batch=batch,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
        )
        get_model_audit_store().record(audit)

        if context.taskpacket_id:
            get_budget_enforcer().record_spend(
                task_id=str(context.taskpacket_id),
                step=self.config.pipeline_step,
                cost=cost,
                tokens=tokens_in + tokens_out,
            )

    def _parse_output(self, raw: str, span: Any) -> BaseModel | None:
        """Parse agent output against output_schema if configured.

        Emits parse success/failure as span attributes for the >90% metric.
        Returns None if no schema or parse fails.
        """
        if self.config.output_schema is None:
            return None

        try:
            json_str = _extract_json_block(raw)
            result = self.config.output_schema.model_validate_json(json_str)
            span.set_attribute("thestudio.agent.parse_result", "success")
            logger.debug("Parse success for agent %s", self.config.agent_name)
            return result
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            span.set_attribute("thestudio.agent.parse_result", "failure")
            logger.warning(
                "Parse failure for agent %s: %s",
                self.config.agent_name,
                exc,
            )
            return None

    async def _call_llm_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        provider: ProviderConfig,
    ) -> LLMResponse:
        """Single-turn LLM call via AnthropicAdapter. For non-tool agents."""
        adapter = get_llm_adapter()
        request = LLMRequest(
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=4096,
            temperature=0.0,
        )
        try:
            return await adapter.complete(provider, request)
        finally:
            await adapter.close()

    async def _call_llm_agentic(
        self,
        system_prompt: str,
        user_prompt: str,
        context: AgentContext,
        provider: ProviderConfig,
    ) -> LLMResponse:
        """Multi-turn tool loop via Claude Agent SDK. For the Primary Agent."""
        from claude_agent_sdk import (  # type: ignore[import-untyped]
            ClaudeAgentOptions,
            ResultMessage,
            query,
        )

        repo_path = context.extra.get("repo_path", context.repo)
        options = ClaudeAgentOptions(
            cwd=repo_path,
            allowed_tools=self.config.tool_allowlist,
            permission_mode=self.config.permission_mode,
            system_prompt=system_prompt,
            model=provider.model_id,
            max_turns=self.config.max_turns,
            max_budget_usd=self.config.max_budget_usd,
        )

        result_text = ""
        async for message in query(prompt=user_prompt, options=options):
            if isinstance(message, ResultMessage):
                result_text = message.result or ""

        # Estimate tokens since SDK doesn't provide them
        tokens_in = (len(system_prompt) + len(user_prompt)) // 4
        tokens_out = len(result_text) // 4

        return LLMResponse(
            content=result_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=provider.model_id,
            stop_reason="end_turn",
        )

    # ------------------------------------------------------------------
    # Story 1.13: Context compression (placeholder — detection only)
    # ------------------------------------------------------------------

    def _compress_context(
        self,
        messages: list[dict[str, Any]],
        context_window: int,
    ) -> list[dict[str, Any]]:
        """Detect when context compression is needed and log a warning.

        Only applies to agentic mode (tool loop).  When the estimated
        token count exceeds ``compress_threshold * context_window``, the
        method would summarise middle turns while preserving the first 3
        and last 4 turns verbatim.

        Current implementation is a **placeholder**: it logs a warning
        when compression would trigger but does *not* call a secondary
        LLM.  Returns the original messages unchanged.
        """
        # Rough token estimate: 1 token ≈ 4 characters
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        estimated_tokens = total_chars // 4

        threshold = self.config.compress_threshold * context_window
        if estimated_tokens <= threshold:
            return messages  # no compression needed

        preserve_head = 3
        preserve_tail = 4

        compressible = len(messages) - preserve_head - preserve_tail
        if compressible <= 0:
            logger.debug(
                "Context compression triggered for %s but not enough "
                "turns to compress (%d messages, need >%d)",
                self.config.agent_name,
                len(messages),
                preserve_head + preserve_tail,
            )
            return messages

        logger.warning(
            "Context compression triggered for agent %s: "
            "estimated_tokens=%d, threshold=%.0f, "
            "would compress %d middle turns (preserving first %d + last %d). "
            "Compression model would be '%s'. "
            "Placeholder: returning uncompressed context.",
            self.config.agent_name,
            estimated_tokens,
            threshold,
            compressible,
            preserve_head,
            preserve_tail,
            self.config.compress_model_class,
        )
        return messages

    async def _run_fallback(
        self,
        context: AgentContext,
        span: Any,
        start_time: float,
    ) -> AgentResult:
        """Execute the fallback function and return a fallback result."""
        raw_output = ""
        if self.config.fallback_fn is not None:
            result = self.config.fallback_fn(context)
            if hasattr(result, "__await__"):
                raw_output = await result  # type: ignore[misc]
            else:
                raw_output = str(result)

        span.set_attribute("thestudio.agent.used_fallback", True)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        return AgentResult(
            agent_name=self.config.agent_name,
            raw_output=raw_output,
            parsed_output=None,
            model_used="fallback",
            duration_ms=elapsed_ms,
            used_fallback=True,
        )
