"""Container protocol — serialization models for agent task I/O.

Epic 25 Story 25.3: Defines AgentTaskInput and AgentContainerResult,
the contract between the Temporal activity (platform side) and the
container runner (agent side). Communication is via JSON files on a
mounted volume: /workspace/task.json → /workspace/result.json.

No database access, no network calls, no message queue.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentTaskInput(BaseModel):
    """Self-contained task description sent to the agent container.

    Serialized to /workspace/task.json by the Temporal activity.
    The container needs no database access or API access to TheStudio.
    """

    taskpacket_id: UUID
    correlation_id: UUID
    repo_url: str
    branch: str = "main"
    system_prompt: str
    tool_allowlist: list[str] = Field(default_factory=list)
    intent_goal: str = ""
    intent_constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    context_summary: str = ""
    max_turns: int = 30
    max_budget_usd: float = 5.0
    loopback_attempt: int = 0
    verification_feedback: str = ""
    repo_tier: str = "observe"
    complexity: str = "low"
    risk_flags: dict[str, bool] = Field(default_factory=dict)


class AgentContainerResult(BaseModel):
    """All output from an agent container run.

    Written to /workspace/result.json by the container runner.
    The Temporal activity reads this to reconstruct an EvidenceBundle.
    """

    success: bool
    files_changed: list[str] = Field(default_factory=list)
    test_results: str = ""
    lint_results: str = ""
    agent_summary: str = ""
    intent_version: int = 1
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    exit_reason: str = "completed"
    error_message: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Volume paths (constants for both sides of the protocol)
WORKSPACE_DIR = "/workspace"
TASK_INPUT_PATH = f"{WORKSPACE_DIR}/task.json"
RESULT_OUTPUT_PATH = f"{WORKSPACE_DIR}/result.json"
