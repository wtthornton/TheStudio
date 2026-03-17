"""Tests for notification channel adapters (Epic 24 Story 24.4).

Tests the abstract base, GitHub channel, and channel registry.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.approval.channels.base import NotificationChannel
from src.approval.channels.github import GitHubChannel
from src.approval.channels.registry import get_configured_channels
from src.approval.review_context import (
    EvidenceHighlights,
    IntentSummary,
    QASummary,
    ReviewContext,
    TaskPacketSummary,
    VerificationSummary,
)


def _make_review_context(**overrides) -> ReviewContext:
    """Create a ReviewContext for testing."""
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
            acceptance_criteria=["Login completes in < 5s", "No regressions in auth tests"],
        ),
        verification=VerificationSummary(passed=True),
        qa=QASummary(passed=True),
        evidence=EvidenceHighlights(
            files_changed=["src/auth/login.py", "tests/test_login.py"],
            agent_summary="Reduced timeout from 30s to 5s",
        ),
        pr_url="https://github.com/test-org/test-repo/pull/99",
        **overrides,
    )


class TestNotificationChannelBase:
    """Test that the abstract base defines the right interface."""

    def test_cannot_instantiate_base(self):
        """ABC prevents direct instantiation."""
        with pytest.raises(TypeError):
            NotificationChannel()

    def test_interface_methods_exist(self):
        """All required methods are defined on the ABC."""
        assert hasattr(NotificationChannel, "notify_awaiting_approval")
        assert hasattr(NotificationChannel, "notify_approved")
        assert hasattr(NotificationChannel, "notify_rejected")
        assert hasattr(NotificationChannel, "notify_timeout")
        assert hasattr(NotificationChannel, "channel_name")


class TestGitHubChannel:
    """Test the GitHub notification channel."""

    def test_channel_name(self):
        channel = GitHubChannel()
        assert channel.channel_name == "github"

    @pytest.mark.asyncio
    async def test_notify_awaiting_approval(self):
        """Approval notification succeeds (log-only fallback)."""
        channel = GitHubChannel()
        context = _make_review_context()
        result = await channel.notify_awaiting_approval(context)
        assert result is True

    @pytest.mark.asyncio
    async def test_notify_approved(self):
        channel = GitHubChannel()
        result = await channel.notify_approved(uuid4(), "reviewer1")
        assert result is True

    @pytest.mark.asyncio
    async def test_notify_rejected(self):
        channel = GitHubChannel()
        result = await channel.notify_rejected(uuid4(), "reviewer1", "Needs refactoring")
        assert result is True

    @pytest.mark.asyncio
    async def test_notify_timeout(self):
        channel = GitHubChannel()
        result = await channel.notify_timeout(uuid4())
        assert result is True

    def test_format_approval_request_contains_sections(self):
        """Formatted comment includes all required sections."""
        channel = GitHubChannel(review_ui_base_url="http://localhost:8000")
        context = _make_review_context()
        body = channel._format_approval_request(context)

        assert "<!-- thestudio-approval-request -->" in body
        assert "Approval Required" in body
        assert str(context.taskpacket.taskpacket_id) in body
        assert "test-org/test-repo" in body
        assert "Fix login timeout" in body
        assert "Fix the 30-second login timeout" in body
        assert "Login completes in < 5s" in body
        assert "PASSED" in body
        assert "src/auth/login.py" in body
        assert "Open Review Interface" in body
        assert "Instructions" in body

    def test_format_without_review_ui_url(self):
        """Comment renders without review link when base URL not set."""
        channel = GitHubChannel()
        context = _make_review_context()
        body = channel._format_approval_request(context)
        assert "Open Review Interface" not in body

    def test_format_truncates_long_file_list(self):
        """File list is truncated after 20 entries."""
        channel = GitHubChannel()
        context = _make_review_context()
        context.evidence.files_changed = [f"src/file{i}.py" for i in range(30)]
        body = channel._format_approval_request(context)
        assert "and 10 more" in body


class TestChannelRegistry:
    """Test the channel resolution registry."""

    def test_github_always_included(self):
        """GitHub channel is always in the registry."""
        channels = get_configured_channels()
        names = [c.channel_name for c in channels]
        assert "github" in names

    def test_returns_notification_channel_instances(self):
        """All returned channels implement the base interface."""
        channels = get_configured_channels()
        for ch in channels:
            assert isinstance(ch, NotificationChannel)
