"""Tests for approval chat API endpoints (Epic 24 Story 24.3).

Tests the router request/response models and helper functions.
Full endpoint integration tests require a database; these test the
logic layer.
"""

from uuid import uuid4

from src.approval.chat_router import (
    ChatMessageOut,
    ReviewContextResponse,
    SendMessageRequest,
    SendMessageResponse,
)


class TestRequestResponseModels:
    """Test Pydantic request/response model validation."""

    def test_review_context_response_defaults(self):
        resp = ReviewContextResponse(
            taskpacket_id=str(uuid4()),
        )
        assert resp.messages == []
        assert resp.files_changed == []
        assert resp.verification_passed is False
        assert resp.qa_passed is False

    def test_review_context_response_populated(self):
        resp = ReviewContextResponse(
            taskpacket_id=str(uuid4()),
            repo="test-org/test-repo",
            repo_tier="suggest",
            status="awaiting_approval",
            issue_title="Fix bug",
            intent_goal="Fix the login bug",
            acceptance_criteria=["Login works", "Tests pass"],
            verification_passed=True,
            qa_passed=True,
            files_changed=["src/auth.py"],
            agent_summary="Fixed the bug",
            pr_url="https://github.com/test/pull/1",
            messages=[
                ChatMessageOut(
                    id=str(uuid4()),
                    role="user",
                    content="Why auth.py?",
                    created_at="2026-03-17T10:00:00Z",
                ),
            ],
            chat_id=str(uuid4()),
        )
        assert len(resp.messages) == 1
        assert resp.messages[0].role == "user"

    def test_send_message_request(self):
        req = SendMessageRequest(content="Why did you change this file?")
        assert req.content == "Why did you change this file?"

    def test_send_message_response(self):
        user_msg = ChatMessageOut(
            id=str(uuid4()),
            role="user",
            content="Question",
            created_at="2026-03-17T10:00:00Z",
        )
        assistant_msg = ChatMessageOut(
            id=str(uuid4()),
            role="assistant",
            content="Answer",
            created_at="2026-03-17T10:00:01Z",
        )
        resp = SendMessageResponse(
            user_message=user_msg,
            assistant_message=assistant_msg,
        )
        assert resp.user_message.role == "user"
        assert resp.assistant_message.role == "assistant"

    def test_chat_message_out_serialization(self):
        msg = ChatMessageOut(
            id=str(uuid4()),
            role="system",
            content="Welcome to the review.",
            created_at="2026-03-17T10:00:00Z",
        )
        data = msg.model_dump()
        assert "id" in data
        assert data["role"] == "system"


class TestReviewContextResponseSerialization:
    """Test round-trip serialization."""

    def test_json_roundtrip(self):
        resp = ReviewContextResponse(
            taskpacket_id=str(uuid4()),
            repo="org/repo",
            acceptance_criteria=["Test 1", "Test 2"],
        )
        json_str = resp.model_dump_json()
        restored = ReviewContextResponse.model_validate_json(json_str)
        assert restored.repo == "org/repo"
        assert len(restored.acceptance_criteria) == 2
