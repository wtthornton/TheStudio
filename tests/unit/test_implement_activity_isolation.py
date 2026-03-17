"""Tests for implement_activity container/process mode branching (Epic 25 Story 25.4).

Validates that implement_activity correctly branches between in-process and
container modes based on the THESTUDIO_AGENT_ISOLATION setting, and that
per-tier resource limits (Story 25.6) flow through correctly.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.workflow.activities import ImplementInput, ImplementOutput


def _make_impl_input(**overrides) -> ImplementInput:
    defaults = {
        "taskpacket_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "repo_path": "/tmp/test-repo",
        "loopback_attempt": 0,
        "repo_tier": "observe",
    }
    defaults.update(overrides)
    return ImplementInput(**defaults)


def _mock_settings(**overrides):
    """Create a mock settings object with container isolation defaults."""
    s = MagicMock()
    s.agent_isolation = overrides.get("agent_isolation", "process")
    s.agent_isolation_fallback = overrides.get(
        "agent_isolation_fallback",
        {"observe": "allow", "suggest": "allow", "execute": "deny"},
    )
    s.agent_container_cpu_limit = overrides.get(
        "agent_container_cpu_limit",
        {"observe": 1.0, "suggest": 2.0, "execute": 4.0},
    )
    s.agent_container_memory_mb = overrides.get(
        "agent_container_memory_mb",
        {"observe": 512, "suggest": 1024, "execute": 2048},
    )
    s.agent_container_timeout_seconds = overrides.get(
        "agent_container_timeout_seconds",
        {"observe": 300, "suggest": 600, "execute": 1200},
    )
    return s


class TestImplementActivityProcessMode:
    """In-process mode (default) — existing behavior."""

    @pytest.mark.asyncio
    async def test_process_mode_default(self):
        """Default agent_isolation='process' runs in-process."""
        params = _make_impl_input()
        mock_s = _mock_settings(agent_isolation="process")

        with patch("src.settings.settings", mock_s):
            result = await _run_implement(params)

        assert isinstance(result, ImplementOutput)
        assert result.taskpacket_id == params.taskpacket_id
        assert result.agent_summary == "Implementation placeholder"


class TestImplementActivityContainerMode:
    """Container mode — delegates to ContainerManager."""

    @pytest.mark.asyncio
    async def test_container_mode_launches_container(self):
        """When active and Docker available, launches container."""
        params = _make_impl_input(repo_tier="suggest")
        mock_s = _mock_settings(agent_isolation="container")

        mock_outcome = MagicMock()
        mock_outcome.result = MagicMock()
        mock_outcome.result.intent_version = 1
        mock_outcome.result.files_changed = ["src/fix.py"]
        mock_outcome.result.agent_summary = "Fixed the bug"
        mock_outcome.container_id = "abc123"
        mock_outcome.exit_code = 0
        mock_outcome.timed_out = False
        mock_outcome.oom_killed = False
        mock_outcome.total_ms = 5000

        with (
            patch("src.settings.settings", mock_s),
            patch(
                "src.agent.container_manager.ContainerManager"
                ".is_docker_available",
                return_value=True,
            ),
            patch(
                "src.agent.container_manager.ContainerManager.launch",
                return_value=mock_outcome,
            ),
        ):
            result = await _run_implement(params)

        assert result.files_changed == ["src/fix.py"]
        assert result.agent_summary == "Fixed the bug"

    @pytest.mark.asyncio
    async def test_container_mode_fallback_observe(self):
        """Observe tier falls back to in-process when Docker unavailable."""
        params = _make_impl_input(repo_tier="observe")
        mock_s = _mock_settings(agent_isolation="container")

        with (
            patch("src.settings.settings", mock_s),
            patch(
                "src.agent.container_manager.ContainerManager"
                ".is_docker_available",
                return_value=False,
            ),
        ):
            result = await _run_implement(params)

        # Falls back to in-process
        assert result.agent_summary == "Implementation placeholder"

    @pytest.mark.asyncio
    async def test_container_mode_execute_deny(self):
        """Execute tier fails closed when Docker unavailable."""
        from src.agent.isolation_policy import ContainerUnavailableError

        params = _make_impl_input(repo_tier="execute")
        mock_s = _mock_settings(agent_isolation="container")

        with (
            patch("src.settings.settings", mock_s),
            patch(
                "src.agent.container_manager.ContainerManager"
                ".is_docker_available",
                return_value=False,
            ),
        ):
            with pytest.raises(ContainerUnavailableError):
                await _run_implement(params)

    @pytest.mark.asyncio
    async def test_container_no_result_returns_failure(self):
        """Container producing no result.json returns failure summary."""
        params = _make_impl_input(repo_tier="suggest")
        mock_s = _mock_settings(agent_isolation="container")

        mock_outcome = MagicMock()
        mock_outcome.result = None
        mock_outcome.container_id = "fail123"
        mock_outcome.exit_code = 1
        mock_outcome.timed_out = False
        mock_outcome.oom_killed = False
        mock_outcome.total_ms = 3000

        with (
            patch("src.settings.settings", mock_s),
            patch(
                "src.agent.container_manager.ContainerManager"
                ".is_docker_available",
                return_value=True,
            ),
            patch(
                "src.agent.container_manager.ContainerManager.launch",
                return_value=mock_outcome,
            ),
        ):
            result = await _run_implement(params)

        assert result.files_changed == []
        assert "exit_code=1" in result.agent_summary


class TestPerTierResourceLimits:
    """Story 25.6: Verify tier-based config resolution."""

    def test_observe_tier_limits(self):
        from src.agent.isolation_policy import IsolationMode, resolve_isolation

        mock_s = _mock_settings(agent_isolation="container")
        with patch("src.settings.settings", mock_s):
            decision = resolve_isolation("observe", container_available=True)

        assert decision.mode == IsolationMode.CONTAINER
        assert decision.cpu_limit == 1.0
        assert decision.memory_mb == 512
        assert decision.timeout_seconds == 300

    def test_suggest_tier_limits(self):
        from src.agent.isolation_policy import resolve_isolation

        mock_s = _mock_settings(agent_isolation="container")
        with patch("src.settings.settings", mock_s):
            decision = resolve_isolation("suggest", container_available=True)

        assert decision.cpu_limit == 2.0
        assert decision.memory_mb == 1024
        assert decision.timeout_seconds == 600

    def test_execute_tier_limits(self):
        from src.agent.isolation_policy import resolve_isolation

        mock_s = _mock_settings(agent_isolation="container")
        with patch("src.settings.settings", mock_s):
            decision = resolve_isolation("execute", container_available=True)

        assert decision.cpu_limit == 4.0
        assert decision.memory_mb == 2048
        assert decision.timeout_seconds == 1200


async def _run_implement(params: ImplementInput) -> ImplementOutput:
    """Call implement_activity outside Temporal context."""
    from src.workflow.activities import implement_activity

    return await implement_activity(params)
