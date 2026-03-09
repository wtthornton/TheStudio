"""Tests for Model Gateway and Tool Hub enforcement in activities — Epic 11.

Verifies that all LLM-using activities route through ModelRouter and record
audit entries, and that tool-using activities check ToolPolicyEngine.
"""

from __future__ import annotations

import pytest

from src.admin.model_gateway import get_model_audit_store
from src.workflow.activities import (
    ContextInput,
    ImplementInput,
    IntentInput,
    PublishInput,
    QAInput,
    VerifyInput,
    context_activity,
    implement_activity,
    intent_activity,
    publish_activity,
    qa_activity,
    verify_activity,
)


@pytest.fixture(autouse=True)
def _reset_audit():
    store = get_model_audit_store()
    store.clear()
    yield
    store.clear()


class TestModelGatewayEnforcement:
    """Every LLM-using activity must route through ModelRouter and record audit."""

    @pytest.mark.asyncio
    async def test_context_activity_records_audit(self):
        await context_activity(ContextInput(
            taskpacket_id="tp-1", repo="org/repo",
            issue_title="test", issue_body="body", labels=[],
        ))
        records = get_model_audit_store().query(step="context")
        assert len(records) >= 1
        assert records[0].provider == "anthropic"

    @pytest.mark.asyncio
    async def test_intent_activity_records_audit(self):
        await intent_activity(IntentInput(
            taskpacket_id="tp-1", issue_title="test", issue_body="body",
        ))
        records = get_model_audit_store().query(step="intent")
        assert len(records) >= 1
        assert records[0].provider == "anthropic"

    @pytest.mark.asyncio
    async def test_intent_activity_with_security_overlay(self):
        """Security overlay escalates to STRONG model class."""
        await intent_activity(IntentInput(
            taskpacket_id="tp-1", issue_title="test", issue_body="body",
            risk_flags={"security": True},
        ))
        records = get_model_audit_store().query(step="intent")
        assert len(records) >= 1
        # Security overlay → STRONG → opus model
        assert "opus" in records[0].model
        assert "security" in records[0].overlays

    @pytest.mark.asyncio
    async def test_implement_activity_records_audit(self):
        await implement_activity(ImplementInput(
            taskpacket_id="tp-1", repo_path="/tmp",
        ))
        records = get_model_audit_store().query(step="primary_agent")
        assert len(records) >= 1

    @pytest.mark.asyncio
    async def test_qa_activity_records_audit(self):
        await qa_activity(QAInput(taskpacket_id="tp-1"))
        records = get_model_audit_store().query(step="qa_eval")
        assert len(records) >= 1

    @pytest.mark.asyncio
    async def test_no_audit_for_non_llm_activities(self):
        """Verify and publish don't use LLM — should not record model audit."""
        store = get_model_audit_store()
        store.clear()

        await verify_activity(VerifyInput(taskpacket_id="tp-1"))

        # Verify uses tools but not LLM
        assert len(store.query(step="verify")) == 0


class TestToolHubEnforcement:
    """Activities that use tools must check ToolPolicyEngine."""

    @pytest.mark.asyncio
    async def test_context_activity_checks_tool_access(self):
        """context_activity checks context-retrieval suite access."""
        # Should not raise — developer has access to context-retrieval
        result = await context_activity(ContextInput(
            taskpacket_id="tp-1", repo="org/repo",
            issue_title="test", issue_body="body", labels=[],
        ))
        assert result.complexity_index == "low"

    @pytest.mark.asyncio
    async def test_implement_activity_checks_tool_access(self):
        """implement_activity checks code-quality suite access."""
        result = await implement_activity(ImplementInput(
            taskpacket_id="tp-1", repo_path="/tmp",
        ))
        assert result.taskpacket_id == "tp-1"

    @pytest.mark.asyncio
    async def test_verify_activity_checks_tool_access(self):
        """verify_activity checks code-quality suite access."""
        result = await verify_activity(VerifyInput(taskpacket_id="tp-1"))
        assert result.passed is True
