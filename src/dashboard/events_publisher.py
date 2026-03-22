"""Fire-and-forget NATS publish helper for pipeline stage and loopback events.

Publishes pipeline.stage.enter / pipeline.stage.exit and
pipeline.loopback.start / pipeline.loopback.resolve events to the
THESTUDIO_PIPELINE JetStream stream for dashboard consumption.
"""

import json
import logging
from datetime import UTC, datetime

import nats
from nats.js import JetStreamContext

from src.settings import settings

logger = logging.getLogger(__name__)

STREAM_NAME = "THESTUDIO_PIPELINE"
SUBJECT_PREFIX = "pipeline.stage"

_js: JetStreamContext | None = None


async def get_pipeline_jetstream() -> JetStreamContext:
    """Get or create a JetStream context for the pipeline stream (singleton).

    Epic 38.25: stream is created with both pipeline.> and github.event.>
    subjects so webhook bridge events flow through the same SSE connection.
    """
    global _js
    if _js is None:
        nc = await nats.connect(settings.nats_url)
        _js = nc.jetstream()
        try:
            await _js.find_stream_name_by_subject("pipeline.>")
        except Exception:
            await _js.add_stream(
                name=STREAM_NAME,
                subjects=["pipeline.>", "github.event.>"],
            )
            logger.info("Created JetStream stream %s", STREAM_NAME)
    return _js


async def emit_stage_enter(
    stage: str,
    taskpacket_id: str,
    *,
    correlation_id: str = "",
) -> None:
    """Emit a pipeline.stage.enter event (fire-and-forget).

    Failures are logged but never raised — callers must not be blocked.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps(
            {
                "type": "pipeline.stage.enter",
                "data": {
                    "stage": stage,
                    "taskpacket_id": taskpacket_id,
                    "correlation_id": correlation_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        ).encode()
        await js.publish(f"{SUBJECT_PREFIX}.enter", payload)
        logger.debug("Emitted stage.enter for %s task=%s", stage, taskpacket_id)
    except Exception:
        logger.debug("Failed to emit stage.enter for %s", stage, exc_info=True)


async def emit_stage_exit(
    stage: str,
    taskpacket_id: str,
    *,
    correlation_id: str = "",
    success: bool = True,
) -> None:
    """Emit a pipeline.stage.exit event (fire-and-forget).

    Failures are logged but never raised — callers must not be blocked.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps(
            {
                "type": "pipeline.stage.exit",
                "data": {
                    "stage": stage,
                    "taskpacket_id": taskpacket_id,
                    "correlation_id": correlation_id,
                    "success": success,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        ).encode()
        await js.publish(f"{SUBJECT_PREFIX}.exit", payload)
        logger.debug("Emitted stage.exit for %s task=%s success=%s", stage, taskpacket_id, success)
    except Exception:
        logger.debug("Failed to emit stage.exit for %s", stage, exc_info=True)


async def emit_cost_update(
    task_id: str,
    cost_delta: float,
    total_cost: float,
    model: str,
    stage: str,
    *,
    correlation_id: str = "",
) -> None:
    """Emit a pipeline.cost_update event (fire-and-forget).

    Published on each model call so the dashboard can track running costs.
    Failures are logged but never raised — callers must not be blocked.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps(
            {
                "type": "pipeline.cost_update",
                "data": {
                    "task_id": task_id,
                    "cost_delta": round(cost_delta, 6),
                    "total_cost": round(total_cost, 6),
                    "model": model,
                    "stage": stage,
                    "correlation_id": correlation_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        ).encode()
        await js.publish("pipeline.cost_update", payload)
        logger.debug(
            "Emitted cost_update task=%s delta=%.4f total=%.4f stage=%s",
            task_id,
            cost_delta,
            total_cost,
            stage,
        )
    except Exception:
        logger.debug("Failed to emit cost_update for task=%s", task_id, exc_info=True)


async def emit_loopback_start(
    task_id: str,
    from_stage: str,
    to_stage: str,
    reason: str,
    attempt: int,
    max_attempts: int,
    *,
    correlation_id: str = "",
) -> None:
    """Emit a pipeline.loopback.start event (fire-and-forget).

    Published when a pipeline loopback is initiated (e.g. verification
    failure triggers re-entry to an earlier stage).
    Failures are logged but never raised — callers must not be blocked.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps(
            {
                "type": "pipeline.loopback.start",
                "data": {
                    "task_id": task_id,
                    "from_stage": from_stage,
                    "to_stage": to_stage,
                    "reason": reason,
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "correlation_id": correlation_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        ).encode()
        await js.publish("pipeline.loopback.start", payload)
        logger.debug(
            "Emitted loopback.start task=%s from=%s to=%s attempt=%d/%d",
            task_id,
            from_stage,
            to_stage,
            attempt,
            max_attempts,
        )
    except Exception:
        logger.debug("Failed to emit loopback.start for task=%s", task_id, exc_info=True)


async def emit_triage_created(
    task_id: str,
    issue_title: str,
    issue_id: int,
    repo: str,
) -> None:
    """Emit a pipeline.triage.created event (fire-and-forget).

    Published when a new TaskPacket enters TRIAGE status.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps(
            {
                "type": "pipeline.triage.created",
                "data": {
                    "task_id": task_id,
                    "issue_title": issue_title,
                    "issue_id": issue_id,
                    "repo": repo,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        ).encode()
        await js.publish("pipeline.triage.created", payload)
        logger.debug("Emitted triage.created task=%s", task_id)
    except Exception:
        logger.debug("Failed to emit triage.created for task=%s", task_id, exc_info=True)


async def emit_triage_accepted(task_id: str) -> None:
    """Emit a pipeline.triage.accepted event (fire-and-forget)."""
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps(
            {
                "type": "pipeline.triage.accepted",
                "data": {
                    "task_id": task_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        ).encode()
        await js.publish("pipeline.triage.accepted", payload)
        logger.debug("Emitted triage.accepted task=%s", task_id)
    except Exception:
        logger.debug("Failed to emit triage.accepted for task=%s", task_id, exc_info=True)


async def emit_triage_rejected(task_id: str, reason: str) -> None:
    """Emit a pipeline.triage.rejected event (fire-and-forget)."""
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps(
            {
                "type": "pipeline.triage.rejected",
                "data": {
                    "task_id": task_id,
                    "reason": reason,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        ).encode()
        await js.publish("pipeline.triage.rejected", payload)
        logger.debug("Emitted triage.rejected task=%s reason=%s", task_id, reason)
    except Exception:
        logger.debug("Failed to emit triage.rejected for task=%s", task_id, exc_info=True)


async def emit_loopback_resolve(
    task_id: str,
    from_stage: str,
    to_stage: str,
    outcome: str,
    attempt: int,
    *,
    correlation_id: str = "",
) -> None:
    """Emit a pipeline.loopback.resolve event (fire-and-forget).

    Published when a loopback completes (passed on retry, escalated, etc.).
    Failures are logged but never raised — callers must not be blocked.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps(
            {
                "type": "pipeline.loopback.resolve",
                "data": {
                    "task_id": task_id,
                    "from_stage": from_stage,
                    "to_stage": to_stage,
                    "outcome": outcome,
                    "attempt": attempt,
                    "correlation_id": correlation_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        ).encode()
        await js.publish("pipeline.loopback.resolve", payload)
        logger.debug(
            "Emitted loopback.resolve task=%s from=%s to=%s outcome=%s attempt=%d",
            task_id,
            from_stage,
            to_stage,
            outcome,
            attempt,
        )
    except Exception:
        logger.debug("Failed to emit loopback.resolve for task=%s", task_id, exc_info=True)


async def emit_trust_tier_assigned(
    task_id: str,
    tier: str,
    matched_rule_id: str | None,
    *,
    safety_capped: bool = False,
    reason: str = "",
) -> None:
    """Emit a pipeline.trust_tier.assigned event (fire-and-forget).

    Published after the trust rule engine assigns a tier to a TaskPacket at
    pipeline start. Used by the notification generator and dashboard SSE stream.
    Failures are logged but never raised — callers must not be blocked.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps(
            {
                "type": "pipeline.trust_tier.assigned",
                "data": {
                    "task_id": task_id,
                    "tier": tier,
                    "matched_rule_id": matched_rule_id,
                    "safety_capped": safety_capped,
                    "reason": reason,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        ).encode()
        await js.publish("pipeline.trust_tier.assigned", payload)
        logger.debug(
            "Emitted trust_tier.assigned task=%s tier=%s rule=%s",
            task_id,
            tier,
            matched_rule_id,
        )
    except Exception:
        logger.debug(
            "Failed to emit trust_tier.assigned for task=%s",
            task_id,
            exc_info=True,
        )


async def emit_github_event(
    event_type: str,
    action: str,
    repo: str,
    payload: dict,
    *,
    delivery_id: str = "",
) -> None:
    """Emit a github.event.{type} event to NATS (fire-and-forget).

    Epic 38.24+38.25: publishes GitHub webhook bridge events to the pipeline
    stream so they appear in the dashboard SSE stream without a separate
    connection.

    Args:
        event_type: GitHub event name (pull_request, pull_request_review, …).
        action: GitHub action within the event (opened, merged, submitted, …).
        repo: Full repo name (owner/repo).
        payload: Raw GitHub webhook payload dict.
        delivery_id: X-GitHub-Delivery header value for tracing.

    Failures are logged but never raised — bridge events never block intake.
    """
    try:
        js = await get_pipeline_jetstream()
        msg = json.dumps(
            {
                "type": f"github.event.{event_type}",
                "data": {
                    "event_type": event_type,
                    "action": action,
                    "repo": repo,
                    "delivery_id": delivery_id,
                    "payload": payload,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        ).encode()
        await js.publish(f"github.event.{event_type}", msg)
        logger.debug(
            "Emitted github.event.%s action=%s repo=%s",
            event_type,
            action,
            repo,
        )
    except Exception:
        logger.debug(
            "Failed to emit github.event.%s repo=%s",
            event_type,
            repo,
            exc_info=True,
        )


async def emit_steering_action(
    task_id: str,
    action: str,
    actor: str,
    audit_id: str,
    *,
    from_stage: str | None = None,
    to_stage: str | None = None,
    reason: str | None = None,
    timestamp_iso: str = "",
) -> None:
    """Emit a pipeline.steering.action event (fire-and-forget).

    Published after each steering signal (pause/resume/abort/redirect/retry)
    so the SSE stream delivers real-time steering state to the dashboard.
    Failures are logged but never raised — callers must not be blocked.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps(
            {
                "type": "pipeline.steering.action",
                "data": {
                    "task_id": task_id,
                    "action": action,
                    "from_stage": from_stage,
                    "to_stage": to_stage,
                    "reason": reason,
                    "actor": actor,
                    "audit_id": audit_id,
                    "timestamp": timestamp_iso,
                },
            }
        ).encode()
        await js.publish("pipeline.steering.action", payload)
        logger.debug(
            "Emitted steering.action task=%s action=%s actor=%s",
            task_id,
            action,
            actor,
        )
    except Exception:
        logger.debug(
            "Failed to emit steering.action for task=%s action=%s",
            task_id,
            action,
            exc_info=True,
        )
