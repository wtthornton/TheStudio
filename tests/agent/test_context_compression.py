"""Unit tests for context compression detection (Epic 23, Story 1.13).

Tests: compression trigger detection, threshold checking,
and first 3 + last 4 turn preservation logic.
"""

from __future__ import annotations

import logging

import pytest

from src.agent.framework import AgentConfig, AgentRunner

# -- Helpers -----------------------------------------------------------------


def _make_config(**overrides: object) -> AgentConfig:
    defaults: dict[str, object] = {
        "agent_name": "test_agent",
        "pipeline_step": "test_step",
        "model_class": "fast",
        "compress_threshold": 0.5,
        "compress_model_class": "fast",
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)  # type: ignore[arg-type]


def _make_messages(count: int, content_size: int = 100) -> list[dict[str, str]]:
    """Create a list of messages with predictable content sizes."""
    return [
        {"role": "user" if i % 2 == 0 else "assistant", "content": "x" * content_size}
        for i in range(count)
    ]


# -- Threshold detection tests -----------------------------------------------


class TestCompressionTriggerDetection:
    """Test that _compress_context detects when compression would trigger."""

    def test_below_threshold_no_compression(self):
        """Messages below threshold are returned unchanged."""
        config = _make_config(compress_threshold=0.5)
        runner = AgentRunner(config)
        messages = _make_messages(5, content_size=100)
        context_window = 10000  # threshold = 5000 tokens

        result = runner._compress_context(messages, context_window)

        assert result is messages  # same object, no copy

    def test_above_threshold_triggers_warning(self, caplog: pytest.LogCaptureFixture):
        """Messages above threshold trigger a warning log."""
        config = _make_config(compress_threshold=0.5)
        runner = AgentRunner(config)
        # 10 messages * 2000 chars = 20000 chars = ~5000 tokens
        # threshold = 0.5 * 4000 = 2000 tokens -> exceeded
        messages = _make_messages(10, content_size=2000)
        context_window = 4000

        with caplog.at_level(logging.WARNING, logger="src.agent.framework"):
            result = runner._compress_context(messages, context_window)

        assert result is messages  # placeholder returns original
        assert "Context compression triggered" in caplog.text
        assert "test_agent" in caplog.text

    def test_exact_threshold_no_compression(self):
        """At exactly the threshold, no compression needed (<=)."""
        config = _make_config(compress_threshold=0.5)
        runner = AgentRunner(config)
        # We want estimated_tokens == threshold
        # threshold = 0.5 * 8000 = 4000 tokens
        # 10 messages * 1600 chars = 16000 chars // 4 = 4000 tokens
        messages = _make_messages(10, content_size=1600)
        context_window = 8000

        result = runner._compress_context(messages, context_window)
        assert result is messages


class TestCompressionThresholdConfig:
    """Test that compress_threshold from AgentConfig is respected."""

    def test_low_threshold_triggers_earlier(self, caplog: pytest.LogCaptureFixture):
        """A low threshold (0.2) triggers compression sooner."""
        config = _make_config(compress_threshold=0.2)
        runner = AgentRunner(config)
        # 10 messages * 400 chars = 4000 chars = 1000 tokens
        # threshold = 0.2 * 4000 = 800 tokens -> 1000 > 800 -> triggers
        messages = _make_messages(10, content_size=400)
        context_window = 4000

        with caplog.at_level(logging.WARNING, logger="src.agent.framework"):
            runner._compress_context(messages, context_window)

        assert "Context compression triggered" in caplog.text

    def test_high_threshold_avoids_trigger(self):
        """A high threshold (0.9) avoids compression for moderate context."""
        config = _make_config(compress_threshold=0.9)
        runner = AgentRunner(config)
        # 10 messages * 400 chars = 4000 chars = 1000 tokens
        # threshold = 0.9 * 4000 = 3600 tokens -> 1000 < 3600 -> no trigger
        messages = _make_messages(10, content_size=400)
        context_window = 4000

        result = runner._compress_context(messages, context_window)
        assert result is messages


class TestCompressionPreservation:
    """Test first 3 + last 4 turn preservation logic."""

    def test_not_enough_turns_to_compress(self, caplog: pytest.LogCaptureFixture):
        """With <= 7 messages, compression is not possible (3+4=7)."""
        config = _make_config(compress_threshold=0.5)
        runner = AgentRunner(config)
        # 7 messages * 4000 chars = 28000 chars = 7000 tokens
        # threshold = 0.5 * 4000 = 2000 -> exceeds, but only 7 messages
        messages = _make_messages(7, content_size=4000)
        context_window = 4000

        with caplog.at_level(logging.DEBUG, logger="src.agent.framework"):
            result = runner._compress_context(messages, context_window)

        assert result is messages
        # Should NOT have the "Context compression triggered" warning
        # because there aren't enough turns to compress
        has_not_enough = "not enough turns" in caplog.text
        has_no_trigger = "Context compression triggered" not in caplog.text
        assert has_not_enough or has_no_trigger

    def test_enough_turns_logs_compressible_count(
        self,
        caplog: pytest.LogCaptureFixture,
    ):
        """With 10 messages, 3 middle turns would be compressed."""
        config = _make_config(compress_threshold=0.5)
        runner = AgentRunner(config)
        # 10 messages * 2000 chars = 20000 chars = 5000 tokens
        # threshold = 0.5 * 4000 = 2000 -> exceeds
        messages = _make_messages(10, content_size=2000)
        context_window = 4000

        with caplog.at_level(logging.WARNING, logger="src.agent.framework"):
            runner._compress_context(messages, context_window)

        assert "would compress 3 middle turns" in caplog.text
        assert "preserving first 3 + last 4" in caplog.text

    def test_large_conversation_compressible_count(
        self,
        caplog: pytest.LogCaptureFixture,
    ):
        """With 20 messages, 13 middle turns would be compressed."""
        config = _make_config(compress_threshold=0.5)
        runner = AgentRunner(config)
        messages = _make_messages(20, content_size=2000)
        context_window = 4000

        with caplog.at_level(logging.WARNING, logger="src.agent.framework"):
            runner._compress_context(messages, context_window)

        assert "would compress 13 middle turns" in caplog.text

    def test_compress_model_class_logged(self, caplog: pytest.LogCaptureFixture):
        """The compress_model_class is included in the warning log."""
        config = _make_config(
            compress_threshold=0.5,
            compress_model_class="ultra_fast",
        )
        runner = AgentRunner(config)
        messages = _make_messages(10, content_size=2000)
        context_window = 4000

        with caplog.at_level(logging.WARNING, logger="src.agent.framework"):
            runner._compress_context(messages, context_window)

        assert "ultra_fast" in caplog.text

    def test_placeholder_returns_original_messages(self):
        """Placeholder implementation always returns the original list."""
        config = _make_config(compress_threshold=0.5)
        runner = AgentRunner(config)
        messages = _make_messages(15, content_size=2000)
        context_window = 4000

        result = runner._compress_context(messages, context_window)

        assert result is messages
        assert len(result) == 15  # nothing removed
