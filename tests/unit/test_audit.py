"""Tests for Story 4.9: Audit Log — Schema, Logging, Query API.

Tests the audit module including:
- AuditEventType enum
- AuditLogRow model
- AuditService methods
- GET /admin/audit endpoint
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.admin.audit import (
    AuditEventType,
    AuditLogCreate,
    AuditLogFilter,
    AuditLogListResult,
    AuditLogRead,
    AuditLogRow,
    AuditService,
    get_audit_service,
    set_audit_service,
)
from src.admin.rbac import (
    ROLE_PERMISSIONS,
    Permission,
    Role,
)
from src.admin.router import (
    AuditLogEntryResponse,
    AuditLogListResponse,
    list_audit_log,
)


class TestAuditEventTypeEnum:
    """Tests for AuditEventType enum."""

    def test_repo_event_types_exist(self) -> None:
        """Repo event types are defined."""
        assert AuditEventType.REPO_REGISTERED.value == "repo_registered"
        assert AuditEventType.REPO_PROFILE_UPDATED.value == "repo_profile_updated"
        assert AuditEventType.REPO_TIER_CHANGED.value == "repo_tier_changed"
        assert AuditEventType.REPO_PAUSED.value == "repo_paused"
        assert AuditEventType.REPO_RESUMED.value == "repo_resumed"
        assert AuditEventType.REPO_WRITES_TOGGLED.value == "repo_writes_toggled"

    def test_workflow_event_types_exist(self) -> None:
        """Workflow event types are defined."""
        assert (
            AuditEventType.WORKFLOW_VERIFICATION_RERUN.value
            == "workflow_verification_rerun"
        )
        assert AuditEventType.WORKFLOW_SENT_TO_AGENT.value == "workflow_sent_to_agent"
        assert AuditEventType.WORKFLOW_ESCALATED.value == "workflow_escalated"

    def test_event_type_count(self) -> None:
        """Nine audit event types are defined."""
        assert len(AuditEventType) == 9


class TestAuditLogModels:
    """Tests for audit log Pydantic models."""

    def test_audit_log_create(self) -> None:
        """AuditLogCreate accepts valid data."""
        create = AuditLogCreate(
            actor="admin@example.com",
            event_type=AuditEventType.REPO_REGISTERED,
            target_id="550e8400-e29b-41d4-a716-446655440000",
            details={"owner": "myorg", "repo": "myrepo"},
        )
        assert create.actor == "admin@example.com"
        assert create.event_type == AuditEventType.REPO_REGISTERED
        assert create.details["owner"] == "myorg"

    def test_audit_log_create_defaults(self) -> None:
        """AuditLogCreate has default details."""
        create = AuditLogCreate(
            actor="admin@example.com",
            event_type=AuditEventType.REPO_PAUSED,
            target_id="test-id",
        )
        assert create.details == {}

    def test_audit_log_filter_defaults(self) -> None:
        """AuditLogFilter has default values."""
        filters = AuditLogFilter()
        assert filters.event_type is None
        assert filters.actor is None
        assert filters.target_id is None
        assert filters.hours is None
        assert filters.limit == 100
        assert filters.offset == 0

    def test_audit_log_filter_with_values(self) -> None:
        """AuditLogFilter accepts filter values."""
        filters = AuditLogFilter(
            event_type=AuditEventType.REPO_REGISTERED,
            actor="admin@example.com",
            target_id="repo-123",
            hours=24,
            limit=50,
            offset=10,
        )
        assert filters.event_type == AuditEventType.REPO_REGISTERED
        assert filters.actor == "admin@example.com"
        assert filters.hours == 24
        assert filters.limit == 50


class TestAuditService:
    """Tests for AuditService."""

    @pytest.fixture
    def service(self) -> AuditService:
        """Create an AuditService instance."""
        return AuditService()

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        session = AsyncMock()
        session.add = MagicMock()  # session.add is synchronous
        return session

    @pytest.mark.asyncio
    async def test_log_event_creates_row(
        self, service: AuditService, mock_session: AsyncMock
    ) -> None:
        """log_event creates an audit log row."""
        result = await service.log_event(
            session=mock_session,
            actor="admin@example.com",
            event_type=AuditEventType.REPO_REGISTERED,
            target_id="550e8400-e29b-41d4-a716-446655440000",
            details={"owner": "myorg", "repo": "myrepo"},
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        assert result.actor == "admin@example.com"
        assert result.event_type == AuditEventType.REPO_REGISTERED

    @pytest.mark.asyncio
    async def test_log_event_with_empty_details(
        self, service: AuditService, mock_session: AsyncMock
    ) -> None:
        """log_event handles empty details."""
        result = await service.log_event(
            session=mock_session,
            actor="admin@example.com",
            event_type=AuditEventType.REPO_PAUSED,
            target_id="repo-123",
            details=None,
        )

        assert result.details == {}

    @pytest.mark.asyncio
    async def test_log_repo_event(
        self, service: AuditService, mock_session: AsyncMock
    ) -> None:
        """log_repo_event logs repo events."""
        repo_id = uuid4()
        result = await service.log_repo_event(
            session=mock_session,
            event_type=AuditEventType.REPO_TIER_CHANGED,
            repo_id=repo_id,
            actor="admin@example.com",
            details={"from_tier": "observe", "to_tier": "suggest"},
        )

        assert result.target_id == str(repo_id)
        assert result.event_type == AuditEventType.REPO_TIER_CHANGED

    @pytest.mark.asyncio
    async def test_log_workflow_event(
        self, service: AuditService, mock_session: AsyncMock
    ) -> None:
        """log_workflow_event logs workflow events."""
        result = await service.log_workflow_event(
            session=mock_session,
            event_type=AuditEventType.WORKFLOW_ESCALATED,
            workflow_id="workflow-abc-123",
            actor="operator@example.com",
            details={"reason": "stuck too long"},
        )

        assert result.target_id == "workflow-abc-123"
        assert result.event_type == AuditEventType.WORKFLOW_ESCALATED

    @pytest.mark.asyncio
    async def test_query_returns_entries(
        self, service: AuditService, mock_session: AsyncMock
    ) -> None:
        """query returns audit log entries."""
        mock_row = MagicMock(spec=AuditLogRow)
        mock_row.id = uuid4()
        mock_row.timestamp = datetime.now(tz=UTC)
        mock_row.actor = "admin@example.com"
        mock_row.event_type = AuditEventType.REPO_REGISTERED
        mock_row.target_id = "repo-123"
        mock_row.details = {"owner": "myorg"}

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_entries_result = MagicMock()
        mock_entries_result.scalars.return_value.all.return_value = [mock_row]

        mock_session.execute.side_effect = [mock_count_result, mock_entries_result]

        result = await service.query(mock_session, AuditLogFilter())

        assert result.total == 1
        assert len(result.entries) == 1
        assert result.entries[0].actor == "admin@example.com"

    @pytest.mark.asyncio
    async def test_query_with_event_type_filter(
        self, service: AuditService, mock_session: AsyncMock
    ) -> None:
        """query applies event_type filter."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_entries_result = MagicMock()
        mock_entries_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_entries_result]

        filters = AuditLogFilter(event_type=AuditEventType.REPO_PAUSED)
        result = await service.query(mock_session, filters)

        assert result.filtered_by["event_type"] == "repo_paused"

    @pytest.mark.asyncio
    async def test_query_with_actor_filter(
        self, service: AuditService, mock_session: AsyncMock
    ) -> None:
        """query applies actor filter."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_entries_result = MagicMock()
        mock_entries_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_entries_result]

        filters = AuditLogFilter(actor="admin@example.com")
        result = await service.query(mock_session, filters)

        assert result.filtered_by["actor"] == "admin@example.com"

    @pytest.mark.asyncio
    async def test_query_with_hours_filter(
        self, service: AuditService, mock_session: AsyncMock
    ) -> None:
        """query applies hours filter."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_entries_result = MagicMock()
        mock_entries_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_entries_result]

        filters = AuditLogFilter(hours=24)
        result = await service.query(mock_session, filters)

        assert result.filtered_by["hours"] == 24

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self, service: AuditService, mock_session: AsyncMock
    ) -> None:
        """get_by_id returns entry when found."""
        audit_id = uuid4()
        mock_row = MagicMock(spec=AuditLogRow)
        mock_row.id = audit_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await service.get_by_id(mock_session, audit_id)

        assert result is not None
        assert result.id == audit_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, service: AuditService, mock_session: AsyncMock
    ) -> None:
        """get_by_id returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.get_by_id(mock_session, uuid4())

        assert result is None


class TestAuditServiceSingleton:
    """Tests for audit service singleton."""

    def test_get_audit_service_returns_service(self) -> None:
        """get_audit_service returns AuditService."""
        set_audit_service(None)
        try:
            service = get_audit_service()
            assert isinstance(service, AuditService)
        finally:
            set_audit_service(None)

    def test_get_audit_service_returns_same_instance(self) -> None:
        """get_audit_service returns same instance."""
        set_audit_service(None)
        try:
            service1 = get_audit_service()
            service2 = get_audit_service()
            assert service1 is service2
        finally:
            set_audit_service(None)

    def test_set_audit_service_overrides(self) -> None:
        """set_audit_service overrides singleton."""
        mock_service = MagicMock(spec=AuditService)
        set_audit_service(mock_service)
        try:
            service = get_audit_service()
            assert service is mock_service
        finally:
            set_audit_service(None)


class TestViewAuditPermission:
    """Tests for VIEW_AUDIT permission."""

    def test_view_audit_permission_exists(self) -> None:
        """VIEW_AUDIT permission is defined."""
        assert Permission.VIEW_AUDIT.value == "view_audit"

    def test_admin_has_view_audit_permission(self) -> None:
        """Admin role has VIEW_AUDIT permission."""
        assert Permission.VIEW_AUDIT in ROLE_PERMISSIONS[Role.ADMIN]

    def test_operator_lacks_view_audit_permission(self) -> None:
        """Operator role lacks VIEW_AUDIT permission."""
        assert Permission.VIEW_AUDIT not in ROLE_PERMISSIONS[Role.OPERATOR]

    def test_viewer_lacks_view_audit_permission(self) -> None:
        """Viewer role lacks VIEW_AUDIT permission."""
        assert Permission.VIEW_AUDIT not in ROLE_PERMISSIONS[Role.VIEWER]


class TestListAuditLogEndpoint:
    """Tests for GET /admin/audit endpoint."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_service(self) -> MagicMock:
        """Create mock audit service."""
        return MagicMock(spec=AuditService)

    @pytest.mark.asyncio
    async def test_list_audit_log_returns_entries(
        self, mock_session: AsyncMock, mock_audit_service: MagicMock
    ) -> None:
        """list_audit_log returns audit entries."""
        entry_id = uuid4()
        mock_result = AuditLogListResult(
            entries=[
                AuditLogRead(
                    id=entry_id,
                    timestamp=datetime.now(tz=UTC),
                    actor="admin@example.com",
                    event_type=AuditEventType.REPO_REGISTERED,
                    target_id="repo-123",
                    details={"owner": "myorg"},
                )
            ],
            total=1,
            filtered_by={},
        )
        mock_audit_service.query = AsyncMock(return_value=mock_result)

        set_audit_service(mock_audit_service)
        try:
            result = await list_audit_log(
                session=mock_session,
                event_type=None,
                actor=None,
                target_id=None,
                hours=None,
                limit=100,
                offset=0,
            )

            assert result.total == 1
            assert len(result.entries) == 1
            assert result.entries[0].actor == "admin@example.com"
        finally:
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_list_audit_log_with_filters(
        self, mock_session: AsyncMock, mock_audit_service: MagicMock
    ) -> None:
        """list_audit_log applies filters."""
        mock_result = AuditLogListResult(
            entries=[],
            total=0,
            filtered_by={"event_type": "repo_paused", "actor": "admin@example.com"},
        )
        mock_audit_service.query = AsyncMock(return_value=mock_result)

        set_audit_service(mock_audit_service)
        try:
            await list_audit_log(
                session=mock_session,
                event_type=AuditEventType.REPO_PAUSED,
                actor="admin@example.com",
                target_id=None,
                hours=24,
                limit=50,
                offset=0,
            )

            mock_audit_service.query.assert_called_once()
            call_args = mock_audit_service.query.call_args
            filters = call_args[0][1]
            assert filters.event_type == AuditEventType.REPO_PAUSED
            assert filters.actor == "admin@example.com"
            assert filters.hours == 24
            assert filters.limit == 50
        finally:
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_list_audit_log_pagination(
        self, mock_session: AsyncMock, mock_audit_service: MagicMock
    ) -> None:
        """list_audit_log supports pagination."""
        mock_result = AuditLogListResult(
            entries=[],
            total=150,
            filtered_by={},
        )
        mock_audit_service.query = AsyncMock(return_value=mock_result)

        set_audit_service(mock_audit_service)
        try:
            await list_audit_log(
                session=mock_session,
                event_type=None,
                actor=None,
                target_id=None,
                hours=None,
                limit=50,
                offset=100,
            )

            call_args = mock_audit_service.query.call_args
            filters = call_args[0][1]
            assert filters.limit == 50
            assert filters.offset == 100
        finally:
            set_audit_service(None)


class TestAuditLogResponseModels:
    """Tests for audit log response models."""

    def test_audit_log_entry_response(self) -> None:
        """AuditLogEntryResponse holds entry data."""
        entry = AuditLogEntryResponse(
            id=uuid4(),
            timestamp=datetime.now(tz=UTC),
            actor="admin@example.com",
            event_type="repo_registered",
            target_id="repo-123",
            details={"owner": "myorg"},
        )
        assert entry.actor == "admin@example.com"
        assert entry.event_type == "repo_registered"

    def test_audit_log_list_response(self) -> None:
        """AuditLogListResponse holds list data."""
        response = AuditLogListResponse(
            entries=[
                AuditLogEntryResponse(
                    id=uuid4(),
                    timestamp=datetime.now(tz=UTC),
                    actor="admin@example.com",
                    event_type="repo_paused",
                    target_id="repo-456",
                    details={},
                )
            ],
            total=1,
            filtered_by={"actor": "admin@example.com"},
        )
        assert response.total == 1
        assert len(response.entries) == 1
        assert response.filtered_by["actor"] == "admin@example.com"
