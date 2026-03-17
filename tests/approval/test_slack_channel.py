"""Tests for Slack notification channel (Epic 24 Story 24.5)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.approval.channels.slack import SlackChannel
from src.approval.review_context import (
    EvidenceHighlights,
    IntentSummary,
    QASummary,
    ReviewContext,
    TaskPacketSummary,
    VerificationSummary,
)


FAKE_WEBHOOK = "https://hooks.slack.com/services/T00/B00/fake"


def _make_context(**overrides) -> ReviewContext:
    tp_id = overrides.pop("taskpacket_id", uuid4())
    return ReviewContext(
        taskpacket=TaskPacketSummary(
            taskpacket_id=tp_id,
            repo="test-org/test-repo",
            status="awaiting_approval",
            repo_tier="suggest",
            issue_title="Fix login timeout",
            issue_number=42,
        ),
        intent=IntentSummary(
            goal="Fix the 30-second login timeout",
            acceptance_criteria=["Login completes in < 5s"],
        ),
        verification=VerificationSummary(passed=True),
        qa=QASummary(passed=True),
        evidence=EvidenceHighlights(
            files_changed=["src/auth/login.py"],
            agent_summary="Reduced timeout",
        ),
        pr_url="https://github.com/test-org/test-repo/pull/99",
        **overrides,
    )


class TestSlackChannel:
    def test_channel_name(self):
        ch = SlackChannel(webhook_url=FAKE_WEBHOOK)
        assert ch.channel_name == "slack"

    def test_requires_webhook_url(self):
        with pytest.raises(ValueError, match="webhook URL is required"):
            SlackChannel(webhook_url="")

    @pytest.mark.asyncio
    async def test_notify_awaiting_approval_success(self):
        """Successful webhook post returns True."""
        ch = SlackChannel(webhook_url=FAKE_WEBHOOK)
        context = _make_context()

        mock_resp = AsyncMock()
        mock_resp.status_code = 200

        with patch("src.approval.channels.slack.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client

            result = await ch.notify_awaiting_approval(context)
            assert result is True
            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args
            assert call_kwargs[0][0] == FAKE_WEBHOOK

    @pytest.mark.asyncio
    async def test_notify_awaiting_approval_failure(self):
        """Failed webhook returns False."""
        ch = SlackChannel(webhook_url=FAKE_WEBHOOK)
        context = _make_context()

        mock_resp = AsyncMock()
        mock_resp.status_code = 500
        mock_resp.text = "server_error"

        with patch("src.approval.channels.slack.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client

            result = await ch.notify_awaiting_approval(context)
            assert result is False

    @pytest.mark.asyncio
    async def test_notify_approved(self):
        ch = SlackChannel(webhook_url=FAKE_WEBHOOK)

        mock_resp = AsyncMock()
        mock_resp.status_code = 200

        with patch("src.approval.channels.slack.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client

            result = await ch.notify_approved(uuid4(), "reviewer1")
            assert result is True

    @pytest.mark.asyncio
    async def test_notify_rejected(self):
        ch = SlackChannel(webhook_url=FAKE_WEBHOOK)

        mock_resp = AsyncMock()
        mock_resp.status_code = 200

        with patch("src.approval.channels.slack.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client

            result = await ch.notify_rejected(uuid4(), "reviewer1", "Needs work")
            assert result is True

    @pytest.mark.asyncio
    async def test_notify_timeout(self):
        ch = SlackChannel(webhook_url=FAKE_WEBHOOK)

        mock_resp = AsyncMock()
        mock_resp.status_code = 200

        with patch("src.approval.channels.slack.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client

            result = await ch.notify_timeout(uuid4())
            assert result is True

    def test_block_kit_structure(self):
        """Blocks contain required sections: header, fields, actions."""
        ch = SlackChannel(webhook_url=FAKE_WEBHOOK)
        context = _make_context()
        blocks = ch._build_approval_blocks(context)

        block_types = [b["type"] for b in blocks]
        assert "header" in block_types
        assert "actions" in block_types
        assert "divider" in block_types

        # Action block has approve and reject buttons
        action_block = next(b for b in blocks if b["type"] == "actions")
        button_ids = [e["action_id"] for e in action_block["elements"]]
        assert any("approve_" in bid for bid in button_ids)
        assert any("reject_" in bid for bid in button_ids)

    def test_blocks_include_pr_link(self):
        ch = SlackChannel(webhook_url=FAKE_WEBHOOK)
        context = _make_context()
        blocks = ch._build_approval_blocks(context)
        block_texts = str(blocks)
        assert "View Pull Request" in block_texts

    def test_blocks_truncate_files(self):
        ch = SlackChannel(webhook_url=FAKE_WEBHOOK)
        context = _make_context()
        context.evidence.files_changed = [f"src/f{i}.py" for i in range(15)]
        blocks = ch._build_approval_blocks(context)
        block_texts = str(blocks)
        assert "and 5 more" in block_texts

    @pytest.mark.asyncio
    async def test_network_error_returns_false(self):
        """Network errors are caught and return False."""
        ch = SlackChannel(webhook_url=FAKE_WEBHOOK)

        with patch("src.approval.channels.slack.httpx") as mock_httpx:
            mock_httpx.AsyncClient.side_effect = Exception("Connection refused")
            result = await ch.notify_timeout(uuid4())
            assert result is False
