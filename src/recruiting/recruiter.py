"""Expert Recruiter — template-based expert creation with qualification.

Architecture reference: thestudioarc/04-expert-recruiter.md

The Recruiter manages expert supply. It:
1. Receives capability requests from the Router (RecruiterRequest)
2. Searches for existing experts (de-duplication)
3. Selects a template if no expert exists
4. Constructs expert pack from template
5. Runs qualification harness
6. Assigns trust tier (shadow or probation — never trusted)
7. Registers in Expert Library
"""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.experts.expert import ExpertClass, ExpertCreate, ExpertRead, TrustTier
from src.experts.expert_crud import (
    create_expert,
    search_experts,
    update_expert_version,
)
from src.recruiting.qualification import QualificationResult, qualify_expert_definition
from src.recruiting.templates import ExpertTemplate, select_template
from src.routing.router import RecruiterRequest

logger = logging.getLogger(__name__)


# Signals emitted by the Recruiter (per 04-expert-recruiter.md)
SIGNAL_EXPERT_CREATED = "expert_created"
SIGNAL_EXPERT_VERSION_CREATED = "expert_version_created"


@dataclass(frozen=True)
class RecruitmentResult:
    """Result of a recruitment attempt."""

    success: bool
    expert: ExpertRead | None = None
    action: str = ""  # "created", "version_updated", "existing", "failed"
    qualification: QualificationResult | None = None
    reason: str = ""


async def recruit(
    session: AsyncSession,
    request: RecruiterRequest,
) -> RecruitmentResult:
    """Process a capability request from the Router.

    Steps per 04-expert-recruiter.md:
    1. Normalize request
    2. Search for existing expert (de-duplication)
    3. If found, return existing or create new version
    4. If not found, select template and create new expert
    5. Run qualification harness
    6. Assign trust tier and register

    Args:
        session: Database session.
        request: Capability request from Router.

    Returns:
        RecruitmentResult with created/updated expert or failure reason.
    """
    # Step 2: Search for existing expert (de-duplication)
    existing = await search_experts(
        session,
        expert_class=request.expert_class,
        capability_tags=request.capability_tags,
    )

    # Check for exact or close match
    for expert in existing:
        tag_overlap = set(expert.capability_tags) & set(request.capability_tags)
        if len(tag_overlap) >= len(request.capability_tags):
            # Exact match — return existing expert
            logger.info(
                "De-duplication: found existing expert %s for %s",
                expert.name, request.expert_class.value,
            )
            return RecruitmentResult(
                success=True,
                expert=expert,
                action="existing",
                reason=f"Existing expert {expert.name} matches capability request",
            )

    # Step 3: Select template
    template = select_template(request.expert_class, request.capability_tags)
    if template is None:
        logger.warning(
            "No template found for %s with tags %s",
            request.expert_class.value, request.capability_tags,
        )
        return RecruitmentResult(
            success=False,
            action="failed",
            reason=f"No template found for {request.expert_class.value}",
        )

    # Step 4: Construct expert pack from template
    definition = dict(template.definition_skeleton)
    tool_policy = dict(template.tool_policy)

    # Step 5: Run qualification harness
    qualification = qualify_expert_definition(definition, tool_policy)
    if not qualification.passed:
        logger.warning(
            "Qualification failed for template %s: %s",
            template.template_id, qualification.failures,
        )
        return RecruitmentResult(
            success=False,
            action="failed",
            qualification=qualification,
            reason=f"Qualification failed: {', '.join(qualification.failures)}",
        )

    # Step 6: Assign trust tier — never trusted for new experts
    # Compliance experts always start as shadow (per 04-expert-recruiter.md)
    trust_tier = template.default_trust_tier
    if request.expert_class == ExpertClass.COMPLIANCE:
        trust_tier = TrustTier.SHADOW

    # Check for deprecated expert that can be revived as new version
    deprecated = await search_experts(
        session,
        expert_class=request.expert_class,
        capability_tags=request.capability_tags,
        include_deprecated=True,
    )
    for dep_expert in deprecated:
        if dep_expert.lifecycle_state.value == "deprecated":
            # Prefer version update over new identity
            updated = await update_expert_version(
                session, dep_expert.id, definition,
            )
            logger.info(
                "Revived deprecated expert %s as v%d",
                updated.name, updated.current_version,
            )
            return RecruitmentResult(
                success=True,
                expert=updated,
                action="version_updated",
                qualification=qualification,
                reason=f"Revived deprecated expert {updated.name}",
            )

    # Step 7: Create new expert
    expert_name = _generate_name(template, request.capability_tags)
    expert_data = ExpertCreate(
        name=expert_name,
        expert_class=request.expert_class,
        capability_tags=request.capability_tags,
        scope_description=template.scope_description,
        tool_policy=tool_policy,
        trust_tier=trust_tier,
        definition=definition,
    )

    expert = await create_expert(session, expert_data)
    logger.info(
        "Created new expert %s (%s, tier=%s)",
        expert.name, expert.expert_class.value, expert.trust_tier.value,
    )

    return RecruitmentResult(
        success=True,
        expert=expert,
        action="created",
        qualification=qualification,
        reason=f"Created from template {template.template_id}",
    )


async def recruit_batch(
    session: AsyncSession,
    requests: list[RecruiterRequest],
) -> list[RecruitmentResult]:
    """Process multiple capability requests from the Router."""
    results: list[RecruitmentResult] = []
    for request in requests:
        result = await recruit(session, request)
        results.append(result)
    return results


def _generate_name(template: ExpertTemplate, capability_tags: list[str]) -> str:
    """Generate a unique-ish expert name from template + tags."""
    tag_suffix = "-".join(sorted(capability_tags)[:2]) if capability_tags else "general"
    return f"{template.name_prefix}-{tag_suffix}"
