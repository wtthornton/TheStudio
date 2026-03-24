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


async def start_workflow(
    taskpacket_id: UUID,
    correlation_id: UUID,
    *,
    repo: str = "",
    issue_title: str = "",
    issue_body: str = "",
    labels: list[str] | None = None,
    pipeline_comments_override: bool | None = None,
) -> str:
    """Start the TheStudio pipeline workflow.

    Uses taskpacket_id as workflow ID for idempotency — Temporal guarantees
    at-most-once start per workflow ID.

    Args:
        taskpacket_id: UUID of the TaskPacket to process.
        correlation_id: Correlation ID for distributed tracing.
        repo: Repository full name (owner/repo).
        issue_title: GitHub issue title.
        issue_body: GitHub issue body.
        labels: List of label names from the issue.
        pipeline_comments_override: Per-repo pipeline comments setting (Epic 38.23).
            None = use global THESTUDIO_PIPELINE_COMMENTS_ENABLED.
            True/False = explicit per-repo enable/disable.

    Returns:
        The workflow run ID.
    """
    # Resolve effective pipeline_comments_enabled: per-repo takes precedence over global.
    effective_pipeline_comments = (
        pipeline_comments_override
        if pipeline_comments_override is not None
        else settings.pipeline_comments_enabled
    )

    client = await get_temporal_client()
    handle = await client.start_workflow(
        "TheStudioPipelineWorkflow",
        arg={
            "taskpacket_id": str(taskpacket_id),
            "correlation_id": str(correlation_id),
            "approval_auto_bypass": settings.approval_auto_bypass,
            "intent_review_enabled": settings.intent_review_enabled,
            "pipeline_comments_enabled": effective_pipeline_comments,
            "projects_v2_enabled": settings.projects_v2_enabled,
            "repo": repo,
            "issue_title": issue_title,
            "issue_body": issue_body,
            "labels": labels or [],
        },
        id=str(taskpacket_id),
        task_queue=settings.temporal_task_queue,
    )
    return handle.result_run_id or ""
