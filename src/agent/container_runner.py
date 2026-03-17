"""Container runner — in-container entrypoint for the Primary Agent.

Epic 25 Story 25.1: Reads AgentTaskInput from /workspace/task.json,
executes the Primary Agent logic, and writes AgentContainerResult to
/workspace/result.json. Exit code 0 on success, 1 on failure.

This module runs INSIDE the ephemeral Docker container. It has:
- Filesystem access to the cloned repo (mounted at /workspace/repo)
- Outbound HTTPS to GitHub and Anthropic APIs
- No access to PostgreSQL, Temporal, NATS, or FastAPI admin

Communication with the platform is exclusively via the mounted volume.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agent.container_protocol import AgentContainerResult, AgentTaskInput
    from src.agent.framework import AgentResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("thestudio.container_runner")


def _read_task_input() -> dict:
    """Read and parse the task input JSON file."""
    from src.agent.container_protocol import TASK_INPUT_PATH

    path = Path(TASK_INPUT_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Task input not found at {TASK_INPUT_PATH}")

    return json.loads(path.read_text(encoding="utf-8"))


def _write_result(result_data: dict) -> None:
    """Write the result JSON file."""
    from src.agent.container_protocol import RESULT_OUTPUT_PATH

    path = Path(RESULT_OUTPUT_PATH)
    path.write_text(
        json.dumps(result_data, default=str, indent=2),
        encoding="utf-8",
    )


def _build_evidence_bundle(
    task_input: AgentTaskInput,
    agent_result: AgentResult,
) -> AgentContainerResult:
    """Convert an AgentResult into an AgentContainerResult."""
    from src.agent.container_protocol import AgentContainerResult

    files_changed: list[str] = []
    if agent_result.raw_output:
        for match in re.finditer(
            r"(?:modified|created|changed|edited|added|deleted|updated)\s*:?\s*[`\"']?([^\s`\"']+\.\w+)",
            agent_result.raw_output,
            re.IGNORECASE,
        ):
            filepath = match.group(1)
            if filepath not in files_changed:
                files_changed.append(filepath)

    return AgentContainerResult(
        success=not agent_result.used_fallback,
        files_changed=files_changed,
        agent_summary=agent_result.raw_output,
        intent_version=1,
        tokens_used=agent_result.tokens_in + agent_result.tokens_out,
        cost_usd=agent_result.cost_estimated,
        duration_ms=agent_result.duration_ms,
        exit_reason="completed",
    )


async def _run_agent(task_input: AgentTaskInput) -> AgentContainerResult:
    """Execute the Primary Agent using AgentRunner."""

    from src.agent.container_protocol import AgentContainerResult
    from src.agent.framework import AgentConfig, AgentContext, AgentRunner

    config = AgentConfig(
        agent_name="primary_agent",
        pipeline_step="implement",
        model_class="strong",
        system_prompt_template="{system_prompt}",
        tool_allowlist=task_input.tool_allowlist,
        max_turns=task_input.max_turns,
        max_budget_usd=task_input.max_budget_usd,
    )

    context = AgentContext(
        taskpacket_id=task_input.taskpacket_id,
        correlation_id=task_input.correlation_id,
        repo=task_input.repo_url,
        issue_title=task_input.intent_goal,
        repo_tier=task_input.repo_tier,
        complexity=task_input.complexity,
        risk_flags=task_input.risk_flags,
        extra={
            "system_prompt": task_input.system_prompt,
            "repo_path": "/workspace/repo",
        },
    )

    runner = AgentRunner(config)

    try:
        result = await runner.run(context)
        return _build_evidence_bundle(task_input, result)
    except Exception as exc:
        logger.exception("Agent execution failed: %s", exc)
        return AgentContainerResult(
            success=False,
            exit_reason="error",
            error_message=str(exc),
        )


async def main() -> int:
    """Container entrypoint: read task, run agent, write result."""
    from src.agent.container_protocol import AgentContainerResult, AgentTaskInput

    start_ms = int(time.monotonic() * 1000)

    logger.info("container_runner.start")

    try:
        raw = _read_task_input()
        task_input = AgentTaskInput.model_validate(raw)
        logger.info(
            "container_runner.task_loaded",
            extra={
                "taskpacket_id": str(task_input.taskpacket_id),
                "correlation_id": str(task_input.correlation_id),
                "loopback_attempt": task_input.loopback_attempt,
            },
        )
    except Exception as exc:
        logger.error("container_runner.task_load_failed: %s", exc)
        _write_result(
            AgentContainerResult(
                success=False,
                exit_reason="input_error",
                error_message=str(exc),
            ).model_dump(mode="json"),
        )
        return 1

    result = await _run_agent(task_input)
    elapsed = int(time.monotonic() * 1000) - start_ms
    result.duration_ms = elapsed

    _write_result(result.model_dump(mode="json"))
    logger.info(
        "container_runner.complete",
        extra={
            "success": result.success,
            "duration_ms": elapsed,
            "files_changed": len(result.files_changed),
            "exit_reason": result.exit_reason,
        },
    )
    return 0 if result.success else 1


if __name__ == "__main__":
    import asyncio

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
