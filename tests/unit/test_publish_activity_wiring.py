"""Tests for publish_activity production wiring.

Validates that publish_activity correctly delegates to the real publisher
when github_provider is "real", and falls back to the stub when "mock".
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.workflow.activities import PublishInput, PublishOutput, publish_activity


@pytest.fixture
def publish_params():
    """Standard publish activity input."""
    return PublishInput(
        taskpacket_id=str(uuid4()),
        repo_tier="observe",
        qa_passed=True,
    )


class TestPublishActivityStubMode:
    """When github_provider is mock, publish_activity returns stub output."""

    @pytest.mark.asyncio
    async def test_stub_returns_zero_pr(self, publish_params):
        """Stub mode returns pr_number=0, created=False."""
        with patch("src.settings.settings.github_provider", "mock"):
            result = await publish_activity(publish_params)

        assert result.pr_number == 0
        assert result.pr_url == ""
        assert result.created is False
        assert result.marked_ready is False

    @pytest.mark.asyncio
    async def test_stub_records_timing(self, publish_params):
        """Stub mode returns successfully (timing recorded internally)."""
        with patch("src.settings.settings.github_provider", "mock"):
            result = await publish_activity(publish_params)

        assert isinstance(result, PublishOutput)


class TestPublishActivityRealMode:
    """When github_provider is real, publish_activity delegates to publisher."""

    @pytest.mark.asyncio
    async def test_real_mode_no_token_returns_stub(self, publish_params):
        """If intake_poll_token is empty, returns stub output safely."""
        with (
            patch("src.settings.settings.github_provider", "real"),
            patch("src.settings.settings.intake_poll_token", ""),
        ):
            result = await publish_activity(publish_params)

        assert result.pr_number == 0
        assert result.created is False

    @pytest.mark.asyncio
    async def test_real_mode_taskpacket_not_found(self, publish_params):
        """If TaskPacket not found in DB, returns stub output safely."""
        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("src.settings.settings.github_provider", "real"),
            patch("src.settings.settings.intake_poll_token", "ghp_test"),
            patch(
                "src.db.connection.get_async_session",
                return_value=mock_session_ctx,
            ),
            patch(
                "src.models.taskpacket_crud.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await publish_activity(publish_params)

        assert result.pr_number == 0
        assert result.created is False

    @pytest.mark.asyncio
    async def test_real_mode_delegates_to_publisher(self, publish_params):
        """With valid token, DB, and TaskPacket, calls publish() and returns result."""
        from datetime import UTC, datetime

        mock_taskpacket = MagicMock()
        mock_taskpacket.repo = "owner/repo"
        mock_taskpacket.correlation_id = uuid4()
        mock_taskpacket.created_at = datetime.now(UTC)

        mock_intent = MagicMock()
        mock_intent.version = 1
        mock_intent.goal = "Fix bug"

        mock_publish_result = MagicMock()
        mock_publish_result.pr_number = 42
        mock_publish_result.pr_url = "https://github.com/owner/repo/pull/42"
        mock_publish_result.created = True
        mock_publish_result.marked_ready = False

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_github = AsyncMock()
        mock_github.close = AsyncMock()

        with (
            patch("src.settings.settings.github_provider", "real"),
            patch("src.settings.settings.intake_poll_token", "ghp_test"),
            patch(
                "src.db.connection.get_async_session",
                return_value=mock_session_ctx,
            ),
            patch(
                "src.models.taskpacket_crud.get_by_id",
                new_callable=AsyncMock,
                return_value=mock_taskpacket,
            ),
            patch(
                "src.intent.intent_crud.get_latest_for_taskpacket",
                new_callable=AsyncMock,
                return_value=mock_intent,
            ),
            patch(
                "src.adapters.github.get_github_client",
                return_value=mock_github,
            ),
            patch(
                "src.publisher.publisher.publish",
                new_callable=AsyncMock,
                return_value=mock_publish_result,
            ) as mock_pub_fn,
        ):
            result = await publish_activity(publish_params)

        assert result.pr_number == 42
        assert result.pr_url == "https://github.com/owner/repo/pull/42"
        assert result.created is True
        mock_pub_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_real_mode_github_client_closed(self, publish_params):
        """GitHubClient.close() is called even if publish raises."""
        from datetime import UTC, datetime

        mock_taskpacket = MagicMock()
        mock_taskpacket.repo = "owner/repo"
        mock_taskpacket.created_at = datetime.now(UTC)

        mock_intent = MagicMock()
        mock_intent.version = 1

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_github = AsyncMock()
        mock_github.close = AsyncMock()

        with (
            patch("src.settings.settings.github_provider", "real"),
            patch("src.settings.settings.intake_poll_token", "ghp_test"),
            patch(
                "src.db.connection.get_async_session",
                return_value=mock_session_ctx,
            ),
            patch(
                "src.models.taskpacket_crud.get_by_id",
                new_callable=AsyncMock,
                return_value=mock_taskpacket,
            ),
            patch(
                "src.intent.intent_crud.get_latest_for_taskpacket",
                new_callable=AsyncMock,
                return_value=mock_intent,
            ),
            patch(
                "src.adapters.github.get_github_client",
                return_value=mock_github,
            ),
            patch(
                "src.publisher.publisher.publish",
                new_callable=AsyncMock,
                side_effect=ValueError("test error"),
            ),
            pytest.raises(ValueError, match="test error"),
        ):
            await publish_activity(publish_params)

        mock_github.close.assert_called_once()
