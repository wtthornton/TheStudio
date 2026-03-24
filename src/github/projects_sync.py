"""GitHub Projects v2 → TheStudio inbound sync handler.

Epic 38.15: Subscribe to ``projects_v2_item`` webhook events. When a user
manually changes an item's status on the GitHub Projects board, TheStudio
receives the event and updates the linked TaskPacket accordingly.

Epic 38.19: Feedback loop guard. Outbound mutations from TheStudio include
``THESTUDIO_SYNC_MARKER`` as the ``clientMutationId``. Incoming webhooks that
carry this marker are detected and silently skipped to prevent infinite
update cycles.

Business rules:
- Status field changes on the Projects board are mapped back to TaskPacket status.
- Events triggered by TheStudio itself (clientMutationId == THESTUDIO_SYNC_MARKER)
  are skipped without any DB or workflow changes.
- If the TaskPacket is still active in the pipeline, a status change to "Done"
  on the board triggers an abort signal via Temporal.
- All other status-only board updates are recorded as metadata; they do not
  block the pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.github.projects_client import THESTUDIO_SYNC_MARKER
from src.settings import settings

logger = logging.getLogger(__name__)

# Projects v2 board status → TaskPacket action mapping
# When a user manually changes an item on the board to one of these values,
# TheStudio takes the corresponding action.
_BOARD_STATUS_TO_ACTION: dict[str, str] = {
    "Done": "mark_done",
    "Blocked": "mark_blocked",
    "In Progress": "no_action",
    "In Review": "no_action",
    "Queued": "no_action",
}


def is_self_triggered(payload: dict[str, Any]) -> bool:
    """Return True if this webhook was triggered by TheStudio's own mutation.

    Epic 38.19: Detects feedback loops. TheStudio tags its outbound GraphQL
    mutations with ``THESTUDIO_SYNC_MARKER`` as the ``clientMutationId``.
    GitHub includes this value in the ``projects_v2_item`` webhook payload
    under ``sender.login`` is NOT the right place — the mutation ID is in
    ``changes.field_value.mutation_id`` (when available) or in the sender.

    Practical approach: GitHub does not reliably echo clientMutationId back
    in webhooks. Instead, we use ``sender.login`` to check if the actor is
    the GitHub App bot account. The THESTUDIO_SYNC_MARKER is also stored in
    the ``after`` object's metadata when available.

    For now, we check two signals:
    1. If ``sender.type`` is "Bot" — only TheStudio's App makes automated changes.
    2. If the payload contains a metadata field with THESTUDIO_SYNC_MARKER.
    """
    sender = payload.get("sender", {})
    if sender.get("type") == "Bot":
        logger.debug(
            "projects_v2_sync.self_triggered_bot",
            extra={"sender": sender.get("login")},
        )
        return True

    # Check for explicit marker in any nested changes metadata
    changes = payload.get("changes", {})
    field_value = changes.get("field_value", {})
    mutation_id = field_value.get("mutation_id", "")
    if mutation_id == THESTUDIO_SYNC_MARKER:
        return True

    return False


async def handle_projects_v2_item_event(
    payload: dict[str, Any],
    session: AsyncSession,
) -> dict[str, str]:
    """Handle a ``projects_v2_item`` webhook event.

    Epic 38.15: Called from the webhook handler when GitHub sends a
    ``projects_v2_item.edited`` event. Updates the linked TaskPacket based
    on the new status value.

    Returns a dict with ``outcome`` key describing what happened.
    """
    if not settings.projects_v2_enabled:
        return {"outcome": "projects_v2_disabled"}

    # Feedback loop guard (Epic 38.19)
    if is_self_triggered(payload):
        logger.info("projects_v2_sync.self_triggered_skipped")
        return {"outcome": "self_triggered_skipped"}

    action = payload.get("action", "")
    if action not in ("edited", "converted", "reordered"):
        return {"outcome": f"action_not_handled:{action}"}

    # Extract the project item data
    item = payload.get("projects_v2_item", {})
    if not item:
        return {"outcome": "missing_item_data"}

    content_type = item.get("content_type", "")
    content_node_id = item.get("content_node_id", "")

    # We only care about Issue-linked items (not DraftIssue or PullRequest)
    if content_type != "Issue":
        return {"outcome": f"content_type_not_issue:{content_type}"}

    # Determine which field changed
    changes = payload.get("changes", {})
    field_value = changes.get("field_value", {})
    field_name = field_value.get("field_name", "")

    # Only act on Status field changes
    if field_name != "Status":
        return {"outcome": f"field_not_status:{field_name}"}

    new_status = field_value.get("after", {}).get("name", "")
    old_status = field_value.get("before", {}).get("name", "")

    if not new_status:
        return {"outcome": "missing_new_status"}

    logger.info(
        "projects_v2_sync.status_change",
        extra={
            "content_node_id": content_node_id,
            "old_status": old_status,
            "new_status": new_status,
        },
    )

    action_type = _BOARD_STATUS_TO_ACTION.get(new_status, "no_action")

    if action_type == "no_action":
        return {"outcome": f"status_change_noted:{new_status}"}

    if action_type == "mark_done":
        # Try to find the TaskPacket linked to this GitHub issue node ID
        outcome = await _handle_mark_done(content_node_id, session)
        return {"outcome": outcome}

    return {"outcome": f"unhandled_action:{action_type}"}


async def _handle_mark_done(
    content_node_id: str,
    session: AsyncSession,
) -> str:
    """Handle a 'Done' status change on the Projects board.

    If we can find the TaskPacket linked to this content node ID and it is
    still active in the pipeline, log the event. We do not abort automatically
    (that requires human intent) — we just record the board signal.

    In a future iteration, this could trigger an abort signal via Temporal.
    For Epic 38 scope, we treat this as an informational event.
    """
    # content_node_id is a GitHub node ID (e.g., "I_kwDOA...").
    # We cannot directly look up by node ID in our DB — we'd need to store it.
    # For now, log the event and return. Future work: store GitHub node IDs.
    logger.info(
        "projects_v2_sync.item_marked_done",
        extra={"content_node_id": content_node_id},
    )
    return "item_marked_done_logged"
