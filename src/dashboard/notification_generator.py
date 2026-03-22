"""Notification generator — NATS JetStream consumer that creates Notification records.

Subscribes to four ``pipeline.*`` subjects on JetStream and persists a
:class:`~src.dashboard.models.notification.NotificationRow` for each event:

* ``pipeline.gate.fail`` — verification or QA gate failure
* ``pipeline.cost_update`` — model-call spend recorded for a task
* ``pipeline.steering.action`` — operator steering action (pause/resume/abort/…)
* ``pipeline.trust_tier.assigned`` — trust tier assigned at pipeline start

All four subjects live on the ``PIPELINE`` stream (created by
``events_publisher.py`` / ``budget_checker.py`` at startup if absent).

Started from ``src/app.py`` lifespan alongside the gate evidence and budget
checker consumers.

Design choices:
* Fire-and-forget: exceptions are always logged and messages are always ack'd
  to prevent infinite redelivery loops.
* Durable consumer names are prefixed ``dashboard-notif-`` so they are distinct
  from the budget checker's durable name on the same stream/subjects.
* Titles are kept short (≤ 500 chars) to fit the ``NotificationRow.title``
  column constraint.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

import nats

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task[None] | None = None

# ---------------------------------------------------------------------------
# Helpers: build Notification payloads per event type
# ---------------------------------------------------------------------------


def _safe_task_id(raw: Any) -> UUID | None:
    """Return a UUID from *raw* or None if the value is absent / invalid."""
    if not raw:
        return None
    try:
        return UUID(str(raw))
    except (ValueError, AttributeError):
        return None


def _notification_for_gate_fail(data: dict[str, Any]) -> dict[str, Any] | None:
    """Build NotificationCreate kwargs from a ``pipeline.gate.fail`` payload."""
    task_id = _safe_task_id(data.get("task_id") or data.get("taskpacket_id"))
    stage = data.get("stage", "unknown")
    checks = data.get("checks")

    title = f"Gate failed: {stage}"[:500]
    if checks:
        message = (
            f"Verification or QA gate failed at stage '{stage}'. "
            f"Checks: {json.dumps(checks, default=str)}"
        )
    else:
        message = f"Verification or QA gate failed at stage '{stage}'."

    return {
        "type": "gate_fail",
        "title": title,
        "message": message,
        "task_id": task_id,
    }


def _notification_for_cost_update(data: dict[str, Any]) -> dict[str, Any] | None:
    """Build NotificationCreate kwargs from a ``pipeline.cost_update`` payload."""
    task_id = _safe_task_id(data.get("task_id"))
    delta = data.get("delta", 0.0)
    total = data.get("total", 0.0)
    stage = data.get("stage", "unknown")

    # Only generate a notification when the per-event delta is notable (> 0).
    if not delta:
        return None

    title = f"Cost update: ${total:.4f} total"[:500]
    message = (
        f"Model call at stage '{stage}' incurred ${delta:.4f} "
        f"(cumulative task spend: ${total:.4f})."
    )
    return {
        "type": "cost_update",
        "title": title,
        "message": message,
        "task_id": task_id,
    }


def _notification_for_steering_action(data: dict[str, Any]) -> dict[str, Any] | None:
    """Build NotificationCreate kwargs from a ``pipeline.steering.action`` payload."""
    task_id = _safe_task_id(data.get("task_id"))
    action = data.get("action", "unknown")
    actor = data.get("actor", "system")
    reason = data.get("reason") or ""
    from_stage = data.get("from_stage")
    to_stage = data.get("to_stage")

    title = f"Steering: {action}"[:500]
    parts: list[str] = [f"Operator '{actor}' performed action '{action}'."]
    if from_stage:
        parts.append(f"From stage: {from_stage}.")
    if to_stage:
        parts.append(f"To stage: {to_stage}.")
    if reason:
        parts.append(f"Reason: {reason}")
    message = " ".join(parts)

    return {
        "type": "steering_action",
        "title": title,
        "message": message,
        "task_id": task_id,
    }


def _notification_for_trust_tier(data: dict[str, Any]) -> dict[str, Any] | None:
    """Build NotificationCreate kwargs from a ``pipeline.trust_tier.assigned`` payload."""
    task_id = _safe_task_id(data.get("task_id"))
    tier = data.get("tier", "unknown")
    matched_rule_id = data.get("matched_rule_id")
    safety_capped = data.get("safety_capped", False)

    title = f"Trust tier assigned: {tier}"[:500]
    parts: list[str] = [f"Trust tier '{tier}' assigned at pipeline start."]
    if matched_rule_id:
        parts.append(f"Matched rule: {matched_rule_id}.")
    if safety_capped:
        parts.append("Safety bounds override applied.")
    message = " ".join(parts)

    return {
        "type": "trust_tier_assigned",
        "title": title,
        "message": message,
        "task_id": task_id,
    }


# Map NATS subject (or ``type`` field) to builder function.
_BUILDERS = {
    "pipeline.gate.fail": _notification_for_gate_fail,
    "pipeline.cost_update": _notification_for_cost_update,
    "pipeline.steering.action": _notification_for_steering_action,
    "pipeline.trust_tier.assigned": _notification_for_trust_tier,
}

# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


async def _persist_notification(kwargs: dict[str, Any]) -> None:
    """Write a single Notification row inside a DB session."""
    from src.dashboard.models.notification import NotificationCreate, create_notification
    from src.db.connection import get_async_session

    payload = NotificationCreate(
        type=kwargs["type"],
        title=kwargs["title"],
        message=kwargs["message"],
        task_id=kwargs.get("task_id"),
    )
    async with get_async_session() as session:
        await create_notification(session, payload)
        await session.commit()
    logger.debug(
        "Persisted notification type=%s task_id=%s",
        kwargs["type"],
        kwargs.get("task_id"),
    )


# ---------------------------------------------------------------------------
# NATS message handler
# ---------------------------------------------------------------------------


async def _on_message(msg: Any) -> None:
    """Dispatch a single NATS message to the appropriate notification builder."""
    try:
        envelope = json.loads(msg.data)
        # Normalise: unwrap {"type": "...", "data": {...}} envelope if present.
        event_type: str = envelope.get("type", "")
        data: dict[str, Any] = envelope.get("data", envelope)

        # Derive builder from the ``type`` field; fall back to the NATS subject.
        builder = _BUILDERS.get(event_type) or _BUILDERS.get(msg.subject)
        if builder is None:
            # Unknown subject — ack and skip silently.
            await msg.ack()
            return

        notification_kwargs = builder(data)
        if notification_kwargs is not None:
            await _persist_notification(notification_kwargs)

        await msg.ack()
    except Exception:
        logger.exception("Failed to process notification message subject=%s", msg.subject)
        await msg.ack()  # Always ack to prevent infinite redelivery.


# ---------------------------------------------------------------------------
# Consumer lifecycle
# ---------------------------------------------------------------------------

_SUBJECTS = [
    "pipeline.gate.fail",
    "pipeline.cost_update",
    "pipeline.steering.action",
    "pipeline.trust_tier.assigned",
]


async def start_notification_generator(
    nats_url: str = "nats://localhost:4222",
) -> asyncio.Task[None]:
    """Start the notification generator as a background NATS consumer.

    Creates durable JetStream subscriptions on the four ``pipeline.*``
    subjects listed in :data:`_SUBJECTS`.  Returns the
    :class:`asyncio.Task` running the consumer loop.
    """

    async def _run() -> None:
        nc = await nats.connect(nats_url)
        js = nc.jetstream()

        # Ensure the PIPELINE stream exists (may already be created by
        # events_publisher / budget_checker at application startup).
        stream_name = "PIPELINE"
        try:
            await js.find_stream_name_by_subject("pipeline.>")
        except Exception:
            try:
                await js.add_stream(name=stream_name, subjects=["pipeline.>"])
                logger.info("Created JetStream stream %s", stream_name)
            except Exception:
                logger.debug(
                    "Could not create stream %s (may already exist)",
                    stream_name,
                    exc_info=True,
                )

        # Subscribe each subject with a distinct durable consumer name.
        for subject in _SUBJECTS:
            durable = "dashboard-notif-" + subject.replace(".", "-")
            await js.subscribe(subject, durable=durable, cb=_on_message)
            logger.debug("Notification generator subscribed: %s (durable=%s)", subject, durable)

        logger.info(
            "Notification generator started — subscribed to %d subjects",
            len(_SUBJECTS),
        )

        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await nc.drain()
            logger.info("Notification generator stopped gracefully")

    global _consumer_task
    _consumer_task = asyncio.create_task(_run())
    return _consumer_task


async def stop_notification_generator() -> None:
    """Stop the notification generator consumer task."""
    global _consumer_task
    if _consumer_task is not None:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
