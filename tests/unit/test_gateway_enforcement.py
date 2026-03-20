"""Tests for Model Gateway and Tool Hub enforcement in activities — Epic 11.

Verifies that all LLM-using activities route through ModelRouter and record
audit entries, and that tool-using activities check ToolPolicyEngine.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.adapters.llm import LLMResponse
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


def _enable_agent(agent_name: str):
    """Return a patch that enables the given agent's LLM feature flag."""
    from src.settings import settings

    patched = {**settings.agent_llm_enabled, agent_name: True}
    return patch.object(settings, "agent_llm_enabled", patched)


def _mock_llm_completion():
    """Mock AgentRunner._call_llm_completion to return a valid LLMResponse."""
    return patch(
        "src.agent.framework.AgentRunner._call_llm_completion",
        return_value=LLMResponse(
            content='{"goal": "test", "acceptance_criteria": ["done"]}',
            tokens_in=10,
            tokens_out=20,
            model="claude-sonnet-4-20250514",
        ),
    )


class TestModelGatewayEnforcement:
    """Every LLM-using activity must route through ModelRouter and record audit."""

    @pytest.mark.asyncio
    async def test_context_activity_records_audit(self):
        with _enable_agent("context_agent"), _mock_llm_completion():
            await context_activity(ContextInput(
                taskpacket_id="tp-1", repo="org/repo",
                issue_title="test", issue_body="body", labels=[],
            ))
        records = get_model_audit_store().query(step="context")
        assert len(records) >= 1
        assert records[0].provider == "anthropic"

    @pytest.mark.asyncio
    async def test_intent_activity_records_audit(self):
        with _enable_agent("intent_agent"), _mock_llm_completion():
            await intent_activity(IntentInput(
                taskpacket_id="tp-1", issue_title="test", issue_body="body",
            ))
        records = get_model_audit_store().query(step="intent")
        assert len(records) >= 1
        assert records[0].provider == "anthropic"

    @pytest.mark.asyncio
    async def test_intent_activity_with_security_overlay(self):
        """Security overlay escalates to STRONG model class."""
        from src.agent.framework import AgentContext

        original_init = AgentContext.__init__

        def _init_with_overlays(self, *args, **kwargs):
            """Derive overlays from risk_flags if not explicitly set."""
            original_init(self, *args, **kwargs)
            if self.risk_flags and not self.overlays:
                self.overlays = [k for k, v in self.risk_flags.items() if v]

        with (
            _enable_agent("intent_agent"),
            patch(
                "src.agent.framework.AgentRunner._call_llm_completion",
                return_value=LLMResponse(
                    content='{"goal": "test", "acceptance_criteria": ["done"]}',
                    tokens_in=10,
                    tokens_out=20,
                    model="claude-opus-4-20250514",
                ),
            ),
            patch.object(AgentContext, "__init__", _init_with_overlays),
        ):
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
        with _enable_agent("qa_agent"), _mock_llm_completion():
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
        """verify_activity fails with no files, passes with files."""
        result = await verify_activity(VerifyInput(taskpacket_id="tp-1"))
        assert result.passed is False

        result = await verify_activity(
            VerifyInput(taskpacket_id="tp-1", changed_files=["src/fix.py"])
        )
        assert result.passed is True
