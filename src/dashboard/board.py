"""Board preferences API endpoints (Epic 36, Story 36.17).

Provides persistent storage for Backlog Board column UI state:
- GET  /board/preferences      — return all column preferences
- POST /board/preferences      — upsert preferences for one or more columns
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/board", tags=["board"])

# ---------------------------------------------------------------------------
# Valid column IDs — must match frontend BOARD_COLUMNS keys
# ---------------------------------------------------------------------------

VALID_COLUMN_IDS = frozenset(
    {"triage", "planning", "building", "verify", "done", "rejected"}
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ColumnPreferences(BaseModel):
    """Preferences for a single board column."""

    column_id: str = Field(..., description="Board column identifier")
    width: int | None = Field(None, ge=100, le=2000, description="Column width in px")
    collapsed: bool = Field(False, description="Whether the column is collapsed")
    sort_field: str | None = Field(
        None,
        max_length=64,
        description="Field to sort tasks by (e.g. 'complexity_index', 'created_at')",
    )
    sort_direction: str | None = Field(
        None,
        description="Sort direction: 'asc' or 'desc'",
        pattern="^(asc|desc)$",
    )
    updated_at: datetime | None = Field(None, description="Last updated timestamp")

    class Config:
        from_attributes = True


class BoardPreferencesRequest(BaseModel):
    """Request body for upserting board preferences."""

    columns: list[ColumnPreferences] = Field(
        ..., min_length=1, description="One or more column preference entries to upsert"
    )


class BoardPreferencesResponse(BaseModel):
    """Response containing all persisted board column preferences."""

    columns: list[ColumnPreferences]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/preferences", response_model=BoardPreferencesResponse)
async def get_board_preferences(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardPreferencesResponse:
    """Return all persisted board column preferences.

    Columns with no saved preferences are omitted from the response.
    The frontend should apply defaults for any missing column_id.
    """
    result = await session.execute(
        text(
            "SELECT column_id, width, collapsed, sort_field, sort_direction, updated_at"
            " FROM board_preferences ORDER BY column_id"
        )
    )
    rows = result.fetchall()
    columns = [
        ColumnPreferences(
            column_id=row.column_id,
            width=row.width,
            collapsed=row.collapsed,
            sort_field=row.sort_field,
            sort_direction=row.sort_direction,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    return BoardPreferencesResponse(columns=columns)


@router.post("/preferences", response_model=BoardPreferencesResponse)
async def upsert_board_preferences(
    body: BoardPreferencesRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardPreferencesResponse:
    """Upsert board column preferences.

    Accepts a list of column preference objects. Each entry is inserted or
    updated by column_id (upsert). Unknown column_ids are silently ignored.
    Returns the full current preferences for all columns after the update.
    """
    for col in body.columns:
        if col.column_id not in VALID_COLUMN_IDS:
            logger.warning("Ignoring unknown board column_id: %s", col.column_id)
            continue
        await session.execute(
            text(
                """
                INSERT INTO board_preferences
                    (column_id, width, collapsed, sort_field, sort_direction, updated_at)
                VALUES
                    (:column_id, :width, :collapsed, :sort_field, :sort_direction, now())
                ON CONFLICT (column_id) DO UPDATE SET
                    width           = EXCLUDED.width,
                    collapsed       = EXCLUDED.collapsed,
                    sort_field      = EXCLUDED.sort_field,
                    sort_direction  = EXCLUDED.sort_direction,
                    updated_at      = now()
                """
            ),
            {
                "column_id": col.column_id,
                "width": col.width,
                "collapsed": col.collapsed,
                "sort_field": col.sort_field,
                "sort_direction": col.sort_direction,
            },
        )
    await session.commit()

    # Return the full current state
    result = await session.execute(
        text(
            "SELECT column_id, width, collapsed, sort_field, sort_direction, updated_at"
            " FROM board_preferences ORDER BY column_id"
        )
    )
    rows = result.fetchall()
    columns = [
        ColumnPreferences(
            column_id=row.column_id,
            width=row.width,
            collapsed=row.collapsed,
            sort_field=row.sort_field,
            sort_direction=row.sort_direction,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    return BoardPreferencesResponse(columns=columns)
