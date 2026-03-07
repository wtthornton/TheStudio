"""Tests for store configuration switch (Story 8.9)."""

from unittest.mock import MagicMock

import pytest

from src.admin.store_factory import (
    get_model_audit_store_for_session,
    get_scorecard_service_for_session,
    get_tool_catalog_for_session,
    is_postgres_backend,
)


class TestIsPostgresBackend:
    def test_default_is_memory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.admin.store_factory.settings.store_backend", "memory")
        assert is_postgres_backend() is False

    def test_postgres_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.admin.store_factory.settings.store_backend", "postgres")
        assert is_postgres_backend() is True


class TestStoreFactories:
    def test_tool_catalog_factory(self) -> None:
        mock_session = MagicMock()
        catalog = get_tool_catalog_for_session(mock_session)
        from src.admin.persistence.pg_tool_catalog import PostgresToolCatalog
        assert isinstance(catalog, PostgresToolCatalog)

    def test_model_audit_store_factory(self) -> None:
        mock_session = MagicMock()
        store = get_model_audit_store_for_session(mock_session)
        from src.admin.persistence.pg_model_audit import PostgresModelAuditStore
        assert isinstance(store, PostgresModelAuditStore)

    def test_scorecard_service_factory(self) -> None:
        mock_session = MagicMock()
        service = get_scorecard_service_for_session(mock_session)
        from src.admin.persistence.pg_compliance import PostgresComplianceScorecardService
        assert isinstance(service, PostgresComplianceScorecardService)


class TestInMemoryGettersStillWork:
    """Verify the default in-memory getters still work unchanged."""

    def test_tool_catalog_default(self) -> None:
        from src.admin.tool_catalog import get_tool_catalog, InMemoryToolCatalog
        catalog = get_tool_catalog()
        assert isinstance(catalog, InMemoryToolCatalog)

    def test_model_audit_store_default(self) -> None:
        from src.admin.model_gateway import get_model_audit_store, InMemoryModelAuditStore
        store = get_model_audit_store()
        assert isinstance(store, InMemoryModelAuditStore)

    def test_scorecard_service_default(self) -> None:
        from src.admin.compliance_scorecard import get_scorecard_service, InMemoryComplianceScorecardService
        service = get_scorecard_service()
        assert isinstance(service, InMemoryComplianceScorecardService)

    def test_budget_enforcer_default(self) -> None:
        from src.admin.model_gateway import get_budget_enforcer, InMemoryBudgetEnforcer
        enforcer = get_budget_enforcer()
        assert isinstance(enforcer, InMemoryBudgetEnforcer)
