"""Story 30.10: Enable Preflight + Container Isolation — Integration Tests.

Verifies that when preflight and container isolation feature flags are
activated, the correct pipeline behavior and security invariants hold:

1. Preflight gate fires between Assembler and Implement when enabled
2. Container isolation activates when THESTUDIO_AGENT_ISOLATION=container
3. Security invariant: Execute tier with deny fallback blocks in-process fallback
4. Preflight only runs for tiers in THESTUDIO_PREFLIGHT_TIERS
5. Settings validation rejects unsafe Execute tier fallback configuration
6. Env var activation paths work end-to-end
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.settings import Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENC_KEY = "hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac="


# ---------------------------------------------------------------------------
# 1. Preflight flag activation via environment variables
# ---------------------------------------------------------------------------


class TestPreflightFlagActivation:
    """Verify preflight gate activates correctly when flags are set."""

    def test_preflight_defaults_off(self) -> None:
        """Preflight is disabled by default."""
        s = Settings(encryption_key=_ENC_KEY)
        assert s.preflight_enabled is False
        assert s.preflight_tiers == ["execute"]

    def test_preflight_enable_via_env(self, monkeypatch) -> None:
        """THESTUDIO_PREFLIGHT_ENABLED=true activates preflight."""
        monkeypatch.setenv("THESTUDIO_PREFLIGHT_ENABLED", "true")
        monkeypatch.setenv("THESTUDIO_ENCRYPTION_KEY", _ENC_KEY)

        s = Settings()
        assert s.preflight_enabled is True
        assert s.preflight_tiers == ["execute"]

    def test_preflight_tiers_configurable_via_env(self, monkeypatch) -> None:
        """THESTUDIO_PREFLIGHT_TIERS overrides default tier list."""
        monkeypatch.setenv("THESTUDIO_PREFLIGHT_ENABLED", "true")
        monkeypatch.setenv("THESTUDIO_PREFLIGHT_TIERS", '["execute", "suggest"]')
        monkeypatch.setenv("THESTUDIO_ENCRYPTION_KEY", _ENC_KEY)

        s = Settings()
        assert s.preflight_enabled is True
        assert "execute" in s.preflight_tiers
        assert "suggest" in s.preflight_tiers

    def test_preflight_config_propagates_to_pipeline_input(self) -> None:
        """PipelineInput carries preflight config from settings."""
        from src.workflow.pipeline import PipelineInput

        inp = PipelineInput(
            taskpacket_id="tp-preflight-30-10",
            correlation_id="corr-preflight-30-10",
            preflight_enabled=True,
            preflight_tiers=["execute", "suggest"],
        )
        assert inp.preflight_enabled is True
        assert "suggest" in inp.preflight_tiers

    @pytest.mark.asyncio
    async def test_preflight_fires_for_matching_tier(self) -> None:
        """When enabled and tier matches, preflight fires between Assembler
        and Implement.

        Uses observe tier with preflight_tiers=["observe"] to avoid
        triggering the approval wait state (which requires Temporal runtime).
        Execute tier behavior is identical but requires Temporal for the
        approval signal wait.
        """
        from src.workflow.activities import (
            AssemblerOutput,
            ContextOutput,
            ImplementOutput,
            IntakeOutput,
            IntentOutput,
            PreflightActivityOutput,
            PublishOutput,
            QAOutput,
            VerifyOutput,
        )
        from src.workflow.pipeline import PipelineInput, TheStudioPipelineWorkflow

        returns = [
            IntakeOutput(accepted=True, base_role="developer", overlays=[]),
            ContextOutput(),
            IntentOutput(
                intent_spec_id="i-1", version=1, goal="Fix it",
                acceptance_criteria=["Works"],
            ),
            object(),  # router
            AssemblerOutput(plan_steps=["implement_changes"]),
            # Preflight runs and approves
            PreflightActivityOutput(approved=True, summary="Plan approved"),
            ImplementOutput(taskpacket_id="tp-obs"),
            VerifyOutput(passed=True),
            QAOutput(passed=True),
            PublishOutput(pr_number=99, created=True),
        ]

        params = PipelineInput(
            taskpacket_id="tp-obs",
            correlation_id="corr-obs",
            labels=["agent:run"],
            repo="acme/widgets",
            repo_registered=True,
            repo_paused=False,
            has_active_workflow=False,
            event_id="evt-obs",
            issue_title="Fix widget",
            issue_body="Widget broken",
            repo_path="/tmp/repo",
            repo_tier="observe",
            preflight_enabled=True,
            preflight_tiers=["observe"],
        )

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(params)

        assert result.success is True
        assert result.preflight_approved is True
        assert result.preflight_summary == "Plan approved"

    @pytest.mark.asyncio
    async def test_preflight_skipped_for_observe_with_default_tiers(self) -> None:
        """With default tiers (execute only), observe tier skips preflight."""
        from src.workflow.activities import (
            AssemblerOutput,
            ContextOutput,
            ImplementOutput,
            IntakeOutput,
            IntentOutput,
            PublishOutput,
            QAOutput,
            VerifyOutput,
        )
        from src.workflow.pipeline import PipelineInput, TheStudioPipelineWorkflow

        # No PreflightActivityOutput in the returns — preflight is skipped
        returns = [
            IntakeOutput(accepted=True, base_role="developer", overlays=[]),
            ContextOutput(),
            IntentOutput(
                intent_spec_id="i-1", version=1, goal="Fix it",
                acceptance_criteria=["Works"],
            ),
            object(),  # router
            AssemblerOutput(plan_steps=["implement_changes"]),
            ImplementOutput(taskpacket_id="tp-obs"),
            VerifyOutput(passed=True),
            QAOutput(passed=True),
            PublishOutput(pr_number=100, created=True),
        ]

        params = PipelineInput(
            taskpacket_id="tp-obs",
            correlation_id="corr-obs",
            labels=["agent:run"],
            repo="acme/widgets",
            repo_registered=True,
            repo_paused=False,
            has_active_workflow=False,
            event_id="evt-obs",
            issue_title="Fix widget",
            issue_body="Widget broken",
            repo_path="/tmp/repo",
            repo_tier="observe",
            preflight_enabled=True,
            preflight_tiers=["execute"],  # observe not included
        )

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(params)

        assert result.success is True
        assert result.preflight_approved is None  # skipped

    @pytest.mark.asyncio
    async def test_preflight_fires_for_custom_tier_list(self) -> None:
        """When multiple tiers are in preflight_tiers, all matching tiers
        trigger preflight.

        Uses observe with preflight_tiers=["execute", "observe"] to test
        the multi-tier configuration path without requiring Temporal runtime.
        """
        from src.workflow.activities import (
            AssemblerOutput,
            ContextOutput,
            ImplementOutput,
            IntakeOutput,
            IntentOutput,
            PreflightActivityOutput,
            PublishOutput,
            QAOutput,
            VerifyOutput,
        )
        from src.workflow.pipeline import PipelineInput, TheStudioPipelineWorkflow

        returns = [
            IntakeOutput(accepted=True, base_role="developer", overlays=[]),
            ContextOutput(),
            IntentOutput(
                intent_spec_id="i-1", version=1, goal="Fix it",
                acceptance_criteria=["Works"],
            ),
            object(),  # router
            AssemblerOutput(plan_steps=["implement_changes"]),
            PreflightActivityOutput(approved=True, summary="Multi-tier plan OK"),
            ImplementOutput(taskpacket_id="tp-obs"),
            VerifyOutput(passed=True),
            QAOutput(passed=True),
            PublishOutput(pr_number=101, created=True),
        ]

        params = PipelineInput(
            taskpacket_id="tp-obs",
            correlation_id="corr-obs",
            labels=["agent:run"],
            repo="acme/widgets",
            repo_registered=True,
            repo_paused=False,
            has_active_workflow=False,
            event_id="evt-obs",
            issue_title="Fix widget",
            issue_body="Widget broken",
            repo_path="/tmp/repo",
            repo_tier="observe",
            preflight_enabled=True,
            preflight_tiers=["execute", "observe"],
        )

        with patch(
            "temporalio.workflow.execute_activity",
            new_callable=AsyncMock,
            side_effect=returns,
        ):
            wf = TheStudioPipelineWorkflow()
            result = await wf.run(params)

        assert result.success is True
        assert result.preflight_approved is True
        assert result.preflight_summary == "Multi-tier plan OK"


# ---------------------------------------------------------------------------
# 2. Container isolation flag activation via environment variables
# ---------------------------------------------------------------------------


class TestContainerIsolationFlagActivation:
    """Verify container isolation activates correctly when flags are set."""

    def test_container_isolation_defaults_process(self) -> None:
        """Agent isolation defaults to in-process mode."""
        s = Settings(encryption_key=_ENC_KEY)
        assert s.agent_isolation == "process"
        assert s.agent_isolation_fallback == {
            "observe": "allow",
            "suggest": "allow",
            "execute": "deny",
        }

    def test_container_isolation_enable_via_env(self, monkeypatch) -> None:
        """THESTUDIO_AGENT_ISOLATION=container activates Docker isolation."""
        monkeypatch.setenv("THESTUDIO_AGENT_ISOLATION", "container")
        monkeypatch.setenv("THESTUDIO_ENCRYPTION_KEY", _ENC_KEY)

        s = Settings()
        assert s.agent_isolation == "container"

    def test_container_isolation_with_custom_fallback(self, monkeypatch) -> None:
        """Custom fallback policy loads from env var."""
        monkeypatch.setenv("THESTUDIO_AGENT_ISOLATION", "container")
        monkeypatch.setenv(
            "THESTUDIO_AGENT_ISOLATION_FALLBACK",
            '{"observe": "deny", "suggest": "deny", "execute": "deny"}',
        )
        monkeypatch.setenv("THESTUDIO_ENCRYPTION_KEY", _ENC_KEY)

        s = Settings()
        assert s.agent_isolation_fallback["observe"] == "deny"
        assert s.agent_isolation_fallback["suggest"] == "deny"
        assert s.agent_isolation_fallback["execute"] == "deny"

    def test_container_resource_limits_defaults(self) -> None:
        """Default resource limits escalate by tier."""
        s = Settings(encryption_key=_ENC_KEY)
        assert s.agent_container_cpu_limit["observe"] < s.agent_container_cpu_limit["suggest"]
        assert s.agent_container_cpu_limit["suggest"] < s.agent_container_cpu_limit["execute"]
        assert s.agent_container_memory_mb["observe"] < s.agent_container_memory_mb["suggest"]
        assert s.agent_container_memory_mb["suggest"] < s.agent_container_memory_mb["execute"]
        timeouts = s.agent_container_timeout_seconds
        assert timeouts["observe"] < timeouts["suggest"]
        assert timeouts["suggest"] < timeouts["execute"]


# ---------------------------------------------------------------------------
# 3. Security invariant: Execute tier deny fallback
# ---------------------------------------------------------------------------


class TestSecurityInvariantExecuteDeny:
    """Execute tier MUST have fallback='deny' when container isolation is on."""

    def test_startup_rejects_execute_allow_fallback(self) -> None:
        """Settings validator blocks execute tier with allow fallback."""
        with pytest.raises(ValueError, match="Execute tier MUST have"):
            Settings(
                encryption_key=_ENC_KEY,
                agent_isolation="container",
                agent_isolation_fallback={
                    "observe": "allow",
                    "suggest": "allow",
                    "execute": "allow",  # UNSAFE — must be rejected
                },
            )

    def test_startup_rejects_execute_allow_via_env(self, monkeypatch) -> None:
        """Settings validator blocks unsafe config via environment variables."""
        monkeypatch.setenv("THESTUDIO_AGENT_ISOLATION", "container")
        monkeypatch.setenv(
            "THESTUDIO_AGENT_ISOLATION_FALLBACK",
            '{"observe": "allow", "suggest": "allow", "execute": "allow"}',
        )
        monkeypatch.setenv("THESTUDIO_ENCRYPTION_KEY", _ENC_KEY)

        with pytest.raises(ValueError, match="Execute tier MUST have"):
            Settings()

    def test_startup_accepts_execute_deny(self) -> None:
        """Settings validator accepts the correct execute deny config."""
        s = Settings(
            encryption_key=_ENC_KEY,
            agent_isolation="container",
            agent_isolation_fallback={
                "observe": "allow",
                "suggest": "allow",
                "execute": "deny",
            },
        )
        assert s.agent_isolation_fallback["execute"] == "deny"

    def test_process_mode_does_not_validate_fallback(self) -> None:
        """In process mode, execute allow fallback is accepted (not relevant)."""
        s = Settings(
            encryption_key=_ENC_KEY,
            agent_isolation="process",
            agent_isolation_fallback={
                "observe": "allow",
                "suggest": "allow",
                "execute": "allow",
            },
        )
        assert s.agent_isolation == "process"
        assert s.agent_isolation_fallback["execute"] == "allow"

    def test_resolve_isolation_execute_deny_raises(self) -> None:
        """resolve_isolation raises ContainerUnavailableError for execute
        when Docker is unavailable and fallback is deny."""
        from src.agent.isolation_policy import ContainerUnavailableError, resolve_isolation

        mock_s = MagicMock()
        mock_s.agent_isolation = "container"
        mock_s.agent_isolation_fallback = {
            "observe": "allow",
            "suggest": "allow",
            "execute": "deny",
        }
        mock_s.agent_container_cpu_limit = {"execute": 4.0}
        mock_s.agent_container_memory_mb = {"execute": 2048}
        mock_s.agent_container_timeout_seconds = {"execute": 1200}

        with patch("src.settings.settings", mock_s):
            with pytest.raises(ContainerUnavailableError) as exc_info:
                resolve_isolation("execute", container_available=False)

        assert exc_info.value.tier == "execute"

    def test_resolve_isolation_observe_allow_falls_back(self) -> None:
        """resolve_isolation falls back to process for observe tier when
        Docker is unavailable and fallback is allow."""
        from src.agent.isolation_policy import IsolationMode, resolve_isolation

        mock_s = MagicMock()
        mock_s.agent_isolation = "container"
        mock_s.agent_isolation_fallback = {
            "observe": "allow",
            "suggest": "allow",
            "execute": "deny",
        }
        mock_s.agent_container_cpu_limit = {"observe": 1.0}
        mock_s.agent_container_memory_mb = {"observe": 512}
        mock_s.agent_container_timeout_seconds = {"observe": 300}

        with patch("src.settings.settings", mock_s):
            decision = resolve_isolation("observe", container_available=False)

        assert decision.mode == IsolationMode.PROCESS
        assert decision.fell_back is True


# ---------------------------------------------------------------------------
# 4. Container isolation activity integration
# ---------------------------------------------------------------------------


class TestContainerIsolationActivityIntegration:
    """Verify implement_activity branches correctly with container isolation."""

    @pytest.mark.asyncio
    async def test_container_mode_launches_when_docker_available(self) -> None:
        """With agent_isolation=container and Docker available, container launches."""
        from src.workflow.activities import ImplementInput, implement_activity

        params = ImplementInput(
            taskpacket_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            repo_path="/tmp/test-repo",
            loopback_attempt=0,
            repo_tier="suggest",
        )

        mock_s = MagicMock()
        mock_s.agent_isolation = "container"
        mock_s.agent_isolation_fallback = {
            "observe": "allow", "suggest": "allow", "execute": "deny",
        }
        mock_s.agent_container_cpu_limit = {"suggest": 2.0}
        mock_s.agent_container_memory_mb = {"suggest": 1024}
        mock_s.agent_container_timeout_seconds = {"suggest": 600}

        mock_outcome = MagicMock()
        mock_outcome.result = MagicMock()
        mock_outcome.result.intent_version = 1
        mock_outcome.result.files_changed = ["src/fix.py"]
        mock_outcome.result.agent_summary = "Container fix applied"
        mock_outcome.container_id = "cnt-30-10"
        mock_outcome.exit_code = 0
        mock_outcome.timed_out = False
        mock_outcome.oom_killed = False
        mock_outcome.total_ms = 4200

        with (
            patch("src.settings.settings", mock_s),
            patch(
                "src.agent.container_manager.ContainerManager.is_docker_available",
                return_value=True,
            ),
            patch(
                "src.agent.container_manager.ContainerManager.launch",
                return_value=mock_outcome,
            ),
        ):
            result = await implement_activity(params)

        assert result.files_changed == ["src/fix.py"]
        assert result.agent_summary == "Container fix applied"

    @pytest.mark.asyncio
    async def test_container_mode_execute_deny_no_docker(self) -> None:
        """Execute tier fails closed when Docker unavailable."""
        from src.agent.isolation_policy import ContainerUnavailableError
        from src.workflow.activities import ImplementInput, implement_activity

        params = ImplementInput(
            taskpacket_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            repo_path="/tmp/test-repo",
            loopback_attempt=0,
            repo_tier="execute",
        )

        mock_s = MagicMock()
        mock_s.agent_isolation = "container"
        mock_s.agent_isolation_fallback = {
            "observe": "allow", "suggest": "allow", "execute": "deny",
        }
        mock_s.agent_container_cpu_limit = {"execute": 4.0}
        mock_s.agent_container_memory_mb = {"execute": 2048}
        mock_s.agent_container_timeout_seconds = {"execute": 1200}

        with (
            patch("src.settings.settings", mock_s),
            patch(
                "src.agent.container_manager.ContainerManager.is_docker_available",
                return_value=False,
            ),
        ):
            with pytest.raises(ContainerUnavailableError):
                await implement_activity(params)

    @pytest.mark.asyncio
    async def test_process_mode_runs_in_process(self) -> None:
        """Default process mode runs implement in-process (no container)."""
        from src.workflow.activities import ImplementInput, implement_activity

        params = ImplementInput(
            taskpacket_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            repo_path="/tmp/test-repo",
            loopback_attempt=0,
            repo_tier="observe",
        )

        mock_s = MagicMock()
        mock_s.agent_isolation = "process"

        with patch("src.settings.settings", mock_s):
            result = await implement_activity(params)

        assert result.taskpacket_id == params.taskpacket_id
        assert result.agent_summary == "Implementation placeholder"


# ---------------------------------------------------------------------------
# 5. Combined preflight + container isolation
# ---------------------------------------------------------------------------


class TestCombinedPreflightAndContainerIsolation:
    """Verify preflight and container isolation work together."""

    def test_both_flags_enable_via_env(self, monkeypatch) -> None:
        """Both flags can be enabled simultaneously."""
        monkeypatch.setenv("THESTUDIO_PREFLIGHT_ENABLED", "true")
        monkeypatch.setenv("THESTUDIO_AGENT_ISOLATION", "container")
        monkeypatch.setenv("THESTUDIO_ENCRYPTION_KEY", _ENC_KEY)

        s = Settings()
        assert s.preflight_enabled is True
        assert s.agent_isolation == "container"
        assert s.agent_isolation_fallback["execute"] == "deny"

    def test_preflight_agent_in_llm_toggle_dict(self) -> None:
        """Preflight agent has a per-agent LLM toggle."""
        s = Settings(encryption_key=_ENC_KEY)
        assert "preflight_agent" in s.agent_llm_enabled
        assert s.agent_llm_enabled["preflight_agent"] is False  # off by default


# ---------------------------------------------------------------------------
# 6. Docker compose env var presence (structural checks)
# ---------------------------------------------------------------------------


class TestDockerComposeEnvVarPresence:
    """Verify docker-compose files declare preflight and container isolation vars."""

    @pytest.fixture
    def compose_files(self) -> dict[str, str]:
        """Load all three docker-compose files."""
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[2]
        files = {}
        for path in [
            root / "docker-compose.dev.yml",
            root / "infra" / "docker-compose.yml",
            root / "infra" / "docker-compose.prod.yml",
        ]:
            files[path.name] = path.read_text()
        return files

    @pytest.mark.parametrize("var", [
        "THESTUDIO_PREFLIGHT_ENABLED",
        "THESTUDIO_PREFLIGHT_TIERS",
        "THESTUDIO_AGENT_ISOLATION",
        "THESTUDIO_AGENT_ISOLATION_FALLBACK",
    ])
    def test_dev_compose_has_var(self, compose_files, var) -> None:
        """docker-compose.dev.yml declares the env var."""
        assert var in compose_files["docker-compose.dev.yml"], (
            f"{var} missing from docker-compose.dev.yml"
        )

    @pytest.mark.parametrize("var", [
        "THESTUDIO_PREFLIGHT_ENABLED",
        "THESTUDIO_PREFLIGHT_TIERS",
        "THESTUDIO_AGENT_ISOLATION",
        "THESTUDIO_AGENT_ISOLATION_FALLBACK",
    ])
    def test_standard_compose_has_var(self, compose_files, var) -> None:
        """infra/docker-compose.yml declares the env var."""
        assert var in compose_files["docker-compose.yml"], (
            f"{var} missing from infra/docker-compose.yml"
        )

    @pytest.mark.parametrize("var", [
        "THESTUDIO_PREFLIGHT_ENABLED",
        "THESTUDIO_PREFLIGHT_TIERS",
        "THESTUDIO_AGENT_ISOLATION",
        "THESTUDIO_AGENT_ISOLATION_FALLBACK",
    ])
    def test_prod_compose_has_var(self, compose_files, var) -> None:
        """infra/docker-compose.prod.yml declares the env var."""
        assert var in compose_files["docker-compose.prod.yml"], (
            f"{var} missing from infra/docker-compose.prod.yml"
        )

    def test_dev_compose_has_docker_socket(self, compose_files) -> None:
        """docker-compose.dev.yml mounts Docker socket for container isolation."""
        assert "/var/run/docker.sock" in compose_files["docker-compose.dev.yml"]

    def test_standard_compose_has_docker_socket(self, compose_files) -> None:
        """infra/docker-compose.yml mounts Docker socket for container isolation."""
        assert "/var/run/docker.sock" in compose_files["docker-compose.yml"]

    def test_prod_compose_has_docker_socket(self, compose_files) -> None:
        """infra/docker-compose.prod.yml mounts Docker socket for container isolation."""
        assert "/var/run/docker.sock" in compose_files["docker-compose.prod.yml"]

    def test_dev_compose_has_agent_net(self, compose_files) -> None:
        """docker-compose.dev.yml defines agent-net network."""
        assert "agent-net" in compose_files["docker-compose.dev.yml"]

    def test_standard_compose_has_agent_net(self, compose_files) -> None:
        """infra/docker-compose.yml defines agent-net network."""
        assert "agent-net" in compose_files["docker-compose.yml"]

    def test_prod_compose_has_agent_net(self, compose_files) -> None:
        """infra/docker-compose.prod.yml defines agent-net network."""
        assert "agent-net" in compose_files["docker-compose.prod.yml"]
