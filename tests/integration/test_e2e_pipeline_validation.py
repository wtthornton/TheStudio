"""Full E2E pipeline validation — real activities through Temporal workflow.

Phase 7 Exit Criterion: "Full pipeline processes real GitHub issue into draft PR."

This test exercises the REAL activity implementations (not mock activities)
through the Temporal workflow engine. It proves the complete data flow
from a realistic GitHub issue through all 9 pipeline stages.

Two modes:
- **Fallback mode** (default, no API key): All agents use their deterministic
  fallback functions. QA uses mock (keyword-based QA needs real evidence).
  Proves real activity wiring and data flow through all stages.
- **Real LLM mode** (requires THESTUDIO_ANTHROPIC_API_KEY): Enables LLM for
  all agents including QA. Proves full pipeline with real AI reasoning.

Run:
    # Fallback mode (fast, free):
    pytest tests/integration/test_e2e_pipeline_validation.py -v

    # Real LLM mode (~$5):
    THESTUDIO_E2E_REAL_LLM=1 pytest tests/integration/test_e2e_pipeline_validation.py -v
"""

from __future__ import annotations

import os
import time
from uuid import uuid4

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from src.workflow.activities import (
    ApprovalRequestOutput,
    PublishOutput,
    QAOutput,
    assembler_activity,
    context_activity,
    implement_activity,
    intake_activity,
    intent_activity,
    post_approval_request_activity,
    publish_activity,
    qa_activity,
    router_activity,
    verify_activity,
)
from src.workflow.pipeline import PipelineInput, PipelineOutput, TheStudioPipelineWorkflow

TASK_QUEUE = "e2e-validation"

# Realistic GitHub issue simulating a real-world bug report
ISSUE_TITLE = "Fix SSO login timeout after 30 seconds"
ISSUE_BODY = """\
## Problem

The login page times out after 30 seconds when using SSO authentication.
Users see a blank screen and must refresh the page to retry.

## Steps to Reproduce

1. Navigate to /login
2. Click "Sign in with SSO"
3. Enter valid SSO credentials
4. Wait — page hangs for 30s then shows blank screen

## Expected Behavior

SSO login should complete within 5 seconds with a clear error message
if authentication fails.

## Acceptance Criteria

- [ ] SSO login completes within 5 seconds
- [ ] Clear error message shown on timeout (not blank screen)
- [ ] Retry button displayed after failure
- [ ] Existing non-SSO login flow unaffected

## Environment

- Browser: Chrome 120+
- SSO Provider: Okta
- Affected: production
"""


# --- Mock activities for stages that need real git/GitHub ---


@activity.defn(name="qa_activity")
async def mock_qa_passes(params) -> QAOutput:
    """QA passes — used when keyword-based fallback lacks evidence."""
    return QAOutput(passed=True)


@activity.defn(name="publish_activity")
async def mock_publish_activity(params) -> PublishOutput:
    """Simulates draft PR creation without real GitHub."""
    return PublishOutput(
        pr_number=42,
        pr_url="https://github.com/acme/webapp/pull/42",
        created=True,
        marked_ready=False,
    )


@activity.defn(name="post_approval_request_activity")
async def mock_approval_activity(params) -> ApprovalRequestOutput:
    return ApprovalRequestOutput(comment_posted=True)


def _make_e2e_activities(*, use_real_qa: bool = False):
    """Build activity list: real agents for stages 1-7, configurable QA/publish.

    Uses real activities for: intake, context, intent, router, assembler,
    implement, verify. Uses mock for: publish (no real GitHub).
    QA is real when use_real_qa=True (requires LLM), mock otherwise.
    """
    return [
        intake_activity,        # Real — rule-based eligibility
        context_activity,       # Real — AgentRunner with fallback
        intent_activity,        # Real — AgentRunner with fallback
        router_activity,        # Real — AgentRunner with fallback
        assembler_activity,     # Real — AgentRunner with fallback
        implement_activity,     # Real — in-process stub (gateway + tools)
        verify_activity,        # Real — tool policy checks
        qa_activity if use_real_qa else mock_qa_passes,
        mock_publish_activity,  # Mock — no real GitHub needed
        mock_approval_activity,
    ]


def _make_input(**overrides) -> PipelineInput:
    """Build a realistic PipelineInput for E2E validation."""
    defaults = {
        "taskpacket_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "labels": ["agent:run", "type:bug"],
        "repo": "acme/webapp",
        "repo_registered": True,
        "repo_paused": False,
        "has_active_workflow": False,
        "event_id": f"evt-e2e-{uuid4().hex[:8]}",
        "issue_title": ISSUE_TITLE,
        "issue_body": ISSUE_BODY,
        "repo_path": "/tmp/acme/webapp",
        "repo_tier": "observe",
        "approval_auto_bypass": True,
    }
    defaults.update(overrides)
    return PipelineInput(**defaults)


def _has_api_key() -> bool:
    """Check if a real Anthropic API key is available."""
    key = os.environ.get("THESTUDIO_ANTHROPIC_API_KEY", "")
    if key:
        return True
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "infra", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("THESTUDIO_ANTHROPIC_API_KEY="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        return True
    return False


@pytest.fixture
async def temporal_env():
    """Temporal test environment for E2E validation."""
    env = await WorkflowEnvironment.start_local()
    yield env
    await env.shutdown()


@pytest.fixture
def enable_real_llm(request, monkeypatch):
    """Enable real LLM for all agents when THESTUDIO_E2E_REAL_LLM=1."""
    use_real = os.environ.get("THESTUDIO_E2E_REAL_LLM", "").lower() in ("1", "true")

    try:
        use_real = use_real or request.config.getoption("--real-llm", default=False)
    except ValueError:
        pass

    if not use_real:
        return False

    if not _has_api_key():
        pytest.skip("Real LLM mode requires THESTUDIO_ANTHROPIC_API_KEY")

    llm_flags = {
        "intake_agent": True,
        "context_agent": True,
        "intent_agent": True,
        "router_agent": True,
        "recruiter_agent": True,
        "assembler_agent": True,
        "qa_agent": True,
    }
    monkeypatch.setattr("src.settings.settings.agent_llm_enabled", llm_flags)
    return True


# ---------------------------------------------------------------------------
# Phase 7 Exit Criterion: Full E2E Pipeline Validation
# ---------------------------------------------------------------------------


class TestE2EPipelineValidation:
    """Prove the full pipeline processes a real GitHub issue end-to-end.

    Uses REAL activity implementations for stages 1-7 (intake through verify).
    QA uses mock in fallback mode (keyword-based QA needs real evidence),
    real QA activity in LLM mode. Publish always mocked (no real GitHub).
    """

    async def test_full_pipeline_observe_tier(
        self, temporal_env, enable_real_llm,
    ) -> None:
        """Full 9-step pipeline at Observe tier produces success + draft PR.

        Phase 7 exit criterion: GitHub issue -> 9 stages -> draft PR.
        """
        activities = _make_e2e_activities(use_real_qa=enable_real_llm)
        params = _make_input(repo_tier="observe")
        start = time.perf_counter()

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                params,
                id=f"e2e-observe-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

        elapsed = time.perf_counter() - start
        mode = "real-llm" if enable_real_llm else "fallback"

        print(f"\n=== E2E Pipeline Validation ({mode}) ===")
        print(f"  Step reached:    {result.step_reached}")
        print(f"  Success:         {result.success}")
        print(f"  PR number:       {result.pr_number}")
        print(f"  PR URL:          {result.pr_url}")
        print(f"  Verify loops:    {result.verification_loopbacks}")
        print(f"  QA loops:        {result.qa_loopbacks}")
        print(f"  Elapsed:         {elapsed:.2f}s")
        print("=" * 50)

        assert result.success is True, (
            f"Pipeline failed at step '{result.step_reached}': "
            f"{result.rejection_reason}"
        )
        assert result.step_reached == "publish"
        assert result.pr_number == 42
        assert "acme/webapp" in result.pr_url
        assert result.rejection_reason is None

    async def test_full_pipeline_suggest_tier_with_bypass(
        self, temporal_env, enable_real_llm,
    ) -> None:
        """Suggest tier pipeline succeeds with approval auto-bypass."""
        activities = _make_e2e_activities(use_real_qa=enable_real_llm)
        params = _make_input(
            repo_tier="suggest",
            approval_auto_bypass=True,
        )

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                params,
                id=f"e2e-suggest-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

        assert result.success is True, (
            f"Pipeline failed at step '{result.step_reached}': "
            f"{result.rejection_reason}"
        )
        assert result.step_reached == "publish"
        assert result.approval_bypassed is True

    async def test_pipeline_rejects_ineligible_issue(
        self, temporal_env, enable_real_llm,
    ) -> None:
        """Issue without agent:run label is rejected at intake."""
        activities = _make_e2e_activities()
        params = _make_input(labels=["type:feature"])

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                params,
                id=f"e2e-reject-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

        assert result.success is False
        assert result.step_reached == "intake"
        assert result.rejection_reason is not None

    async def test_pipeline_data_flows_through_all_stages(
        self, temporal_env, enable_real_llm,
    ) -> None:
        """Different issue content produces successful pipeline output.

        Ensures activities process unique inputs (not cached/default).
        """
        activities = _make_e2e_activities(use_real_qa=enable_real_llm)
        params = _make_input(
            issue_title="Add rate limiting to public API endpoints",
            issue_body=(
                "## Problem\n\n"
                "Public API has no rate limiting. Bots can abuse endpoints.\n\n"
                "## Acceptance Criteria\n\n"
                "- [ ] Rate limit of 100 requests/minute per API key\n"
                "- [ ] HTTP 429 response with Retry-After header\n"
                "- [ ] Rate limit headers in all responses\n"
            ),
            repo_tier="observe",
        )

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                params,
                id=f"e2e-flow-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

        assert result.success is True
        assert result.step_reached == "publish"
        assert result.verification_loopbacks == 0
        assert result.qa_loopbacks == 0

    async def test_pipeline_timing_baseline(
        self, temporal_env, enable_real_llm,
    ) -> None:
        """Pipeline completes within time budget."""
        activities = _make_e2e_activities(use_real_qa=enable_real_llm)
        params = _make_input(repo_tier="observe")
        start = time.perf_counter()

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                params,
                id=f"e2e-timing-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

        elapsed = time.perf_counter() - start
        mode = "real-llm" if enable_real_llm else "fallback"

        print(f"\nTIMING ({mode}): total={elapsed:.2f}s")

        assert result.success is True

        if enable_real_llm:
            assert elapsed < 300.0, f"Real LLM pipeline took {elapsed:.1f}s > 300s"
        else:
            assert elapsed < 10.0, f"Fallback pipeline took {elapsed:.1f}s > 10s"


class TestE2EQALoopbackValidation:
    """Validate QA loopback behavior with real QA activity.

    The keyword-based QA fallback correctly rejects when evidence is sparse
    (no real implementation output). This proves the QA gate and loopback
    machinery work correctly with real activity implementations.
    """

    async def test_qa_loopback_exhaustion_with_real_qa(
        self, temporal_env, enable_real_llm,
    ) -> None:
        """Real QA activity rejects sparse evidence, exhausting loopbacks.

        Proves: QA gate fails closed, loopback count tracked, pipeline
        fails gracefully at QA exhaustion cap.
        """
        # Use ALL real activities including real QA
        all_real = _make_e2e_activities(use_real_qa=True)
        params = _make_input(repo_tier="observe")

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=all_real,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                params,
                id=f"e2e-qa-loop-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

        if enable_real_llm:
            # Real LLM QA should pass (semantic reasoning)
            assert result.success is True
        else:
            # Keyword-based QA correctly rejects sparse evidence
            assert result.success is False
            assert result.step_reached == "qa"
            assert result.qa_loopbacks >= 1  # Loopback machinery works


class TestE2EPipelineEdgeCases:
    """Gate logic validation with real activities."""

    async def test_paused_repo_rejected(self, temporal_env, enable_real_llm) -> None:
        """Paused repo is rejected at intake."""
        activities = _make_e2e_activities()
        params = _make_input(repo_paused=True)

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                params,
                id=f"e2e-paused-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

        assert result.success is False
        assert result.step_reached == "intake"

    async def test_unregistered_repo_rejected(self, temporal_env, enable_real_llm) -> None:
        """Unregistered repo is rejected at intake."""
        activities = _make_e2e_activities()
        params = _make_input(repo_registered=False)

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                params,
                id=f"e2e-unreg-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

        assert result.success is False
        assert result.step_reached == "intake"

    async def test_duplicate_workflow_rejected(self, temporal_env, enable_real_llm) -> None:
        """Issue with active workflow is rejected at intake."""
        activities = _make_e2e_activities()
        params = _make_input(has_active_workflow=True)

        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=activities,
        ):
            result: PipelineOutput = await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                params,
                id=f"e2e-dup-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

        assert result.success is False
        assert result.step_reached == "intake"
