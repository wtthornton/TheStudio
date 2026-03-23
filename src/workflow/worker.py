"""Temporal worker — registers workflow and activities with the Temporal server.

Runs as a background task alongside the FastAPI app. When the app starts,
it connects to Temporal and begins polling the task queue for work.
"""

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from src.settings import Settings
from src.workflow.activities import (
    assembler_activity,
    context_activity,
    escalate_timeout_activity,
    implement_activity,
    intake_activity,
    intent_activity,
    monitor_post_merge_activity,
    persist_steering_audit_activity,
    post_approval_request_activity,
    preflight_activity,
    publish_activity,
    qa_activity,
    readiness_activity,
    router_activity,
    update_project_status_activity,
    verify_activity,
)
from src.workflow.pipeline import TheStudioPipelineWorkflow

logger = logging.getLogger(__name__)

ACTIVITIES = [
    intake_activity,
    context_activity,
    readiness_activity,
    intent_activity,
    router_activity,
    assembler_activity,
    preflight_activity,
    implement_activity,
    verify_activity,
    qa_activity,
    publish_activity,
    post_approval_request_activity,
    update_project_status_activity,
    escalate_timeout_activity,
    persist_steering_audit_activity,
    monitor_post_merge_activity,
]


async def run_worker() -> None:
    """Connect to Temporal and run the worker until cancelled."""
    settings = Settings()
    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[TheStudioPipelineWorkflow],
        activities=ACTIVITIES,
    )
    logger.info(
        "Temporal worker started task_queue=%s namespace=%s",
        settings.temporal_task_queue,
        settings.temporal_namespace,
    )
    await worker.run()


async def start_worker_background() -> asyncio.Task:
    """Start the Temporal worker as a background asyncio task."""
    task = asyncio.create_task(_run_worker_with_retry(), name="temporal-worker")
    return task


async def _run_worker_with_retry() -> None:
    """Run worker with retry on connection failure."""
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            await run_worker()
        except asyncio.CancelledError:
            logger.info("Temporal worker cancelled")
            return
        except Exception:
            if attempt == max_retries:
                logger.exception("Temporal worker failed after %d attempts", max_retries)
                return
            wait = min(2**attempt, 30)
            logger.warning(
                "Temporal worker failed (attempt %d/%d), retrying in %ds",
                attempt,
                max_retries,
                wait,
                exc_info=True,
            )
            await asyncio.sleep(wait)
