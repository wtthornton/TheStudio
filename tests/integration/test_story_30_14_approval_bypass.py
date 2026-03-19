"""Story 30.14: Approval Auto-Bypass Feature Flag — Integration Tests.

Verifies that the approval_auto_bypass feature flag:

1. Defaults to False (safe default)
2. Can be enabled via THESTUDIO_APPROVAL_AUTO_BYPASS=true
3. Safety validator rejects bypass + real GitHub + real LLM
4. Safety validator allows bypass + mock GitHub
5. Safety validator allows bypass + mock LLM
6. Pipeline skips approval gate when bypass is enabled (Execute tier)
7. Pipeline skips approval gate when bypass is enabled (Suggest tier)
8. Observe tier is unaffected by the bypass flag
9. PipelineOutput.approval_bypassed is True when gate is skipped
10. Docker Compose files contain the env var with correct defaults
11. workflow_trigger threads the setting into PipelineInput
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.settings import Settings
from src.workflow.pipeline import (
    APPROVAL_REQUIRED_TIERS,
    PipelineInput,
    PipelineOutput,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENC_KEY = "hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac="

# Project root for Docker Compose file checks
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# 1. Feature flag default and activation
# ---------------------------------------------------------------------------


class TestApprovalBypassFlagActivation:
    """Verify approval_auto_bypass flag activates correctly."""

    def test_default_off(self) -> None:
        """approval_auto_bypass defaults to False."""
        s = Settings(encryption_key=_ENC_KEY)
        assert s.approval_auto_bypass is False

    def test_enable_via_env(self, monkeypatch) -> None:
        """THESTUDIO_APPROVAL_AUTO_BYPASS=true enables bypass."""
        monkeypatch.setenv("THESTUDIO_APPROVAL_AUTO_BYPASS", "true")
        monkeypatch.setenv("THESTUDIO_ENCRYPTION_KEY", _ENC_KEY)

        s = Settings()
        assert s.approval_auto_bypass is True

    def test_disable_via_env(self, monkeypatch) -> None:
        """THESTUDIO_APPROVAL_AUTO_BYPASS=false keeps bypass off."""
        monkeypatch.setenv("THESTUDIO_APPROVAL_AUTO_BYPASS", "false")
        monkeypatch.setenv("THESTUDIO_ENCRYPTION_KEY", _ENC_KEY)

        s = Settings()
        assert s.approval_auto_bypass is False


# ---------------------------------------------------------------------------
# 2. Safety validator
# ---------------------------------------------------------------------------


class TestApprovalBypassSafetyValidator:
    """Validator must reject bypass + real GitHub + real LLM."""

    def test_rejects_bypass_with_real_github_and_real_llm(self) -> None:
        """ValueError when all three conditions are true."""
        with pytest.raises(ValueError, match="THESTUDIO_APPROVAL_AUTO_BYPASS"):
            Settings(
                encryption_key=_ENC_KEY,
                approval_auto_bypass=True,
                github_provider="real",
                llm_provider="anthropic",
            )

    def test_allows_bypass_with_mock_github(self) -> None:
        """Bypass is allowed when github_provider=mock (even with real LLM)."""
        s = Settings(
            encryption_key=_ENC_KEY,
            approval_auto_bypass=True,
            github_provider="mock",
            llm_provider="anthropic",
        )
        assert s.approval_auto_bypass is True

    def test_allows_bypass_with_mock_llm(self) -> None:
        """Bypass is allowed when llm_provider=mock (even with real GitHub)."""
        s = Settings(
            encryption_key=_ENC_KEY,
            approval_auto_bypass=True,
            github_provider="real",
            llm_provider="mock",
        )
        assert s.approval_auto_bypass is True

    def test_allows_bypass_with_both_mock(self) -> None:
        """Bypass is allowed when both providers are mock."""
        s = Settings(
            encryption_key=_ENC_KEY,
            approval_auto_bypass=True,
            github_provider="mock",
            llm_provider="mock",
        )
        assert s.approval_auto_bypass is True

    def test_no_bypass_no_validation_error(self) -> None:
        """When bypass is False, real providers are fine (normal production)."""
        s = Settings(
            encryption_key=_ENC_KEY,
            approval_auto_bypass=False,
            github_provider="real",
            llm_provider="anthropic",
        )
        assert s.approval_auto_bypass is False


# ---------------------------------------------------------------------------
# 3. PipelineInput / PipelineOutput field existence
# ---------------------------------------------------------------------------


class TestPipelineDataclassFields:
    """Verify new fields exist on pipeline dataclasses."""

    def test_pipeline_input_has_bypass_field(self) -> None:
        """PipelineInput.approval_auto_bypass defaults to False."""
        inp = PipelineInput(
            taskpacket_id="tp-bypass-test",
            correlation_id="corr-bypass-test",
        )
        assert inp.approval_auto_bypass is False

    def test_pipeline_input_bypass_settable(self) -> None:
        """PipelineInput.approval_auto_bypass can be set to True."""
        inp = PipelineInput(
            taskpacket_id="tp-bypass-test",
            correlation_id="corr-bypass-test",
            approval_auto_bypass=True,
        )
        assert inp.approval_auto_bypass is True

    def test_pipeline_output_has_bypassed_field(self) -> None:
        """PipelineOutput.approval_bypassed defaults to False."""
        out = PipelineOutput()
        assert out.approval_bypassed is False

    def test_pipeline_output_bypassed_settable(self) -> None:
        """PipelineOutput.approval_bypassed can be set to True."""
        out = PipelineOutput()
        out.approval_bypassed = True
        assert out.approval_bypassed is True


# ---------------------------------------------------------------------------
# 4. Pipeline bypass behavior (mocked workflow)
# ---------------------------------------------------------------------------


class TestPipelineBypassBehavior:
    """Verify pipeline skips approval when bypass is enabled."""

    @pytest.mark.asyncio
    async def test_execute_tier_bypass_skips_approval(self) -> None:
        """Execute tier with approval_auto_bypass=True skips the approval gate."""
        from src.workflow.pipeline import TheStudioPipelineWorkflow

        wf = TheStudioPipelineWorkflow()
        params = PipelineInput(
            taskpacket_id="tp-exec-bypass",
            correlation_id="corr-exec-bypass",
            repo_tier="execute",
            approval_auto_bypass=True,
        )

        # Mock all activities to return valid results
        mock_intake = AsyncMock(return_value=_mock_intake_output())
        mock_context = AsyncMock(return_value=_mock_context_output())
        mock_intent = AsyncMock(return_value=_mock_intent_output())
        mock_router = AsyncMock(return_value=None)
        mock_assembler = AsyncMock(return_value=_mock_assembler_output())
        mock_impl = AsyncMock(return_value=_mock_impl_output())
        mock_verify = AsyncMock(return_value=_mock_verify_output())
        mock_qa = AsyncMock(return_value=_mock_qa_output())
        mock_publish = AsyncMock(return_value=_mock_publish_output())

        with (
            patch("src.workflow.pipeline.workflow") as mock_wf,
            patch("src.workflow.pipeline.intake_activity", mock_intake),
            patch("src.workflow.pipeline.context_activity", mock_context),
            patch("src.workflow.pipeline.intent_activity", mock_intent),
            patch("src.workflow.pipeline.router_activity", mock_router),
            patch("src.workflow.pipeline.assembler_activity", mock_assembler),
            patch("src.workflow.pipeline.implement_activity", mock_impl),
            patch("src.workflow.pipeline.verify_activity", mock_verify),
            patch("src.workflow.pipeline.qa_activity", mock_qa),
            patch("src.workflow.pipeline.publish_activity", mock_publish),
            patch("src.workflow.pipeline.post_approval_request_activity") as mock_approval_req,
            patch("src.workflow.pipeline.escalate_timeout_activity") as mock_escalate,
        ):
            mock_wf.execute_activity = _side_effect_execute_activity({
                "intake_activity": mock_intake,
                "context_activity": mock_context,
                "intent_activity": mock_intent,
                "router_activity": mock_router,
                "assembler_activity": mock_assembler,
                "implement_activity": mock_impl,
                "verify_activity": mock_verify,
                "qa_activity": mock_qa,
                "publish_activity": mock_publish,
            })
            mock_wf.logger = _mock_logger()

            output = await wf.run(params)

        assert output.success is True
        assert output.approval_bypassed is True
        assert output.awaiting_approval is False
        # Approval request and escalation should NOT have been called
        mock_approval_req.assert_not_called()
        mock_escalate.assert_not_called()

    @pytest.mark.asyncio
    async def test_suggest_tier_bypass_skips_approval(self) -> None:
        """Suggest tier with approval_auto_bypass=True also skips approval."""
        from src.workflow.pipeline import TheStudioPipelineWorkflow

        wf = TheStudioPipelineWorkflow()
        params = PipelineInput(
            taskpacket_id="tp-suggest-bypass",
            correlation_id="corr-suggest-bypass",
            repo_tier="suggest",
            approval_auto_bypass=True,
        )

        mock_intake = AsyncMock(return_value=_mock_intake_output())
        mock_context = AsyncMock(return_value=_mock_context_output())
        mock_intent = AsyncMock(return_value=_mock_intent_output())
        mock_router = AsyncMock(return_value=None)
        mock_assembler = AsyncMock(return_value=_mock_assembler_output())
        mock_impl = AsyncMock(return_value=_mock_impl_output())
        mock_verify = AsyncMock(return_value=_mock_verify_output())
        mock_qa = AsyncMock(return_value=_mock_qa_output())
        mock_publish = AsyncMock(return_value=_mock_publish_output())

        with (
            patch("src.workflow.pipeline.workflow") as mock_wf,
            patch("src.workflow.pipeline.intake_activity", mock_intake),
            patch("src.workflow.pipeline.context_activity", mock_context),
            patch("src.workflow.pipeline.intent_activity", mock_intent),
            patch("src.workflow.pipeline.router_activity", mock_router),
            patch("src.workflow.pipeline.assembler_activity", mock_assembler),
            patch("src.workflow.pipeline.implement_activity", mock_impl),
            patch("src.workflow.pipeline.verify_activity", mock_verify),
            patch("src.workflow.pipeline.qa_activity", mock_qa),
            patch("src.workflow.pipeline.publish_activity", mock_publish),
        ):
            mock_wf.execute_activity = _side_effect_execute_activity({
                "intake_activity": mock_intake,
                "context_activity": mock_context,
                "intent_activity": mock_intent,
                "router_activity": mock_router,
                "assembler_activity": mock_assembler,
                "implement_activity": mock_impl,
                "verify_activity": mock_verify,
                "qa_activity": mock_qa,
                "publish_activity": mock_publish,
            })
            mock_wf.logger = _mock_logger()

            output = await wf.run(params)

        assert output.success is True
        assert output.approval_bypassed is True

    @pytest.mark.asyncio
    async def test_observe_tier_unaffected_by_bypass(self) -> None:
        """Observe tier never enters approval gate, bypass flag is irrelevant."""
        from src.workflow.pipeline import TheStudioPipelineWorkflow

        assert "observe" not in APPROVAL_REQUIRED_TIERS

        wf = TheStudioPipelineWorkflow()
        params = PipelineInput(
            taskpacket_id="tp-observe-bypass",
            correlation_id="corr-observe-bypass",
            repo_tier="observe",
            approval_auto_bypass=True,
        )

        mock_intake = AsyncMock(return_value=_mock_intake_output())
        mock_context = AsyncMock(return_value=_mock_context_output())
        mock_intent = AsyncMock(return_value=_mock_intent_output())
        mock_router = AsyncMock(return_value=None)
        mock_assembler = AsyncMock(return_value=_mock_assembler_output())
        mock_impl = AsyncMock(return_value=_mock_impl_output())
        mock_verify = AsyncMock(return_value=_mock_verify_output())
        mock_qa = AsyncMock(return_value=_mock_qa_output())
        mock_publish = AsyncMock(return_value=_mock_publish_output())

        with (
            patch("src.workflow.pipeline.workflow") as mock_wf,
            patch("src.workflow.pipeline.intake_activity", mock_intake),
            patch("src.workflow.pipeline.context_activity", mock_context),
            patch("src.workflow.pipeline.intent_activity", mock_intent),
            patch("src.workflow.pipeline.router_activity", mock_router),
            patch("src.workflow.pipeline.assembler_activity", mock_assembler),
            patch("src.workflow.pipeline.implement_activity", mock_impl),
            patch("src.workflow.pipeline.verify_activity", mock_verify),
            patch("src.workflow.pipeline.qa_activity", mock_qa),
            patch("src.workflow.pipeline.publish_activity", mock_publish),
        ):
            mock_wf.execute_activity = _side_effect_execute_activity({
                "intake_activity": mock_intake,
                "context_activity": mock_context,
                "intent_activity": mock_intent,
                "router_activity": mock_router,
                "assembler_activity": mock_assembler,
                "implement_activity": mock_impl,
                "verify_activity": mock_verify,
                "qa_activity": mock_qa,
                "publish_activity": mock_publish,
            })
            mock_wf.logger = _mock_logger()

            output = await wf.run(params)

        assert output.success is True
        # Observe tier never triggers approval, so approval_bypassed stays False
        assert output.approval_bypassed is False
        assert output.awaiting_approval is False


# ---------------------------------------------------------------------------
# 5. Docker Compose env var checks
# ---------------------------------------------------------------------------


class TestDockerComposeEnvVar:
    """All 3 Docker Compose files must contain THESTUDIO_APPROVAL_AUTO_BYPASS."""

    @staticmethod
    def _get_bypass_default(content: str) -> str:
        """Extract the default value from THESTUDIO_APPROVAL_AUTO_BYPASS line."""
        match = re.search(r"THESTUDIO_APPROVAL_AUTO_BYPASS.*:-(true|false)\}", content)
        assert match, "THESTUDIO_APPROVAL_AUTO_BYPASS with default not found"
        return match.group(1)

    def test_dev_compose_has_bypass_true(self) -> None:
        """docker-compose.dev.yml defaults bypass to true."""
        content = (_PROJECT_ROOT / "docker-compose.dev.yml").read_text()
        assert "THESTUDIO_APPROVAL_AUTO_BYPASS" in content
        assert self._get_bypass_default(content) == "true"

    def test_staging_compose_has_bypass_true(self) -> None:
        """infra/docker-compose.yml defaults bypass to true."""
        content = (_PROJECT_ROOT / "infra" / "docker-compose.yml").read_text()
        assert "THESTUDIO_APPROVAL_AUTO_BYPASS" in content
        assert self._get_bypass_default(content) == "true"

    def test_prod_compose_has_bypass_false(self) -> None:
        """infra/docker-compose.prod.yml defaults bypass to false."""
        content = (_PROJECT_ROOT / "infra" / "docker-compose.prod.yml").read_text()
        assert "THESTUDIO_APPROVAL_AUTO_BYPASS" in content
        assert self._get_bypass_default(content) == "false"


# ---------------------------------------------------------------------------
# 6. Workflow trigger wiring
# ---------------------------------------------------------------------------


class TestWorkflowTriggerWiring:
    """workflow_trigger.py must thread approval_auto_bypass from settings."""

    def test_workflow_trigger_source_contains_bypass(self) -> None:
        """The source code of workflow_trigger.py passes approval_auto_bypass."""
        source = (_PROJECT_ROOT / "src" / "ingress" / "workflow_trigger.py").read_text()
        assert "approval_auto_bypass" in source

    @pytest.mark.asyncio
    async def test_workflow_trigger_passes_bypass_to_workflow(self) -> None:
        """start_workflow passes approval_auto_bypass in the arg dict."""
        from uuid import uuid4

        from src.ingress.workflow_trigger import start_workflow

        mock_handle = AsyncMock()
        mock_handle.result_run_id = "run-id-123"
        mock_client = AsyncMock()
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with (
            patch("src.ingress.workflow_trigger.get_temporal_client", return_value=mock_client),
            patch("src.ingress.workflow_trigger.settings") as mock_settings,
        ):
            mock_settings.temporal_task_queue = "test-queue"
            mock_settings.approval_auto_bypass = True

            tp_id = uuid4()
            corr_id = uuid4()
            await start_workflow(tp_id, corr_id)

            # Verify the arg dict includes approval_auto_bypass
            call_kwargs = mock_client.start_workflow.call_args
            arg_dict = call_kwargs.kwargs.get("arg") or call_kwargs[1].get("arg")
            assert arg_dict["approval_auto_bypass"] is True


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_intake_output():
    from src.workflow.activities import IntakeOutput
    return IntakeOutput(accepted=True, base_role="developer", overlays=[])


def _mock_context_output():
    from src.workflow.activities import ContextOutput
    return ContextOutput(
        complexity_index="low",
        risk_flags={},
    )


def _mock_intent_output():
    from src.workflow.activities import IntentOutput
    return IntentOutput(
        intent_spec_id="intent-test-001",
        version=1,
        goal="Test goal",
        acceptance_criteria=["AC1"],
    )


def _mock_assembler_output():
    from src.workflow.activities import AssemblerOutput
    return AssemblerOutput(
        plan_steps=["Step 1"],
        qa_handoff=[],
    )


def _mock_impl_output():
    from src.workflow.activities import ImplementOutput
    return ImplementOutput(taskpacket_id="tp-test", files_changed=["test.py"])


def _mock_verify_output():
    from src.workflow.activities import VerifyOutput
    return VerifyOutput(passed=True, exhausted=False)


def _mock_qa_output():
    from src.workflow.activities import QAOutput
    return QAOutput(passed=True)


def _mock_publish_output():
    from src.workflow.activities import PublishOutput
    return PublishOutput(pr_number=42, pr_url="https://github.com/test/pr/42", marked_ready=True)


def _mock_logger():
    """Create a mock logger with info/warning/error methods."""
    from unittest.mock import MagicMock
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


def _side_effect_execute_activity(activity_map: dict):
    """Create an async side effect that dispatches to the correct mock based on the activity function."""
    async def _execute(activity_fn, *args, **kwargs):
        # activity_fn might be a mock or the real function
        fn_name = getattr(activity_fn, "__name__", None) or str(activity_fn)
        for name, mock in activity_map.items():
            if name in fn_name or activity_fn is mock:
                return mock.return_value
        # Fallback: call the function
        return await activity_fn(*args)
    return _execute
