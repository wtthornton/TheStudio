"""Full pipeline smoke test — webhook to draft PR.

Story 15.2: Proves the full 9-step pipeline executes end-to-end with
realistic mock data flowing stage-to-stage. Each stage receives output
from the previous stage (not hardcoded inputs).

Story 15.6: Pipeline latency baseline — timing instrumentation.
"""

from __future__ import annotations

import time

from src.workflow.pipeline import PipelineOutput
from tests.integration.conftest import make_pipeline_input
from tests.integration.mock_providers import (
    ALL_MOCK_ACTIVITIES,
    activities_with_qa_exhaustion,
    activities_with_qa_loopback,
    activities_with_verify_exhaustion,
    activities_with_verify_loopback,
)

# --- Story 15.2: Happy Path ---


class TestFullPipelineSmoke:
    """Full 9-stage pipeline with realistic mock data."""

    async def test_happy_path_succeeds(self, run_workflow) -> None:
        """Pipeline runs all 9 steps and produces valid output."""
        params = make_pipeline_input()
        result: PipelineOutput = await run_workflow(
            ALL_MOCK_ACTIVITIES, params,
        )

        assert result.success is True
        assert result.step_reached == "publish"
        assert result.verification_loopbacks == 0
        assert result.qa_loopbacks == 0
        assert result.pr_number == 42
        assert result.pr_url == (
            "https://github.com/test-org/test-repo/pull/42"
        )
        assert result.rejection_reason is None

    async def test_ineligible_issue_rejected(self, run_workflow) -> None:
        """Issue without agent:run label is rejected at intake."""
        params = make_pipeline_input(labels=["type:feature"])
        result: PipelineOutput = await run_workflow(
            ALL_MOCK_ACTIVITIES, params,
        )

        assert result.success is False
        assert result.step_reached == "intake"
        assert result.rejection_reason is not None
        assert "agent:run" in result.rejection_reason.lower()

    async def test_paused_repo_rejected(self, run_workflow) -> None:
        """Paused repository is rejected at intake."""
        params = make_pipeline_input(repo_paused=True)
        result: PipelineOutput = await run_workflow(
            ALL_MOCK_ACTIVITIES, params,
        )

        assert result.success is False
        assert result.step_reached == "intake"

    async def test_output_fields_populated(self, run_workflow) -> None:
        """All PipelineOutput fields are populated after success."""
        params = make_pipeline_input()
        result: PipelineOutput = await run_workflow(
            ALL_MOCK_ACTIVITIES, params,
        )

        assert isinstance(result.success, bool)
        assert isinstance(result.step_reached, str)
        assert isinstance(result.pr_number, int)
        assert isinstance(result.pr_url, str)
        assert isinstance(result.verification_loopbacks, int)
        assert isinstance(result.qa_loopbacks, int)


# --- Story 15.3: Loopback Integration Tests ---


class TestRealisticLoopback:
    """Loopback tests with realistic mock data."""

    async def test_verification_loopback_once(self, run_workflow) -> None:
        """Verify fails once, then passes. Pipeline succeeds."""
        params = make_pipeline_input()
        result: PipelineOutput = await run_workflow(
            activities_with_verify_loopback(fail_count=1), params,
        )

        assert result.success is True
        assert result.verification_loopbacks == 1
        assert result.step_reached == "publish"

    async def test_verification_exhaustion(self, run_workflow) -> None:
        """Verify always fails — pipeline fails closed."""
        params = make_pipeline_input()
        result: PipelineOutput = await run_workflow(
            activities_with_verify_exhaustion(), params,
        )

        assert result.success is False
        assert result.step_reached == "verify"
        assert result.verification_loopbacks >= 1

    async def test_qa_loopback_once(self, run_workflow) -> None:
        """QA fails once, then passes. Pipeline succeeds."""
        params = make_pipeline_input()
        result: PipelineOutput = await run_workflow(
            activities_with_qa_loopback(fail_count=1), params,
        )

        assert result.success is True
        assert result.qa_loopbacks == 1
        assert result.step_reached == "publish"

    async def test_qa_exhaustion(self, run_workflow) -> None:
        """QA always fails — pipeline fails closed."""
        params = make_pipeline_input()
        result: PipelineOutput = await run_workflow(
            activities_with_qa_exhaustion(), params,
        )

        assert result.success is False
        assert result.step_reached == "qa"
        assert result.qa_loopbacks >= 1


# --- Story 15.6: Pipeline Latency Baseline ---


class TestPipelineLatency:
    """Pipeline latency measurement with mock providers."""

    async def test_pipeline_under_5_seconds(self, run_workflow) -> None:
        """Full pipeline completes in under 5 seconds with mocks."""
        params = make_pipeline_input()
        start = time.perf_counter()
        result: PipelineOutput = await run_workflow(
            ALL_MOCK_ACTIVITIES, params,
        )
        elapsed = time.perf_counter() - start

        assert result.success is True
        # With mock providers, pipeline should be fast
        assert elapsed < 5.0, f"Pipeline took {elapsed:.2f}s, expected < 5s"

        # Print timing for baseline recording
        print(f"\nTIMING: total={elapsed:.3f}s")
