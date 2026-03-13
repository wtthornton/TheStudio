"""Shared fixtures for integration tests.

Provides mock providers, pipeline input factories, and activity
overrides for testing the full 9-step pipeline without external services.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from src.workflow.pipeline import PipelineInput, TheStudioPipelineWorkflow

TASK_QUEUE = "integration-test"


def make_pipeline_input(**overrides) -> PipelineInput:
    """Build a realistic PipelineInput with fresh UUIDs.

    Returns an eligible input by default (has agent:run label, registered,
    not paused, no active workflow).
    """
    defaults = {
        "taskpacket_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "labels": ["agent:run", "type:bug"],
        "repo": "test-org/test-repo",
        "repo_registered": True,
        "repo_paused": False,
        "has_active_workflow": False,
        "event_id": f"evt-{uuid4().hex[:8]}",
        "issue_title": "Fix SSO login timeout after 30 seconds",
        "issue_body": (
            "## Problem\n\n"
            "The login page times out after 30 seconds when using SSO.\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] SSO login completes within 5 seconds\n"
            "- [ ] Error message shown on timeout\n"
            "- [ ] Retry button available\n\n"
            "## Steps to Reproduce\n\n"
            "1. Navigate to /login\n"
            "2. Click 'Sign in with SSO'\n"
            "3. Wait 30 seconds\n"
        ),
        "repo_path": "/tmp/test-org/test-repo",
        "repo_tier": "suggest",
    }
    defaults.update(overrides)
    return PipelineInput(**defaults)


@pytest.fixture
async def temporal_env():
    """Temporal test environment — function-scoped."""
    env = await WorkflowEnvironment.start_local()
    yield env
    await env.shutdown()


@pytest.fixture
def pipeline_input():
    """Default realistic pipeline input."""
    return make_pipeline_input()


@pytest.fixture
async def run_workflow(temporal_env):
    """Factory fixture: run a workflow with given activities.

    Usage:
        result = await run_workflow(activities, pipeline_input)
    """

    async def _run(activities, params: PipelineInput) -> object:
        async with Worker(
            temporal_env.client,
            task_queue=TASK_QUEUE,
            workflows=[TheStudioPipelineWorkflow],
            activities=activities,
        ):
            return await temporal_env.client.execute_workflow(
                TheStudioPipelineWorkflow.run,
                params,
                id=f"integration-{uuid4()}",
                task_queue=TASK_QUEUE,
            )

    return _run
