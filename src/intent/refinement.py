"""Intent Refinement Loop — versioned re-specification from QA/Assembler triggers.

Refinement produces a new IntentSpec version when QA or Assembler identifies
ambiguity. Prior versions are preserved. Capped at 2 versions per workflow.

Architecture reference: thestudioarc/11-intent-layer.md — Refinement Loop
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.intent.intent_crud import create_intent, get_latest_for_taskpacket
from src.intent.intent_spec import IntentSpecCreate, IntentSpecRead
from src.models.taskpacket_crud import get_by_id, update_intent_version
from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_TASKPACKET_ID,
    SPAN_INTENT_REFINE,
)
from src.observability.tracing import get_tracer
from src.settings import settings

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.intent")

# Maximum intent versions per workflow (configurable via settings)
MAX_INTENT_VERSIONS = settings.max_intent_versions


class RefinementCapExceededError(Exception):
    """Raised when intent refinement exceeds the per-workflow version cap."""

    def __init__(self, taskpacket_id: UUID, current_version: int) -> None:
        super().__init__(
            f"Intent refinement cap ({MAX_INTENT_VERSIONS}) exceeded for "
            f"TaskPacket {taskpacket_id} (current version: {current_version})"
        )
        self.taskpacket_id = taskpacket_id
        self.current_version = current_version


@dataclass(frozen=True)
class RefinementTrigger:
    """Describes why intent refinement was requested."""

    source: str  # "qa_agent" or "assembler"
    questions: list[str]
    triggering_defects: list[str] = ()  # type: ignore[assignment]
    triggering_conflict: str = ""

    def __post_init__(self) -> None:
        # Coerce tuple default for frozen dataclass
        if isinstance(self.triggering_defects, list):
            return
        object.__setattr__(self, "triggering_defects", list(self.triggering_defects))


async def refine_intent(
    session: AsyncSession,
    taskpacket_id: UUID,
    trigger: RefinementTrigger,
    updated_goal: str | None = None,
    additional_constraints: list[str] | None = None,
    additional_criteria: list[str] | None = None,
) -> IntentSpecRead:
    """Refine an existing Intent Specification based on QA or Assembler feedback.

    Creates a new version of the IntentSpec incorporating the refinement
    trigger's questions and any updated fields. Prior versions are preserved.

    Args:
        session: Database session.
        taskpacket_id: The TaskPacket whose intent is being refined.
        trigger: The refinement trigger with source and questions.
        updated_goal: Optional updated goal statement.
        additional_constraints: Optional new constraints to add.
        additional_criteria: Optional new acceptance criteria to add.

    Returns:
        The newly created IntentSpecRead (new version).

    Raises:
        RefinementCapExceededError: If version cap (2) would be exceeded.
        ValueError: If TaskPacket or existing intent not found.
    """
    with tracer.start_as_current_span(SPAN_INTENT_REFINE) as span:
        # Load TaskPacket
        tp = await get_by_id(session, taskpacket_id)
        if tp is None:
            raise ValueError(f"TaskPacket {taskpacket_id} not found")

        span.set_attribute(ATTR_TASKPACKET_ID, str(taskpacket_id))
        span.set_attribute(ATTR_CORRELATION_ID, str(tp.correlation_id))

        # Load current intent
        current = await get_latest_for_taskpacket(session, taskpacket_id)
        if current is None:
            raise ValueError(f"No IntentSpec found for TaskPacket {taskpacket_id}")

        # Enforce version cap
        if current.version >= MAX_INTENT_VERSIONS:
            raise RefinementCapExceededError(taskpacket_id, current.version)

        new_version = current.version + 1

        # Build refined intent: carry forward existing fields, apply updates
        goal = updated_goal if updated_goal else current.goal
        constraints = list(current.constraints)
        if additional_constraints:
            constraints.extend(additional_constraints)

        criteria = list(current.acceptance_criteria)
        if additional_criteria:
            criteria.extend(additional_criteria)

        # Add refinement-derived constraints from trigger questions
        for question in trigger.questions:
            constraints.append(f"[Refinement v{new_version}] {question}")

        non_goals = list(current.non_goals)

        # Create new version
        intent_data = IntentSpecCreate(
            taskpacket_id=taskpacket_id,
            version=new_version,
            goal=goal,
            constraints=constraints,
            acceptance_criteria=criteria,
            non_goals=non_goals,
        )
        refined = await create_intent(session, intent_data)

        # Update TaskPacket with new intent version (no status change)
        await update_intent_version(session, taskpacket_id, refined.id, refined.version)

        # Record span attributes
        span.set_attribute("thestudio.intent_version", new_version)
        span.set_attribute("thestudio.refinement_source", trigger.source)
        span.set_attribute("thestudio.refinement_questions", len(trigger.questions))

        logger.info(
            "Intent refined for TaskPacket %s: v%d -> v%d (source=%s, questions=%d)",
            taskpacket_id,
            current.version,
            new_version,
            trigger.source,
            len(trigger.questions),
        )

        return refined
