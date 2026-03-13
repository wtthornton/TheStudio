"""Unit tests for readiness re-evaluation (Story 16.5).

Tests webhook payload normalization, re-evaluation trigger detection,
and pipeline re-evaluation loop behavior.
"""

from __future__ import annotations

from src.ingress.webhook_handler import (
    _is_reevaluation_trigger,
    normalize_webhook_payload,
)


class TestNormalizeWebhookPayload:
    """Tests for normalize_webhook_payload()."""

    def test_issues_event_extracts_issue_data(self):
        payload = {
            "action": "opened",
            "issue": {
                "number": 42,
                "title": "Fix login bug",
                "body": "Login fails after timeout",
            },
        }
        result = normalize_webhook_payload("issues", payload)
        assert result["issue_number"] == 42
        assert result["issue_title"] == "Fix login bug"
        assert result["issue_body"] == "Login fails after timeout"
        assert result["action"] == "opened"

    def test_issue_comment_event_extracts_nested_issue_data(self):
        payload = {
            "action": "created",
            "comment": {"id": 1, "body": "I added more detail"},
            "issue": {
                "number": 42,
                "title": "Fix login bug",
                "body": "Updated body with acceptance criteria",
            },
        }
        result = normalize_webhook_payload("issue_comment", payload)
        assert result["issue_number"] == 42
        assert result["issue_title"] == "Fix login bug"
        assert result["issue_body"] == "Updated body with acceptance criteria"
        assert result["action"] == "created"

    def test_missing_issue_data_returns_defaults(self):
        result = normalize_webhook_payload("issues", {"action": "opened"})
        assert result["issue_number"] == 0
        assert result["issue_title"] == ""
        assert result["issue_body"] == ""

    def test_issues_edited_action(self):
        payload = {
            "action": "edited",
            "issue": {
                "number": 7,
                "title": "Updated title",
                "body": "Better description",
            },
        }
        result = normalize_webhook_payload("issues", payload)
        assert result["action"] == "edited"
        assert result["issue_number"] == 7


class TestIsReevaluationTrigger:
    """Tests for _is_reevaluation_trigger()."""

    def test_issues_edited_is_trigger(self):
        assert _is_reevaluation_trigger("issues", "edited") is True

    def test_issue_comment_created_is_trigger(self):
        assert _is_reevaluation_trigger("issue_comment", "created") is True

    def test_issues_opened_is_not_trigger(self):
        assert _is_reevaluation_trigger("issues", "opened") is False

    def test_issue_comment_deleted_is_not_trigger(self):
        assert _is_reevaluation_trigger("issue_comment", "deleted") is False

    def test_unknown_event_is_not_trigger(self):
        assert _is_reevaluation_trigger("pull_request", "opened") is False


class TestPipelineReadinessReeval:
    """Tests for the readiness re-evaluation loop in the pipeline workflow."""

    def test_pipeline_output_has_readiness_fields(self):
        from src.workflow.pipeline import PipelineOutput

        output = PipelineOutput()
        assert output.readiness_evaluations == 0
        assert output.readiness_escalated is False

    def test_max_readiness_evaluations_constant(self):
        from src.workflow.pipeline import MAX_READINESS_EVALUATIONS

        assert MAX_READINESS_EVALUATIONS == 3

    def test_readiness_reevaluation_timeout_is_7_days(self):
        from datetime import timedelta

        from src.workflow.pipeline import READINESS_REEVALUATION_TIMEOUT

        assert READINESS_REEVALUATION_TIMEOUT == timedelta(days=7)
