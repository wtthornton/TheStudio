"""RalphAgent cancel (51.6) and completion-indicator decay (evaluation §1.6)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ralph_sdk.agent import CancelResult, RalphAgent
from ralph_sdk.config import RalphConfig
from ralph_sdk.state import NullStateBackend
from ralph_sdk.status import RalphStatus


@pytest.mark.asyncio
async def test_cancel_no_subprocess_returns_cancel_result(tmp_path: Path) -> None:
    agent = RalphAgent(
        config=RalphConfig(dry_run=True),
        project_dir=tmp_path,
        state_backend=NullStateBackend(),
    )
    cr = agent.cancel()
    assert isinstance(cr, CancelResult)
    assert cr.requested is True
    assert cr.subprocess_terminated is False


def test_cancel_terminates_active_subprocess() -> None:
    agent = RalphAgent(config=RalphConfig(), state_backend=NullStateBackend())
    proc = MagicMock()
    proc.returncode = None
    agent._current_cli_proc = proc
    cr = agent.cancel()
    assert cr.subprocess_terminated is True
    proc.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_should_exit_resets_indicators_on_progress_without_exit_signal(
    tmp_path: Path,
) -> None:
    (tmp_path / ".ralph").mkdir()
    agent = RalphAgent(
        config=RalphConfig(),
        project_dir=tmp_path,
        state_backend=NullStateBackend(),
    )
    agent._completion_indicators = 5
    agent._last_iteration_files_changed = ["src/foo.py"]
    st = RalphStatus(exit_signal=False, progress_summary="")
    await agent.should_exit(st, 1)
    assert agent._completion_indicators == 0


@pytest.mark.asyncio
async def test_should_exit_completed_task_clears_without_exit_signal(
    tmp_path: Path,
) -> None:
    (tmp_path / ".ralph").mkdir()
    agent = RalphAgent(
        config=RalphConfig(),
        project_dir=tmp_path,
        state_backend=NullStateBackend(),
    )
    agent._completion_indicators = 3
    agent._last_iteration_files_changed = []
    st = RalphStatus(exit_signal=False, completed_task="Ticked one checkbox", progress_summary="")
    await agent.should_exit(st, 1)
    assert agent._completion_indicators == 0
