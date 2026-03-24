"""Unit tests for Epic 51-git: git-missing and dirty-repo hardening.

Covers:
- _git_changed_paths() sets _last_git_available=False on FileNotFoundError
- _git_changed_paths() sets _last_git_available=True on success
- Pre-iteration delta: only newly-dirty files count for stall detection
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ralph_sdk.agent import RalphAgent
from ralph_sdk.config import RalphConfig
from ralph_sdk.state import NullStateBackend


def _make_agent(tmp_path: Path) -> RalphAgent:
    """Create a minimal RalphAgent wired to a temp directory."""
    # The agent derives ralph_dir as project_dir / config.ralph_dir (".ralph")
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    (ralph_dir / "logs").mkdir()
    cfg = RalphConfig(max_iterations=1)
    return RalphAgent(
        project_dir=tmp_path,
        config=cfg,
        state_backend=NullStateBackend(),
    )


@pytest.mark.asyncio
async def test_git_changed_paths_sets_unavailable_on_file_not_found(
    tmp_path: Path,
) -> None:
    """FileNotFoundError from subprocess → _last_git_available=False, returns []."""
    agent = _make_agent(tmp_path)
    agent._last_git_available = True  # start as True

    with patch(
        "asyncio.create_subprocess_exec",
        side_effect=FileNotFoundError("git: not found"),
    ):
        result = await agent._git_changed_paths()

    assert result == []
    assert agent._last_git_available is False


@pytest.mark.asyncio
async def test_git_changed_paths_sets_unavailable_on_os_error(
    tmp_path: Path,
) -> None:
    """Generic OSError from subprocess → _last_git_available=False, returns []."""
    agent = _make_agent(tmp_path)

    with patch(
        "asyncio.create_subprocess_exec",
        side_effect=OSError("permission denied"),
    ):
        result = await agent._git_changed_paths()

    assert result == []
    assert agent._last_git_available is False


@pytest.mark.asyncio
async def test_git_changed_paths_sets_available_on_success(
    tmp_path: Path,
) -> None:
    """Successful git invocation → _last_git_available=True, returns file list."""
    agent = _make_agent(tmp_path)
    agent._last_git_available = False  # start as False

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"src/foo.py\nsrc/bar.py\n", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("asyncio.wait_for", new=AsyncMock(return_value=(b"src/foo.py\nsrc/bar.py\n", b""))):
            result = await agent._git_changed_paths()

    assert agent._last_git_available is True
    assert "src/foo.py" in result
    assert "src/bar.py" in result


@pytest.mark.asyncio
async def test_git_changed_paths_returns_empty_on_nonzero_exit(
    tmp_path: Path,
) -> None:
    """Non-zero returncode → empty list (but git WAS available)."""
    agent = _make_agent(tmp_path)

    mock_proc = MagicMock()
    mock_proc.returncode = 128  # typical git error
    mock_proc.communicate = AsyncMock(return_value=(b"", b"fatal: not a git repo"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("asyncio.wait_for", new=AsyncMock(return_value=(b"", b"fatal: not a git repo"))):
            result = await agent._git_changed_paths()

    assert result == []
    # returncode != 0 still means git was found; _last_git_available reflects
    # the subprocess launch succeeded (no exception raised)
    assert agent._last_git_available is True


@pytest.mark.asyncio
async def test_pre_iteration_delta_excludes_pre_existing_dirty_files(
    tmp_path: Path,
) -> None:
    """Files dirty BEFORE the iteration must not count toward files_changed_count.

    Arrange:
      - Pre-iteration snapshot returns ["old_dirty.py"]
      - Post-iteration snapshot returns ["old_dirty.py", "new_change.py"]
    Expect:
      - _last_iteration_files_changed == ["new_change.py"] (delta only)
    """
    agent = _make_agent(tmp_path)

    pre_snapshot = ["old_dirty.py"]
    post_snapshot = ["old_dirty.py", "new_change.py"]
    call_count = 0

    async def fake_git_changed_paths() -> list[str]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Pre-iteration call
            agent._last_git_available = True
            return pre_snapshot
        # Post-iteration call
        agent._last_git_available = True
        return post_snapshot

    agent._git_changed_paths = fake_git_changed_paths  # type: ignore[method-assign]

    # Simulate a successful Claude CLI run returning a trivial status
    from ralph_sdk.status import RalphLoopStatus, RalphStatus

    fake_status = RalphStatus(status=RalphLoopStatus.IN_PROGRESS)

    with patch.object(agent, "_build_iteration_prompt", return_value="prompt"):
        with patch.object(agent, "_build_claude_command", return_value=["echo", "hi"]):
            with patch.object(agent, "_increment_call_count", new=AsyncMock()):
                with patch.object(agent, "_parse_response", return_value=fake_status):
                    with patch.object(agent, "_save_session", new=AsyncMock()):
                        with patch.object(agent, "_log_output"):
                            # Patch subprocess so nothing actually runs
                            mock_proc = MagicMock()
                            mock_proc.returncode = 0
                            stdout_bytes = b"---RALPH_STATUS---\nSTATUS: IN_PROGRESS\n---END_RALPH_STATUS---"
                            mock_proc.communicate = AsyncMock(
                                return_value=(stdout_bytes, b"")
                            )
                            with patch(
                                "asyncio.create_subprocess_exec",
                                return_value=mock_proc,
                            ):
                                with patch(
                                    "asyncio.wait_for",
                                    new=AsyncMock(return_value=(stdout_bytes, b"")),
                                ):
                                    from ralph_sdk.agent import TaskInput

                                    task_input = TaskInput(prompt="test task")
                                    await agent.run_iteration(task_input)

    # Delta should only contain the newly-dirty file
    assert agent._last_iteration_files_changed == ["new_change.py"]
    # Session set should contain ALL post dirty files
    assert "old_dirty.py" in agent._files_changed_session
    assert "new_change.py" in agent._files_changed_session


@pytest.mark.asyncio
async def test_pre_iteration_delta_all_new_when_pre_was_clean(
    tmp_path: Path,
) -> None:
    """When repo was clean before iteration, all post-dirty files count."""
    agent = _make_agent(tmp_path)

    pre_snapshot: list[str] = []
    post_snapshot = ["src/foo.py", "tests/test_foo.py"]
    call_count = 0

    async def fake_git_changed_paths() -> list[str]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            agent._last_git_available = True
            return pre_snapshot
        agent._last_git_available = True
        return post_snapshot

    agent._git_changed_paths = fake_git_changed_paths  # type: ignore[method-assign]

    from ralph_sdk.status import RalphLoopStatus, RalphStatus

    fake_status = RalphStatus(status=RalphLoopStatus.IN_PROGRESS)

    with patch.object(agent, "_build_iteration_prompt", return_value="prompt"):
        with patch.object(agent, "_build_claude_command", return_value=["echo", "hi"]):
            with patch.object(agent, "_increment_call_count", new=AsyncMock()):
                with patch.object(agent, "_parse_response", return_value=fake_status):
                    with patch.object(agent, "_save_session", new=AsyncMock()):
                        with patch.object(agent, "_log_output"):
                            mock_proc = MagicMock()
                            mock_proc.returncode = 0
                            stdout_bytes = b"---RALPH_STATUS---\nSTATUS: IN_PROGRESS\n---END_RALPH_STATUS---"
                            mock_proc.communicate = AsyncMock(
                                return_value=(stdout_bytes, b"")
                            )
                            with patch(
                                "asyncio.create_subprocess_exec",
                                return_value=mock_proc,
                            ):
                                with patch(
                                    "asyncio.wait_for",
                                    new=AsyncMock(return_value=(stdout_bytes, b"")),
                                ):
                                    from ralph_sdk.agent import TaskInput

                                    task_input = TaskInput(prompt="test task")
                                    await agent.run_iteration(task_input)

    assert set(agent._last_iteration_files_changed) == {"src/foo.py", "tests/test_foo.py"}
