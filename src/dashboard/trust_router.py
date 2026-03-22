"""Trust tier configuration API endpoints.

Endpoints:
- GET    /trust/rules                — list all trust tier rules (ordered by priority)
- POST   /trust/rules                — create a new rule
- GET    /trust/rules/{rule_id}      — fetch a single rule
- PUT    /trust/rules/{rule_id}      — partial update a rule
- DELETE /trust/rules/{rule_id}      — delete a rule

- GET    /trust/safety-bounds        — fetch the safety bounds singleton
- PUT    /trust/safety-bounds        — update safety bounds

- GET    /trust/default-tier         — fetch the default fallback tier
- PUT    /trust/default-tier         — set the default fallback tier

All endpoints use the async DB session and the CRUD helpers from
``src/dashboard/models/trust_config``.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard.models.trust_config import (
    DefaultTierRead,
    DefaultTierUpdate,
    SafeBoundsRead,
    SafeBoundsUpdate,
    TrustTierRuleCreate,
    TrustTierRuleRead,
    TrustTierRuleUpdate,
    create_rule,
    delete_rule,
    get_default_tier,
    get_rule,
    get_safety_bounds,
    list_rules,
    update_default_tier,
    update_rule,
    update_safety_bounds,
)
from src.db.connection import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trust", tags=["trust"])


# ---------------------------------------------------------------------------
# Trust tier rule endpoints
# ---------------------------------------------------------------------------


@router.get("/rules", response_model=list[TrustTierRuleRead])
async def list_trust_rules(
    active_only: bool = Query(False, description="When true, return only active rules"),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[TrustTierRuleRead]:
    """Return all trust-tier rules ordered by priority ascending.

    Returns:
        200 — list of rules (empty list if none exist)
    """
    rules = await list_rules(session, active_only=active_only)
    logger.debug("list_trust_rules", extra={"count": len(rules), "active_only": active_only})
    return rules


@router.post("/rules", response_model=TrustTierRuleRead, status_code=201)
async def create_trust_rule(
    body: TrustTierRuleCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TrustTierRuleRead:
    """Create a new trust-tier rule.

    Returns:
        201 — rule created
        422 — validation error
    """
    rule = await create_rule(session, body)
    await session.commit()
    logger.info(
        "trust rule created",
        extra={"rule_id": str(rule.id), "priority": rule.priority, "tier": rule.assigned_tier},
    )
    return rule


@router.get("/rules/{rule_id}", response_model=TrustTierRuleRead)
async def get_trust_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TrustTierRuleRead:
    """Fetch a single trust-tier rule by ID.

    Returns:
        200 — rule found
        404 — rule not found
    """
    rule = await get_rule(session, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Trust rule {rule_id} not found")
    return rule


@router.put("/rules/{rule_id}", response_model=TrustTierRuleRead)
async def update_trust_rule(
    rule_id: UUID,
    body: TrustTierRuleUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TrustTierRuleRead:
    """Partially update a trust-tier rule.

    All fields in the request body are optional.  Only supplied fields are
    modified.

    Returns:
        200 — rule updated
        404 — rule not found
        422 — validation error
    """
    rule = await update_rule(session, rule_id, body)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Trust rule {rule_id} not found")
    await session.commit()
    logger.info("trust rule updated", extra={"rule_id": str(rule_id)})
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_trust_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    """Delete a trust-tier rule by ID.

    Returns:
        204 — rule deleted
        404 — rule not found
    """
    deleted = await delete_rule(session, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Trust rule {rule_id} not found")
    await session.commit()
    logger.info("trust rule deleted", extra={"rule_id": str(rule_id)})


# ---------------------------------------------------------------------------
# Safety bounds endpoints
# ---------------------------------------------------------------------------


@router.get("/safety-bounds", response_model=SafeBoundsRead)
async def get_trust_safety_bounds(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SafeBoundsRead:
    """Return the safety bounds singleton.

    Creates the singleton with safe defaults if it does not yet exist.

    Returns:
        200 — safety bounds
    """
    bounds = await get_safety_bounds(session)
    return bounds


@router.put("/safety-bounds", response_model=SafeBoundsRead)
async def update_trust_safety_bounds(
    body: SafeBoundsUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SafeBoundsRead:
    """Update the safety bounds singleton.

    All fields are optional; only supplied fields are modified.

    Returns:
        200 — updated safety bounds
        422 — validation error
    """
    bounds = await update_safety_bounds(session, body)
    await session.commit()
    logger.info("trust safety bounds updated")
    return bounds


# ---------------------------------------------------------------------------
# Default tier endpoints
# ---------------------------------------------------------------------------


@router.get("/default-tier", response_model=DefaultTierRead)
async def get_trust_default_tier(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> DefaultTierRead:
    """Return the default trust tier used when no rule matches.

    Returns:
        200 — default tier
    """
    return await get_default_tier(session)


@router.put("/default-tier", response_model=DefaultTierRead)
async def set_trust_default_tier(
    body: DefaultTierUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> DefaultTierRead:
    """Set the default trust tier fallback.

    This tier is assigned when the rule engine finds no matching active rule.
    Defaults to ``observe`` (most restrictive).

    Returns:
        200 — updated default tier
        422 — validation error
    """
    result = await update_default_tier(session, body)
    await session.commit()
    logger.info("trust default tier updated", extra={"tier": result.default_tier})
    return result
