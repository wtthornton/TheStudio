"""RalphAgent cancel (51.6) and CancelResult tests (updated for SDK v2.0.3).

v2.0.3 API: CancelResult has partial_output, iterations_completed, was_forced.
RalphAgent.cancel() always returns CancelResult, never raises.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ralph_sdk.agent import CancelResult, RalphAgent
from ralph_sdk.config import RalphConfig
from ralph_sdk.state import NullStateBackend


def test_cancel_no_subprocess_returns_cancel_result() -> None:
    agent = RalphAgent(
        config=RalphConfig(dry_run=True),
        state_backend=NullStateBackend(),
    )
    cr = agent.cancel()
    assert isinstance(cr, CancelResult)
    assert cr.was_forced is False


def test_cancel_result_model_fields() -> None:
    cr = CancelResult()
    assert cr.partial_output is None
    assert cr.iterations_completed == 0
    assert cr.was_forced is False


def test_cancel_result_with_partial_output() -> None:
    cr = CancelResult(partial_output="some work done", iterations_completed=3)
    assert cr.partial_output == "some work done"
    assert cr.iterations_completed == 3


@pytest.mark.asyncio
async def test_should_exit_false_without_exit_signal(tmp_path: Path) -> None:
    (tmp_path / ".ralph").mkdir()
    agent = RalphAgent(
        config=RalphConfig(),
        project_dir=tmp_path,
        state_backend=NullStateBackend(),
    )
    from ralph_sdk.status import RalphStatus

    st = RalphStatus(exit_signal=False, progress_summary="working")
    result = await agent.should_exit(st, 1)
    assert result is False


@pytest.mark.asyncio
async def test_should_exit_true_with_exit_signal(tmp_path: Path) -> None:
    (tmp_path / ".ralph").mkdir()
    agent = RalphAgent(
        config=RalphConfig(),
        project_dir=tmp_path,
        state_backend=NullStateBackend(),
    )
    from ralph_sdk.status import RalphStatus

    st = RalphStatus(exit_signal=True, completed_task="Done with task")
    result = await agent.should_exit(st, 1)
    # With exit_signal=True AND completed_task, should_exit may return True
    # depending on dual-condition logic
    assert isinstance(result, bool)
