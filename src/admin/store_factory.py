"""Store factory — switches between in-memory and PostgreSQL backends.

Story 8.9: Store Configuration Switch
Feature flag: THESTUDIO_STORE_BACKEND ("memory" or "postgres")

In-memory mode (default): Returns module-level singletons.
Postgres mode: Returns session-scoped instances for use with FastAPI Depends.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.settings import settings


def is_postgres_backend() -> bool:
    """Check if PostgreSQL backend is configured."""
    return settings.store_backend == "postgres"


def get_tool_catalog_for_session(session: AsyncSession):
    """Return a PostgresToolCatalog bound to the given session."""
    from src.admin.persistence.pg_tool_catalog import PostgresToolCatalog
    return PostgresToolCatalog(session)


def get_model_audit_store_for_session(session: AsyncSession):
    """Return a PostgresModelAuditStore bound to the given session."""
    from src.admin.persistence.pg_model_audit import PostgresModelAuditStore
    return PostgresModelAuditStore(session)


def get_scorecard_service_for_session(session: AsyncSession):
    """Return a PostgresComplianceScorecardService bound to the given session."""
    from src.admin.persistence.pg_compliance import PostgresComplianceScorecardService
    return PostgresComplianceScorecardService(session)
