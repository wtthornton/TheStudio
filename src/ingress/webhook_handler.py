"""HTTP webhook endpoint for receiving GitHub issue events."""

import logging

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import get_session
from src.ingress.dedupe import is_duplicate
from src.ingress.signature import validate_signature
from src.ingress.workflow_trigger import start_workflow
from src.models.taskpacket import TaskPacketCreate
from src.models.taskpacket_crud import create as create_taskpacket
from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_OUTCOME,
    ATTR_REPO,
    SPAN_INGRESS_RECEIVE,
)
from src.observability.correlation import attach_correlation_id, generate_correlation_id
from src.observability.tracing import get_tracer
from src.repo.repo_profile_crud import get_webhook_secret

logger = logging.getLogger(__name__)
router = APIRouter()
tracer = get_tracer("thestudio.ingress")


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
    x_github_delivery: str | None = Header(None),
    x_github_event: str | None = Header(None),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Response:
    """Receive GitHub webhook events, validate, dedupe, and start workflow."""
    with tracer.start_as_current_span(SPAN_INGRESS_RECEIVE) as span:
        # 1. Validate required headers
        if x_github_delivery is None:
            span.set_attribute(ATTR_OUTCOME, "missing_delivery_id")
            return Response(status_code=400, content="Missing X-GitHub-Delivery header")

        if x_hub_signature_256 is None:
            span.set_attribute(ATTR_OUTCOME, "missing_signature")
            return Response(status_code=401, content="Missing X-Hub-Signature-256 header")

        # 2. Read raw body for signature validation
        body = await request.body()
        payload = await request.json()

        # 3. Determine repo from payload
        repo_data = payload.get("repository", {})
        repo_full_name = repo_data.get("full_name", "")
        if not repo_full_name:
            span.set_attribute(ATTR_OUTCOME, "missing_repo")
            return Response(status_code=400, content="Missing repository in payload")

        span.set_attribute(ATTR_REPO, repo_full_name)

        # 4. Get webhook secret from repo profile
        owner, repo_name = repo_full_name.split("/", 1)
        secret = await get_webhook_secret(session, owner, repo_name)
        if secret is None:
            span.set_attribute(ATTR_OUTCOME, "unknown_repo")
            return Response(status_code=404, content="Repository not registered")

        # 5. Validate signature
        if not validate_signature(body, secret, x_hub_signature_256):
            span.set_attribute(ATTR_OUTCOME, "invalid_signature")
            return Response(status_code=401, content="Invalid signature")

        # 6. Filter for issue events only
        if x_github_event != "issues":
            span.set_attribute(ATTR_OUTCOME, "not_issue_event")
            return Response(status_code=200, content="Event type not handled")

        # 7. Dedupe check
        if await is_duplicate(session, x_github_delivery, repo_full_name):
            span.set_attribute(ATTR_OUTCOME, "duplicate")
            return Response(status_code=200, content="Duplicate delivery, already processed")

        # 8. Create TaskPacket
        correlation_id = generate_correlation_id()
        token = attach_correlation_id(correlation_id)

        span.set_attribute(ATTR_CORRELATION_ID, str(correlation_id))

        issue_data = payload.get("issue", {})
        issue_id = issue_data.get("number", 0)
        issue_title = issue_data.get("title", "")
        issue_body = issue_data.get("body", "")
        logger.info(
            "Webhook received issue #%d: %s",
            issue_id,
            issue_title,
            extra={"issue_title": issue_title, "issue_body_length": len(issue_body)},
        )

        task_data = TaskPacketCreate(
            repo=repo_full_name,
            issue_id=issue_id,
            delivery_id=x_github_delivery,
            correlation_id=correlation_id,
        )
        taskpacket = await create_taskpacket(session, task_data)

        # 9. Start Temporal workflow
        try:
            await start_workflow(taskpacket.id, correlation_id)
        except Exception:
            logger.exception("Failed to start Temporal workflow for TaskPacket %s", taskpacket.id)
            # TaskPacket is created — workflow can be retried later
            span.set_attribute(ATTR_OUTCOME, "workflow_start_failed")
            return Response(status_code=201, content="TaskPacket created, workflow pending")

        from opentelemetry import context as otel_context

        otel_context.detach(token)

        span.set_attribute(ATTR_OUTCOME, "created")
        return Response(status_code=201, content="TaskPacket created, workflow started")
