"""Persistence round-trip tests for store factory and PostgreSQL backends.

Story 9.6 (Epic 9): Verify store factory switches correctly and persistence
classes can write and read data using async sessions.

Note: Full PostgreSQL round-trip tests require a running Postgres instance
and are marked as integration tests. Store factory switching tests run
without external dependencies.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.admin.store_factory import (
    get_model_audit_store_for_session,
    get_scorecard_service_for_session,
    get_tool_catalog_for_session,
    is_postgres_backend,
)


# --- Store Factory Switching Tests ---


class TestStoreFactorySwitching:
    """Store factory returns correct backend based on feature flag."""

    def test_is_postgres_backend_false_by_default(self, monkeypatch):
        """Default store_backend='memory' returns False."""
        monkeypatch.setenv("THESTUDIO_STORE_BACKEND", "memory")
        from src.settings import Settings

        monkeypatch.setattr("src.admin.store_factory.settings", Settings())
        assert is_postgres_backend() is False

    def test_is_postgres_backend_true_when_postgres(self, monkeypatch):
        """store_backend='postgres' returns True."""
        monkeypatch.setenv("THESTUDIO_STORE_BACKEND", "postgres")
        # Settings validator requires a non-placeholder encryption key when store_backend=postgres
        monkeypatch.setenv(
            "THESTUDIO_ENCRYPTION_KEY",
            "xYz1234567890123456789012345678901234567890=",
        )
        from src.settings import Settings

        monkeypatch.setattr("src.admin.store_factory.settings", Settings())
        assert is_postgres_backend() is True

    def test_get_tool_catalog_returns_postgres_impl(self):
        """Factory returns PostgresToolCatalog for a session."""
        from src.admin.persistence.pg_tool_catalog import PostgresToolCatalog

        mock_session = MagicMock(spec=AsyncSession)
        catalog = get_tool_catalog_for_session(mock_session)
        assert isinstance(catalog, PostgresToolCatalog)

    def test_get_model_audit_store_returns_postgres_impl(self):
        """Factory returns PostgresModelAuditStore for a session."""
        from src.admin.persistence.pg_model_audit import PostgresModelAuditStore

        mock_session = MagicMock(spec=AsyncSession)
        store = get_model_audit_store_for_session(mock_session)
        assert isinstance(store, PostgresModelAuditStore)

    def test_get_scorecard_service_returns_postgres_impl(self):
        """Factory returns PostgresComplianceScorecardService for a session."""
        from src.admin.persistence.pg_compliance import PostgresComplianceScorecardService

        mock_session = MagicMock(spec=AsyncSession)
        service = get_scorecard_service_for_session(mock_session)
        assert isinstance(service, PostgresComplianceScorecardService)


# --- In-Memory Store Round-Trip Tests ---
# These test the in-memory implementations that are used when store_backend='memory'


class TestInMemoryToolCatalog:
    """In-memory ToolCatalog write/read round-trip."""

    def test_register_and_get_suite(self):
        from src.admin.tool_catalog import (
            ApprovalStatus,
            CapabilityCategory,
            ToolCatalog,
            ToolEntry,
            ToolSuite,
        )

        catalog = ToolCatalog()
        suite = ToolSuite(
            name="test-suite",
            description="A test suite",
            tools=[
                ToolEntry(
                    name="tool-1",
                    description="A test tool",
                    capability=CapabilityCategory.CODE_QUALITY,
                    read_only=True,
                ),
            ],
            approval_status=ApprovalStatus.OBSERVE,
        )

        catalog.register(suite)
        fetched = catalog.get_suite("test-suite")

        assert fetched.name == "test-suite"
        assert len(fetched.tools) == 1
        assert fetched.tools[0].name == "tool-1"

    def test_list_suites(self):
        from src.admin.tool_catalog import (
            ApprovalStatus,
            ToolCatalog,
            ToolSuite,
        )

        catalog = ToolCatalog()
        for i in range(3):
            catalog.register(
                ToolSuite(
                    name=f"suite-{i}",
                    description=f"Suite {i}",
                    tools=[],
                    approval_status=ApprovalStatus.OBSERVE,
                )
            )

        suites = catalog.list_suites()
        assert len(suites) == 3

    def test_promote_suite(self):
        from src.admin.tool_catalog import (
            ApprovalStatus,
            ToolCatalog,
            ToolSuite,
        )

        catalog = ToolCatalog()
        catalog.register(
            ToolSuite(
                name="promote-me",
                description="Test",
                tools=[],
                approval_status=ApprovalStatus.OBSERVE,
            )
        )

        promoted = catalog.promote_suite("promote-me")
        assert promoted.approval_status == ApprovalStatus.SUGGEST


class TestInMemoryModelGateway:
    """In-memory ModelCallAudit write/read round-trip."""

    def test_record_and_query(self):
        from src.admin.model_gateway import (
            ModelCallAudit,
            InMemoryModelAuditStore,
        )

        store = InMemoryModelAuditStore()
        audit = ModelCallAudit(
            id=uuid4(),
            correlation_id=uuid4(),
            task_id=uuid4(),
            step="intent",
            role="developer",
            overlays=[],
            provider="anthropic",
            model="claude-sonnet-4-5",
            tokens_in=100,
            tokens_out=50,
            cost=0.003,
            latency_ms=1200.0,
            created_at=datetime.now(UTC),
        )

        store.record(audit)
        results = store.query(step="intent")

        assert len(results) == 1
        assert results[0].id == audit.id
        assert results[0].provider == "anthropic"

    def test_query_filters(self):
        from src.admin.model_gateway import ModelCallAudit, InMemoryModelAuditStore

        store = InMemoryModelAuditStore()
        task = uuid4()

        for i, step in enumerate(["intake", "context", "intent"]):
            store.record(
                ModelCallAudit(
                    id=uuid4(),
                    task_id=task,
                    step=step,
                    provider="anthropic",
                    model="claude-sonnet-4-5",
                    tokens_in=10 * (i + 1),
                    tokens_out=5 * (i + 1),
                    cost=0.001 * (i + 1),
                    latency_ms=100.0 * (i + 1),
                    created_at=datetime.now(UTC),
                )
            )

        # Filter by step
        results = store.query(step="intent")
        assert len(results) == 1
        assert results[0].step == "intent"

        # Filter by task_id
        results = store.query(task_id=str(task))
        assert len(results) == 3


class TestComplianceScorecardRoundTrip:
    """Compliance scorecard evaluate and read-back."""

    def test_evaluate_all_passing(self):
        from src.admin.compliance_scorecard import (
            ComplianceScorecard,
            InMemoryComplianceScorecardService,
            RepoComplianceData,
        )

        service = InMemoryComplianceScorecardService()
        data = RepoComplianceData(
            branch_protection_enabled=True,
            required_reviewers_configured=True,
            standard_labels_present=True,
            projects_v2_configured=True,
            evidence_format_valid=True,
            idempotency_guard_active=True,
            execution_plane_healthy=True,
        )

        scorecard = service.evaluate("acme/widgets", data)
        assert scorecard.overall_pass is True
        assert all(c.passed for c in scorecard.checks)

    def test_evaluate_with_failure(self):
        from src.admin.compliance_scorecard import (
            InMemoryComplianceScorecardService,
            RepoComplianceData,
        )

        service = InMemoryComplianceScorecardService()
        data = RepoComplianceData(
            branch_protection_enabled=False,  # Failing check
            required_reviewers_configured=True,
            standard_labels_present=True,
            projects_v2_configured=True,
            evidence_format_valid=True,
            idempotency_guard_active=True,
            execution_plane_healthy=True,
        )

        scorecard = service.evaluate("acme/widgets", data)
        assert scorecard.overall_pass is False
        failed = [c for c in scorecard.checks if not c.passed]
        assert len(failed) == 1
        assert failed[0].name == "branch_protection"
