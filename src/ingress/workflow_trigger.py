"""Temporal workflow trigger for starting the TheStudio pipeline."""

from uuid import UUID

from temporalio.client import Client

from src.settings import settings

_client: Client | None = None


async def get_temporal_client() -> Client:
    """Get or create a Temporal client (singleton)."""
    global _client
    if _client is None:
        _client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
    return _client


async def start_workflow(taskpacket_id: UUID, correlation_id: UUID) -> str:
    """Start the TheStudio pipeline workflow.

    Uses taskpacket_id as workflow ID for idempotency — Temporal guarantees
    at-most-once start per workflow ID.

    Returns:
        The workflow run ID.
    """
    client = await get_temporal_client()
    handle = await client.start_workflow(
        "TheStudioPipelineWorkflow",
        arg={
            "taskpacket_id": str(taskpacket_id),
            "correlation_id": str(correlation_id),
            "approval_auto_bypass": settings.approval_auto_bypass,
        },
        id=str(taskpacket_id),
        task_queue=settings.temporal_task_queue,
    )
    return handle.result_run_id or ""
