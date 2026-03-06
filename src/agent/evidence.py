"""Evidence bundle — structured record of what the Primary Agent did.

Produced after implementation, consumed by Verification Gate and Publisher.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceBundle(BaseModel):
    """Evidence produced by the Primary Agent after implementation."""

    taskpacket_id: UUID
    intent_version: int
    files_changed: list[str] = Field(default_factory=list)
    test_results: str = ""
    lint_results: str = ""
    agent_summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    loopback_attempt: int = 0
