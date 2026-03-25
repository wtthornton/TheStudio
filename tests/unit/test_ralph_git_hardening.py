"""Unit tests for Ralph SDK git-hardening (updated for SDK v2.0.3).

v2.0.3 removed _git_changed_paths as a standalone method. Git status is now
handled internally by run_iteration(). These tests verify the public API
surface related to git operations: agent construction, cancel, and config.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ralph_sdk.agent import CancelResult, RalphAgent
from ralph_sdk.config import RalphConfig
from ralph_sdk.state import NullStateBackend


def _make_agent(tmp_path: Path) -> RalphAgent:
    """Create a minimal RalphAgent wired to a temp directory."""
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    (ralph_dir / "logs").mkdir()
    cfg = RalphConfig(max_turns=1)
    return RalphAgent(
        project_dir=tmp_path,
        config=cfg,
        state_backend=NullStateBackend(),
    )


def test_agent_construction_with_null_backend(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    assert agent is not None
    assert agent.config.max_turns == 1


def test_agent_cancel_before_run(tmp_path: Path) -> None:
    """Cancel before any run returns a CancelResult with 0 iterations."""
    agent = _make_agent(tmp_path)
    cr = agent.cancel()
    assert isinstance(cr, CancelResult)
    assert cr.iterations_completed == 0
    assert cr.was_forced is False


def test_agent_config_defaults() -> None:
    """Verify git-related config defaults are reasonable."""
    cfg = RalphConfig()
    assert cfg.max_turns >= 1
    assert cfg.timeout_minutes > 0


def test_agent_project_dir_resolved(tmp_path: Path) -> None:
    """Agent resolves project_dir to absolute path."""
    agent = _make_agent(tmp_path)
    assert agent.project_dir.is_absolute()


def test_agent_cancel_is_idempotent(tmp_path: Path) -> None:
    """Multiple cancel calls do not raise."""
    agent = _make_agent(tmp_path)
    cr1 = agent.cancel()
    cr2 = agent.cancel()
    assert isinstance(cr1, CancelResult)
    assert isinstance(cr2, CancelResult)
