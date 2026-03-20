"""Tests for the eval preflight guard module.

Validates that the preflight correctly:
  1. Rejects mock LLM provider with a clear error message.
  2. Rejects mismatched API keys.
  3. Accepts matching anthropic provider + API key.
  4. Handles unreachable containers gracefully.

These tests mock ``_read_container_env`` to simulate Docker responses,
so they run without a Docker stack.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.p0.eval_preflight import PreflightResult, check_container_env


def _mock_container_env(provider: str | None, api_key: str | None):
    """Create a side_effect function for _read_container_env."""

    def _read(compose_file: str, var_name: str) -> str | None:
        if var_name == "THESTUDIO_LLM_PROVIDER":
            return provider
        if var_name == "THESTUDIO_ANTHROPIC_API_KEY":
            return api_key
        return None

    return _read


class TestEvalPreflightGuard:
    """Unit tests for eval preflight guard (no Docker needed)."""

    @patch("tests.p0.eval_preflight._read_container_env")
    def test_rejects_mock_provider(self, mock_read) -> None:
        """Guard rejects container with LLM provider set to 'mock'."""
        mock_read.side_effect = _mock_container_env("mock", "sk-ant-test-key")
        result = check_container_env(host_api_key="sk-ant-test-key")
        assert result.ok is False
        assert "not 'anthropic'" in result.message
        assert "eval results would be meaningless" in result.message

    @patch("tests.p0.eval_preflight._read_container_env")
    def test_rejects_empty_provider(self, mock_read) -> None:
        """Guard rejects when container is unreachable (provider is None)."""
        mock_read.side_effect = _mock_container_env(None, None)
        result = check_container_env(host_api_key="sk-ant-test-key")
        assert result.ok is False
        assert "Could not read THESTUDIO_LLM_PROVIDER" in result.message

    @patch("tests.p0.eval_preflight._read_container_env")
    def test_rejects_mismatched_api_key(self, mock_read) -> None:
        """Guard rejects when container API key differs from host."""
        mock_read.side_effect = _mock_container_env("anthropic", "sk-ant-container")
        result = check_container_env(host_api_key="sk-ant-host")
        assert result.ok is False
        assert "does not match host env" in result.message

    @patch("tests.p0.eval_preflight._read_container_env")
    def test_accepts_matching_config(self, mock_read) -> None:
        """Guard passes when provider is anthropic and keys match."""
        mock_read.side_effect = _mock_container_env("anthropic", "sk-ant-test-key")
        result = check_container_env(host_api_key="sk-ant-test-key")
        assert result.ok is True
        assert "anthropic" in result.message

    @patch("tests.p0.eval_preflight._read_container_env")
    def test_accepts_when_keys_both_empty(self, mock_read) -> None:
        """Guard passes when provider is anthropic and both keys are empty.

        Key mismatch check only fires when both are non-empty.
        """
        mock_read.side_effect = _mock_container_env("anthropic", "")
        result = check_container_env(host_api_key="")
        assert result.ok is True

    @patch("tests.p0.eval_preflight._read_container_env")
    def test_accepts_when_container_key_none(self, mock_read) -> None:
        """Guard passes when container key can't be read (not exposed)."""
        mock_read.side_effect = _mock_container_env("anthropic", None)
        result = check_container_env(host_api_key="sk-ant-test-key")
        assert result.ok is True

    def test_preflight_result_str_pass(self) -> None:
        """String representation includes PASS for success."""
        r = PreflightResult(ok=True, message="all good")
        assert "PASS" in str(r)

    def test_preflight_result_str_fail(self) -> None:
        """String representation includes FAIL for failure."""
        r = PreflightResult(ok=False, message="bad config")
        assert "FAIL" in str(r)
