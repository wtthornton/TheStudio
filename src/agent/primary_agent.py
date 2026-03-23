"""Primary Agent — implements code changes from an Intent Specification.

Uses the Unified Agent Framework (AgentRunner) with the Developer role
to implement changes, produce an evidence bundle, and support verification
loopbacks.

When THESTUDIO_AGENT_MODE=ralph, dispatches to RalphAgent from ralph_sdk
(Epic 43) instead of the legacy PrimaryAgentRunner. The function signatures
for implement() and handle_loopback() are unchanged.

Architecture reference: thestudioarc/08-agent-roles.md
Epic reference: Story 0.5 — Primary Agent
Epic 23 Story 1.8: Refactored to use AgentRunner framework.
Epic 43 Story 43.4: Added Ralph SDK dispatch path.
"""

import logging
import tempfile
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.developer_role import (
    DEFAULT_TOOL_ALLOWLIST,
    DeveloperRoleConfig,
    build_system_prompt,
)
from src.agent.evidence import EvidenceBundle
from src.agent.framework import AgentConfig, AgentContext, AgentRunner
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


# ---------------------------------------------------------------------------
# Developer Agent Configuration
# ---------------------------------------------------------------------------


def _make_developer_config(
    role_config: DeveloperRoleConfig | None = None,
) -> AgentConfig:
    """Build an AgentConfig for the Developer role.

    When *role_config* is provided, its values override the defaults.
    Otherwise, settings-based defaults are used.
    """
    if role_config is not None:
        return AgentConfig(
            agent_name="developer",
            pipeline_step="primary_agent",
            tool_allowlist=role_config.tool_allowlist,
            max_turns=role_config.max_turns,
            max_budget_usd=role_config.max_budget_usd,
            permission_mode=role_config.permission_mode,
        )
    return AgentConfig(
        agent_name="developer",
        pipeline_step="primary_agent",
        tool_allowlist=list(DEFAULT_TOOL_ALLOWLIST),
        max_turns=settings.agent_max_turns,
        max_budget_usd=settings.agent_max_budget_usd,
        permission_mode="acceptEdits",
    )


class PrimaryAgentRunner(AgentRunner):
    """AgentRunner subclass for the Primary Agent.

    Overrides prompt building to use pre-built prompts from IntentSpec
    and TaskPacket, passed via ``context.extra``.
    """

    def build_system_prompt(self, context: AgentContext) -> str:
        """Return the pre-built system prompt from context.extra."""
        return context.extra["system_prompt"]

    def build_user_prompt(self, context: AgentContext) -> str:
        """Return the pre-built user prompt from context.extra."""
        return context.extra["user_prompt"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Ralph SDK dispatch (Epic 43 — Story 43.4)
# ---------------------------------------------------------------------------


async def _implement_ralph(
    taskpacket: object,  # TaskPacketRow — avoid circular import at module level
    intent: object,  # IntentSpecRead
    repo_path: str,
    loopback_context: str = "",
    complexity: str = "",
) -> EvidenceBundle:
    """Implement using RalphAgent with NullStateBackend (Slice 1 — no persistence).

    Builds the task input from the Ralph bridge, writes it to a temp directory
    that RalphAgent expects, then runs the agent loop and converts the result
    to an EvidenceBundle.

    Session persistence (PostgresStateBackend) is added in Slice 2 (Story 43.6).

    Args:
        taskpacket: TaskPacketRow ORM object.
        intent: IntentSpecRead for the current version.
        repo_path: Local path to the target repository (working directory for Ralph).
        loopback_context: Formatted verification failures for retry passes.
        complexity: Complexity hint string from the caller.

    Returns:
        EvidenceBundle from the Ralph run.
    """
    # Late imports keep ralph_sdk out of the module-level dependency graph
    # so legacy mode works without the SDK installed.
    from ralph_sdk import NullStateBackend, RalphAgent
    from ralph_sdk.converters import from_task_packet

    from src.agent.ralph_bridge import (
        build_ralph_config,
        ralph_result_to_evidence,
        taskpacket_to_ralph_input,
    )

    packet_input, intent_input = taskpacket_to_ralph_input(
        taskpacket,  # type: ignore[arg-type]
        intent,  # type: ignore[arg-type]
        loopback_context=loopback_context,
        complexity_hint=complexity,
    )

    ralph_config = build_ralph_config(
        model_id=settings.agent_model,
        max_turns=settings.agent_max_turns,
        complexity=packet_input.intent.complexity,
    )

    # Build the TaskInput the agent will read from .ralph/PROMPT.md
    task_input = from_task_packet(
        packet_input,
        intent_input,
        loopback_context=loopback_context,
    )

    # Write task input to a temp directory (RalphAgent reads from .ralph/)
    with tempfile.TemporaryDirectory() as tmpdir:
        ralph_dir = Path(tmpdir) / ".ralph"
        ralph_dir.mkdir(parents=True, exist_ok=True)

        # Write PROMPT.md with the full task prompt
        (ralph_dir / "PROMPT.md").write_text(task_input.prompt, encoding="utf-8")

        # Write agent instructions to AGENT.md if present
        if task_input.agent_instructions:
            (ralph_dir / "AGENT.md").write_text(
                task_input.agent_instructions, encoding="utf-8"
            )

        agent = RalphAgent(
            config=ralph_config,
            project_dir=repo_path or tmpdir,
            state_backend=NullStateBackend(),
            correlation_id=str(getattr(taskpacket, "correlation_id", "")),
        )

        # Ensure agent reads from our temp ralph_dir (not repo_path/.ralph)
        agent.ralph_dir = ralph_dir

        result = await agent.run()

    taskpacket_id = taskpacket.id
    intent_version = intent.version
    loopback_attempt = getattr(taskpacket, "loopback_count", 0)

    return ralph_result_to_evidence(result, taskpacket_id, intent_version, loopback_attempt)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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
    """
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

        # Build framework config and context
        config = _make_developer_config(role_config)
        ctx = AgentContext(
            taskpacket_id=taskpacket_id,
            correlation_id=taskpacket.correlation_id,
            repo=getattr(taskpacket, "repo", ""),
            complexity=complexity,
            overlays=overlays or [],
            repo_tier=repo_tier,
            intent=intent,
            extra={
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "repo_path": repo_path,
            },
        )

        logger.info(
            "Starting Primary Agent for TaskPacket %s (intent v%d, mode=%s)",
            taskpacket_id,
            intent.version,
            settings.agent_mode,
        )

        # Dispatch to Ralph SDK when agent_mode="ralph" (Epic 43)
        if settings.agent_mode == "ralph":
            evidence = await _implement_ralph(
                taskpacket,
                intent,
                repo_path,
                loopback_context="",
                complexity=complexity,
            )
            span.set_attribute("thestudio.files_changed_count", len(evidence.files_changed))
            logger.info(
                "Primary Agent (ralph) completed for TaskPacket %s: %d files changed",
                taskpacket_id,
                len(evidence.files_changed),
            )
            return evidence

        # Legacy path: PrimaryAgentRunner (default)
        runner = PrimaryAgentRunner(config)
        result = await runner.run(ctx)

        span.set_attribute("thestudio.agent_model", result.model_used)

        # Build evidence bundle
        changed_files = _parse_changed_files(result.raw_output)
        evidence = EvidenceBundle(
            taskpacket_id=taskpacket_id,
            intent_version=intent.version,
            files_changed=changed_files,
            agent_summary=result.raw_output,
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
    """
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

        # Build framework config and context
        config = _make_developer_config(role_config)
        ctx = AgentContext(
            taskpacket_id=taskpacket_id,
            correlation_id=taskpacket.correlation_id,
            repo=getattr(taskpacket, "repo", ""),
            complexity=complexity,
            overlays=overlays or [],
            repo_tier=repo_tier,
            intent=intent,
            extra={
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "repo_path": repo_path,
            },
        )

        logger.info(
            "Starting loopback %d for TaskPacket %s (mode=%s)",
            taskpacket.loopback_count,
            taskpacket_id,
            settings.agent_mode,
        )

        # Dispatch to Ralph SDK when agent_mode="ralph" (Epic 43)
        if settings.agent_mode == "ralph":
            from src.agent.ralph_bridge import build_verification_loopback_context

            loopback_ctx = build_verification_loopback_context(verification_result)
            evidence = await _implement_ralph(
                taskpacket,
                intent,
                repo_path,
                loopback_context=loopback_ctx,
                complexity=complexity,
            )
            span.set_attribute("thestudio.files_changed_count", len(evidence.files_changed))
            return evidence

        # Legacy path: PrimaryAgentRunner
        runner = PrimaryAgentRunner(config)
        result = await runner.run(ctx)

        changed_files = _parse_changed_files(result.raw_output)
        evidence = EvidenceBundle(
            taskpacket_id=taskpacket_id,
            intent_version=intent.version,
            files_changed=changed_files,
            agent_summary=result.raw_output,
            loopback_attempt=taskpacket.loopback_count,
        )

        span.set_attribute("thestudio.files_changed_count", len(changed_files))
        return evidence
