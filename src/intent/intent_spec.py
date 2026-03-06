"""Intent Specification model — the definition of correctness for a task.

SOUL.md: "Intent is the definition of correctness."
Architecture reference: thestudioarc/11-intent-layer.md
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class IntentSpecRow(Base):
    """SQLAlchemy ORM model for the intent_spec table."""

    __tablename__ = "intent_spec"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    taskpacket_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    goal: Mapped[str] = mapped_column(String(2000), nullable=False)
    constraints: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    acceptance_criteria: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    non_goals: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        {"comment": "Intent Specification — definition of correctness for a task"},
    )


class IntentSpecCreate(BaseModel):
    """Input for creating an Intent Specification."""

    taskpacket_id: UUID
    version: int = 1
    goal: str
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)


class IntentSpecRead(BaseModel):
    """Output for reading an Intent Specification."""

    model_config = {"from_attributes": True}

    id: UUID
    taskpacket_id: UUID
    version: int
    goal: str
    constraints: list[str]
    acceptance_criteria: list[str]
    non_goals: list[str]
    created_at: datetime
