"""Primary Agent — implements code changes from an Intent Specification.

Uses Claude Agent SDK with the Developer role to implement changes,
produce an evidence bundle, and support verification loopbacks.

Architecture reference: thestudioarc/08-agent-roles.md
Epic reference: Story 0.5 — Primary Agent
Sprint 19 Stream A: Model Gateway integration (Stories A1-A6)
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.model_gateway import (
    BudgetExceededError,
    ModelCallAudit,
    NoProviderAvailableError,
    ProviderConfig,
    get_budget_enforcer,
    get_model_audit_store,
    get_model_router,
)
from src.agent.developer_role import DeveloperRoleConfig, build_system_prompt
from src.agent.evidence import EvidenceBundle
from src.intent.intent_crud import get_latest_for_taskpacket
from src.models.taskpacket import TaskPacketStatus
from src.models.taskpacket_crud import get_by_id, update_status
from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_TASKPACKET_ID,
    SPAN_AGENT_IMPLEMENT,
    SPAN_AGENT_LOOPBACK,
)
from src.observability.tracing import get_tracer
from src.settings import settings
from src.verification.gate import VerificationResult

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.agent")


async def _run_agent(
    system_prompt: str,
    user_prompt: str,
    repo_path: str,
    role_config: DeveloperRoleConfig,
) -> str:
    """Run the Claude Agent SDK to implement changes.

    Returns the agent's text result (summary of changes).
    """
    from claude_agent_sdk import (  # type: ignore[import-untyped]
        ClaudeAgentOptions,
        ResultMessage,
        query,
    )

    options = ClaudeAgentOptions(
        cwd=repo_path,
        allowed_tools=role_config.tool_allowlist,
        permission_mode=role_config.permission_mode,
        system_prompt=system_prompt,
        model=role_config.model,
        max_turns=role_config.max_turns,
        max_budget_usd=role_config.max_budget_usd,
    )

    result_text = ""
    async for message in query(prompt=user_prompt, options=options):
        if isinstance(message, ResultMessage):
            result_text = message.result or ""

    return result_text


def _parse_changed_files(agent_summary: str) -> list[str]:
    """Extract file paths from the agent's summary output.

    Looks for lines starting with '- ' that contain file-path-like strings.
    """
    files: list[str] = []
    for line in agent_summary.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and ("." in stripped or "/" in stripped):
            # Extract the file path (first token after "- ")
            parts = stripped[2:].split()
            if parts:
                candidate = parts[0].rstrip(":")
                # Basic validation: contains a dot or slash
                if "." in candidate or "/" in candidate:
                    files.append(candidate)
    return files


def _resolve_provider(
    overlays: list[str] | None,
    repo_tier: str,
    complexity: str,
) -> ProviderConfig:
    """Select a provider via the Model Gateway, with fallback on failure.

    Tries ``select_model`` first; on ``NoProviderAvailableError`` falls back
    to ``select_with_fallback`` and logs the chain.
    """
    router = get_model_router()
    try:
        return router.select_model(
            step="primary_agent",
            role="developer",
            overlays=overlays,
            repo_tier=repo_tier,
            complexity=complexity,
        )
    except NoProviderAvailableError:
        logger.warning(
            "Primary provider unavailable, attempting fallback chain "
            "(overlays=%s, repo_tier=%s, complexity=%s)",
            overlays,
            repo_tier,
            complexity,
        )
        provider, chain = router.select_with_fallback(
            step="primary_agent",
            role="developer",
            overlays=overlays,
            repo_tier=repo_tier,
            complexity=complexity,
        )
        logger.info("Fallback resolved to %s (chain: %s)", provider.model_id, chain)
        return provider


def _estimate_tokens(*texts: str) -> int:
    """Rough token estimate: 1 token per 4 characters."""
    return sum(len(t) // 4 for t in texts)


def _record_audit_and_spend(
    *,
    taskpacket_correlation_id: UUID | None,
    taskpacket_id: UUID,
    provider: ProviderConfig,
    prompt_tokens: int,
    response_tokens: int,
    estimated_cost: float,
) -> None:
    """Create an audit record and record spend after an agent call."""
    audit = ModelCallAudit(
        correlation_id=taskpacket_correlation_id,
        task_id=taskpacket_id,
        step="primary_agent",
        role="developer",
        provider=provider.provider,
        model=provider.model_id,
        tokens_in=prompt_tokens,
        tokens_out=response_tokens,
        cost=estimated_cost,
    )
    get_model_audit_store().record(audit)

    get_budget_enforcer().record_spend(
        task_id=str(taskpacket_id),
        step="primary_agent",
        cost=estimated_cost,
        tokens=prompt_tokens + response_tokens,
    )


async def implement(
    session: AsyncSession,
    taskpacket_id: UUID,
    repo_path: str,
    role_config: DeveloperRoleConfig | None = None,
    *,
    overlays: list[str] | None = None,
    repo_tier: str = "",
    complexity: str = "",
) -> EvidenceBundle:
    """Run the Primary Agent to implement changes from an Intent Specification.

    Transitions TaskPacket status from intent_built -> in_progress.
    Returns an EvidenceBundle with the agent's output.

    Args:
        session: Database session.
        taskpacket_id: TaskPacket to implement.
        repo_path: Local path to the target repository.
        role_config: Developer role configuration (uses defaults if None).
            When *None*, the Model Gateway selects the provider.
        overlays: Optional overlays for model routing (e.g. ``["security"]``).
        repo_tier: Repository trust tier for routing rules.
        complexity: Task complexity hint (``"high"`` escalates to STRONG).

    Returns:
        EvidenceBundle with files changed, test/lint results, and summary.

    Raises:
        ValueError: If TaskPacket or IntentSpec not found.
        BudgetExceededError: If the task has exceeded its spend budget.
    """
    # --- A1: Gateway-aware role config resolution ---
    provider: ProviderConfig | None = None
    if role_config is None:
        provider = _resolve_provider(overlays, repo_tier, complexity)
        budget = get_budget_enforcer().get_budget(repo_tier)
        role_config = DeveloperRoleConfig(
            model=provider.model_id,
            max_turns=settings.agent_max_turns,
            max_budget_usd=budget.per_task_max_spend,
        )

    # --- A2: Budget check before agent call ---
    if not get_budget_enforcer().check_budget(str(taskpacket_id)):
        budget = get_budget_enforcer().get_budget(repo_tier)
        current = get_budget_enforcer().get_task_spend(str(taskpacket_id))
        raise BudgetExceededError(
            str(taskpacket_id),
            current,
            budget.per_task_max_spend,
        )

    with tracer.start_as_current_span(SPAN_AGENT_IMPLEMENT) as span:
        # Load TaskPacket and IntentSpec
        taskpacket = await get_by_id(session, taskpacket_id)
        if taskpacket is None:
            raise ValueError(f"TaskPacket {taskpacket_id} not found")

        span.set_attribute(ATTR_TASKPACKET_ID, str(taskpacket_id))
        span.set_attribute(ATTR_CORRELATION_ID, str(taskpacket.correlation_id))

        intent = await get_latest_for_taskpacket(session, taskpacket_id)
        if intent is None:
            raise ValueError(f"No IntentSpec found for TaskPacket {taskpacket_id}")

        # Transition to in_progress
        await update_status(session, taskpacket_id, TaskPacketStatus.IN_PROGRESS)

        # Build prompts
        system_prompt = build_system_prompt(intent, taskpacket)
        user_prompt = (
            f"Implement the following goal in this repository:\n\n"
            f"{intent.goal}\n\n"
            f"Follow all constraints and acceptance criteria from the system prompt."
        )

        span.set_attribute("thestudio.intent_version", intent.version)
        span.set_attribute("thestudio.agent_model", role_config.model)

        # Run the agent
        logger.info(
            "Starting Primary Agent for TaskPacket %s (intent v%d)",
            taskpacket_id,
            intent.version,
        )
        agent_summary = await _run_agent(system_prompt, user_prompt, repo_path, role_config)

        # --- A3+A4: Record spend and audit after agent call ---
        if provider is not None:
            prompt_tokens = _estimate_tokens(system_prompt, user_prompt)
            response_tokens = _estimate_tokens(agent_summary)
            estimated_cost = (prompt_tokens + response_tokens) * provider.cost_per_1k_tokens / 1000
            _record_audit_and_spend(
                taskpacket_correlation_id=taskpacket.correlation_id,
                taskpacket_id=taskpacket_id,
                provider=provider,
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                estimated_cost=estimated_cost,
            )

        # Build evidence bundle
        changed_files = _parse_changed_files(agent_summary)
        evidence = EvidenceBundle(
            taskpacket_id=taskpacket_id,
            intent_version=intent.version,
            files_changed=changed_files,
            agent_summary=agent_summary,
            loopback_attempt=taskpacket.loopback_count,
        )

        span.set_attribute("thestudio.files_changed_count", len(changed_files))
        logger.info(
            "Primary Agent completed for TaskPacket %s: %d files changed",
            taskpacket_id,
            len(changed_files),
        )

        return evidence


async def handle_loopback(
    session: AsyncSession,
    taskpacket_id: UUID,
    repo_path: str,
    verification_result: VerificationResult,
    role_config: DeveloperRoleConfig | None = None,
    *,
    overlays: list[str] | None = None,
    repo_tier: str = "",
    complexity: str = "",
) -> EvidenceBundle:
    """Handle a verification failure loopback.

    Provides the agent with failure context and asks it to fix the issues.
    Transitions TaskPacket from verification_failed -> in_progress.

    Args:
        session: Database session.
        taskpacket_id: TaskPacket to retry.
        repo_path: Local path to the target repository.
        verification_result: The failed verification result with check details.
        role_config: Developer role configuration.
            When *None*, the Model Gateway selects the provider.
        overlays: Optional overlays for model routing.
        repo_tier: Repository trust tier for routing rules.
        complexity: Task complexity hint.

    Returns:
        New EvidenceBundle from the retry attempt.

    Raises:
        BudgetExceededError: If the task has exceeded its spend budget.
    """
    # --- A1: Gateway-aware role config resolution ---
    provider: ProviderConfig | None = None
    if role_config is None:
        provider = _resolve_provider(overlays, repo_tier, complexity)
        budget = get_budget_enforcer().get_budget(repo_tier)
        role_config = DeveloperRoleConfig(
            model=provider.model_id,
            max_turns=settings.agent_max_turns,
            max_budget_usd=budget.per_task_max_spend,
        )

    # --- A2: Budget check before agent call ---
    if not get_budget_enforcer().check_budget(str(taskpacket_id)):
        budget = get_budget_enforcer().get_budget(repo_tier)
        current = get_budget_enforcer().get_task_spend(str(taskpacket_id))
        raise BudgetExceededError(
            str(taskpacket_id),
            current,
            budget.per_task_max_spend,
        )

    with tracer.start_as_current_span(SPAN_AGENT_LOOPBACK) as span:
        taskpacket = await get_by_id(session, taskpacket_id)
        if taskpacket is None:
            raise ValueError(f"TaskPacket {taskpacket_id} not found")

        span.set_attribute(ATTR_TASKPACKET_ID, str(taskpacket_id))
        span.set_attribute(ATTR_CORRELATION_ID, str(taskpacket.correlation_id))
        span.set_attribute("thestudio.loopback_count", taskpacket.loopback_count)

        intent = await get_latest_for_taskpacket(session, taskpacket_id)
        if intent is None:
            raise ValueError(f"No IntentSpec found for TaskPacket {taskpacket_id}")

        # Transition back to in_progress for retry
        await update_status(session, taskpacket_id, TaskPacketStatus.IN_PROGRESS)

        # Build failure context for the agent
        failure_details = "\n".join(
            f"- {check.name}: {'PASSED' if check.passed else 'FAILED'} — {check.details}"
            for check in verification_result.checks
        )

        system_prompt = build_system_prompt(intent, taskpacket)
        user_prompt = (
            f"Your previous implementation attempt failed verification checks. "
            f"This is loopback attempt {taskpacket.loopback_count}.\n\n"
            f"## Verification Results\n\n{failure_details}\n\n"
            f"Fix the issues identified above. The original goal was:\n\n"
            f"{intent.goal}\n\n"
            f"Focus on fixing the failing checks while maintaining the original intent."
        )

        logger.info(
            "Starting loopback %d for TaskPacket %s",
            taskpacket.loopback_count,
            taskpacket_id,
        )
        agent_summary = await _run_agent(system_prompt, user_prompt, repo_path, role_config)

        # --- A3+A4: Record spend and audit after agent call ---
        if provider is not None:
            prompt_tokens = _estimate_tokens(system_prompt, user_prompt)
            response_tokens = _estimate_tokens(agent_summary)
            estimated_cost = (prompt_tokens + response_tokens) * provider.cost_per_1k_tokens / 1000
            _record_audit_and_spend(
                taskpacket_correlation_id=taskpacket.correlation_id,
                taskpacket_id=taskpacket_id,
                provider=provider,
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                estimated_cost=estimated_cost,
            )

        changed_files = _parse_changed_files(agent_summary)
        evidence = EvidenceBundle(
            taskpacket_id=taskpacket_id,
            intent_version=intent.version,
            files_changed=changed_files,
            agent_summary=agent_summary,
            loopback_attempt=taskpacket.loopback_count,
        )

        span.set_attribute("thestudio.files_changed_count", len(changed_files))
        return evidence
