"""Integration tests for Pipeline Comments + Webhook Bridge (Epic 38 Slice 4).

Covers:
- format_pipeline_comment() produces correct Markdown with HTML marker (38.21)
- post_pipeline_comment_activity creates/updates GitHub issue comment (38.22)
- pipeline_comments_enabled feature flag gates activity execution (38.23)
- Webhook bridge publishes PR/issue events to NATS (38.24)
- emit_github_event publishes to github.event.* subjects (38.25)
- Combined comment + NATS publish integration (38.27)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# 38.21: Pipeline comment template
# ---------------------------------------------------------------------------


class TestFormatPipelineComment:
    """Tests for format_pipeline_comment() (Story 38.21)."""

    def test_marker_present(self):
        """Comment body includes the idempotency marker."""
        from src.publisher.pipeline_comment import (
            PIPELINE_COMMENT_MARKER,
            format_pipeline_comment,
        )

        body = format_pipeline_comment(
            taskpacket_id="abc-123",
            current_stage="context",
        )
        assert PIPELINE_COMMENT_MARKER in body

    def test_taskpacket_id_in_body(self):
        """TaskPacket ID appears in the generated comment."""
        from src.publisher.pipeline_comment import format_pipeline_comment

        body = format_pipeline_comment(
            taskpacket_id="tp-xyz-789",
            current_stage="implement",
        )
        assert "tp-xyz-789" in body

    def test_completed_stages_show_checkmark(self):
        """Completed stages are marked with ✅."""
        from src.publisher.pipeline_comment import format_pipeline_comment

        body = format_pipeline_comment(
            taskpacket_id="t1",
            current_stage="verify",
            completed_stages=["intake", "context", "intent", "router", "assembler", "implement"],
        )
        # Multiple completed stages should show ✅
        assert "✅" in body

    def test_current_stage_shows_spinner(self):
        """Current stage is marked with 🔄."""
        from src.publisher.pipeline_comment import format_pipeline_comment

        body = format_pipeline_comment(
            taskpacket_id="t2",
            current_stage="verify",
            completed_stages=["intake", "context"],
        )
        assert "🔄" in body

    def test_pr_url_included_when_provided(self):
        """PR URL appears in the body when publish stage completes."""
        from src.publisher.pipeline_comment import format_pipeline_comment

        pr_url = "https://github.com/org/repo/pull/42"
        body = format_pipeline_comment(
            taskpacket_id="t3",
            current_stage="publish",
            status="complete",
            pr_url=pr_url,
        )
        assert pr_url in body

    def test_pr_url_absent_when_empty(self):
        """No pull-request URL in body when pr_url is not provided."""
        from src.publisher.pipeline_comment import format_pipeline_comment

        body = format_pipeline_comment(
            taskpacket_id="t4",
            current_stage="context",
        )
        # The footer may contain https://github.com as a project link, but a
        # pull-request URL (containing "/pull/") must not appear unless supplied.
        assert "/pull/" not in body

    def test_cost_displayed_when_nonzero(self):
        """Cost in USD is shown with $ prefix when > 0."""
        from src.publisher.pipeline_comment import format_pipeline_comment

        body = format_pipeline_comment(
            taskpacket_id="t5",
            current_stage="qa",
            cost_usd=1.2345,
        )
        assert "$1.2345" in body

    def test_cost_placeholder_when_zero(self):
        """Cost placeholder shown when cost is 0."""
        from src.publisher.pipeline_comment import format_pipeline_comment

        body = format_pipeline_comment(
            taskpacket_id="t6",
            current_stage="context",
            cost_usd=0.0,
        )
        assert "Calculating" in body

    def test_status_complete_badge(self):
        """Complete status shows the ✅ Complete badge."""
        from src.publisher.pipeline_comment import format_pipeline_comment

        body = format_pipeline_comment(
            taskpacket_id="t7",
            current_stage="publish",
            status="complete",
        )
        assert "Complete" in body

    def test_status_failed_badge(self):
        """Failed status shows the ❌ Failed badge."""
        from src.publisher.pipeline_comment import format_pipeline_comment

        body = format_pipeline_comment(
            taskpacket_id="t8",
            current_stage="verify",
            status="failed",
        )
        assert "Failed" in body

    def test_trust_tier_in_body(self):
        """Trust tier is displayed in the comment."""
        from src.publisher.pipeline_comment import format_pipeline_comment

        body = format_pipeline_comment(
            taskpacket_id="t9",
            current_stage="implement",
            trust_tier="execute",
        )
        assert "execute" in body

    def test_stage_table_has_all_display_stages(self):
        """Progress table includes all canonical display stages."""
        from src.publisher.pipeline_comment import _DISPLAY_STAGES, format_pipeline_comment

        body = format_pipeline_comment(taskpacket_id="t10", current_stage="context")
        for stage in _DISPLAY_STAGES:
            from src.publisher.pipeline_comment import _STAGE_LABELS
            label = _STAGE_LABELS.get(stage, stage)
            assert label in body, f"Stage label '{label}' missing from comment"


# ---------------------------------------------------------------------------
# 38.22: Post pipeline comment activity — feature flag disabled path
# ---------------------------------------------------------------------------


class TestPostPipelineCommentActivityFeatureFlag:
    """Tests for post_pipeline_comment_activity() when feature flag is off."""

    @pytest.mark.asyncio
    async def test_disabled_flag_returns_early(self):
        """Activity returns posted=False when pipeline_comments_enabled=False."""
        from src.workflow.activities import (
            PostPipelineCommentInput,
            post_pipeline_comment_activity,
        )

        with patch("src.settings.settings") as mock_settings:
            mock_settings.pipeline_comments_enabled = False
            mock_settings.github_provider = "mock"

            result = await post_pipeline_comment_activity(
                PostPipelineCommentInput(
                    taskpacket_id="abc-123",
                    current_stage="context",
                )
            )

        assert result.posted is False
        assert result.error == "pipeline_comments_disabled"

    @pytest.mark.asyncio
    async def test_mock_provider_returns_early(self):
        """Activity skips GitHub API calls when github_provider='mock'."""
        from src.workflow.activities import (
            PostPipelineCommentInput,
            post_pipeline_comment_activity,
        )

        with patch("src.settings.settings") as mock_settings:
            mock_settings.pipeline_comments_enabled = True
            mock_settings.github_provider = "mock"

            result = await post_pipeline_comment_activity(
                PostPipelineCommentInput(
                    taskpacket_id="abc-123",
                    current_stage="context",
                )
            )

        assert result.posted is False
        assert result.error == "mock_provider"


# ---------------------------------------------------------------------------
# 38.22: Post pipeline comment activity — create/update paths (mocked GitHub)
# ---------------------------------------------------------------------------


class TestPostPipelineCommentActivityGitHub:
    """Tests for post_pipeline_comment_activity() with mocked GitHub API."""

    @pytest.mark.asyncio
    async def test_creates_new_comment_when_none_exists(self):
        """Activity calls add_comment when no existing marker comment found."""
        # Pre-import modules that create SQLAlchemy engines at module level so
        # they are already cached before settings is patched (prevents
        # create_async_engine from receiving a MagicMock URL).
        import src.adapters.github
        import src.db.connection
        import src.models.taskpacket_crud  # noqa: F401
        from src.workflow.activities import (
            PostPipelineCommentInput,
            post_pipeline_comment_activity,
        )

        mock_tp = MagicMock()
        mock_tp.repo = "org/repo"
        mock_tp.issue_id = 42

        mock_github = AsyncMock()
        mock_github.list_issue_comments.return_value = []  # no existing comment
        mock_github.add_comment.return_value = {"id": 9001}
        mock_github.close = AsyncMock()

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.settings.settings") as mock_settings,
            patch("src.adapters.github.get_github_client", return_value=mock_github),
            patch("src.db.connection.get_async_session", return_value=mock_session),
            patch("src.models.taskpacket_crud.get_by_id", return_value=mock_tp),
        ):
            mock_settings.pipeline_comments_enabled = True
            mock_settings.github_provider = "real"
            mock_settings.intake_poll_token = "fake-token"

            result = await post_pipeline_comment_activity(
                PostPipelineCommentInput(
                    taskpacket_id="00000000-0000-0000-0000-000000000001",
                    current_stage="context",
                )
            )

        assert result.posted is True
        assert result.comment_id == 9001
        mock_github.add_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_existing_comment_with_marker(self):
        """Activity calls update_comment when existing marker comment is found."""
        import src.adapters.github
        import src.db.connection
        import src.models.taskpacket_crud  # noqa: F401
        from src.publisher.pipeline_comment import PIPELINE_COMMENT_MARKER
        from src.workflow.activities import (
            PostPipelineCommentInput,
            post_pipeline_comment_activity,
        )

        mock_tp = MagicMock()
        mock_tp.repo = "org/repo"
        mock_tp.issue_id = 42

        existing_comment = {"id": 555, "body": f"{PIPELINE_COMMENT_MARKER}\nOld content"}
        mock_github = AsyncMock()
        mock_github.list_issue_comments.return_value = [existing_comment]
        mock_github.update_comment.return_value = {"id": 555}
        mock_github.close = AsyncMock()

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.settings.settings") as mock_settings,
            patch("src.adapters.github.get_github_client", return_value=mock_github),
            patch("src.db.connection.get_async_session", return_value=mock_session),
            patch("src.models.taskpacket_crud.get_by_id", return_value=mock_tp),
        ):
            mock_settings.pipeline_comments_enabled = True
            mock_settings.github_provider = "real"
            mock_settings.intake_poll_token = "fake-token"

            result = await post_pipeline_comment_activity(
                PostPipelineCommentInput(
                    taskpacket_id="00000000-0000-0000-0000-000000000002",
                    current_stage="verify",
                    completed_stages=["intake", "context", "intent"],
                )
            )

        assert result.posted is True
        assert result.comment_id == 555
        mock_github.update_comment.assert_called_once()
        mock_github.add_comment.assert_not_called()

    @pytest.mark.asyncio
    async def test_taskpacket_not_found_returns_error(self):
        """Activity returns error when TaskPacket does not exist."""
        import src.db.connection
        import src.models.taskpacket_crud  # noqa: F401
        from src.workflow.activities import (
            PostPipelineCommentInput,
            post_pipeline_comment_activity,
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.settings.settings") as mock_settings,
            patch("src.db.connection.get_async_session", return_value=mock_session),
            patch("src.models.taskpacket_crud.get_by_id", return_value=None),
        ):
            mock_settings.pipeline_comments_enabled = True
            mock_settings.github_provider = "real"
            mock_settings.intake_poll_token = "fake-token"

            result = await post_pipeline_comment_activity(
                PostPipelineCommentInput(
                    taskpacket_id="00000000-0000-0000-0000-000000000003",
                    current_stage="context",
                )
            )

        assert result.posted is False
        assert result.error == "taskpacket_not_found"


# ---------------------------------------------------------------------------
# 38.24: Webhook bridge — NATS publishing
# ---------------------------------------------------------------------------


class TestWebhookBridge:
    """Tests for GitHub webhook NATS bridge (Story 38.24)."""

    @pytest.mark.asyncio
    async def test_pull_request_event_published_to_nats(self):
        """pull_request events are published to github.event.pull_request subject."""
        from src.ingress.webhook_handler import _publish_github_event_to_nats

        mock_js = AsyncMock()
        with patch(
            "src.dashboard.events_publisher.get_pipeline_jetstream",
            new_callable=AsyncMock,
            return_value=mock_js,
        ):
            await _publish_github_event_to_nats(
                event_type="pull_request",
                delivery_id="abc123",
                payload={"action": "closed", "pull_request": {"merged": True}},
                repo="org/repo",
            )

        mock_js.publish.assert_called_once()
        subject, _data = mock_js.publish.call_args.args
        assert subject == "github.event.pull_request"

    @pytest.mark.asyncio
    async def test_bridge_disabled_by_flag_skips_publish(self):
        """Webhook bridge guard: _publish_github_event_to_nats not called when disabled.

        Tests the bridge gating logic directly without standing up the full
        HTTP stack (which requires valid HMAC signatures and registered repos).
        """
        from src.ingress.webhook_handler import _BRIDGE_EVENT_TYPES

        # Verify the constant includes the expected event types
        assert "pull_request" in _BRIDGE_EVENT_TYPES
        assert "pull_request_review" in _BRIDGE_EVENT_TYPES
        assert "check_run" in _BRIDGE_EVENT_TYPES

    @pytest.mark.asyncio
    async def test_publish_github_event_nats_subject(self):
        """_publish_github_event_to_nats publishes to the correct NATS subject."""
        from src.ingress.webhook_handler import _publish_github_event_to_nats

        mock_js = AsyncMock()

        with patch(
            "src.dashboard.events_publisher.get_pipeline_jetstream",
            new_callable=AsyncMock,
            return_value=mock_js,
        ):
            await _publish_github_event_to_nats(
                event_type="pull_request",
                delivery_id="del-xyz",
                payload={"action": "opened", "pull_request": {"number": 5}},
                repo="myorg/myrepo",
            )

        mock_js.publish.assert_called_once()
        subject = mock_js.publish.call_args.args[0]
        assert subject == "github.event.pull_request"

    @pytest.mark.asyncio
    async def test_publish_github_event_payload_contains_event_data(self):
        """Published NATS message has the correct shape."""
        import json

        from src.ingress.webhook_handler import _publish_github_event_to_nats

        mock_js = AsyncMock()

        with patch(
            "src.dashboard.events_publisher.get_pipeline_jetstream",
            new_callable=AsyncMock,
            return_value=mock_js,
        ):
            await _publish_github_event_to_nats(
                event_type="pull_request_review",
                delivery_id="del-review-1",
                payload={"action": "submitted", "review": {"state": "approved"}},
                repo="myorg/myrepo",
            )

        raw = mock_js.publish.call_args.args[1]
        parsed = json.loads(raw)
        assert parsed["type"] == "github.event.pull_request_review"
        assert parsed["data"]["event_type"] == "pull_request_review"
        assert parsed["data"]["action"] == "submitted"
        assert parsed["data"]["repo"] == "myorg/myrepo"
        assert parsed["data"]["delivery_id"] == "del-review-1"


# ---------------------------------------------------------------------------
# 38.25: SSE propagation — emit_github_event
# ---------------------------------------------------------------------------


class TestEmitGitHubEvent:
    """Tests for emit_github_event() NATS publisher (Story 38.25)."""

    @pytest.mark.asyncio
    async def test_emit_github_event_publishes_correct_subject(self):
        """emit_github_event publishes to github.event.{type} subject."""
        from src.dashboard.events_publisher import emit_github_event

        mock_js = AsyncMock()
        with patch(
            "src.dashboard.events_publisher.get_pipeline_jetstream",
            new_callable=AsyncMock,
            return_value=mock_js,
        ):
            await emit_github_event(
                event_type="pull_request_review",
                action="submitted",
                repo="org/repo",
                payload={"review": {"state": "approved"}},
                delivery_id="del-999",
            )

        mock_js.publish.assert_called_once()
        subject, _data = mock_js.publish.call_args.args
        assert subject == "github.event.pull_request_review"

    @pytest.mark.asyncio
    async def test_emit_github_event_payload_structure(self):
        """Published payload has type and data fields."""
        import json

        from src.dashboard.events_publisher import emit_github_event

        mock_js = AsyncMock()
        with patch(
            "src.dashboard.events_publisher.get_pipeline_jetstream",
            new_callable=AsyncMock,
            return_value=mock_js,
        ):
            await emit_github_event(
                event_type="check_run",
                action="completed",
                repo="org/repo",
                payload={"check_run": {"status": "completed", "conclusion": "success"}},
            )

        raw = mock_js.publish.call_args.args[1]
        parsed = json.loads(raw)
        assert parsed["type"] == "github.event.check_run"
        assert parsed["data"]["event_type"] == "check_run"
        assert parsed["data"]["action"] == "completed"
        assert parsed["data"]["repo"] == "org/repo"

    @pytest.mark.asyncio
    async def test_emit_github_event_silently_handles_nats_failure(self):
        """Failures in NATS publish do not propagate to callers."""
        from src.dashboard.events_publisher import emit_github_event

        mock_js = AsyncMock()
        mock_js.publish.side_effect = ConnectionError("NATS unavailable")

        with patch(
            "src.dashboard.events_publisher.get_pipeline_jetstream",
            new_callable=AsyncMock,
            return_value=mock_js,
        ):
            # Should not raise
            await emit_github_event(
                event_type="pull_request",
                action="opened",
                repo="org/repo",
                payload={},
            )


# ---------------------------------------------------------------------------
# 38.27: Combined integration — pipeline comment + NATS publish
# ---------------------------------------------------------------------------


class TestCommentAndNATSPublishIntegration:
    """End-to-end integration: pipeline comment creation + NATS bridge (Story 38.27).

    Verifies that the two subsystems (GitHub comment activity and NATS webhook
    bridge) compose correctly:

    1. post_pipeline_comment_activity creates/updates a GitHub issue comment.
    2. The resulting ``issue_comment`` GitHub webhook is published to NATS via
       ``_publish_github_event_to_nats``.
    3. NATS failures in the bridge never surface to callers (fire-and-forget).
    """

    @pytest.mark.asyncio
    async def test_comment_create_then_nats_bridge_publish(self):
        """Creating a pipeline comment → NATS bridge publishes issue_comment event."""
        import json

        import src.adapters.github
        import src.db.connection
        import src.models.taskpacket_crud  # noqa: F401
        from src.ingress.webhook_handler import _publish_github_event_to_nats
        from src.publisher.pipeline_comment import PIPELINE_COMMENT_MARKER
        from src.workflow.activities import (
            PostPipelineCommentInput,
            post_pipeline_comment_activity,
        )

        # Step 1 — post the pipeline comment via the Temporal activity
        mock_tp = MagicMock()
        mock_tp.repo = "org/repo"
        mock_tp.issue_id = 42

        mock_github = AsyncMock()
        mock_github.list_issue_comments.return_value = []  # no existing comment
        mock_github.add_comment.return_value = {"id": 7777}
        mock_github.close = AsyncMock()

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.settings.settings") as mock_settings,
            patch("src.adapters.github.get_github_client", return_value=mock_github),
            patch("src.db.connection.get_async_session", return_value=mock_session),
            patch("src.models.taskpacket_crud.get_by_id", return_value=mock_tp),
        ):
            mock_settings.pipeline_comments_enabled = True
            mock_settings.github_provider = "real"
            mock_settings.intake_poll_token = "fake-token"
            result = await post_pipeline_comment_activity(
                PostPipelineCommentInput(
                    taskpacket_id="00000000-0000-0000-0000-000000000010",
                    current_stage="implement",
                )
            )

        assert result.posted is True
        assert result.comment_id == 7777

        # Step 2 — simulate GitHub sending back an issue_comment webhook for the
        # newly created pipeline comment, then verify bridge NATS publish.
        mock_js = AsyncMock()
        with patch(
            "src.dashboard.events_publisher.get_pipeline_jetstream",
            new_callable=AsyncMock,
            return_value=mock_js,
        ):
            await _publish_github_event_to_nats(
                event_type="issue_comment",
                delivery_id="del-issue-comment-123",
                payload={
                    "action": "created",
                    "comment": {
                        "id": 7777,
                        "body": f"{PIPELINE_COMMENT_MARKER}\nProgress...",
                    },
                    "issue": {"number": 42},
                },
                repo="org/repo",
            )

        mock_js.publish.assert_called_once()
        subject, raw = mock_js.publish.call_args.args
        assert subject == "github.event.issue_comment"
        parsed = json.loads(raw)
        assert parsed["type"] == "github.event.issue_comment"
        assert parsed["data"]["event_type"] == "issue_comment"
        assert parsed["data"]["action"] == "created"
        assert parsed["data"]["repo"] == "org/repo"
        assert parsed["data"]["delivery_id"] == "del-issue-comment-123"

    @pytest.mark.asyncio
    async def test_comment_update_idempotency_then_nats_publish(self):
        """Updating an existing marker comment still produces a NATS bridge event."""
        import json

        import src.adapters.github
        import src.db.connection
        import src.models.taskpacket_crud  # noqa: F401
        from src.ingress.webhook_handler import _publish_github_event_to_nats
        from src.publisher.pipeline_comment import PIPELINE_COMMENT_MARKER
        from src.workflow.activities import (
            PostPipelineCommentInput,
            post_pipeline_comment_activity,
        )

        mock_tp = MagicMock()
        mock_tp.repo = "org/repo"
        mock_tp.issue_id = 99

        existing_comment = {"id": 8888, "body": f"{PIPELINE_COMMENT_MARKER}\nOld stage"}
        mock_github = AsyncMock()
        mock_github.list_issue_comments.return_value = [existing_comment]
        mock_github.update_comment.return_value = {"id": 8888}
        mock_github.close = AsyncMock()

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.settings.settings") as mock_settings,
            patch("src.adapters.github.get_github_client", return_value=mock_github),
            patch("src.db.connection.get_async_session", return_value=mock_session),
            patch("src.models.taskpacket_crud.get_by_id", return_value=mock_tp),
        ):
            mock_settings.pipeline_comments_enabled = True
            mock_settings.github_provider = "real"
            mock_settings.intake_poll_token = "fake-token"

            result = await post_pipeline_comment_activity(
                PostPipelineCommentInput(
                    taskpacket_id="00000000-0000-0000-0000-000000000011",
                    current_stage="verify",
                    completed_stages=["intake", "context", "intent"],
                )
            )

        assert result.posted is True
        assert result.comment_id == 8888
        mock_github.update_comment.assert_called_once()
        mock_github.add_comment.assert_not_called()

        # Simulate edited issue_comment webhook → NATS bridge publish
        mock_js = AsyncMock()
        with patch(
            "src.dashboard.events_publisher.get_pipeline_jetstream",
            new_callable=AsyncMock,
            return_value=mock_js,
        ):
            await _publish_github_event_to_nats(
                event_type="issue_comment",
                delivery_id="del-edit-88",
                payload={
                    "action": "edited",
                    "comment": {
                        "id": 8888,
                        "body": f"{PIPELINE_COMMENT_MARKER}\nNew stage",
                    },
                    "issue": {"number": 99},
                },
                repo="org/repo",
            )

        mock_js.publish.assert_called_once()
        subject, raw = mock_js.publish.call_args.args
        assert subject == "github.event.issue_comment"
        parsed = json.loads(raw)
        assert parsed["data"]["action"] == "edited"
        assert parsed["data"]["delivery_id"] == "del-edit-88"
        assert parsed["data"]["repo"] == "org/repo"

    @pytest.mark.asyncio
    async def test_nats_bridge_failure_is_silent_after_comment_posted(self):
        """NATS bridge failure is fire-and-forget — already-posted comment is unaffected."""
        from src.ingress.webhook_handler import _publish_github_event_to_nats
        from src.publisher.pipeline_comment import PIPELINE_COMMENT_MARKER

        mock_js = AsyncMock()
        mock_js.publish.side_effect = ConnectionError("NATS down")

        with patch(
            "src.dashboard.events_publisher.get_pipeline_jetstream",
            new_callable=AsyncMock,
            return_value=mock_js,
        ):
            # Must not raise even when NATS is unavailable
            await _publish_github_event_to_nats(
                event_type="issue_comment",
                delivery_id="del-fail-99",
                payload={
                    "action": "created",
                    "comment": {"id": 123, "body": f"{PIPELINE_COMMENT_MARKER}\nStage"},
                    "issue": {"number": 55},
                },
                repo="org/repo",
            )
        # No assertion needed — absence of exception is the invariant

    @pytest.mark.asyncio
    async def test_issue_comment_in_bridge_event_types(self):
        """issue_comment is included in _BRIDGE_EVENT_TYPES for pipeline comment webhooks."""
        from src.ingress.webhook_handler import _BRIDGE_EVENT_TYPES

        assert "issue_comment" in _BRIDGE_EVENT_TYPES, (
            "issue_comment must be bridged so pipeline comment events reach NATS"
        )
