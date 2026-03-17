"""Tests for container isolation policy enforcement (Epic 25 blocker fix)."""

from unittest.mock import patch

import pytest

from src.agent.isolation_policy import (
    ContainerUnavailableError,
    IsolationDecision,
    IsolationMode,
    resolve_isolation,
)


def _mock_settings(**overrides):
    """Create a mock settings object with isolation defaults."""
    defaults = {
        "agent_isolation": "container",
        "agent_isolation_fallback": {
            "observe": "allow",
            "suggest": "allow",
            "execute": "deny",
        },
        "agent_container_cpu_limit": {
            "observe": 1.0,
            "suggest": 2.0,
            "execute": 4.0,
        },
        "agent_container_memory_mb": {
            "observe": 512,
            "suggest": 1024,
            "execute": 2048,
        },
        "agent_container_timeout_seconds": {
            "observe": 300,
            "suggest": 600,
            "execute": 1200,
        },
    }
    defaults.update(overrides)

    class MockSettings:
        pass

    s = MockSettings()
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


class TestResolveIsolation:
    """Test isolation policy resolution per tier."""

    def test_process_mode_always_returns_process(self):
        settings = _mock_settings(agent_isolation="process")
        with patch("src.settings.settings", settings):
            result = resolve_isolation("execute", container_available=False)
        assert result.mode == IsolationMode.PROCESS
        assert not result.fell_back

    def test_container_available_returns_container(self):
        settings = _mock_settings()
        with patch("src.settings.settings", settings):
            result = resolve_isolation("observe", container_available=True)
        assert result.mode == IsolationMode.CONTAINER
        assert not result.fell_back

    def test_observe_tier_falls_back_when_unavailable(self):
        settings = _mock_settings()
        with patch("src.settings.settings", settings):
            result = resolve_isolation("observe", container_available=False)
        assert result.mode == IsolationMode.PROCESS
        assert result.fell_back

    def test_suggest_tier_falls_back_when_unavailable(self):
        settings = _mock_settings()
        with patch("src.settings.settings", settings):
            result = resolve_isolation("suggest", container_available=False)
        assert result.mode == IsolationMode.PROCESS
        assert result.fell_back

    def test_execute_tier_raises_when_unavailable(self):
        settings = _mock_settings()
        with patch("src.settings.settings", settings):
            with pytest.raises(ContainerUnavailableError) as exc_info:
                resolve_isolation("execute", container_available=False)
        assert exc_info.value.tier == "execute"
        assert "deny" in str(exc_info.value)

    def test_execute_tier_succeeds_when_available(self):
        settings = _mock_settings()
        with patch("src.settings.settings", settings):
            result = resolve_isolation("execute", container_available=True)
        assert result.mode == IsolationMode.CONTAINER
        assert not result.fell_back
        assert result.cpu_limit == 4.0
        assert result.memory_mb == 2048
        assert result.timeout_seconds == 1200

    def test_resource_limits_per_tier(self):
        settings = _mock_settings()
        with patch("src.settings.settings", settings):
            observe = resolve_isolation("observe", container_available=True)
            suggest = resolve_isolation("suggest", container_available=True)
            execute = resolve_isolation("execute", container_available=True)

        assert observe.cpu_limit < suggest.cpu_limit < execute.cpu_limit
        assert observe.memory_mb < suggest.memory_mb < execute.memory_mb
        assert observe.timeout_seconds < suggest.timeout_seconds < execute.timeout_seconds

    def test_unknown_tier_defaults_to_allow_fallback(self):
        settings = _mock_settings()
        with patch("src.settings.settings", settings):
            result = resolve_isolation("unknown_tier", container_available=False)
        assert result.mode == IsolationMode.PROCESS
        assert result.fell_back


class TestIsolationDecision:
    """Test IsolationDecision dataclass."""

    def test_frozen(self):
        decision = IsolationDecision(
            mode=IsolationMode.CONTAINER,
            fell_back=False,
            tier="execute",
            cpu_limit=4.0,
            memory_mb=2048,
            timeout_seconds=1200,
        )
        with pytest.raises(AttributeError):
            decision.mode = IsolationMode.PROCESS  # type: ignore[misc]
