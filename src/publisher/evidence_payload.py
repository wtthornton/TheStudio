"""EvidencePayload — structured JSON schema for machine-readable PR evidence.

Produced alongside the Markdown evidence comment. Consumed by the Evidence
Explorer frontend and the evidence endpoint (Epic 38 Story 38.7).

Architecture reference: thestudioarc/15-system-runtime-flow.md
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TaskSummary(BaseModel):
    """High-level summary of the task."""

    taskpacket_id: UUID
    correlation_id: UUID
    repo: str
    issue_id: int
    issue_title: str | None = None
    status: str
    trust_tier: str | None = None
    loopback_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    pr_number: int | None = None
    pr_url: str | None = None


class IntentSummary(BaseModel):
    """Summary of the intent specification used for this task."""

    goal: str
    version: int
    acceptance_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)


class GateResult(BaseModel):
    """Result of a single verification gate check."""

    name: str
    passed: bool
    details: str | None = None


class GateResults(BaseModel):
    """Aggregated verification and QA gate results."""

    verification_passed: bool = False
    qa_passed: bool | None = None
    checks: list[GateResult] = Field(default_factory=list)
    defect_count: int = 0
    defect_categories: list[str] = Field(default_factory=list)


class CostEntry(BaseModel):
    """Cost attribution for a single stage or model."""

    label: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


class CostBreakdown(BaseModel):
    """Token and cost summary for the task run."""

    total_cost_usd: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    entries: list[CostEntry] = Field(default_factory=list)


class ProvenanceEntry(BaseModel):
    """A single expert or agent that contributed to the task."""

    name: str
    version: str | None = None
    role: str | None = None
    policy_triggers: list[str] = Field(default_factory=list)


class Provenance(BaseModel):
    """Provenance chain — who contributed to this task output."""

    experts_consulted: list[ProvenanceEntry] = Field(default_factory=list)
    agent_model: str | None = None
    loopback_stages: list[str] = Field(default_factory=list)


class EvidencePayload(BaseModel):
    """Structured JSON evidence payload for a completed TaskPacket.

    Produced by format_evidence_json() alongside the Markdown evidence comment.
    All sections are optional — callers populate what they have; missing data
    is represented by None or empty defaults rather than raising errors.
    """

    schema_version: str = "1.0"
    generated_at: datetime | None = None

    task_summary: TaskSummary
    intent: IntentSummary | None = None
    gate_results: GateResults | None = None
    cost_breakdown: CostBreakdown | None = None
    provenance: Provenance | None = None
    files_changed: list[str] = Field(default_factory=list)

    # Raw metadata bag for forward-compat (extensions can store extra keys here)
    extra: dict[str, Any] = Field(default_factory=dict)
