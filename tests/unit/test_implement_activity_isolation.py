"""Tests for implement_activity container/process mode branching (Epic 25 Story 25.4).

Validates that implement_activity correctly branches between in-process and
container modes based on the THESTUDIO_AGENT_ISOLATION setting, and that
per-tier resource limits (Story 25.6) flow through correctly.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.workflow.activities import ImplementInput, ImplementOutput


def _make_impl_input(**overrides) -> ImplementInput:
    defaults = {
        "taskpacket_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "repo_path": "/tmp/test-repo",
        "loopback_attempt": 0,
        "repo_tier": "observe",
        "repo": "test-owner/test-repo",
        "issue_title": "Add hello_world function",
        "issue_body": "Create a hello_world() function in utils.py",
        "intent_goal": "Add hello_world function to utils.py",
        "acceptance_criteria": ["hello_world() returns 'Hello, World!'"],
        "plan_steps": ["Create utils.py with hello_world function"],
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
    s.intake_poll_token = "fake-token"
    return s


def _mock_llm_response(files: list[dict]) -> MagicMock:
    """Create a mock LLM response with JSON file output."""
    response = MagicMock()
    response.content = json.dumps({"files": files, "summary": "Test implementation"})
    response.tokens_in = 100
    response.tokens_out = 200
    return response


def _mock_github_client():
    """Create a mock GitHub client with async methods."""
    client = AsyncMock()
    client.get_default_branch.return_value = "main"
    client.get_branch_sha.return_value = "abc123sha"
    client.create_branch.return_value = None
    client.get_file_content.return_value = None  # File doesn't exist yet
    client.create_or_update_file.return_value = {"content": {"sha": "new_sha"}}
    client.close.return_value = None
    return client


class TestImplementActivityProcessMode:
    """In-process mode (default) — generates code via LLM and pushes to GitHub."""

    @pytest.mark.asyncio
    async def test_process_mode_generates_code(self):
        """Default agent_isolation='process' calls LLM and pushes to GitHub."""
        params = _make_impl_input()
        mock_s = _mock_settings(agent_isolation="process")
        mock_github = _mock_github_client()

        files = [{"path": "utils.py", "content": "def hello_world():\n    return 'Hello, World!'\n", "action": "create"}]
        mock_resp = _mock_llm_response(files)
        mock_adapter = AsyncMock()
        mock_adapter.complete.return_value = mock_resp

        mock_provider = MagicMock()
        mock_provider.provider = "anthropic"
        mock_provider.model_id = "claude-sonnet-4-5-20250514"
        mock_provider.estimate_cost.return_value = 0.01

        with (
            patch("src.settings.settings", mock_s),
            patch("src.adapters.llm.get_llm_adapter", return_value=mock_adapter),
            patch("src.adapters.github.get_github_client", return_value=mock_github),
            patch("src.admin.model_gateway.get_model_router") as mock_router,
            patch("src.admin.model_gateway.get_model_audit_store"),
        ):
            mock_router.return_value.select_model.return_value = mock_provider
            result = await _run_implement(params)

        assert isinstance(result, ImplementOutput)
        assert result.taskpacket_id == params.taskpacket_id
        assert result.files_changed == ["utils.py"]
        assert result.agent_summary == "Test implementation"
        mock_github.create_branch.assert_called_once()
        mock_github.create_or_update_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_mode_no_token(self):
        """Returns empty result when no GitHub token configured."""
        params = _make_impl_input()
        mock_s = _mock_settings(agent_isolation="process")
        mock_s.intake_poll_token = ""

        mock_resp = _mock_llm_response([{"path": "x.py", "content": "x", "action": "create"}])
        mock_adapter = AsyncMock()
        mock_adapter.complete.return_value = mock_resp

        mock_provider = MagicMock()
        mock_provider.provider = "anthropic"
        mock_provider.model_id = "test"
        mock_provider.estimate_cost.return_value = 0.0

        with (
            patch("src.settings.settings", mock_s),
            patch("src.adapters.llm.get_llm_adapter", return_value=mock_adapter),
            patch("src.admin.model_gateway.get_model_router") as mock_router,
            patch("src.admin.model_gateway.get_model_audit_store"),
        ):
            mock_router.return_value.select_model.return_value = mock_provider
            result = await _run_implement(params)

        assert result.files_changed == []
        assert "No GitHub token" in result.agent_summary

    @pytest.mark.asyncio
    async def test_process_mode_llm_parse_failure(self):
        """Returns empty result when LLM output is not valid JSON."""
        params = _make_impl_input()
        mock_s = _mock_settings(agent_isolation="process")

        mock_resp = MagicMock()
        mock_resp.content = "This is not JSON"
        mock_resp.tokens_in = 10
        mock_resp.tokens_out = 10

        mock_adapter = AsyncMock()
        mock_adapter.complete.return_value = mock_resp

        mock_provider = MagicMock()
        mock_provider.provider = "anthropic"
        mock_provider.model_id = "test"
        mock_provider.estimate_cost.return_value = 0.0

        with (
            patch("src.settings.settings", mock_s),
            patch("src.adapters.llm.get_llm_adapter", return_value=mock_adapter),
            patch("src.admin.model_gateway.get_model_router") as mock_router,
            patch("src.admin.model_gateway.get_model_audit_store"),
        ):
            mock_router.return_value.select_model.return_value = mock_provider
            result = await _run_implement(params)

        assert result.files_changed == []
        assert "parsed as JSON" in result.agent_summary


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
        mock_s.intake_poll_token = "fake-token"
        mock_github = _mock_github_client()

        files = [{"path": "utils.py", "content": "code", "action": "create"}]
        mock_resp = _mock_llm_response(files)
        mock_adapter = AsyncMock()
        mock_adapter.complete.return_value = mock_resp

        mock_provider = MagicMock()
        mock_provider.provider = "anthropic"
        mock_provider.model_id = "test"
        mock_provider.estimate_cost.return_value = 0.0

        with (
            patch("src.settings.settings", mock_s),
            patch(
                "src.agent.container_manager.ContainerManager"
                ".is_docker_available",
                return_value=False,
            ),
            patch("src.adapters.llm.get_llm_adapter", return_value=mock_adapter),
            patch("src.adapters.github.get_github_client", return_value=mock_github),
            patch("src.admin.model_gateway.get_model_router") as mock_router,
            patch("src.admin.model_gateway.get_model_audit_store"),
        ):
            mock_router.return_value.select_model.return_value = mock_provider
            result = await _run_implement(params)

        # Falls back to in-process, generates code
        assert result.files_changed == ["utils.py"]

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
