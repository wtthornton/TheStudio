"""HTTP webhook endpoint for receiving GitHub issue events."""

import logging

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import get_session
from src.ingress.dedupe import is_duplicate
from src.ingress.signature import validate_signature
from src.ingress.workflow_trigger import start_workflow
from src.models.taskpacket import TaskPacketCreate, TaskPacketStatus
from src.models.taskpacket_crud import (
    create as create_taskpacket,
)
from src.models.taskpacket_crud import (
    get_by_repo_and_issue,
)
from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_OUTCOME,
    ATTR_REPO,
    SPAN_INGRESS_RECEIVE,
)
from src.observability.correlation import attach_correlation_id, generate_correlation_id
from src.observability.tracing import get_tracer
from src.repo.repo_profile_crud import get_webhook_secret
from src.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()
tracer = get_tracer("thestudio.ingress")

# Event types that trigger re-evaluation of held issues
_REEVALUATION_EVENTS = frozenset({"issues", "issue_comment"})
# Actions on issues that indicate content was updated
_ISSUE_UPDATE_ACTIONS = frozenset({"edited"})
# Actions on issue_comment that indicate new clarification response
_COMMENT_TRIGGER_ACTIONS = frozenset({"created"})
# Epic 38.15: Projects v2 item event type for inbound sync
_PROJECTS_V2_ITEM_EVENT = "projects_v2_item"
# Epic 38.24: Webhook bridge — event types published to NATS github.event.* subjects
_BRIDGE_EVENT_TYPES = frozenset({
    "pull_request",
    "pull_request_review",
    "pull_request_review_comment",
    "check_run",
    "check_suite",
    "issue_comment",
})


def normalize_webhook_payload(
    event_type: str, payload: dict,
) -> dict:
    """Extract normalized issue data from webhook payload.

    GitHub nests issue data differently for issue_comment events
    (under ``payload.issue``) vs issues events (top-level ``issue`` key).
    Both shapes are normalized to the same structure.

    Returns:
        dict with keys: issue_number, issue_title, issue_body, action
    """
    action = payload.get("action", "")

    if event_type == "issue_comment":
        issue_data = payload.get("issue", {})
    else:
        issue_data = payload.get("issue", {})

    raw_labels = issue_data.get("labels", [])
    labels = [lbl.get("name", "") for lbl in raw_labels if isinstance(lbl, dict)]

    return {
        "issue_number": issue_data.get("number", 0),
        "issue_title": issue_data.get("title", ""),
        "issue_body": issue_data.get("body", "") or "",
        "labels": labels,
        "action": action,
    }


def _is_reevaluation_trigger(event_type: str, action: str) -> bool:
    """Check if this event+action combination should trigger re-evaluation."""
    if event_type == "issues" and action in _ISSUE_UPDATE_ACTIONS:
        return True
    if event_type == "issue_comment" and action in _COMMENT_TRIGGER_ACTIONS:
        return True
    return False


async def _publish_github_event_to_nats(
    event_type: str,
    delivery_id: str,
    payload: dict,
    repo: str,
) -> None:
    """Publish a GitHub webhook event to NATS JetStream (fire-and-forget).

    Epic 38.24 — Webhook Bridge.

    Publishes to subject ``github.event.{event_type}`` so the SSE stream
    can relay real-time GitHub events to the dashboard.

    Failures are logged but never raised — bridge events never block intake.
    """
    from datetime import UTC, datetime

    try:
        from src.dashboard.events_publisher import get_pipeline_jetstream

        action = payload.get("action", "")
        nats_payload = {
            "type": f"github.event.{event_type}",
            "data": {
                "event_type": event_type,
                "action": action,
                "delivery_id": delivery_id,
                "repo": repo,
                "payload": payload,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }
        import json

        js = await get_pipeline_jetstream()
        await js.publish(
            f"github.event.{event_type}",
            json.dumps(nats_payload).encode(),
        )
        logger.debug(
            "github.event.published event=%s action=%s repo=%s",
            event_type,
            action,
            repo,
        )
    except Exception:
        logger.debug(
            "github.event.publish_failed event=%s repo=%s",
            event_type,
            repo,
            exc_info=True,
        )


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
    x_github_delivery: str | None = Header(None),
    x_github_event: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
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

        # 2b. Epic 38.15: Handle projects_v2_item events early — these use the
        # global webhook_secret (not per-repo) and have no ``repository`` field.
        if x_github_event == _PROJECTS_V2_ITEM_EVENT:
            # Validate using global webhook secret for project-level events.
            global_secret = settings.webhook_secret
            if global_secret and not validate_signature(body, global_secret, x_hub_signature_256):
                span.set_attribute(ATTR_OUTCOME, "invalid_signature")
                return Response(status_code=401, content="Invalid signature")

            from src.github.projects_sync import handle_projects_v2_item_event

            result = await handle_projects_v2_item_event(payload, session)
            outcome = result.get("outcome", "unknown")
            span.set_attribute(ATTR_OUTCOME, outcome)
            logger.info("projects_v2_item event handled: %s", outcome)
            return Response(status_code=200, content=outcome)

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

        # 5. Validate signature (same HMAC secret for all event types)
        if not validate_signature(body, secret, x_hub_signature_256):
            span.set_attribute(ATTR_OUTCOME, "invalid_signature")
            return Response(status_code=401, content="Invalid signature")

        # 6. Filter for handled event types; bridge supported events to NATS (38.24)
        if x_github_event not in _REEVALUATION_EVENTS:
            # Epic 38.24: Publish bridge-eligible events to NATS before returning
            if x_github_event in _BRIDGE_EVENT_TYPES and settings.pipeline_webhook_bridge_enabled:
                await _publish_github_event_to_nats(
                    x_github_event,
                    x_github_delivery or "",
                    payload,
                    repo_full_name,
                )
            span.set_attribute(ATTR_OUTCOME, "not_issue_event")
            return Response(status_code=200, content="Event type not handled")

        # 7. Normalize payload and determine action
        normalized = normalize_webhook_payload(x_github_event, payload)
        action = normalized["action"]

        # 8. Check if this is a re-evaluation trigger for a held issue
        if _is_reevaluation_trigger(x_github_event, action):
            return await _handle_reevaluation(
                session, span, repo_full_name, normalized, x_github_delivery,
            )

        # 9. For new issue events (issues.opened), proceed with standard flow
        if x_github_event == "issues" and action != "opened":
            span.set_attribute(ATTR_OUTCOME, "action_not_handled")
            return Response(status_code=200, content="Action not handled")

        if x_github_event == "issue_comment":
            # issue_comment events that aren't re-evaluation triggers are ignored
            span.set_attribute(ATTR_OUTCOME, "comment_not_applicable")
            return Response(status_code=200, content="Comment event not applicable")

        # 10. Dedupe check
        if await is_duplicate(session, x_github_delivery, repo_full_name):
            span.set_attribute(ATTR_OUTCOME, "duplicate")
            return Response(status_code=200, content="Duplicate delivery, already processed")

        # 11. Create TaskPacket
        correlation_id = generate_correlation_id()
        token = attach_correlation_id(correlation_id)

        span.set_attribute(ATTR_CORRELATION_ID, str(correlation_id))

        issue_id = normalized["issue_number"]
        issue_title = normalized["issue_title"]
        issue_body = normalized["issue_body"]
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
            issue_title=issue_title,
            issue_body=issue_body,
        )

        # 11b. Triage mode: create in TRIAGE status, skip workflow start
        if settings.triage_mode_enabled:
            from src.context.prescan import prescan_issue

            enrichment = prescan_issue(
                issue_title, issue_body, normalized.get("labels", []),
            )
            task_data.triage_enrichment = enrichment

            taskpacket = await create_taskpacket(
                session, task_data, initial_status=TaskPacketStatus.TRIAGE,
            )

            # Emit SSE event for real-time triage queue updates
            from src.dashboard.events_publisher import emit_triage_created

            await emit_triage_created(
                str(taskpacket.id), issue_title, issue_id, repo_full_name,
            )

            from opentelemetry import context as otel_context

            otel_context.detach(token)
            span.set_attribute(ATTR_OUTCOME, "triage_created")
            logger.info(
                "TaskPacket %s created in TRIAGE mode (issue #%d)",
                taskpacket.id,
                issue_id,
            )
            return Response(status_code=201, content="TaskPacket created in triage")

        # 11c. Normal mode: create in RECEIVED status
        taskpacket = await create_taskpacket(session, task_data)

        # 12. Start Temporal workflow
        try:
            await start_workflow(
                taskpacket.id,
                correlation_id,
                repo=repo_full_name,
                issue_title=issue_title,
                issue_body=issue_body,
                labels=normalized.get("labels", []),
            )
        except Exception:
            logger.exception(
                "Failed to start Temporal workflow for TaskPacket %s",
                taskpacket.id,
            )
            # TaskPacket is created — workflow can be retried later
            span.set_attribute(ATTR_OUTCOME, "workflow_start_failed")
            return Response(status_code=201, content="TaskPacket created, workflow pending")

        from opentelemetry import context as otel_context

        otel_context.detach(token)

        span.set_attribute(ATTR_OUTCOME, "created")
        return Response(status_code=201, content="TaskPacket created, workflow started")


async def _handle_reevaluation(
    session: AsyncSession,
    span,
    repo_full_name: str,
    normalized: dict,
    delivery_id: str,
) -> Response:
    """Handle re-evaluation of a held issue after submitter update.

    Looks up an existing TaskPacket in ``clarification_requested`` status and
    sends a ``readiness_cleared`` Temporal signal to resume the workflow.
    """
    issue_number = normalized["issue_number"]

    # Find the TaskPacket for this repo + issue
    taskpacket = await get_by_repo_and_issue(session, repo_full_name, issue_number)
    if taskpacket is None:
        span.set_attribute(ATTR_OUTCOME, "no_taskpacket_for_issue")
        return Response(status_code=200, content="No TaskPacket found for this issue")

    # Only re-evaluate if the issue is currently held for clarification
    if taskpacket.status != TaskPacketStatus.CLARIFICATION_REQUESTED:
        span.set_attribute(ATTR_OUTCOME, "not_held_for_clarification")
        return Response(
            status_code=200,
            content="TaskPacket not in clarification_requested status",
        )

    # Send readiness_cleared signal to the Temporal workflow
    try:
        from src.ingress.workflow_trigger import get_temporal_client

        client = await get_temporal_client()
        handle = client.get_workflow_handle(str(taskpacket.id))
        await handle.signal(
            "readiness_cleared",
            arg={
                "issue_title": normalized["issue_title"],
                "issue_body": normalized["issue_body"],
            },
        )
        logger.info(
            "Sent readiness_cleared signal for TaskPacket %s (issue #%d)",
            taskpacket.id,
            issue_number,
        )
        span.set_attribute(ATTR_OUTCOME, "reevaluation_triggered")
        return Response(status_code=200, content="Re-evaluation signal sent")

    except Exception:
        logger.exception(
            "Failed to send readiness_cleared signal for TaskPacket %s",
            taskpacket.id,
        )
        span.set_attribute(ATTR_OUTCOME, "reevaluation_signal_failed")
        return Response(
            status_code=500,
            content="Failed to send re-evaluation signal",
        )
