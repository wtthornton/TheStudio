"""Pydantic read schemas for routing review API.

These schemas expose the Router's ConsultPlan data to the planning
dashboard so developers can review and override expert selections
before execution begins.

Epic 36, Slice 3 — Story 36.14a
"""

from uuid import UUID

from pydantic import BaseModel

from src.experts.expert import ExpertClass


class ExpertSelectionRead(BaseModel):
    """API-facing representation of a single expert selection."""

    model_config = {"from_attributes": True}

    expert_id: UUID
    expert_class: ExpertClass
    pattern: str  # "parallel" or "staged"
    reputation_weight: float  # 0.0-1.0
    reputation_confidence: float  # 0.0-1.0
    selection_score: float  # trust_tier * (1 + weight * confidence)
    selection_reason: str  # Human-readable rationale for this selection


class RoutingResultRead(BaseModel):
    """API-facing representation of the full routing result (ConsultPlan)."""

    model_config = {"from_attributes": True}

    taskpacket_id: UUID
    selections: list[ExpertSelectionRead]
    rationale: str
    budget_remaining: int
