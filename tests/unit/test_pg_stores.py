"""Tests for PostgreSQL store implementations (Story 8.8).

Uses SQLite in-memory via aiosqlite for fast, isolated testing.
No PostgreSQL required.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.admin.compliance_scorecard import RepoComplianceData
from src.admin.model_gateway import ModelCallAudit
from src.admin.persistence.pg_compliance import PostgresComplianceScorecardService
from src.admin.persistence.pg_model_audit import PostgresModelAuditStore
from src.admin.persistence.pg_tool_catalog import PostgresToolCatalog
from src.admin.tool_catalog import (
    ApprovalStatus,
    CapabilityCategory,
    InvalidPromotionError,
    SuiteDuplicateError,
    SuiteNotFoundError,
    ToolEntry,
    ToolSuite,
)
from src.db.models import ModelCallAuditRow, ToolEntryRow, ToolProfileRow, ToolSuiteRow

# Only the tables defined in src.db.models (Epic 8 Sprint 2)
_TABLES = [
    ToolSuiteRow.__table__,
    ToolEntryRow.__table__,
    ToolProfileRow.__table__,
    ModelCallAuditRow.__table__,
]


@pytest.fixture
async def session():
    """Create an in-memory SQLite async session for testing."""
    from sqlalchemy.orm import registry as sa_registry
    from src.db.base import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # SQLite needs foreign key pragma
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(sync_conn, tables=_TABLES)
        )

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess

    await engine.dispose()


def _make_suite(name: str = "test-suite", status: ApprovalStatus = ApprovalStatus.OBSERVE) -> ToolSuite:
    return ToolSuite(
        name=name,
        description=f"Test suite {name}",
        tools=[
            ToolEntry("tool-a", "Tool A", CapabilityCategory.CODE_QUALITY),
            ToolEntry("tool-b", "Tool B", CapabilityCategory.SECURITY, read_only=False),
        ],
        approval_status=status,
        version="1.0.0",
    )


class TestPostgresToolCatalog:
    async def test_register_and_get(self, session: AsyncSession) -> None:
        catalog = PostgresToolCatalog(session)
        suite = _make_suite()
        await catalog.register(suite)
        result = await catalog.get_suite("test-suite")
        assert result.name == "test-suite"
        assert len(result.tools) == 2
        assert result.tools[0].name == "tool-a"

    async def test_register_duplicate_raises(self, session: AsyncSession) -> None:
        catalog = PostgresToolCatalog(session)
        await catalog.register(_make_suite())
        with pytest.raises(SuiteDuplicateError):
            await catalog.register(_make_suite())

    async def test_get_not_found_raises(self, session: AsyncSession) -> None:
        catalog = PostgresToolCatalog(session)
        with pytest.raises(SuiteNotFoundError):
            await catalog.get_suite("nonexistent")

    async def test_list_suites(self, session: AsyncSession) -> None:
        catalog = PostgresToolCatalog(session)
        await catalog.register(_make_suite("suite-1"))
        await catalog.register(_make_suite("suite-2"))
        result = await catalog.list_suites()
        assert len(result) == 2
        names = {s.name for s in result}
        assert names == {"suite-1", "suite-2"}

    async def test_promote_suite(self, session: AsyncSession) -> None:
        catalog = PostgresToolCatalog(session)
        await catalog.register(_make_suite())
        result = await catalog.promote_suite("test-suite")
        assert result.approval_status == ApprovalStatus.SUGGEST

        result = await catalog.promote_suite("test-suite")
        assert result.approval_status == ApprovalStatus.EXECUTE

    async def test_promote_past_execute_raises(self, session: AsyncSession) -> None:
        catalog = PostgresToolCatalog(session)
        await catalog.register(_make_suite(status=ApprovalStatus.EXECUTE))
        with pytest.raises(InvalidPromotionError):
            await catalog.promote_suite("test-suite")

    async def test_clear(self, session: AsyncSession) -> None:
        catalog = PostgresToolCatalog(session)
        await catalog.register(_make_suite())
        await catalog.clear()
        result = await catalog.list_suites()
        assert result == []

    async def test_preserves_tool_attributes(self, session: AsyncSession) -> None:
        catalog = PostgresToolCatalog(session)
        await catalog.register(_make_suite())
        result = await catalog.get_suite("test-suite")
        tool_b = [t for t in result.tools if t.name == "tool-b"][0]
        assert tool_b.capability == CapabilityCategory.SECURITY
        assert tool_b.read_only is False


class TestPostgresModelAuditStore:
    async def test_record_and_query(self, session: AsyncSession) -> None:
        store = PostgresModelAuditStore(session)
        task_id = uuid4()
        audit = ModelCallAudit(
            task_id=task_id,
            step="intent",
            provider="anthropic",
            model="claude-sonnet-4-6",
            tokens_in=100,
            tokens_out=50,
            cost=0.003,
            latency_ms=150.0,
        )
        await store.record(audit)
        results = await store.query(task_id=str(task_id))
        assert len(results) == 1
        assert results[0].step == "intent"
        assert results[0].tokens_in == 100

    async def test_query_by_step(self, session: AsyncSession) -> None:
        store = PostgresModelAuditStore(session)
        for step in ["intake", "intent", "intent"]:
            await store.record(ModelCallAudit(step=step, provider="anthropic"))
        results = await store.query(step="intent")
        assert len(results) == 2

    async def test_query_by_provider(self, session: AsyncSession) -> None:
        store = PostgresModelAuditStore(session)
        await store.record(ModelCallAudit(provider="anthropic"))
        await store.record(ModelCallAudit(provider="openai"))
        results = await store.query(provider="anthropic")
        assert len(results) == 1

    async def test_query_limit(self, session: AsyncSession) -> None:
        store = PostgresModelAuditStore(session)
        for i in range(10):
            await store.record(ModelCallAudit(step=f"step-{i}"))
        results = await store.query(limit=5)
        assert len(results) == 5

    async def test_query_ordered_by_created_at_desc(self, session: AsyncSession) -> None:
        store = PostgresModelAuditStore(session)
        for i in range(3):
            await store.record(ModelCallAudit(step=f"step-{i}"))
        results = await store.query()
        # Most recent first
        assert results[0].created_at >= results[-1].created_at

    async def test_clear(self, session: AsyncSession) -> None:
        store = PostgresModelAuditStore(session)
        await store.record(ModelCallAudit())
        await store.clear()
        results = await store.query()
        assert results == []


class TestPostgresComplianceScorecardService:
    async def test_evaluate_all_passing(self, session: AsyncSession) -> None:
        service = PostgresComplianceScorecardService(session)
        data = RepoComplianceData(
            branch_protection_enabled=True,
            required_reviewers_configured=True,
            standard_labels_present=True,
            projects_v2_configured=True,
            evidence_format_valid=True,
            idempotency_guard_active=True,
            execution_plane_healthy=True,
        )
        result = service.evaluate("test-repo", data)
        assert result.overall_pass is True
        assert all(c.passed for c in result.checks)
        assert len(result.checks) == 7

    async def test_evaluate_partial_failing(self, session: AsyncSession) -> None:
        service = PostgresComplianceScorecardService(session)
        data = RepoComplianceData(branch_protection_enabled=True)
        result = service.evaluate("test-repo", data)
        assert result.overall_pass is False
        passed = [c for c in result.checks if c.passed]
        assert len(passed) == 1

    async def test_evaluate_default_all_fail(self, session: AsyncSession) -> None:
        service = PostgresComplianceScorecardService(session)
        result = service.evaluate("test-repo")
        assert result.overall_pass is False

    async def test_invalidate_cache_noop(self, session: AsyncSession) -> None:
        service = PostgresComplianceScorecardService(session)
        service.invalidate_cache("test-repo")  # Should not raise
