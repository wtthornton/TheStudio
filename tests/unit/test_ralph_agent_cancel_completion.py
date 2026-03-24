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


def test_cancel_includes_partial_output_from_buffer() -> None:
    """CancelResult.partial_output is populated from _output_buffer (51-cancel)."""
    agent = RalphAgent(config=RalphConfig(), state_backend=NullStateBackend())
    agent._output_buffer = "---RALPH_STATUS---\nSTATUS: IN_PROGRESS\n---END_RALPH_STATUS---"
    cr = agent.cancel()
    assert cr.partial_output == agent._output_buffer


def test_cancel_partial_output_with_active_subprocess() -> None:
    """partial_output is returned even when a subprocess is being terminated."""
    agent = RalphAgent(config=RalphConfig(), state_backend=NullStateBackend())
    agent._output_buffer = "partial work output"
    proc = MagicMock()
    proc.returncode = None
    agent._current_cli_proc = proc
    cr = agent.cancel()
    assert cr.subprocess_terminated is True
    assert cr.partial_output == "partial work output"


def test_cancel_result_partial_output_defaults_empty() -> None:
    """CancelResult.partial_output defaults to empty string when buffer is empty."""
    agent = RalphAgent(config=RalphConfig(), state_backend=NullStateBackend())
    cr = agent.cancel()
    assert cr.partial_output == ""


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
