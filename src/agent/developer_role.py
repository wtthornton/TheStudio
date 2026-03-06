"""Developer role configuration for the Primary Agent.

Defines the system prompt template, tool allowlist, and model settings
for the Developer base role (Phase 0 — single role, no Router/Assembler).

Architecture reference: thestudioarc/08-agent-roles.md — Developer role
"""

from dataclasses import dataclass, field

from src.intent.intent_spec import IntentSpecRead
from src.models.taskpacket import TaskPacketRead

# Tools the Developer role is allowed to use (Phase 0 — conservative)
DEFAULT_TOOL_ALLOWLIST: list[str] = [
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
]

DEVELOPER_SYSTEM_PROMPT = """\
You are a Developer Agent for TheStudio. Your job is to implement code changes \
in a target repository according to a precise Intent Specification.

## Rules

1. Implement ONLY what the intent goal describes. Do not add features, refactor \
unrelated code, or make "improvements" beyond what is specified.
2. Respect all constraints listed in the intent. If a constraint says "no new \
dependencies," do not add dependencies.
3. Write tests that map to the acceptance criteria when possible.
4. Produce small, focused diffs. Prefer editing existing files over creating new ones.
5. Do not modify files outside the repository working directory.
6. After making changes, run the repository's lint and test commands to verify \
your work before finishing.

## Intent Specification

**Goal:** {goal}

**Constraints:**
{constraints}

**Acceptance Criteria:**
{acceptance_criteria}

**Non-Goals (do NOT do these):**
{non_goals}

## Context

- Repository: {repo}
- TaskPacket ID: {taskpacket_id}
- Complexity: {complexity}
- Risk flags: {risk_flags}

## Output

When you are done, summarize what you changed in a structured format:
- Files changed (list each file and what was modified)
- Tests added or modified
- Any issues encountered
"""


@dataclass(frozen=True)
class DeveloperRoleConfig:
    """Configuration for the Developer base role."""

    tool_allowlist: list[str] = field(default_factory=lambda: list(DEFAULT_TOOL_ALLOWLIST))
    model: str = "claude-sonnet-4-5"
    max_turns: int = 30
    max_budget_usd: float = 5.0
    permission_mode: str = "acceptEdits"


def build_system_prompt(
    intent: IntentSpecRead,
    taskpacket: TaskPacketRead,
) -> str:
    """Build the Developer role system prompt from intent and taskpacket context."""
    constraints = (
        "\n".join(f"- {c}" for c in intent.constraints) if intent.constraints else "- None"
    )
    criteria = (
        "\n".join(f"- {c}" for c in intent.acceptance_criteria)
        if intent.acceptance_criteria
        else "- None"
    )
    non_goals = "\n".join(f"- {ng}" for ng in intent.non_goals) if intent.non_goals else "- None"
    risk_flags_str = (
        ", ".join(f"{k}={v}" for k, v in taskpacket.risk_flags.items())
        if taskpacket.risk_flags
        else "none"
    )

    return DEVELOPER_SYSTEM_PROMPT.format(
        goal=intent.goal,
        constraints=constraints,
        acceptance_criteria=criteria,
        non_goals=non_goals,
        repo=taskpacket.repo,
        taskpacket_id=taskpacket.id,
        complexity=taskpacket.complexity_index or "unknown",
        risk_flags=risk_flags_str,
    )
