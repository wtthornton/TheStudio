"""Intent Builder — produces Intent Specifications from enriched TaskPackets.

Reads enriched TaskPacket + GitHub issue content, extracts goal, constraints,
acceptance criteria, and non-goals. Rule-based extraction (no LLM in Phase 0).

Architecture reference: thestudioarc/11-intent-layer.md
SOUL.md: "Intent is the definition of correctness."
"""

import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.intent.intent_crud import create_intent, get_latest_for_taskpacket
from src.intent.intent_spec import IntentSpecCreate, IntentSpecRead
from src.models.taskpacket_crud import get_by_id, update_intent
from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_TASKPACKET_ID,
    SPAN_INTENT_BUILD,
)
from src.observability.tracing import get_tracer

tracer = get_tracer("thestudio.intent")

# Risk flag -> constraint mappings
_RISK_CONSTRAINTS: dict[str, list[str]] = {
    "risk_security": [
        "Must not expose credentials, tokens, or secrets",
        "Security-sensitive changes require review",
    ],
    "risk_breaking": [
        "Must maintain backward compatibility or document migration path",
        "Breaking changes require deprecation notice",
    ],
    "risk_cross_team": [
        "Changes affecting other teams require cross-team notification",
    ],
    "risk_data": [
        "Database changes must include reversible migration",
        "Must not cause data loss",
    ],
}

# Default constraint applied to all tasks
_DEFAULT_CONSTRAINT = "Must include tests for new or changed behavior"

# Pattern for markdown checkboxes: - [ ] or - [x] items
_CHECKBOX_PATTERN = re.compile(r"^\s*-\s*\[[ xX]?\]\s*(.+)$", re.MULTILINE)

# Pattern for "out of scope" sections
_OUT_OF_SCOPE_PATTERN = re.compile(
    r"(?:out\s*of\s*scope|non[\s-]?goals?|not\s+included|won'?t\s+(?:do|fix|implement))"
    r"\s*:?\s*(.+?)(?:\n\n|\Z)",
    re.IGNORECASE | re.DOTALL,
)

# Pattern for bullet list items
_BULLET_PATTERN = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)


def extract_goal(title: str, body: str) -> str:
    """Extract the goal from issue title and first paragraph of body."""
    goal = title.strip()

    # Add first meaningful paragraph from body as elaboration
    if body:
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        for para in paragraphs:
            # Skip headings, checkboxes, code blocks
            if para.startswith(("#", "```", "- [")) or len(para) < 10:
                continue
            goal = f"{goal}: {para[:500]}"
            break

    return goal


def derive_constraints(risk_flags: dict[str, bool] | None) -> list[str]:
    """Derive constraints from risk flags."""
    constraints = [_DEFAULT_CONSTRAINT]

    if risk_flags:
        for flag_name, is_set in risk_flags.items():
            if is_set and flag_name in _RISK_CONSTRAINTS:
                constraints.extend(_RISK_CONSTRAINTS[flag_name])

    return constraints


def extract_acceptance_criteria(body: str) -> list[str]:
    """Extract acceptance criteria from issue body.

    Looks for markdown checkboxes first, then falls back to bullet lists
    under "acceptance criteria" or "requirements" headings.
    """
    # Try checkboxes first
    checkboxes = _CHECKBOX_PATTERN.findall(body)
    if checkboxes:
        return [c.strip() for c in checkboxes if len(c.strip()) > 5]

    # Look for bullet items under relevant headings
    criteria: list[str] = []
    lines = body.split("\n")
    in_criteria_section = False
    for line in lines:
        lower = line.lower().strip()
        if re.match(r"^#+\s*(acceptance\s*criteria|requirements|definition\s*of\s*done)", lower):
            in_criteria_section = True
            continue
        if in_criteria_section:
            if line.startswith("#"):
                break  # New heading ends the section
            match = _BULLET_PATTERN.match(line)
            if match:
                criteria.append(match.group(1).strip())

    if criteria:
        return criteria

    # Fallback: use first 3 bullet items
    bullets = _BULLET_PATTERN.findall(body)
    return [b.strip() for b in bullets[:3] if len(b.strip()) > 5]


def extract_non_goals(body: str) -> list[str]:
    """Extract non-goals from explicit 'out of scope' mentions."""
    non_goals: list[str] = []

    # Find "out of scope" sections
    for match in _OUT_OF_SCOPE_PATTERN.finditer(body):
        section_text = match.group(1)
        # Extract bullet items from the section
        bullets = _BULLET_PATTERN.findall(section_text)
        if bullets:
            non_goals.extend(b.strip() for b in bullets)
        else:
            # Treat the whole text as a single non-goal
            cleaned = section_text.strip()
            if cleaned:
                non_goals.append(cleaned)

    return non_goals


async def build_intent(
    session: AsyncSession,
    taskpacket_id: UUID,
    issue_title: str,
    issue_body: str,
) -> IntentSpecRead:
    """Build an Intent Specification from an enriched TaskPacket.

    Args:
        session: Database session.
        taskpacket_id: The TaskPacket to build intent for.
        issue_title: GitHub issue title.
        issue_body: GitHub issue body text.

    Returns:
        The created IntentSpecRead.

    Raises:
        ValueError: If TaskPacket not found or not in enriched status.
    """
    with tracer.start_as_current_span(SPAN_INTENT_BUILD) as span:
        # Load TaskPacket
        tp = await get_by_id(session, taskpacket_id)
        if tp is None:
            raise ValueError(f"TaskPacket {taskpacket_id} not found")

        span.set_attribute(ATTR_TASKPACKET_ID, str(taskpacket_id))
        span.set_attribute(ATTR_CORRELATION_ID, str(tp.correlation_id))

        # Determine version
        existing = await get_latest_for_taskpacket(session, taskpacket_id)
        version = (existing.version + 1) if existing else 1

        # Extract intent components
        goal = extract_goal(issue_title, issue_body)
        constraints = derive_constraints(tp.risk_flags)
        criteria = extract_acceptance_criteria(issue_body)
        non_goals = extract_non_goals(issue_body)

        # Ensure at least one criterion
        if not criteria:
            criteria = [f"Implementation satisfies: {issue_title}"]

        # Create Intent Specification
        intent_data = IntentSpecCreate(
            taskpacket_id=taskpacket_id,
            version=version,
            goal=goal,
            constraints=constraints,
            acceptance_criteria=criteria,
            non_goals=non_goals,
        )
        intent = await create_intent(session, intent_data)

        # Update TaskPacket with intent reference
        await update_intent(session, taskpacket_id, intent.id, intent.version)

        # Record span attributes
        span.set_attribute("thestudio.intent_version", version)
        span.set_attribute("thestudio.constraint_count", len(constraints))
        span.set_attribute("thestudio.criteria_count", len(criteria))

        return intent
