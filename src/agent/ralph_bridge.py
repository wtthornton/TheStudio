"""Ralph SDK bridge — converts TheStudio domain models to/from Ralph SDK types.

This module is the translation layer between TheStudio's TaskPacket/IntentSpec
models and the Ralph SDK's TaskPacketInput/IntentSpecInput/TaskResult types.
It has no side effects and is fully unit-testable without a database.

Epic reference: Epic 43 Story 43.2 — Model Bridge
"""

from __future__ import annotations

import shutil
from uuid import UUID

from ralph_sdk.agent import TaskResult
from ralph_sdk.config import RalphConfig
from ralph_sdk.converters import (
    COMPLEXITY_MAX_TURNS,
    ComplexityBand,
    IntentSpecInput,
    RiskFlag,
    TaskPacketInput,
    TrustTier,
    get_max_turns,
)

from src.agent.evidence import EvidenceBundle
from src.intent.intent_spec import IntentSpecRead
from src.models.taskpacket import TaskPacketRow, TaskTrustTier
from src.verification.gate import VerificationResult

__all__ = [
    "build_ralph_config",
    "build_verification_loopback_context",
    "check_ralph_cli_available",
    "ralph_result_to_evidence",
    "taskpacket_to_ralph_input",
]

# ---------------------------------------------------------------------------
# Complexity mapping
# ---------------------------------------------------------------------------

_COMPLEXITY_BAND_MAP: dict[str, ComplexityBand] = {
    "low": ComplexityBand.LOW,
    "medium": ComplexityBand.MEDIUM,
    "moderate": ComplexityBand.MEDIUM,
    "high": ComplexityBand.HIGH,
}


def _map_complexity(
    complexity_index: dict[str, object] | None,
    complexity_hint: str = "",
) -> ComplexityBand:
    """Map TaskPacket complexity data to a Ralph ComplexityBand.

    Args:
        complexity_index: TaskPacket.complexity_index JSONB dict (may have 'band' key).
        complexity_hint: Free-text hint from the implement() caller (e.g. 'high').

    Returns:
        ComplexityBand for max_turns scaling.
    """
    if complexity_index and isinstance(complexity_index, dict):
        band_str = str(complexity_index.get("band", "")).lower()
        if band_str in _COMPLEXITY_BAND_MAP:
            return _COMPLEXITY_BAND_MAP[band_str]
    hint = complexity_hint.lower()
    if hint in _COMPLEXITY_BAND_MAP:
        return _COMPLEXITY_BAND_MAP[hint]
    return ComplexityBand.UNKNOWN


# ---------------------------------------------------------------------------
# Trust tier mapping
# ---------------------------------------------------------------------------

_TRUST_TIER_MAP: dict[TaskTrustTier, TrustTier] = {
    TaskTrustTier.EXECUTE: TrustTier.FULL,
    TaskTrustTier.SUGGEST: TrustTier.STANDARD,
    TaskTrustTier.OBSERVE: TrustTier.RESTRICTED,
}


def _map_trust_tier(task_trust_tier: TaskTrustTier | None) -> TrustTier:
    """Map TheStudio TaskTrustTier to Ralph TrustTier.

    Args:
        task_trust_tier: TaskPacket's trust tier (may be None for unassigned).

    Returns:
        Ralph TrustTier determining permission_mode for the agent.
    """
    if task_trust_tier is None:
        return TrustTier.STANDARD
    return _TRUST_TIER_MAP.get(task_trust_tier, TrustTier.STANDARD)


# ---------------------------------------------------------------------------
# Public bridge functions
# ---------------------------------------------------------------------------


def taskpacket_to_ralph_input(
    taskpacket: TaskPacketRow,
    intent: IntentSpecRead,
    loopback_context: str = "",
    complexity_hint: str = "",
) -> tuple[TaskPacketInput, IntentSpecInput]:
    """Convert TheStudio TaskPacket + IntentSpec to Ralph SDK input types.

    Produces the two typed input models consumed by
    ``ralph_sdk.converters.from_task_packet()``.

    Args:
        taskpacket: The TaskPacket ORM row.
        intent: The latest IntentSpec for the task.
        loopback_context: Formatted verification failure text for retry passes.
        complexity_hint: Optional free-text complexity hint from the caller.

    Returns:
        Tuple ``(TaskPacketInput, IntentSpecInput)`` ready for conversion.
    """
    complexity = _map_complexity(taskpacket.complexity_index, complexity_hint)
    trust_tier = _map_trust_tier(taskpacket.task_trust_tier)

    # Convert risk_flags dict[str, bool] -> list[RiskFlag]
    risk_flags: list[RiskFlag] = []
    if taskpacket.risk_flags and isinstance(taskpacket.risk_flags, dict):
        for flag_name, is_flagged in taskpacket.risk_flags.items():
            if is_flagged:
                risk_flags.append(
                    RiskFlag(
                        category=flag_name,
                        severity="medium",
                        description=f"Risk flag raised: {flag_name}",
                    )
                )

    intent_input = IntentSpecInput(
        goal=intent.goal,
        constraints=intent.constraints,
        acceptance_criteria=intent.acceptance_criteria,
        non_goals=intent.non_goals,
        risk_flags=risk_flags,
        trust_tier=trust_tier,
        complexity=complexity,
    )

    packet_input = TaskPacketInput(
        id=str(taskpacket.id),
        type="implementation",
        intent=intent_input,
        loopback_context=loopback_context,
        loopback_attempt=taskpacket.loopback_count,
        expert_outputs=[],
        payload={
            "repo": taskpacket.repo,
            "issue_id": taskpacket.issue_id,
        },
    )

    return packet_input, intent_input


def ralph_result_to_evidence(
    result: TaskResult,
    taskpacket_id: UUID,
    intent_version: int,
    loopback_attempt: int,
) -> EvidenceBundle:
    """Convert Ralph SDK TaskResult to TheStudio EvidenceBundle.

    Args:
        result: The TaskResult returned by ``RalphAgent.run()``.
        taskpacket_id: UUID of the TaskPacket that was implemented.
        intent_version: Version of the IntentSpec that was used.
        loopback_attempt: Current loopback attempt count from the TaskPacket.

    Returns:
        EvidenceBundle suitable for downstream Verification and Publisher stages.
    """
    # Compose agent_summary from progress_summary and raw output
    summary_parts: list[str] = []
    if result.status.progress_summary:
        summary_parts.append(result.status.progress_summary)
    if result.output:
        summary_parts.append(result.output)
    agent_summary = "\n\n".join(summary_parts)

    structured = list(getattr(result, "files_changed", None) or [])
    changed_files = structured if structured else _parse_changed_files(agent_summary)

    return EvidenceBundle(
        taskpacket_id=taskpacket_id,
        intent_version=intent_version,
        files_changed=changed_files,
        agent_summary=agent_summary,
        loopback_attempt=loopback_attempt,
    )


def _parse_changed_files(text: str) -> list[str]:
    """Extract file paths from agent output (matches primary_agent heuristic).

    Looks for bullet-list lines starting with '- ' that contain
    file-path-like strings (with a dot or slash).
    """
    files: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and ("." in stripped or "/" in stripped):
            parts = stripped[2:].split()
            if parts:
                candidate = parts[0].rstrip(":")
                if "." in candidate or "/" in candidate:
                    files.append(candidate)
    return files


def build_ralph_config(
    model_id: str = "",
    max_turns: int = 30,
    complexity: ComplexityBand = ComplexityBand.UNKNOWN,
) -> RalphConfig:
    """Build a RalphConfig for TheStudio-embedded operation.

    The config is intentionally minimal for Slice 1 (NullStateBackend).
    Cost tracking and model routing are added in Slice 3 (Story 43.10-43.12).

    Args:
        model_id: Claude model ID from TheStudio's model gateway (unused in Slice 1
            because the embedded agent inherits the active Claude session).
        max_turns: Base max_turns from TheStudio settings.
        complexity: Task complexity band for max_turns scaling.

    Returns:
        RalphConfig ready for ``RalphAgent.__init__()``.
    """
    # Scale max_turns by complexity (take the higher of the two)
    effective_max_turns = max(max_turns, get_max_turns(complexity))

    return RalphConfig(
        project_name="thestudio-task",
        project_type="python",
        max_turns=effective_max_turns,
        output_format="json",
        session_continuity=True,
    )


def check_ralph_cli_available() -> bool:
    """Return True if the Claude CLI binary ('claude') is available in PATH.

    Used by the health endpoint (Story 43.13) and startup probe to verify
    that Ralph mode can actually execute before switching away from legacy mode.

    Returns:
        True if 'claude' binary found via shutil.which(), False otherwise.
    """
    return shutil.which("claude") is not None


def build_verification_loopback_context(verification_result: VerificationResult) -> str:
    """Format VerificationResult failures as markdown for Ralph's loopback context.

    The formatted string is injected as the ``loopback_context`` field in
    ``TaskPacketInput``, which ``from_task_packet()`` prepends to the prompt
    as a ``## Retry Context`` section.

    Args:
        verification_result: The failed VerificationResult from the gate.

    Returns:
        Markdown-formatted string describing each check's pass/fail status.
    """
    if not verification_result.checks:
        return "Verification failed with no check details available."

    lines: list[str] = ["The following verification checks failed. Fix all failing checks.\n"]
    for check in verification_result.checks:
        status_icon = "✅ PASSED" if check.passed else "❌ FAILED"
        lines.append(f"### {check.name}: {status_icon}")
        if check.details:
            lines.append("")
            lines.append(check.details)
        lines.append("")

    return "\n".join(lines)


# Expose COMPLEXITY_MAX_TURNS for tests that verify scaling behaviour
__all__ += ["COMPLEXITY_MAX_TURNS", "ComplexityBand", "TrustTier"]
