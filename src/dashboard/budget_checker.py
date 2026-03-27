"""Budget threshold checker — NATS consumer that enforces spend limits.

Subscribes to ``pipeline.cost_update`` on JetStream.  After each event:

1. Loads the current :class:`BudgetConfigRow` singleton.
2. Computes weekly spend from :func:`~src.admin.model_spend.get_spend_report`.
3. If ``pause_on_budget_exceeded`` is True **and** weekly spend ≥
   ``weekly_budget_cap`` → sends ``pause_task`` Temporal signal to every
   active (non-terminal) workflow.
4. If ``model_downgrade_on_approach`` is True **and** weekly spend ≥
   ``downgrade_threshold_percent``% of ``weekly_budget_cap`` → enables
   ``cost_optimization_routing_enabled`` in the settings DB so the
   :class:`~src.admin.model_gateway.ModelRouter` routes cheaper models.

Started from ``src/app.py`` lifespan alongside the gate evidence consumer.

Design choices:
* Fire-and-forget: exceptions are logged, never re-raised, so cost events are
  always ack'd to prevent infinite redelivery loops.
* Debounce: a module-level flag ``_downgrade_activated`` prevents redundant DB
  writes once downgrade routing has been enabled for the current process lifetime.
  It is reset when the consumer is stopped (i.e. on application restart).
* Weekly window (168 h) matches the ``weekly_budget_cap`` semantic.
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

# Prevent redundant DB writes once downgrade routing is already active.
_downgrade_activated: bool = False

# Statuses whose workflows are still alive and can receive signals.
_ACTIVE_STATUSES = frozenset(
    {
        "received",
        "enriched",
        "clarification_requested",
        "human_review_required",
        "intent_built",
        "in_progress",
        "verification_passed",
        "verification_failed",
        "awaiting_approval",
    }
)

_WEEKLY_WINDOW_HOURS = 168


# ---------------------------------------------------------------------------
# Core check logic
# ---------------------------------------------------------------------------


async def _check_budget_thresholds(payload: dict[str, Any]) -> None:
    """Evaluate budget thresholds and take automated actions if warranted.

    Parameters
    ----------
    payload:
        Decoded ``data`` dict from a ``pipeline.cost_update`` NATS message.
        Only ``task_id`` is used for structured logging; actual spend comes
        from the model-call audit store.
    """
    global _downgrade_activated

    from src.admin.model_spend import get_spend_report
    from src.dashboard.models.budget_config import get_budget_config
    from src.db.connection import get_async_session

    task_id: str = payload.get("task_id", "unknown")

    # Load budget config singleton from DB.
    async with get_async_session() as session:
        config = await get_budget_config(session)

    # get_spend_report is synchronous — reads from in-process audit store.
    report = get_spend_report(window_hours=_WEEKLY_WINDOW_HOURS)
    weekly_spend = report.total_cost

    logger.debug(
        "budget_check task=%s weekly_spend=%.4f cap=%s downgrade_pct=%s",
        task_id,
        weekly_spend,
        config.weekly_budget_cap,
        config.downgrade_threshold_percent,
    )

    # ------------------------------------------------------------------
    # Action 1: Pause all active workflows when cap is breached.
    # ------------------------------------------------------------------
    if (
        config.pause_on_budget_exceeded
        and config.weekly_budget_cap is not None
        and weekly_spend >= config.weekly_budget_cap
    ):
        logger.warning(
            "weekly_budget_cap breached (%.4f >= %.4f); pausing all active workflows",
            weekly_spend,
            config.weekly_budget_cap,
        )
        await _pause_all_active_workflows()

    # ------------------------------------------------------------------
    # Action 2: Enable cheap-model routing when approaching the cap.
    # ------------------------------------------------------------------
    if (
        not _downgrade_activated
        and config.model_downgrade_on_approach
        and config.weekly_budget_cap is not None
        and weekly_spend >= (config.weekly_budget_cap * config.downgrade_threshold_percent / 100.0)
    ):
        logger.warning(
            "spend approaching cap (%.1f%% threshold reached); enabling cost_optimization_routing",
            config.downgrade_threshold_percent,
        )
        await _enable_cost_optimization_routing()
        _downgrade_activated = True


async def _pause_all_active_workflows() -> None:
    """Send ``pause_task`` Temporal signal to every active TaskPacket workflow."""
    from sqlalchemy import select

    from src.db.connection import get_async_session
    from src.models.taskpacket import TaskPacketRow

    async with get_async_session() as session:
        result = await session.execute(
            select(TaskPacketRow.id).where(
                TaskPacketRow.status.in_(list(_ACTIVE_STATUSES))
            )
        )
        task_ids: list[UUID] = [row[0] for row in result.fetchall()]

    if not task_ids:
        logger.debug("No active workflows found to pause")
        return

    try:
        from src.ingress.workflow_trigger import get_temporal_client

        client = await get_temporal_client()
    except Exception:
        logger.exception("Failed to obtain Temporal client; cannot pause workflows")
        return

    paused = 0
    for task_id in task_ids:
        try:
            handle = client.get_workflow_handle(str(task_id))
            await handle.signal("pause_task", args=["budget_checker", str(task_id)])
            paused += 1
        except Exception:
            logger.debug("Could not pause workflow %s (may already be terminal)", task_id)

    logger.info("budget_checker paused %d/%d active workflow(s)", paused, len(task_ids))


async def _enable_cost_optimization_routing() -> None:
    """Persist cost_optimization_routing_enabled=true to the settings DB."""
    try:
        from src.admin.settings_service import get_settings_service
        from src.db.connection import get_async_session

        svc = get_settings_service()
        async with get_async_session() as session:
            await svc.set(
                session,
                "cost_optimization_routing_enabled",
                "true",
                updated_by="budget_checker",
            )
            await session.commit()
        logger.info("cost_optimization_routing_enabled set to true by budget_checker")
    except Exception:
        logger.exception("Failed to enable cost_optimization_routing_enabled")


# ---------------------------------------------------------------------------
# NATS consumer
# ---------------------------------------------------------------------------


async def _on_message(msg: Any) -> None:
    """Process a single ``pipeline.cost_update`` NATS message."""
    try:
        envelope = json.loads(msg.data)
        # Support both bare payload and typed envelope
        # {"type": "pipeline.cost_update", "data": {...}}
        data: dict[str, Any] = envelope.get("data", envelope)
        await _check_budget_thresholds(data)
        await msg.ack()
    except Exception:
        logger.exception("Failed to process cost_update message")
        await msg.ack()  # Always ack to prevent infinite redelivery


async def start_budget_checker(
    nats_url: str = "nats://localhost:4222",
) -> asyncio.Task[None]:
    """Start the budget threshold checker as a background NATS consumer.

    Creates a durable JetStream subscription on ``pipeline.cost_update``.
    Returns the :class:`asyncio.Task` running the consumer loop.
    """
    global _consumer_task, _downgrade_activated

    # Reset debounce flag on (re)start so a fresh process reflects the DB state.
    _downgrade_activated = False

    async def _run() -> None:
        nc = await nats.connect(nats_url)
        js = nc.jetstream()

        # Ensure the pipeline stream exists (may already be created by
        # events_publisher / gate_consumer at application startup).
        stream_name = "THESTUDIO_PIPELINE"
        subject = "pipeline.cost_update"
        try:
            await js.find_stream_name_by_subject(subject)
        except Exception:
            try:
                await js.add_stream(
                    name=stream_name,
                    subjects=["pipeline.>", "github.event.>"],
                )
                logger.info("Created JetStream stream %s", stream_name)
            except Exception:
                logger.debug(
                    "Could not create stream %s (may already exist)",
                    stream_name,
                    exc_info=True,
                )

        await js.subscribe(
            subject,
            durable="dashboard-budget-checker",
            cb=_on_message,
        )

        logger.info("Budget checker consumer started on subject %s", subject)

        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await nc.drain()
            logger.info("Budget checker consumer stopped gracefully")

    _consumer_task = asyncio.create_task(_run())
    return _consumer_task


async def stop_budget_checker() -> None:
    """Stop the budget checker consumer task."""
    global _consumer_task
    if _consumer_task is not None:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
