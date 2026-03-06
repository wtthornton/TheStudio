"""Context Manager — enriches TaskPackets with scope, risk, complexity, and context packs.

Sits between Ingress and Intent Builder. Reads the TaskPacket, analyzes the
GitHub issue content, and updates the TaskPacket with structured enrichment data.

Architecture reference: thestudioarc/03-context-manager.md
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.context.complexity import compute_complexity_index
from src.context.risk_flagger import flag_risks
from src.context.scope_analyzer import analyze_scope
from src.context.service_context_pack import get_context_packs
from src.models.taskpacket import TaskPacketRead
from src.models.taskpacket_crud import get_by_id, update_enrichment
from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_TASKPACKET_ID,
    SPAN_CONTEXT_ENRICH,
)
from src.observability.tracing import get_tracer

tracer = get_tracer("thestudio.context")


async def enrich_taskpacket(
    session: AsyncSession,
    taskpacket_id: UUID,
    issue_title: str,
    issue_body: str,
) -> TaskPacketRead:
    """Enrich a TaskPacket with scope, risk flags, complexity, and context packs.

    Args:
        session: Database session.
        taskpacket_id: The TaskPacket to enrich.
        issue_title: GitHub issue title.
        issue_body: GitHub issue body text.

    Returns:
        Updated TaskPacketRead with enrichment data and status=enriched.

    Raises:
        ValueError: If TaskPacket not found.
    """
    with tracer.start_as_current_span(SPAN_CONTEXT_ENRICH) as span:
        # Fetch the TaskPacket
        tp = await get_by_id(session, taskpacket_id)
        if tp is None:
            raise ValueError(f"TaskPacket {taskpacket_id} not found")

        span.set_attribute(ATTR_TASKPACKET_ID, str(taskpacket_id))
        span.set_attribute(ATTR_CORRELATION_ID, str(tp.correlation_id))

        # Analyze scope
        scope_result = analyze_scope(issue_title, issue_body)

        # Flag risks
        risk_flags = flag_risks(issue_title, issue_body)

        # Get context packs
        packs = get_context_packs(tp.repo)
        pack_dicts: list[dict[str, Any]] = [p.to_dict() for p in packs]

        # Compute Complexity Index v1 with full dimensions
        # Note: mandatory_expert_classes requires EffectiveRolePolicy which is computed
        # by Intake Agent. At enrichment time, we don't have it yet, so we pass empty.
        # The expert_coverage dimension will be 0 but can be updated later if needed.
        complexity_index = compute_complexity_index(
            scope_result=scope_result,
            risk_flags=risk_flags,
            mandatory_expert_classes=(),
        )

        # Record span attributes
        risk_count = sum(1 for v in risk_flags.values() if v)
        span.set_attribute("thestudio.complexity_score", complexity_index.score)
        span.set_attribute("thestudio.complexity_band", complexity_index.band)
        span.set_attribute("thestudio.risk_flag_count", risk_count)

        # Update TaskPacket with enrichment data
        updated = await update_enrichment(
            session=session,
            task_id=taskpacket_id,
            scope=scope_result.to_dict(),
            risk_flags=risk_flags,
            complexity_index=complexity_index.to_dict(),
            context_packs=pack_dicts,
        )

        return updated
